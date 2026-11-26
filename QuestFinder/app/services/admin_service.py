"""Barangay Admin actions on member accounts: suspend, lift a suspension, delete.

Callers commit the session (except delete_user, which commits itself because it
removes the account with a single SQL DELETE and lets the database cascade).
"""
from datetime import timedelta

from sqlalchemy import delete, or_

from app.extensions import db
from app.models.base import utcnow
from app.models.messaging import Conversation, Message
from app.models.notification import NOTIF_QUEST_UPDATE
from app.models.quest import (
    APP_PENDING, PAYMENT_HELD, PAYMENT_UNPAID, QUEST_ASSIGNED, QUEST_OPEN, Quest,
)
from app.models.user import User
from app.services import notification_service, upload_service, wallet_service

DURATION_UNITS = {"hours": "hour(s)", "days": "day(s)", "weeks": "week(s)"}
MAX_SUSPENSION_DAYS = 365


class AdminError(Exception):
    """Business-rule violation, shown to the admin."""


def _check_target(user: User, admin: User) -> None:
    if user.is_admin:
        raise AdminError("Barangay Admin accounts cannot be suspended or deleted here.")
    if user.id == admin.id:
        raise AdminError("You cannot do this to your own account.")


def suspend(user: User, admin: User, amount, unit: str, reason: str) -> None:
    _check_target(user, admin)
    try:
        amount = int(amount)
    except (TypeError, ValueError):
        raise AdminError("Enter how long the suspension lasts.")
    if unit not in DURATION_UNITS:
        raise AdminError("Choose hours, days or weeks.")
    if amount < 1:
        raise AdminError("The suspension must last at least 1 " + DURATION_UNITS[unit].replace("(s)", "") + ".")
    length = timedelta(**{unit: amount})
    if length > timedelta(days=MAX_SUSPENSION_DAYS):
        raise AdminError(f"A suspension can last at most {MAX_SUSPENSION_DAYS} days. "
                         "Delete the account if the user should not come back.")
    reason = " ".join((reason or "").split())
    if not reason:
        raise AdminError("Write the reason for the suspension. The user will see it.")
    now = utcnow()
    user.suspended_at = now
    user.suspended_until = now + length
    user.suspension_reason = reason[:255]


def lift_suspension(user: User, admin: User) -> None:
    _check_target(user, admin)
    user.suspended_until = None
    user.suspended_at = None
    user.suspension_reason = None


def delete_user(user: User, admin: User) -> dict:
    """Delete a member account and everything that belongs to it.

    - Quests the user is doing for other clients go back to open, and the
      client's reserved pay is returned to the client's wallet.
    - Quests the user posted are deleted; their assigned task workers are told.
    - Applications, chats, ratings, notifications, the wallet and the
      verification requests are removed by the database (ON DELETE CASCADE).
    - Uploaded images (avatar, ID/face scans, quest photos, chat images) are deleted.
    """
    _check_target(user, admin)
    user_id = user.id
    summary = {"reopened": 0, "removed_quests": 0}

    # 1) Quests this user is working on for someone else: reopen and refund the client.
    doing = Quest.query.filter(Quest.worker_id == user_id, Quest.status == QUEST_ASSIGNED) \
        .with_for_update().all()
    for quest in doing:
        if quest.payment_status == PAYMENT_HELD:
            wallet_service.refund_to_client(quest.client_id, quest)
        quest.status = QUEST_OPEN
        quest.payment_status = PAYMENT_UNPAID
        quest.worker_id = None
        quest.assigned_at = None
        if quest.conversation is not None:
            db.session.delete(quest.conversation)
        notification_service.notify(
            quest.client_id, NOTIF_QUEST_UPDATE,
            f"The task worker for \"{quest.title}\" is no longer on QuestFinder. "
            "Your quest is open again and the reserved pay is back in your wallet.",
            link=f"/quests/{quest.id}")
        summary["reopened"] += 1

    # 2) Quests this user posted: tell the task workers who were assigned or waiting.
    posted = Quest.query.filter(Quest.client_id == user_id).all()
    for quest in posted:
        if quest.status == QUEST_ASSIGNED and quest.worker_id:
            notification_service.notify(
                quest.worker_id, NOTIF_QUEST_UPDATE,
                f"The quest \"{quest.title}\" was removed because the client's account was deleted.")
        for application in quest.applications.filter_by(status=APP_PENDING):
            notification_service.notify(
                application.worker_id, NOTIF_QUEST_UPDATE,
                f"The quest \"{quest.title}\" you applied to was removed.")
    summary["removed_quests"] = len(posted)

    # 3) Collect uploaded files to delete after the rows are gone.
    files = [("avatars", user.avatar_filename)]
    for req in user.verification_requests:
        files += [("verification", req.id_image_filename), ("verification", req.face_image_filename)]
    files += [("quests", q.photo_filename) for q in posted]
    convo_ids = [c.id for c in Conversation.query.filter(
        or_(Conversation.client_id == user_id, Conversation.worker_id == user_id)).all()]
    if convo_ids:
        files += [("chat", m.image_filename) for m in
                  Message.query.filter(Message.conversation_id.in_(convo_ids),
                                       Message.image_filename.isnot(None)).all()]

    db.session.flush()
    db.session.expunge(user)
    db.session.execute(delete(User).where(User.id == user_id))
    db.session.commit()

    for kind, name in files:
        upload_service.delete(kind, name)
    return summary
