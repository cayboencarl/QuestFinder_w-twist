"""In-app chat between a client and the accepted task worker of a quest."""
from sqlalchemy import or_

from app.extensions import db
from app.models.base import utcnow
from app.models.messaging import Conversation, Message
from app.services import upload_service

MAX_BODY = 1000


class ChatError(Exception):
    pass


def conversations_for(user):
    return Conversation.query.filter(or_(Conversation.client_id == user.id, Conversation.worker_id == user.id)) \
        .order_by(Conversation.last_message_at.desc()).all()


def unread_count(user) -> int:
    return Message.query.join(Conversation).filter(
        or_(Conversation.client_id == user.id, Conversation.worker_id == user.id),
        Message.sender_id != user.id, Message.read_at.is_(None)).count()


def unread_in(convo: Conversation, user) -> int:
    return convo.messages.filter(Message.sender_id != user.id, Message.read_at.is_(None)).count()


def last_message(convo: Conversation):
    return convo.messages.order_by(Message.id.desc()).first()


def send(convo: Conversation, sender, body: str | None, image=None) -> Message:
    if not convo.includes(sender):
        raise ChatError("You are not part of this conversation.")
    body = (body or "").strip()
    if len(body) > MAX_BODY:
        raise ChatError(f"Messages can be up to {MAX_BODY} characters.")
    image_name = upload_service.save_image(image, "chat") if image else None
    if not body and not image_name:
        raise ChatError("Type a message or attach a photo.")
    msg = Message(conversation_id=convo.id, sender_id=sender.id, body=body or None, image_filename=image_name)
    db.session.add(msg)
    convo.last_message_at = utcnow()
    db.session.commit()
    return msg


def messages_after(convo: Conversation, user, after_id: int = 0, limit: int = 200):
    """New messages since after_id; marks the other person's messages as read."""
    msgs = convo.messages.filter(Message.id > after_id).order_by(Message.id).limit(limit).all()
    changed = False
    now = utcnow()
    for m in msgs:
        if m.sender_id != user.id and m.read_at is None:
            m.read_at = now
            changed = True
    if changed:
        db.session.commit()
    return msgs
