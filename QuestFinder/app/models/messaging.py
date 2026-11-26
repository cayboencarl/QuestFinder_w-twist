"""In-app chat. One conversation per quest, opened when the client accepts a worker."""
from app.extensions import db
from app.models.base import utcnow


class Conversation(db.Model):
    __tablename__ = "conversations"

    id = db.Column(db.Integer, primary_key=True)
    quest_id = db.Column(db.Integer, db.ForeignKey("quests.id", ondelete="CASCADE"),
                         nullable=False, unique=True)
    client_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    worker_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    last_message_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)

    quest = db.relationship("Quest", back_populates="conversation")
    client = db.relationship("User", foreign_keys=[client_id])
    worker = db.relationship("User", foreign_keys=[worker_id])
    messages = db.relationship("Message", back_populates="conversation", lazy="dynamic",
                               order_by="Message.id", cascade="all, delete-orphan")

    __table_args__ = (
        db.CheckConstraint("client_id <> worker_id", name="ck_conversations_two_people"),
    )

    def includes(self, user) -> bool:
        return user is not None and user.id in (self.client_id, self.worker_id)

    def other_party(self, user):
        return self.worker if user.id == self.client_id else self.client

    def role_of(self, user) -> str:
        """'client' or 'worker' — the role this user plays in this quest."""
        return "client" if user.id == self.client_id else "worker"


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversations.id", ondelete="CASCADE"),
                                nullable=False, index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    body = db.Column(db.Text)
    image_filename = db.Column(db.String(255))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    read_at = db.Column(db.DateTime(timezone=True))

    conversation = db.relationship("Conversation", back_populates="messages")
    sender = db.relationship("User")

    __table_args__ = (
        db.CheckConstraint("body IS NOT NULL OR image_filename IS NOT NULL",
                           name="ck_messages_not_empty"),
    )
