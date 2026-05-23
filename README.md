# 🤖 AI Content Bot

Автоматический сбор и переписывание AI-контента из Telegram и Reddit в Notion.

## Как работает

```
Telegram-каналы ──┐
                   ├──► Скоринг ──► Claude переписывает ──► Notion
Reddit             ──┘
```

Каждое утро бот:
1. Парсит посты из 9 Telegram-каналов (RU + EN) за последние 24 часа
2. Парсит топ-посты из 4 сабреддитов
3. Отбирает топ-3 по охвату, реакциям и свежести
4. Переписывает их через Claude в стиле блога для широкой аудитории
5. Сохраняет в Notion со статусом «Draft»

---

## Установка

### 1. Клонировать и установить зависимости

```bash
git clone <repo>
cd ai-content-bot
pip install -r requirements.txt
```

### 2. Настроить API-ключи

```bash
cp .env.example .env
```

Открой `.env` и заполни все переменные:

#### Telegram API
1. Зайди на https://my.telegram.org
2. Войди с номером телефона → «API development tools»
3. Создай приложение, скопируй `api_id` и `api_hash`

#### Reddit API
1. Зайди на https://reddit.com/prefs/apps
2. «Create another app» → тип **script**
3. Название: ai-content-bot, redirect URI: http://localhost
4. Скопируй `client_id` (под названием) и `client_secret`

#### Anthropic API
Возьми ключ с https://console.anthropic.com

#### Notion
1. Зайди на https://notion.so/my-integrations → «New integration»
2. Скопируй токен
3. Создай базу данных со следующими полями:

| Поле        | Тип       |
|-------------|-----------|
| Title       | Title     |
| Status      | Select    |
| Source      | Select    |
| Channel     | Rich text |
| OriginalURL | URL       |
| Score       | Number    |
| CreatedAt   | Date      |

4. Открой базу данных → «Share» → добавь свою интеграцию
5. Скопируй ID из URL (32 символа после последнего `/`)

---

### 3. Настроить каналы (опционально)

В `config.py` можно изменить список каналов:
```python
TELEGRAM_CHANNELS_RU = ["channel_username", ...]
TELEGRAM_CHANNELS_EN = ["channel_username", ...]
```

---

## Запуск

### Немедленно (для теста)
```bash
python main.py --now
```

### По расписанию каждое утро
```bash
python main.py
```
Время задаётся в `.env` через `RUN_HOUR` и `RUN_MINUTE` (UTC).

### Через Claude Code
```bash
cd ai-content-bot
python main.py --now
```

---

## Структура проекта

```
ai-content-bot/
├── .env.example          # шаблон переменных окружения
├── config.py             # каналы, пороги, стиль блога
├── main.py               # точка входа + планировщик
├── scorer.py             # скоринг и отбор постов
├── rewriter.py           # переписывание через Claude
├── notion_uploader.py    # загрузка в Notion
├── parsers/
│   ├── telegram.py       # парсинг Telegram
│   └── reddit.py         # парсинг Reddit
└── requirements.txt
```

---

## Настройка стиля

В `config.py` → `BLOG_STYLE_PROMPT` — промпт для Claude.
Можно полностью переписать под свой голос.

---

## FAQ

**Q: При первом запуске Telegram просит код — это нормально?**
A: Да, один раз. Потом сессия сохраняется в `session_bot.session`.

**Q: Можно добавить свои Telegram-каналы?**
A: Да, в `config.py` → `TELEGRAM_CHANNELS_RU` или `TELEGRAM_CHANNELS_EN`.

**Q: Как автоматически запускать на сервере?**
A: Используй `cron` или `systemd`. Пример cron на 8:00 МСК (05:00 UTC):
```
0 5 * * * cd /path/to/ai-content-bot && python main.py --now >> logs/bot.log 2>&1
```
