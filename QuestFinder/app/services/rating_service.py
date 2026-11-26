"""Ratings and reviews (read side). The 'rate after completion' flow is added in the Ratings module."""
from sqlalchemy import func

from app.extensions import db
from app.models.rating import Rating


def summary(user_id: int) -> dict:
    avg, count = db.session.query(func.avg(Rating.stars), func.count(Rating.id)) \
        .filter(Rating.ratee_id == user_id).one()
    return {"average": round(float(avg), 1) if avg is not None else None, "count": count}


def recent_reviews(user_id: int, limit: int = 10):
    return Rating.query.filter_by(ratee_id=user_id).order_by(Rating.created_at.desc()).limit(limit).all()


class RatingError(Exception):
    pass


def submit(quest, rater, stars: int, comment: str | None) -> Rating:
    """Two-way rating after completion: the client rates the worker and the worker rates the client."""
    from app.models.quest import QUEST_COMPLETED
    if quest.status != QUEST_COMPLETED:
        raise RatingError("You can rate only after the quest is completed.")
    if rater.id == quest.client_id:
        ratee_id = quest.worker_id
    elif rater.id == quest.worker_id:
        ratee_id = quest.client_id
    else:
        raise RatingError("Only the client and the task worker of this quest can rate.")
    if Rating.query.filter_by(quest_id=quest.id, rater_id=rater.id).first():
        raise RatingError("You already rated this quest.")
    if stars not in range(1, 6):
        raise RatingError("Choose 1 to 5 stars.")
    rating = Rating(quest_id=quest.id, rater_id=rater.id, ratee_id=ratee_id, stars=stars,
                    comment=(comment or "").strip()[:500] or None)
    db.session.add(rating)
    db.session.commit()
    return rating
