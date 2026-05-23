# parsers/rss.py
import feedparser
from datetime import datetime, timezone, timedelta
from config import MAX_SOURCE_AGE_HOURS

RSS_FEEDS = [
    {"url": "https://openai.com/blog/rss.xml",           "name": "OpenAI Blog"},
    {"url": "https://www.anthropic.com/rss.xml",          "name": "Anthropic News"},
    {"url": "https://huggingface.co/blog/feed.xml",       "name": "HuggingFace Blog"},
    {"url": "https://techcrunch.com/tag/artificial-intelligence/feed/", "name": "TechCrunch AI"},
    {"url": "https://venturebeat.com/category/ai/feed/",  "name": "VentureBeat AI"},
    {"url": "https://the-decoder.com/feed/",              "name": "The Decoder"},
    {"url": "https://www.unite.ai/feed/",                 "name": "Unite.AI"},
]

def fetch_rss_posts() -> list[dict]:
    """Парсит RSS-ленты AI-блогов и возвращает свежие посты."""
    posts = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=MAX_SOURCE_AGE_HOURS)

    for feed_info in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_info["url"])

            for entry in feed.entries[:10]:
                # Дата публикации
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                else:
                    pub_date = datetime.now(timezone.utc)

                if pub_date < cutoff:
                    continue

                # Текст поста
                text = ""
                if hasattr(entry, "summary"):
                    text = entry.summary
                elif hasattr(entry, "description"):
                    text = entry.description

                # Убираем HTML-теги
                import re
                text = re.sub(r"<[^>]+>", "", text).strip()

                if len(text) < 100:
                    continue

                title = entry.get("title", "")
                full_text = f"{title}\n\n{text[:1500]}"

                posts.append({
                    "source": "rss",
                    "channel": feed_info["name"],
                    "text": full_text,
                    "views": 1000,      # базовый скор для RSS
                    "reactions": 50,
                    "date": pub_date,
                    "url": entry.get("link", feed_info["url"]),
                    "raw_score": 1000 + 50 * 10,
                })

        except Exception as e:
            print(f"⚠️  Ошибка парсинга {feed_info['name']}: {e}")
            continue

    posts.sort(key=lambda x: x["date"], reverse=True)
    print(f"✅ RSS: найдено {len(posts)} постов")
    return posts
