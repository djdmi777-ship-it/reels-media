# parsers/telegram.py
import os
import asyncio
from datetime import datetime, timezone, timedelta
from telethon import TelegramClient
from telethon.tl.types import MessageReactions
from config import ALL_CHANNELS, MIN_TELEGRAM_VIEWS, MAX_SOURCE_AGE_HOURS


async def fetch_telegram_posts() -> list[dict]:
    """Парсит посты из Telegram-каналов и возвращает отсортированный список."""
    
    api_id = int(os.getenv("TELEGRAM_API_ID"))
    api_hash = os.getenv("TELEGRAM_API_HASH")
    phone = os.getenv("TELEGRAM_PHONE")

    client = TelegramClient("session_bot", api_id, api_hash)
    posts = []

    async with client:
        if not await client.is_user_authorized():
            await client.send_code_request(phone)
            code = input("Введи код из Telegram: ")
            await client.sign_in(phone, code)

        cutoff = datetime.now(timezone.utc) - timedelta(hours=MAX_SOURCE_AGE_HOURS)

        for channel in ALL_CHANNELS:
            try:
                entity = await client.get_entity(channel)
                
                async for msg in client.iter_messages(entity, limit=20):
                    # Пропускаем старые посты
                    if msg.date < cutoff:
                        break
                    
                    # Пропускаем без текста и с малым охватом
                    if not msg.text or len(msg.text) < 100:
                        continue
                    if msg.views and msg.views < MIN_TELEGRAM_VIEWS:
                        continue

                    # Считаем реакции
                    reactions_count = 0
                    if msg.reactions and isinstance(msg.reactions, MessageReactions):
                        for r in msg.reactions.results:
                            reactions_count += r.count

                    posts.append({
                        "source": "telegram",
                        "channel": channel,
                        "text": msg.text[:2000],  # ограничиваем длину
                        "views": msg.views or 0,
                        "reactions": reactions_count,
                        "date": msg.date,
                        "url": f"https://t.me/{channel}/{msg.id}",
                        # Скор: просмотры + реакции с весом свежести
                        "raw_score": (msg.views or 0) + reactions_count * 10,
                    })

            except Exception as e:
                print(f"⚠️  Ошибка парсинга канала @{channel}: {e}")
                continue

    # Сортируем по скору
    posts.sort(key=lambda x: x["raw_score"], reverse=True)
    print(f"✅ Telegram: найдено {len(posts)} постов")
    return posts
