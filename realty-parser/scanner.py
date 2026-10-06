"""Сканер новых объявлений: сравнивает выдачу с базой виденных ссылок и сообщает о новых.

  python scanner.py            # обычный запуск (cron / GitHub Actions каждые 30 минут)
  python scanner.py --dry-run  # ничего не сохранять и не отправлять

Первый запуск (пустая база) только запоминает текущие объявления, без уведомлений.
Telegram: переменные TG_BOT_TOKEN и TG_CHAT_ID (если не заданы - уведомление пропускается).
"""
import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from parser import FIELDS, save, scrape

HERE = Path(__file__).parent
STATE = Path(os.getenv("STATE_FILE", HERE / "state" / "seen.json"))
SEARCHES = Path(os.getenv("SEARCHES_FILE", HERE / "searches.json"))


def price_num(s):
    d = re.sub(r"\D", "", s or "")
    return int(d) if d else None


def fmt(r, prefix=""):
    bits = [b for b in (r["price"], r["title"], r["address"]) if b]
    return f"{prefix}{' | '.join(bits)}\n{r['url']}"


def send_telegram(text):
    token, chat = os.getenv("TG_BOT_TOKEN"), os.getenv("TG_CHAT_ID")
    if not (token and chat):
        print("Telegram не настроен (TG_BOT_TOKEN / TG_CHAT_ID), пропускаю отправку.")
        return False
    data = urllib.parse.urlencode({"chat_id": chat, "text": text,
                                   "disable_web_page_preview": "true"}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status == 200


def notify(blocks):
    """Собирает блоки в сообщения до ~3500 символов и отправляет."""
    msg = ""
    for b in blocks:
        if msg and len(msg) + len(b) > 3500:
            send_telegram(msg)
            msg = ""
        msg += b + "\n\n"
    if msg:
        send_telegram(msg.strip())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--pages", type=int, default=int(os.getenv("SEARCH_PAGES", "2")))
    a = ap.parse_args()

    searches = json.loads(SEARCHES.read_text(encoding="utf-8"))
    if os.getenv("CI") and not os.getenv("AVITO_PROXY_URL"):
        skipped = [s["name"] for s in searches if "avito" in s["url"]]
        searches = [s for s in searches if "avito" not in s["url"]]
        if skipped:
            print("CI без AVITO_PROXY_URL: пропускаю Авито (", ", ".join(skipped), ")")
    rows, failures = scrape([s["url"] for s in searches], a.pages)
    print(f"Получено объявлений: {len(rows)}; проблем: {len(failures)}")
    for f in failures:
        print("  !", f, file=sys.stderr)
    if not rows:
        print("Ни одного объявления не получено - состояние не трогаю.", file=sys.stderr)
        return 1

    seen = json.loads(STATE.read_text()) if STATE.exists() else None
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    first_run = seen is None
    seen = seen or {}

    new, changed = [], []
    for r in rows:
        old = seen.get(r["url"])
        if old is None:
            new.append(r)
            seen[r["url"]] = {"first_seen": now, "price": r["price"], "title": r["title"]}
        else:
            o, n = price_num(old.get("price")), price_num(r["price"])
            if o and n and o != n:
                changed.append((r, old["price"]))
                old["price"] = r["price"]

    summary = [f"Сканирование: {len(rows)} в выдаче, новых {len(new)}, цена изменилась {len(changed)}"
               + (" (первый запуск: база заполнена без уведомлений)" if first_run else "")]
    if new and not first_run:
        save(new, str(HERE / "new_listings.csv"))
    print("\n".join(summary))

    if a.dry_run:
        print("--dry-run: состояние и уведомления пропущены.")
        for r in new[:5]:
            print(fmt(r, "NEW "))
        return 0

    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(seen, ensure_ascii=False))

    if not first_run and (new or changed):
        blocks = [fmt(r, "🆕 ") for r in new] + [fmt(r, f"💸 было {old} -> ") for r, old in changed]
        notify(blocks)
    if first_run:
        send_telegram(f"Сканер Анапы запущен. В базе {len(seen)} объявлений, дальше пришлю только новые.") \
            if os.getenv("TG_BOT_TOKEN") else None

    out = os.getenv("GITHUB_STEP_SUMMARY")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write("### " + summary[0] + "\n")
            for r in new[:30]:
                f.write(f"- {r['price']} - [{r['title'] or r['url']}]({r['url']}) {r['address']}\n")
            for x in failures:
                f.write(f"- ⚠️ {x}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
