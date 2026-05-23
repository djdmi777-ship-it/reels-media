# notion_uploader.py — загружает готовые посты в Notion
import os
from datetime import datetime
from notion_client import Client


def upload_to_notion(posts: list[dict]) -> None:
    """
    Создаёт страницы в Notion для каждого готового поста.
    
    Структура базы данных Notion (создай вручную):
    - Title        (title)     — заголовок поста
    - Status       (select)    — Draft / Ready / Published
    - Source       (select)    — telegram / reddit
    - Channel      (rich_text) — название канала/сабреддита
    - OriginalURL  (url)       — ссылка на оригинал
    - Score        (number)    — итоговый скор
    - CreatedAt    (date)      — дата генерации
    - Content      (содержимое страницы)
    """
    notion = Client(auth=os.getenv("NOTION_TOKEN"))
    db_id = os.getenv("NOTION_DATABASE_ID")

    for post in posts:
        try:
            # Первая строка — заголовок поста
            lines = post["rewritten_text"].split("\n")
            title = lines[0].strip().lstrip("#").strip()
            if len(title) > 100:
                title = title[:97] + "..."

            body = "\n".join(lines[1:]).strip()

            notion.pages.create(
                parent={"database_id": db_id},
                properties={
                    "Title": {
                        "title": [{"text": {"content": title}}]
                    },
                    "Status": {
                        "select": {"name": "Draft"}
                    },
                    "Source": {
                        "select": {"name": post["source"].capitalize()}
                    },
                    "Channel": {
                        "rich_text": [{"text": {"content": post["channel"]}}]
                    },
                    "OriginalURL": {
                        "url": post["url"]
                    },
                    "Score": {
                        "number": round(post.get("final_score", 0), 3)
                    },
                    "CreatedAt": {
                        "date": {"start": datetime.utcnow().isoformat()}
                    },
                },
                children=[
                    # Готовый текст поста
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": body[:2000]}}]
                        },
                    },
                    # Разделитель
                    {"object": "block", "type": "divider", "divider": {}},
                    # Метаданные
                    {
                        "object": "block",
                        "type": "callout",
                        "callout": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": (
                                            f"📌 Источник: {post['channel']}\n"
                                            f"🔗 Оригинал: {post['url']}\n"
                                            f"📊 Score: {post.get('final_score', 0):.3f} | "
                                            f"Views: {post['views']} | "
                                            f"Reactions: {post['reactions']}"
                                        )
                                    },
                                }
                            ],
                            "icon": {"emoji": "🤖"},
                            "color": "gray_background",
                        },
                    },
                ],
            )
            print(f"📝 Загружен в Notion: «{title[:50]}»")

        except Exception as e:
            print(f"⚠️  Ошибка загрузки в Notion: {e}")
