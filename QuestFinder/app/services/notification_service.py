"""Create and read in-app notifications. Callers commit the session."""
from app.extensions import db
from app.models.notification import Notification


def notify(user_id: int, kind: str, message: str, link: str | None = None) -> Notification:
    note = Notification(user_id=user_id, kind=kind, message=message[:255], link=link)
    db.session.add(note)
    return note


def mark_all_read(user) -> None:
    user.notifications.filter_by(is_read=False).update({"is_read": True})
