"""Identity verification for members: ID scan → face scan → submit for Barangay Admin review."""
from datetime import date

from flask import Blueprint, current_app, g, jsonify, render_template, request, url_for

from app.models.verification import ID_TYPES, VERIFICATION_PENDING, VERIFICATION_REJECTED
from app.services import upload_service, verification_service
from app.utils.auth import member_required

bp = Blueprint("verification", __name__, url_prefix="/verification")


@bp.route("/")
@member_required
def start():
    latest = g.user.latest_verification
    if g.user.is_verified:
        state = "verified"
    elif latest and latest.status == VERIFICATION_PENDING:
        state = "pending"
    elif latest and latest.status == VERIFICATION_REJECTED:
        state = "rejected"
    else:
        state = "new"
    return render_template("verification/start.html", state=state, latest=latest,
                           back_url=url_for("main.home"))


@bp.route("/scan")
@member_required
def scan():
    if g.user.is_verified or verification_service.has_pending(g.user):
        return start()
    return render_template("verification/scan.html", id_types=ID_TYPES,
                           threshold=current_app.config["FACE_MATCH_THRESHOLD"],
                           back_url=url_for("verification.start"))


@bp.route("/submit", methods=["POST"])
@member_required
def submit():
    """Receives the ID photo, the live face capture and the browser's face-match distance (JSON reply)."""
    f = request.form
    if f.get("id_type") not in dict(ID_TYPES):
        return jsonify(error="Choose the type of ID you scanned."), 400
    name_on_id = (f.get("name_on_id") or "").strip()
    if not 3 <= len(name_on_id) <= 130:
        return jsonify(error="Enter your full name exactly as printed on your ID."), 400
    try:
        birthdate_on_id = date.fromisoformat(f.get("birthdate_on_id", ""))
    except ValueError:
        return jsonify(error="Enter the birthdate printed on your ID."), 400
    id_image, face_image = request.files.get("id_image"), request.files.get("face_image")
    if not id_image or not face_image:
        return jsonify(error="Both the ID scan and the face scan are required."), 400

    try:
        verification_service.submit(
            g.user, id_type=f["id_type"], id_number=f.get("id_number", ""), name_on_id=name_on_id,
            birthdate_on_id=birthdate_on_id, id_image=id_image, face_image=face_image,
            face_distance=f.get("face_distance"),
        )
    except (verification_service.VerificationError, upload_service.UploadError) as err:
        return jsonify(error=str(err)), 400
    return jsonify(ok=True, redirect=url_for("verification.start"))
