# scorer.py — отбирает топ-N постов по комбинированному скору
from datetime import datetime, timezone
from config import SCORE_WEIGHTS, SOURCES_TO_FETCH, POSTS_TO_GENERATE


def score_posts(all_posts: list[dict]) -> list[dict]:
    """
    Нормализует метрики и считает итоговый скор.
    Возвращает топ постов для генерации.
    """
    if not all_posts:
        return []

    # Берём не больше SOURCES_TO_FETCH для обработки
    candidates = all_posts[:SOURCES_TO_FETCH]

    # Нормализация: находим max значения
    max_views = max(p["views"] for p in candidates) or 1
    max_reactions = max(p["reactions"] for p in candidates) or 1
    now = datetime.now(timezone.utc)

    for post in candidates:
        # 1. Охват (просмотры / upvotes)
        views_score = post["views"] / max_views

        # 2. Вовлечённость (реакции / комментарии)
        reactions_score = post["reactions"] / max_reactions

        # 3. Свежесть (1.0 = только что, 0.0 = 24 часа назад)
        age_hours = (now - post["date"]).total_seconds() / 3600
        recency_score = max(0.0, 1.0 - age_hours / 24)

        # Итоговый скор
        post["final_score"] = (
            SCORE_WEIGHTS["views_or_upvotes"] * views_score
            + SCORE_WEIGHTS["reactions_or_comments"] * reactions_score
            + SCORE_WEIGHTS["recency"] * recency_score
        )

    # Сортируем и берём топ
    candidates.sort(key=lambda x: x["final_score"], reverse=True)
    top = candidates[:POSTS_TO_GENERATE]

    print(f"📊 Скоринг: отобрано {len(top)} из {len(candidates)} постов")
    for i, p in enumerate(top, 1):
        print(f"   {i}. [{p['source']}] {p['channel']} — score: {p['final_score']:.2f} | views: {p['views']}")

    return top
