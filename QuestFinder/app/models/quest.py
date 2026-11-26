"""Quests (posted tasks) and the applications task workers make to them.

Flow:
  open  --worker taps ACCEPT QUEST-->  application (pending)
  client accepts one application   -->  quest assigned, pay reserved from client wallet
  client confirms the work is done -->  quest completed, pay released to the worker
  client cancels an open quest     -->  quest cancelled
"""
from app.extensions import db
from app.models.base import TimestampMixin, utcnow

QUEST_OPEN = "open"
QUEST_ASSIGNED = "assigned"
QUEST_COMPLETED = "completed"
QUEST_CANCELLED = "cancelled"
QUEST_STATUSES = (QUEST_OPEN, QUEST_ASSIGNED, QUEST_COMPLETED, QUEST_CANCELLED)

PAYMENT_UNPAID = "unpaid"
PAYMENT_HELD = "held"
PAYMENT_RELEASED = "released"
PAYMENT_STATUSES = (PAYMENT_UNPAID, PAYMENT_HELD, PAYMENT_RELEASED)

APP_PENDING = "pending"
APP_ACCEPTED = "accepted"
APP_REJECTED = "rejected"
APP_WITHDRAWN = "withdrawn"
APP_STATUSES = (APP_PENDING, APP_ACCEPTED, APP_REJECTED, APP_WITHDRAWN)


def _in(values) -> str:
    return ", ".join(f"'{v}'" for v in values)


class Quest(TimestampMixin, db.Model):
    __tablename__ = "quests"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
                          nullable=False, index=True)

    title = db.Column(db.String(80), nullable=False)
    description = db.Column(db.Text, nullable=False)
    qualification = db.Column(db.Text, nullable=False)
    pay = db.Column(db.Numeric(10, 2), nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    photo_filename = db.Column(db.String(255))

    # Exact location: shown only to the client and the accepted task worker.
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    location_label = db.Column(db.String(255), nullable=False)
    # Approximate location: shown to everyone else (privacy-preserving).
    approx_latitude = db.Column(db.Float, nullable=False)
    approx_longitude = db.Column(db.Float, nullable=False)

    status = db.Column(db.String(10), nullable=False, default=QUEST_OPEN, index=True)
    payment_status = db.Column(db.String(10), nullable=False, default=PAYMENT_UNPAID)
    worker_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), index=True)
    assigned_at = db.Column(db.DateTime(timezone=True))
    completed_at = db.Column(db.DateTime(timezone=True))
    cancelled_at = db.Column(db.DateTime(timezone=True))

    client = db.relationship("User", back_populates="posted_quests", foreign_keys=[client_id])
    worker = db.relationship("User", foreign_keys=[worker_id])
    applications = db.relationship("QuestApplication", back_populates="quest", lazy="dynamic",
                                   cascade="all, delete-orphan")
    conversation = db.relationship("Conversation", back_populates="quest", uselist=False,
                                   cascade="all, delete-orphan")
    ratings = db.relationship("Rating", back_populates="quest", lazy="dynamic",
                              cascade="all, delete-orphan")

    __table_args__ = (
        db.CheckConstraint(f"status IN ({_in(QUEST_STATUSES)})", name="ck_quests_status"),
        db.CheckConstraint(f"payment_status IN ({_in(PAYMENT_STATUSES)})", name="ck_quests_payment"),
        db.CheckConstraint("pay > 0", name="ck_quests_pay_positive"),
        db.CheckConstraint("duration_minutes > 0", name="ck_quests_duration_positive"),
        db.CheckConstraint("worker_id IS NULL OR worker_id <> client_id", name="ck_quests_not_own"),
        db.Index("ix_quests_approx_location", "approx_latitude", "approx_longitude"),
    )

    def can_see_exact_location(self, user) -> bool:
        if user is None:
            return False
        return user.id == self.client_id or (self.worker_id is not None and user.id == self.worker_id)

    def is_participant(self, user) -> bool:
        return self.can_see_exact_location(user)

    def mark_assigned(self, worker_id: int) -> None:
        self.worker_id = worker_id
        self.status = QUEST_ASSIGNED
        self.assigned_at = utcnow()


class QuestApplication(TimestampMixin, db.Model):
    __tablename__ = "quest_applications"

    id = db.Column(db.Integer, primary_key=True)
    quest_id = db.Column(db.Integer, db.ForeignKey("quests.id", ondelete="CASCADE"),
                         nullable=False, index=True)
    worker_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
                          nullable=False, index=True)
    message = db.Column(db.String(300))
    status = db.Column(db.String(10), nullable=False, default=APP_PENDING)
    # Distance (km) from the worker to the quest when they applied, for the client's review.
    distance_km = db.Column(db.Float)

    quest = db.relationship("Quest", back_populates="applications")
    worker = db.relationship("User", back_populates="applications")

    __table_args__ = (
        db.UniqueConstraint("quest_id", "worker_id", name="uq_application_quest_worker"),
        db.CheckConstraint(f"status IN ({_in(APP_STATUSES)})", name="ck_applications_status"),
    )
