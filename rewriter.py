# rewriter.py — переписывает посты через Claude под стиль блога
import anthropic
from config import BLOG_STYLE_PROMPT


def rewrite_post(post: dict) -> dict:
    """
    Отправляет исходный пост в Claude и получает готовый текст для блога.
    Возвращает пост с добавленным полем 'rewritten_text'.
    """
    client = anthropic.Anthropic()

    source_label = "Telegram-канал" if post["source"] == "telegram" else "Reddit"

    prompt = f"""Вот материал из {source_label} ({post['channel']}):

---
{post['text']}
---

Перепиши это как пост для блога об агрегаторе нейросетей. 
Следуй инструкциям по стилю."""

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=600,
        system=BLOG_STYLE_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    rewritten = message.content[0].text.strip()
    
    post["rewritten_text"] = rewritten
    print(f"✍️  Переписан пост из {post['channel']}")
    return post


def rewrite_all(posts: list[dict]) -> list[dict]:
    """Переписывает все отобранные посты."""
    result = []
    for post in posts:
        try:
            result.append(rewrite_post(post))
        except Exception as e:
            print(f"⚠️  Ошибка переписывания поста из {post['channel']}: {e}")
    return result
