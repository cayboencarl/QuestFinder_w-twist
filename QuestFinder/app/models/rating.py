"""Two-way ratings and reviews after a quest is completed."""
from app.extensions import db
from app.models.base import utcnow


class Rating(db.Model):
    __tablename__ = "ratings"

    id = db.Column(db.Integer, primary_key=True)
    quest_id = db.Column(db.Integer, db.ForeignKey("quests.id", ondelete="CASCADE"),
                         nullable=False, index=True)
    rater_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ratee_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
                         nullable=False, index=True)
    stars = db.Column(db.SmallInteger, nullable=False)
    comment = db.Column(db.String(500))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    quest = db.relationship("Quest", back_populates="ratings")
    rater = db.relationship("User", foreign_keys=[rater_id])
    ratee = db.relationship("User", back_populates="ratings_received", foreign_keys=[ratee_id])

    __table_args__ = (
        db.UniqueConstraint("quest_id", "rater_id", name="uq_rating_once_per_quest"),
        db.CheckConstraint("stars BETWEEN 1 AND 5", name="ck_ratings_stars"),
        db.CheckConstraint("rater_id <> ratee_id", name="ck_ratings_not_self"),
    )
