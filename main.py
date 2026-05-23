#!/usr/bin/env python3
import os
import schedule
import time
from dotenv import load_dotenv

load_dotenv()

from parsers.rss import fetch_rss_posts
from scorer import score_posts
from rewriter import rewrite_all
from notion_uploader import upload_to_notion
from prompt_generator import run_prompt_generator


def run_pipeline():
    """Основной пайплайн: RSS → скоринг → Claude → Notion."""
    print("\n" + "="*50)
    print("🚀 Запуск пайплайна...")
    print("="*50)

    print("\n📡 Шаг 1: Парсинг RSS-лент...")
    posts = fetch_rss_posts()
    print(f"   Всего найдено: {len(posts)} постов")

    if not posts:
        print("❌ Нет постов для обработки.")
        return

    print("\n📊 Шаг 2: Отбор топ-постов...")
    top_posts = score_posts(posts)

    if not top_posts:
        print("❌ Нет постов после скоринга.")
        return

    print("\n✍️  Шаг 3: Переписывание через Claude...")
    rewritten = rewrite_all(top_posts)

    print("\n📝 Шаг 4: Загрузка в Notion...")
    upload_to_notion(rewritten)

    print("\n" + "="*50)
    print(f"✅ Готово! Создано {len(rewritten)} постов в Notion.")
    print("="*50 + "\n")


def run():
    run_pipeline()
    run_prompt_generator()


if __name__ == "__main__":
    import sys

    if "--now" in sys.argv:
        run()
    elif "--prompts" in sys.argv:
        run_prompt_generator()
    else:
        hour = int(os.getenv("RUN_HOUR", 8))
        minute = int(os.getenv("RUN_MINUTE", 0))
        run_time = f"{hour:02d}:{minute:02d}"

        print(f"⏰ Бот запущен. Ежедневный запуск в {run_time} (UTC)")
        print("   Для немедленного запуска:  python main.py --now")
        print("   Только промпты:            python main.py --prompts")

        schedule.every().day.at(run_time).do(run)

        while True:
            schedule.run_pending()
            time.sleep(30)
