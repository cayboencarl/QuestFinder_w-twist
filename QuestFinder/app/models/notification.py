"""In-app notifications (bell icon beside Settings)."""
from app.extensions import db
from app.models.base import utcnow

NOTIF_QUEST_ACCEPTED_BY_WORKER = "quest_accepted_by_worker"  # to client: a worker accepted your quest
NOTIF_WORKER_CONFIRMED = "worker_confirmed"                  # to worker: client accepted you
NOTIF_QUEST_COMPLETED = "quest_completed"                    # to worker: pay released
NOTIF_VERIFICATION_RESULT = "verification_result"            # to user: admin decision
NOTIF_QUEST_UPDATE = "quest_update"                          # quest changed by the Barangay Admin
NOTIF_KINDS = (NOTIF_QUEST_ACCEPTED_BY_WORKER, NOTIF_WORKER_CONFIRMED,
               NOTIF_QUEST_COMPLETED, NOTIF_VERIFICATION_RESULT, NOTIF_QUEST_UPDATE)


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    kind = db.Column(db.String(30), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    link = db.Column(db.String(255))
    is_read = db.Column(db.Boolean, nullable=False, default=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    user = db.relationship("User", back_populates="notifications")

    __table_args__ = (
        db.CheckConstraint("kind IN (" + ", ".join(f"'{k}'" for k in NOTIF_KINDS) + ")",
                           name="ck_notifications_kind"),
    )
