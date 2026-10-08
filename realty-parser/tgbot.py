"""Управление списком поисков через Telegram: /add, /list, /remove, /help.

Сканер раз в запуск забирает новые сообщения бота и применяет команды от владельца (TG_CHAT_ID).
"""
import json
import os
import re
import urllib.parse
import urllib.request
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

ALLOWED_HOSTS = ("cian.ru", "avito.ru")
MAX_SEARCHES = int(os.getenv("MAX_SEARCHES", "20"))

HELP = (
    "Я слежу за новыми объявлениями на Авито и ЦИАН и присылаю их сюда.\n\n"
    "Команды:\n"
    "/add <ссылка> [название] - добавить поиск. Откройте нужный поиск на сайте "
    "(любой регион и категория, нужные фильтры) и пришлите ссылку из адресной строки.\n"
    "/list - список поисков\n"
    "/remove <номер> - удалить поиск\n\n"
    "Проверка идёт примерно каждые 30 минут, поэтому команды применяются не мгновенно."
)


def api(method, token, **params):
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/{method}", data=data)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def fetch_updates(token, offset):
    res = api("getUpdates", token, offset=offset, timeout=0,
              allowed_updates=json.dumps(["message"]))
    return res.get("result", [])


def normalize_search_url(url):
    """Проверяет сайт и добавляет сортировку «сначала новые», иначе новые объявления можно пропустить."""
    u = urlparse(url)
    host = (u.hostname or "").lower()
    if u.scheme not in ("http", "https") or not any(host == h or host.endswith("." + h) for h in ALLOWED_HOSTS):
        return None
    q = dict(parse_qsl(u.query))
    if "cian.ru" in host and "sort" not in q:
        q["sort"] = "creation_date_desc"
    if "avito.ru" in host and "s" not in q:
        q["s"] = "104"
    return urlunparse(u._replace(query=urlencode(q)))


def auto_name(url):
    u = urlparse(url)
    site = "ЦИАН" if "cian" in u.hostname else "Авито"
    return f"{site}: {u.path.strip('/')[:40] or u.hostname}"


def handle_command(text, searches):
    """Применяет команду к списку searches (изменяет на месте). Возвращает (ответ, изменено_ли)."""
    parts = text.strip().split(maxsplit=1)
    cmd = parts[0].split("@")[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd in ("/start", "/help"):
        return HELP, False

    if cmd == "/list":
        if not searches:
            return "Поисков пока нет. Добавьте: /add <ссылка>", False
        lines = [f"{i}. {s['name']}\n{s['url']}" for i, s in enumerate(searches, 1)]
        return "Ваши поиски:\n\n" + "\n\n".join(lines), False

    if cmd == "/add":
        m = re.search(r"https?://\S+", arg)
        if not m:
            return "Пришлите ссылку на поиск: /add <ссылка> [название]", False
        if len(searches) >= MAX_SEARCHES:
            return f"Достигнут лимит поисков ({MAX_SEARCHES}). Удалите ненужные: /remove <номер>", False
        url = normalize_search_url(m.group(0))
        if not url:
            return "Поддерживаются только ссылки с avito.ru и cian.ru.", False
        if any(s["url"] == url for s in searches):
            return "Такой поиск уже есть, смотрите /list", False
        name = (arg.replace(m.group(0), "").strip()) or auto_name(url)
        searches.append({"name": name, "url": url, "seeded": False})
        return (f"Добавил поиск №{len(searches)}: {name}\n"
                "Объявления, которые уже есть на сайте, я запомню без уведомлений. "
                "Новые пойдут после следующей проверки (до 30 минут)."), True

    if cmd == "/remove":
        if not arg.isdigit() or not (1 <= int(arg) <= len(searches)):
            return "Укажите номер поиска из /list: /remove <номер>", False
        removed = searches.pop(int(arg) - 1)
        return f"Удалил: {removed['name']}", True

    return "Не знаю такую команду. Список команд: /help", False
