"""Identity verification: ID scan → face scan → Barangay Admin decision.

Checks done on the server (the browser's result is never trusted on its own):
  * the birthdate on the ID must match the account birthdate, and both must be 18+;
  * a face match score must be present and within FACE_MATCH_THRESHOLD;
  * only one pending request per user at a time;
  * the admin re-checks the age from the ID before approving.
"""
from datetime import date

from flask import current_app

from app.extensions import db
from app.models.base import utcnow
from app.models.notification import NOTIF_VERIFICATION_RESULT
from app.models.user import age_on
from app.models.verification import (
    VERIFICATION_APPROVED, VERIFICATION_PENDING, VERIFICATION_REJECTED, VerificationRequest,
)
from app.services import notification_service, upload_service


class VerificationError(Exception):
    pass


def has_pending(user) -> bool:
    return user.verification_requests.filter_by(status=VERIFICATION_PENDING).first() is not None


def submit(user, *, id_type, id_number, name_on_id, birthdate_on_id: date,
           id_image, face_image, face_distance) -> VerificationRequest:
    if user.is_verified:
        raise VerificationError("Your account is already verified.")
    if has_pending(user):
        raise VerificationError("You already have a verification waiting for review.")

    minimum = current_app.config["MINIMUM_AGE"]
    if age_on(birthdate_on_id, date.today()) < minimum:
        raise VerificationError(f"QuestFinder is strictly for users {minimum} years old and above.")
    if birthdate_on_id != user.birthdate:
        raise VerificationError("The birthdate on your ID does not match your account birthdate.")

    try:
        distance = float(face_distance)
    except (TypeError, ValueError):
        raise VerificationError("Face scan result is missing. Please scan your face again.")
    if not 0 <= distance <= 2:
        raise VerificationError("Face scan result is invalid. Please scan your face again.")
    if distance > current_app.config["FACE_MATCH_THRESHOLD"]:
        raise VerificationError("Your face did not match the photo on your ID. Try again in good lighting.")

    id_number = "".join(ch for ch in (id_number or "") if ch.isalnum())
    if len(id_number) < 4:
        raise VerificationError("Enter the ID number as printed on your ID.")

    id_name = upload_service.save_image(id_image, "verification")
    try:
        face_name = upload_service.save_image(face_image, "verification")
    except upload_service.UploadError:
        upload_service.delete("verification", id_name)
        raise

    req = VerificationRequest(
        user_id=user.id, id_type=id_type, id_number_last4=id_number[-4:].upper(),
        name_on_id=" ".join(name_on_id.split()), birthdate_on_id=birthdate_on_id,
        id_image_filename=id_name, face_image_filename=face_name,
        face_match_distance=round(distance, 4), face_match_passed=True,
    )
    db.session.add(req)
    db.session.commit()
    return req


def approve(req: VerificationRequest, admin) -> None:
    if req.status != VERIFICATION_PENDING:
        raise VerificationError("This request was already reviewed.")
    minimum = current_app.config["MINIMUM_AGE"]
    if age_on(req.birthdate_on_id, date.today()) < minimum:
        raise VerificationError(f"Cannot approve: the ID shows the user is under {minimum}.")
    req.status = VERIFICATION_APPROVED
    req.reviewed_by_id = admin.id
    req.reviewed_at = utcnow()
    req.user.is_verified = True
    req.user.verified_at = req.reviewed_at
    notification_service.notify(
        req.user_id, NOTIF_VERIFICATION_RESULT,
        "Your identity is verified. You can now post and accept quests.", "/")
    db.session.commit()


def reject(req: VerificationRequest, admin, reason: str) -> None:
    if req.status != VERIFICATION_PENDING:
        raise VerificationError("This request was already reviewed.")
    req.status = VERIFICATION_REJECTED
    req.reviewed_by_id = admin.id
    req.reviewed_at = utcnow()
    req.rejection_reason = reason.strip()[:255]
    notification_service.notify(
        req.user_id, NOTIF_VERIFICATION_RESULT,
        f"Your verification was not approved: {req.rejection_reason} You can submit again.",
        "/verification")
    db.session.commit()
