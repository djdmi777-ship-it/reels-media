# parsers/reddit.py
import os
import praw
from datetime import datetime, timezone, timedelta
from config import SUBREDDITS, MIN_REDDIT_SCORE, MIN_REDDIT_COMMENTS, MAX_SOURCE_AGE_HOURS


def fetch_reddit_posts() -> list[dict]:
    """Парсит топовые посты с Reddit за последние 24 часа."""
    
    reddit = praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent=os.getenv("REDDIT_USER_AGENT", "ai-content-bot/1.0"),
    )

    posts = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=MAX_SOURCE_AGE_HOURS)

    for sub_name in SUBREDDITS:
        try:
            subreddit = reddit.subreddit(sub_name)
            
            for post in subreddit.hot(limit=25):
                # Фильтр по времени
                post_time = datetime.fromtimestamp(post.created_utc, tz=timezone.utc)
                if post_time < cutoff:
                    continue

                # Фильтр по качеству
                if post.score < MIN_REDDIT_SCORE:
                    continue
                if post.num_comments < MIN_REDDIT_COMMENTS:
                    continue
                if post.is_self and len(post.selftext) < 100:
                    continue  # слишком короткий текст

                # Берём текст поста или заголовок + ссылку
                text = post.selftext if post.is_self else f"{post.title}\n\nИсточник: {post.url}"
                
                posts.append({
                    "source": "reddit",
                    "channel": f"r/{sub_name}",
                    "text": f"{post.title}\n\n{text[:1500]}",
                    "views": post.score,      # upvotes как proxy для охвата
                    "reactions": post.num_comments,
                    "date": post_time,
                    "url": f"https://reddit.com{post.permalink}",
                    "raw_score": post.score + post.num_comments * 5,
                })

        except Exception as e:
            print(f"⚠️  Ошибка парсинга r/{sub_name}: {e}")
            continue

    posts.sort(key=lambda x: x["raw_score"], reverse=True)
    print(f"✅ Reddit: найдено {len(posts)} постов")
    return posts
