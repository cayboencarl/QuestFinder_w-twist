"""User accounts.

One account can act as both a client (posts quests) and a task worker
(accepts quests). The only separate role is the Barangay Admin, who
reviews identity verification requests, views posted quests and users,
and can suspend or delete member accounts.
"""
from datetime import date, datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models.base import TimestampMixin, utcnow

ROLE_MEMBER = "member"
ROLE_ADMIN = "admin"


class User(TimestampMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(60), nullable=False)
    last_name = db.Column(db.String(60), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    phone = db.Column(db.String(20))
    password_hash = db.Column(db.String(255), nullable=False)
    birthdate = db.Column(db.Date, nullable=False)
    role = db.Column(db.String(10), nullable=False, default=ROLE_MEMBER)

    bio = db.Column(db.Text)
    skills = db.Column(db.String(255))
    avatar_filename = db.Column(db.String(255))

    # Task worker's / client's own location (set by GPS or by placing a pin).
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    location_label = db.Column(db.String(255))
    location_updated_at = db.Column(db.DateTime(timezone=True))

    is_verified = db.Column(db.Boolean, nullable=False, default=False)
    verified_at = db.Column(db.DateTime(timezone=True))
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    last_login_at = db.Column(db.DateTime(timezone=True))

    # Suspension set by the Barangay Admin. The account cannot log in until suspended_until.
    suspended_until = db.Column(db.DateTime(timezone=True), index=True)
    suspended_at = db.Column(db.DateTime(timezone=True))
    suspension_reason = db.Column(db.String(255))

    # --- Relationships ------------------------------------------------------
    wallet = db.relationship("Wallet", back_populates="user", uselist=False,
                             cascade="all, delete-orphan")
    verification_requests = db.relationship(
        "VerificationRequest", back_populates="user",
        foreign_keys="VerificationRequest.user_id",
        order_by="VerificationRequest.submitted_at.desc()", lazy="dynamic",
    )
    posted_quests = db.relationship("Quest", back_populates="client",
                                    foreign_keys="Quest.client_id", lazy="dynamic")
    applications = db.relationship("QuestApplication", back_populates="worker", lazy="dynamic")
    notifications = db.relationship("Notification", back_populates="user", lazy="dynamic",
                                    cascade="all, delete-orphan")
    ratings_received = db.relationship("Rating", back_populates="ratee",
                                       foreign_keys="Rating.ratee_id", lazy="dynamic")

    __table_args__ = (
        db.CheckConstraint(f"role IN ('{ROLE_MEMBER}', '{ROLE_ADMIN}')", name="ck_users_role"),
        db.CheckConstraint("latitude IS NULL OR (latitude BETWEEN -90 AND 90)", name="ck_users_lat"),
        db.CheckConstraint("longitude IS NULL OR (longitude BETWEEN -180 AND 180)", name="ck_users_lng"),
    )

    # --- Password -------------------------------------------------------------
    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    # --- Convenience ------------------------------------------------------------
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def is_admin(self) -> bool:
        return self.role == ROLE_ADMIN

    @property
    def is_suspended(self) -> bool:
        if self.suspended_until is None:
            return False
        until = self.suspended_until
        if until.tzinfo is None:
            until = until.replace(tzinfo=timezone.utc)
        return until > datetime.now(timezone.utc)

    @property
    def has_location(self) -> bool:
        return self.latitude is not None and self.longitude is not None

    @property
    def age(self) -> int:
        return age_on(self.birthdate, date.today())

    def set_location(self, lat: float, lng: float, label: str | None = None) -> None:
        self.latitude = lat
        self.longitude = lng
        self.location_label = label
        self.location_updated_at = utcnow()

    @property
    def latest_verification(self):
        return self.verification_requests.first()

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User {self.id} {self.email}>"


def age_on(birthdate: date, today: date) -> int:
    """Exact age in completed years."""
    years = today.year - birthdate.year
    if (today.month, today.day) < (birthdate.month, birthdate.day):
        years -= 1
    return years
