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
from datetime import datetime, timedelta, timezone
from pathlib import Path

import tgbot
import parser as scraper
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
    token, chats = os.getenv("TG_BOT_TOKEN"), chat_ids()
    if not (token and chats):
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
        chat = str(msg.get("chat", {}).get("id"))
        if chat not in chats or not text.startswith("/"):
            continue  # чужие чаты и обычный текст игнорируем
        reply, ch = tgbot.handle_command(text, searches)
        changed |= ch
        print(f"Команда бота: {text.split()[0]}")
        try:
            send_telegram(reply, chat)
        except Exception as e:
            print(f"Не удалось ответить в Telegram: {str(e)[:100]}", file=sys.stderr)
    if updates:
        save_json(OFFSET, offset)
    return changed


def fingerprint(r):
    """Один и тот же объект часто выставляют несколько агентов под разными ссылками:
    совпадают сайт, цена, площадь и адрес - считаем это повтором."""
    addr = re.sub(r"\W+", "", (r.get("address") or "").lower())
    return "|".join([r.get("source", ""), str(price_num(r.get("price"))), r.get("area_m2", ""), addr])


def price_num(s):
    d = re.sub(r"\D", "", s or "")
    return int(d) if d else None


SITE_NAMES = {"avito": "Авито", "cian": "ЦИАН", "domclick": "Домклик"}


def card(r, search_name="", old_price=None):
    """Карточка объявления (HTML): источник и поиск, цена крупно, параметры, адрес."""
    from html import escape
    src = SITE_NAMES.get(r.get("source"), r.get("source", ""))
    name = search_name.split(":", 1)[-1].strip() if search_name else ""
    name = name[:1].upper() + name[1:]
    head = f"{'💸' if old_price else '🆕'} <b>{escape(src)}{' · ' + escape(name) if name else ''}</b>"
    price = f"<b>{escape(r['price'])}</b>" if r.get("price") else "цена не указана"
    n, a = price_num(r.get("price")), r.get("area_m2")
    try:
        if n and a and float(a) > 0 and "сот" not in (r.get("title") or ""):
            price += f"  ·  {round(n / float(a)):,} ₽/м²".replace(",", " ")
    except ValueError:
        pass
    lines = [head]
    if old_price:
        o = price_num(old_price)
        diff = f" ({(n - o) / o:+.0%})" if n and o else ""
        lines.append(f"Цена изменилась: было {escape(old_price)} → стало {price}{diff}")
    else:
        lines.append(price)
    details = r.get("title") or " · ".join(x for x in (
        f"{r['rooms']}-комн." if r.get("rooms") else "", f"{r['area_m2']} м²" if r.get("area_m2") else "",
        f"{r['floor']} эт." if r.get("floor") else "") if x)
    if details:
        lines.append(escape(details))
    if r.get("address"):
        lines.append("📍 " + escape(r["address"]))
    return "\n".join(lines)


def send_cards(items):
    """items: [(row, search_name, old_price|None)] - по сообщению на объявление с кнопкой."""
    import time
    for r, name, old in items:
        try:
            send_telegram(card(r, name, old), button=("Открыть объявление", r["url"]), html=True)
        except Exception as e:
            print(f"Не удалось отправить карточку: {str(e)[:100]}", file=sys.stderr)
        time.sleep(0.5)  # Telegram ограничивает частоту сообщений в один чат


HEALTH = STATE.parent / "health.json"


def check_health(searches_active, rows, now):
    """Владельцу (TG_CHAT_ID): «⚠️ Авито не отвечает уже 2 часа» и «✅ снова работает».
    Сбой = ни одного объявления с сайта за проверку; тревога после 2 часов и 3 проверок подряд."""
    owner = os.getenv("TG_CHAT_ID")
    hours = float(os.getenv("ALERT_HOURS", "2"))
    health = json.loads(HEALTH.read_text()) if HEALTH.exists() else {}
    got = {r.get("source") or scraper.detect_site(r.get("search") or r["url"]) for r in rows}
    for site in {scraper.detect_site(x["url"]) for x in searches_active}:
        h = health.setdefault(site, {})
        if site in got:
            if h.get("alerted") and owner:
                send_telegram(f"✅ {SITE_NAMES.get(site, site)} снова работает.", owner)
            health[site] = {"last_ok": now.isoformat(timespec="seconds")}
            continue
        h.setdefault("first_fail", now.isoformat(timespec="seconds"))
        h["fails"] = h.get("fails", 0) + 1
        down = (now - datetime.fromisoformat(h["first_fail"])).total_seconds() / 3600
        if owner and not h.get("alerted") and down >= hours and h["fails"] >= 3:
            send_telegram(f"⚠️ {SITE_NAMES.get(site, site)} не отвечает уже {down:.0f} ч "
                          f"({h['fails']} проверок подряд без объявлений). Проверьте прокси.", owner)
            h["alerted"] = True
    save_json(HEALTH, health)


def fmt(r, prefix=""):
    bits = [b for b in (r["price"], r["title"], r["address"]) if b]
    return f"{prefix}{' | '.join(bits)}\n{r['url']}"


def chat_ids():
    """Получатели: TG_CHAT_ID и дополнительные TG_EXTRA_CHAT_IDS (через запятую)."""
    raw = ",".join([os.getenv("TG_CHAT_ID") or "", os.getenv("TG_EXTRA_CHAT_IDS") or ""])
    return list(dict.fromkeys(c.strip() for c in raw.split(",") if c.strip()))


def send_telegram(text, chat=None, button=None, html=False):
    """Отправляет в один чат (chat) или всем получателям. Ошибка одного чата не мешает остальным
    (например, если человек ещё не нажал /start у бота)."""
    token, chats = os.getenv("TG_BOT_TOKEN"), [chat] if chat else chat_ids()
    if not (token and chats):
        print("Telegram не настроен (TG_BOT_TOKEN / TG_CHAT_ID), пропускаю отправку.")
        return False
    ok = False
    for c in chats:
        params = {"chat_id": c, "text": text, "disable_web_page_preview": "true"}
        if html:
            params["parse_mode"] = "HTML"
        if button:  # (подпись, ссылка) - кнопка под сообщением
            params["reply_markup"] = json.dumps({"inline_keyboard": [[{"text": button[0], "url": button[1]}]]})
        data = urllib.parse.urlencode(params).encode()
        req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                ok |= resp.status == 200
        except Exception as e:
            print(f"Не удалось отправить в чат ...{str(c)[-3:]}: {str(e)[:80]} "
                  "(получатель должен сначала написать боту /start)", file=sys.stderr)
    return ok


def notify(blocks, chat=None):
    """Собирает блоки в сообщения до ~3500 символов и отправляет (всем или в один чат)."""
    msg = ""
    for b in blocks:
        if msg and len(msg) + len(b) > 3500:
            send_telegram(msg, chat)
            msg = ""
        msg += b + "\n\n"
    if msg:
        send_telegram(msg.strip(), chat)


REPLAY_DONE = STATE.parent / "replay_done.json"


def replay_today(seen):
    """Разово дублирует новому получателю (REPLAY_TO) объявления, присланные сегодня (с 00:00 МСК).
    Пачки, записанные «тихо» при подключении поиска (20+ объявлений за раз), пропускаются;
    повторы по ссылке и по объекту (цена+площадь+адрес) убираются."""
    chat = os.getenv("REPLAY_TO")
    done = json.loads(REPLAY_DONE.read_text()) if REPLAY_DONE.exists() else []
    if not chat or chat in done:
        return
    since = datetime.now(timezone(timedelta(hours=3))).replace(hour=0, minute=0, second=0,
                                                              microsecond=0).astimezone(timezone.utc)
    today = {u: v for u, v in seen.items()
             if v.get("first_seen") and datetime.fromisoformat(v["first_seen"]) >= since}
    batch = {}
    for v in today.values():
        batch[v["first_seen"]] = batch.get(v["first_seen"], 0) + 1
    picked, fps = [], set()
    for u, v in sorted(today.items(), key=lambda kv: kv[1]["first_seen"]):
        if v.get("notified") is False or (v.get("notified") is None and batch[v["first_seen"]] >= 20):
            continue
        if v.get("fp") and v["fp"] in fps:
            continue
        fps.add(v.get("fp"))
        picked.append(fmt({"price": v.get("price", ""), "title": v.get("title", ""),
                           "address": v.get("address", ""), "url": u}, "🆕 "))
    print(f"Дубль за сегодня для нового получателя: {len(picked)} объявлений")
    if picked:
        notify([f"Объявления за сегодня ({len(picked)} шт.), дальше будут приходить новые:"] + picked, chat)
    save_json(REPLAY_DONE, done + [chat])


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
    rot = os.getenv("AVITO_PROXY_ROTATE_URL")
    if rot:
        ok = rot.startswith("https://") and "@" not in rot.split("/")[2]
        print("Ссылка смены IP:", f"задана ({urllib.parse.urlparse(rot).hostname})" if ok
              else "ошибка - это не ссылка смены IP (должна начинаться с https:// и быть без логина)")
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
        if not a.dry_run:
            check_health(active, rows, datetime.now(timezone.utc))
        return 1

    seen = json.loads(STATE.read_text()) if STATE.exists() else {}
    fps = {v.get("fp") for v in seen.values() if v.get("fp")}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    seeded = {s["url"] for s in searches if s.get("seeded")}

    new, changed, quiet, dupes, stale = [], [], 0, 0, 0
    for r in rows:  # отпечатки для уже известных ссылок (база старше этой проверки)
        old = seen.get(r["url"])
        if old is not None and not old.get("address"):
            old["address"] = r.get("address", "")
        if old is not None and not old.get("fp") and price_num(r["price"]) and r.get("address"):
            old["fp"] = fingerprint(r)
            fps.add(old["fp"])
    if not a.dry_run:
        replay_today(seen)  # до новых находок этой проверки: их новый получатель получит обычным порядком
    for r in rows:
        old = seen.get(r["url"])
        if old is None:
            fp = fingerprint(r) if price_num(r["price"]) and r.get("address") else None
            seen[r["url"]] = {"first_seen": now, "price": r["price"], "title": r["title"], "fp": fp,
                              "address": r.get("address", ""), "notified": False}
            was_dupe = bool(fp and fp in fps)
            if fp:
                fps.add(fp)
            if was_dupe:
                dupes += 1  # тот же объект под другой ссылкой - не дублируем уведомление
            elif r.get("posted") == "old":
                stale += 1  # старое объявление впервые попало в выдачу (поднято, VIP) - не новое
            elif r["search"] in seeded:
                new.append(r)
                seen[r["url"]]["notified"] = True
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
               f"цена изменилась {len(changed)}, запомнено без уведомления {quiet}, повторов объекта {dupes}, старых (не сегодня) {stale}")
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

    if os.getenv("TECH_REPORT") == "1" and os.getenv("TG_CHAT_ID"):
        # техотчёт только владельцу (TG_CHAT_ID): видно ход теста без логов GitHub
        by = {}
        for r in rows:
            by[r["source"]] = by.get(r["source"], 0) + 1
        mb = scraper.LAST_TRAFFIC
        parts = [f"{k}: {by.get(k, 0)} объявл., {mb.get(k, 0):.1f} МБ" for k in sorted(set(by) | set(mb))]
        tz = timezone(timedelta(hours=3))
        try:
            send_telegram(f"⚙️ {datetime.now(tz):%H:%M} проверка: " + "; ".join(parts)
                          + f". Новых {len(new)}, повторов отсеяно {dupes}, старых отсеяно {stale}"
                          + (f". Проблемы: {'; '.join(failures)[:300]}" if failures else ""),
                          os.environ["TG_CHAT_ID"])
        except Exception as e:
            print(f"Техотчёт не отправлен: {e}")
    names = {x["url"]: x["name"] for x in searches}
    if new or changed:
        send_cards([(r, names.get(r["search"], ""), None) for r in new]
                   + [(r, names.get(r["search"], ""), old) for r, old in changed])
    check_health(active, rows, datetime.now(timezone.utc))
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
