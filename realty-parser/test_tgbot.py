"""Проверка команд бота и логики сканера без сети: python test_tgbot.py"""
import json
import os
import sys
import tempfile
from pathlib import Path

tmp = Path(tempfile.mkdtemp())
os.environ.update(STATE_FILE=str(tmp / "seen.json"), TG_BOT_TOKEN="test", TG_CHAT_ID="42")
os.environ.pop("CI", None)

import scanner  # noqa: E402
import tgbot  # noqa: E402

# --- команды ---
s = []
r, ch = tgbot.handle_command("/add https://www.avito.ru/sochi/kvartiry/prodam Сочи квартиры", s)
assert ch and s[0]["name"] == "Сочи квартиры" and "s=104" in s[0]["url"], (r, s)
r, ch = tgbot.handle_command("/add@my_bot https://anapa.cian.ru/kupit-dom/", s)
assert ch and "sort=creation_date_desc" in s[1]["url"] and s[1]["name"].startswith("ЦИАН"), s
assert not tgbot.handle_command("/add https://www.avito.ru/sochi/kvartiry/prodam", s)[1]  # дубль
assert not tgbot.handle_command("/add https://example.com/x", s)[1]                       # чужой сайт
assert not tgbot.handle_command("/add", s)[1]
assert "1. Сочи квартиры" in tgbot.handle_command("/list", s)[0]
assert not tgbot.handle_command("/remove 9", s)[1]
assert tgbot.handle_command("/remove 1", s)[1] and len(s) == 1
assert "/add" in tgbot.handle_command("/start", s)[0]
assert "Не знаю" in tgbot.handle_command("/foo", s)[0]
tgbot.MAX_SEARCHES = 1
assert "лимит" in tgbot.handle_command("/add https://www.avito.ru/a/b", s)[0]
tgbot.MAX_SEARCHES = 20

# --- обработка сообщений: только владелец, offset сохраняется ---
sent = []
scanner.send_telegram = lambda text, chat=None: sent.append(text) or True
tgbot.fetch_updates = lambda token, offset: [
    {"update_id": 10, "message": {"chat": {"id": 42}, "text": "/add https://www.avito.ru/anapa/doma"}},
    {"update_id": 11, "message": {"chat": {"id": 999}, "text": "/remove 1"}},   # чужой чат
    {"update_id": 12, "message": {"chat": {"id": 42}, "text": "привет"}},        # не команда
]
searches = [{"name": "ЦИАН", "url": "https://anapa.cian.ru/kupit-dom/?sort=creation_date_desc", "seeded": True}]
assert scanner.process_commands(searches) and len(searches) == 2 and len(sent) == 1
assert json.loads((tmp / "tg_offset.json").read_text()) == 13

# --- сканирование: новый поиск первый раз тихий, старый уведомляет ---
avito = searches[1]["url"]
cian = searches[0]["url"]
def fake_rows(urls, pages):
    rows = [{"url": f"https://x/{i}", "price": "1 ₽", "title": f"t{i}", "address": "", "search": u}
            for i, u in enumerate(urls)]
    return rows, []
scanner.scrape = fake_rows
scanner.save = lambda rows, path: None
scanner.SEARCH_STATE.write_text(json.dumps(searches, ensure_ascii=False))
tgbot.fetch_updates = lambda token, offset: []
notified = []
scanner.notify = lambda blocks: notified.extend(blocks)
sent.clear()
sys.argv = ["scanner.py"]
assert scanner.main() == 0
assert len(notified) == 1 and "t0" in notified[0], notified        # ЦИАН (seeded) -> уведомление
assert any("подключён" in m for m in sent), sent                     # Авито -> тихо + сообщение
saved = json.loads(scanner.SEARCH_STATE.read_text())
assert all(x["seeded"] for x in saved)

# --- Авито по кругу: по одному поиску за запуск ---
os.environ["AVITO_PER_RUN"] = "1"
three = [{"name": f"A{i}", "url": f"https://www.avito.ru/x{i}?s=104", "seeded": True} for i in range(3)]
scanner.SEARCH_STATE.write_text(json.dumps(three))
seen_urls = []
scanner.scrape = lambda urls, pages: (seen_urls.append(list(urls)) or fake_rows(urls, pages))
for _ in range(4):
    assert scanner.main() == 0
assert [u_[0].split("/")[-1] for u_ in seen_urls] == ["x0?s=104", "x1?s=104", "x2?s=104", "x0?s=104"], seen_urls

print("Все проверки пройдены")
