"""Access-checked serving of uploaded images (uploads are never in the public static folder)."""
import os

from flask import Blueprint, abort, g, send_file

from app.extensions import db
from app.models.messaging import Message
from app.models.quest import Quest
from app.models.user import User
from app.models.verification import VerificationRequest
from app.services import upload_service
from app.utils.auth import login_required

bp = Blueprint("files", __name__, url_prefix="/files")


def _send(kind: str, name: str | None, private: bool = True):
    if not name:
        abort(404)
    try:
        path = upload_service.path_for(kind, name)
    except upload_service.UploadError:
        abort(404)
    if not os.path.isfile(path):
        abort(404)
    response = send_file(path, mimetype="image/jpeg", max_age=0 if private else 3600)
    if private:
        response.headers["Cache-Control"] = "private, no-store"
    return response


@bp.route("/avatar/<int:user_id>")
@login_required
def avatar(user_id: int):
    user = db.session.get(User, user_id)
    return _send("avatars", user.avatar_filename if user else None, private=False)


@bp.route("/verification/<int:req_id>/<any(id, face):which>")
@login_required
def verification(req_id: int, which: str):
    req = db.session.get(VerificationRequest, req_id)
    if req is None:
        abort(404)
    # Only the owner and the Barangay Admin may see ID and face scans.
    if not (g.user.is_admin or g.user.id == req.user_id):
        abort(403)
    return _send("verification", req.id_image_filename if which == "id" else req.face_image_filename)


@bp.route("/quest/<int:quest_id>")
@login_required
def quest_photo(quest_id: int):
    quest = db.session.get(Quest, quest_id)
    return _send("quests", quest.photo_filename if quest else None, private=False)


@bp.route("/chat/<int:message_id>")
@login_required
def chat_image(message_id: int):
    msg = db.session.get(Message, message_id)
    # Only the two people in the conversation may see chat photos.
    if msg is None or not msg.conversation.includes(g.user):
        abort(404)
    return _send("chat", msg.image_filename)
