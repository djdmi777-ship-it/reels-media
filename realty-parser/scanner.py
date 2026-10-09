"""Сканер новых объявлений: сравнивает выдачу с базой виденных ссылок и сообщает о новых.

  python scanner.py            # обычный запуск (cron / GitHub Actions каждые 30 минут)
  python scanner.py --dry-run  # ничего не сохранять и не отправлять

Новый поиск (и самый первый запуск) сканируется «тихо»: объявления запоминаются без уведомлений.
Список поисков меняется командами Telegram-бота (/add, /list, /remove), см. tgbot.py.
Настройки: переменные окружения или файл .env рядом со скриптом:
  TG_BOT_TOKEN, TG_CHAT_ID - Telegram; AVITO_PROXY_URL - прокси для Авито.
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

import tgbot
from parser import parse_proxy, save, scrape

HERE = Path(__file__).parent
STATE = Path(os.getenv("STATE_FILE", HERE / "state" / "seen.json"))
SEARCHES = Path(os.getenv("SEARCHES_FILE", HERE / "searches.json"))  # стартовый список
SEARCH_STATE = STATE.parent / "searches.json"  # актуальный список, меняется командами бота
OFFSET = STATE.parent / "tg_offset.json"
AVITO_RR = STATE.parent / "avito_rr.json"  # чей черёд среди поисков Авито


def load_dotenv(path=HERE / ".env"):
    """Мини-загрузчик .env: KEY=value, переменные окружения имеют приоритет."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def avito_proxy_ready():
    """Диагностика в логе: адрес прокси и его выходной IP. На сам Авито здесь не ходим:
    запрос не из браузера выдаёт бота и может «испортить» IP перед настоящей проверкой."""
    from urllib.parse import urlparse
    raw = os.getenv("AVITO_PROXY_URL")
    if not raw:
        return False
    u = urlparse(raw)
    print(f"Прокси: {u.hostname}:{u.port}")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({"https": raw, "http": raw}))
    try:
        info = json.load(opener.open("https://ipinfo.io/json", timeout=25))
        print(f"Выходной адрес: {info.get('ip')} | {info.get('org')} | {info.get('country')} {info.get('city')}")
    except Exception as e:
        print(f"Не удалось определить адрес прокси: {str(e)[:80]}")
    return False


def load_searches():
    if SEARCH_STATE.exists():
        return json.loads(SEARCH_STATE.read_text(encoding="utf-8"))
    seed = json.loads(SEARCHES.read_text(encoding="utf-8"))
    return [{"name": s["name"], "url": s["url"], "seeded": False} for s in seed]


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def process_commands(searches):
    """Применяет команды владельца бота к списку поисков. Возвращает True, если список изменился."""
    token, chat = os.getenv("TG_BOT_TOKEN"), os.getenv("TG_CHAT_ID")
    if not (token and chat):
        return False
    offset = int(OFFSET.read_text()) if OFFSET.exists() else 0
    try:
        updates = tgbot.fetch_updates(token, offset)
    except Exception as e:  # сеть или Telegram недоступны - сканируем как есть
        print(f"Не удалось получить команды бота: {str(e)[:100]}", file=sys.stderr)
        return False
    changed = False
    for u in updates:
        offset = max(offset, u["update_id"] + 1)
        msg = u.get("message") or {}
        text = (msg.get("text") or "").strip()
        if str(msg.get("chat", {}).get("id")) != str(chat) or not text.startswith("/"):
            continue  # чужие чаты и обычный текст игнорируем
        reply, ch = tgbot.handle_command(text, searches)
        changed |= ch
        print(f"Команда бота: {text.split()[0]}")
        try:
            send_telegram(reply)
        except Exception as e:
            print(f"Не удалось ответить в Telegram: {str(e)[:100]}", file=sys.stderr)
    if updates:
        save_json(OFFSET, offset)
    return changed


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
    load_dotenv()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--pages", type=int, default=int(os.getenv("SEARCH_PAGES", "1")))
    a = ap.parse_args()

    searches = load_searches()
    if not a.dry_run:
        process_commands(searches)
        save_json(SEARCH_STATE, searches)  # сохраняем сразу: команды не потеряются, даже если сканирование упадёт

    if os.getenv("AVITO_PROXY_URL"):
        try:
            parse_proxy(os.environ["AVITO_PROXY_URL"])
        except ValueError as e:
            print(f"Ошибка настройки: {e}. Авито в этом запуске пропускаю.", file=sys.stderr)
            del os.environ["AVITO_PROXY_URL"]
    avito_ok = True  # решает браузер: он сам пробует, меняет IP и повторяет (см. parser.scrape)
    if os.getenv("AVITO_PROXY_URL") and any("avito" in x["url"] for x in searches):
        avito_proxy_ready()  # только диагностика в логе: адрес и ответ Авито на обычный запрос
    print("Прокси для Авито:", "задан" if os.getenv("AVITO_PROXY_URL") else "НЕ задан",
          "| Telegram:", "задан" if os.getenv("TG_BOT_TOKEN") and os.getenv("TG_CHAT_ID") else "НЕ задан")
    active = searches
    if not avito_ok:
        print("Авито через прокси сейчас недоступен - пропускаю Авито в этом запуске (трафик не тратим)")
        active = [x for x in active if "avito" not in x["url"]]
    if os.getenv("CI") and not os.getenv("AVITO_PROXY_URL"):
        active = [s for s in searches if "avito" not in s["url"]]
        if len(active) != len(searches):
            print("CI без AVITO_PROXY_URL: пропускаю поиски Авито")
    # Авито блокирует IP после 1-2 запросов подряд, поэтому за запуск проверяем AVITO_PER_RUN
    # поисков Авито по кругу (остальные - в следующих запусках)
    per_run = int(os.getenv("AVITO_PER_RUN", "1"))
    avito = [s for s in active if "avito" in s["url"]]
    if per_run > 0 and len(avito) > per_run:
        rr = int(AVITO_RR.read_text()) if AVITO_RR.exists() else 0
        pick = [avito[(rr + i) % len(avito)] for i in range(per_run)]
        active = [s for s in active if "avito" not in s["url"]] + pick
        print("Авито в этом запуске:", ", ".join(s["name"] for s in pick))
        if not a.dry_run:
            save_json(AVITO_RR, (rr + per_run) % len(avito))
    if not active:
        print("Поисков нет - нечего сканировать.")
        return 0

    rows, failures = scrape([s["url"] for s in active], a.pages)
    print(f"Получено объявлений: {len(rows)}; проблем: {len(failures)}")
    for f in failures:
        print("  !", f, file=sys.stderr)
    if not rows:
        print("Ни одного объявления не получено - базу не трогаю.", file=sys.stderr)
        return 1

    seen = json.loads(STATE.read_text()) if STATE.exists() else {}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    seeded = {s["url"] for s in searches if s.get("seeded")}

    new, changed, quiet = [], [], 0
    for r in rows:
        old = seen.get(r["url"])
        if old is None:
            seen[r["url"]] = {"first_seen": now, "price": r["price"], "title": r["title"]}
            if r["search"] in seeded:
                new.append(r)
            else:
                quiet += 1  # первый проход нового поиска: запоминаем без уведомления
        else:
            o, n = price_num(old.get("price")), price_num(r["price"])
            if o and n and o != n:
                changed.append((r, old["price"]))
                old["price"] = r["price"]

    found_in = {r["search"] for r in rows}
    newly_seeded = [s for s in searches if not s.get("seeded") and s["url"] in found_in]
    for s in newly_seeded:
        s["seeded"] = True

    summary = (f"Сканирование: {len(rows)} в выдаче, новых {len(new)}, "
               f"цена изменилась {len(changed)}, запомнено без уведомления {quiet}")
    print(summary)
    if new:
        save(new, str(HERE / "new_listings.csv"))

    if a.dry_run:
        print("--dry-run: состояние и уведомления пропущены.")
        for r in (new or rows)[:5]:
            print(fmt(r, "NEW "))
        return 0

    save_json(STATE, seen)
    save_json(SEARCH_STATE, searches)

    if new or changed:
        notify([fmt(r, "🆕 ") for r in new] + [fmt(r, f"💸 было {old} -> ") for r, old in changed])
    for s in newly_seeded:
        send_telegram(f"Поиск «{s['name']}» подключён: запомнил текущие объявления, "
                      "дальше пришлю только новые.")

    out = os.getenv("GITHUB_STEP_SUMMARY")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write("### " + summary + "\n")
            for r in new[:30]:
                f.write(f"- {r['price']} - [{r['title'] or r['url']}]({r['url']}) {r['address']}\n")
            for x in failures:
                f.write(f"- ⚠️ {x}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
