"""Identity verification: ID scan + face scan, reviewed by the Barangay Admin."""
from app.extensions import db
from app.models.base import utcnow

VERIFICATION_PENDING = "pending"
VERIFICATION_APPROVED = "approved"
VERIFICATION_REJECTED = "rejected"

ID_TYPES = [
    ("philsys", "PhilSys National ID"),
    ("drivers_license", "Driver's License"),
    ("passport", "Passport"),
    ("umid", "UMID"),
    ("postal", "Postal ID"),
    ("voters", "Voter's ID"),
    ("student", "School ID (with birthdate)"),
]


class VerificationRequest(db.Model):
    __tablename__ = "verification_requests"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
                        nullable=False, index=True)

    id_type = db.Column(db.String(30), nullable=False)
    # Only the last 4 characters of the ID number are stored (privacy).
    id_number_last4 = db.Column(db.String(4), nullable=False)
    name_on_id = db.Column(db.String(130), nullable=False)
    birthdate_on_id = db.Column(db.Date, nullable=False)

    id_image_filename = db.Column(db.String(255), nullable=False)
    face_image_filename = db.Column(db.String(255), nullable=False)
    # Euclidean distance between the face on the ID and the live face scan
    # (lower = more similar). Computed in the browser, checked again by the admin.
    face_match_distance = db.Column(db.Float)
    face_match_passed = db.Column(db.Boolean, nullable=False, default=False)

    status = db.Column(db.String(10), nullable=False, default=VERIFICATION_PENDING, index=True)
    submitted_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at = db.Column(db.DateTime(timezone=True))
    rejection_reason = db.Column(db.String(255))

    user = db.relationship("User", back_populates="verification_requests", foreign_keys=[user_id])
    reviewed_by = db.relationship("User", foreign_keys=[reviewed_by_id])

    __table_args__ = (
        db.CheckConstraint(
            f"status IN ('{VERIFICATION_PENDING}', '{VERIFICATION_APPROVED}', '{VERIFICATION_REJECTED}')",
            name="ck_verification_status",
        ),
    )

    @property
    def id_type_label(self) -> str:
        return dict(ID_TYPES).get(self.id_type, self.id_type)
