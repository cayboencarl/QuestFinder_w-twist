"""Messages tab: conversation list and chat thread (JSON polling for new messages)."""
from flask import Blueprint, abort, g, jsonify, render_template, request, url_for

from app.extensions import db
from app.models.messaging import Conversation
from app.services import chat_service, upload_service
from app.utils.auth import member_required
from app.utils.template_helpers import local_dt

bp = Blueprint("messages", __name__, url_prefix="/messages")


def _get_convo(convo_id: int) -> Conversation:
    convo = db.session.get(Conversation, convo_id)
    if convo is None or not convo.includes(g.user):
        abort(404)
    return convo


def _to_json(m, me_id: int) -> dict:
    return {
        "id": m.id,
        "mine": m.sender_id == me_id,
        "body": m.body,
        "image": url_for("files.chat_image", message_id=m.id) if m.image_filename else None,
        "time": local_dt(m.created_at, "%b %d, %I:%M %p"),
    }


@bp.route("/")
@member_required
def inbox():
    rows = []
    for c in chat_service.conversations_for(g.user):
        last = chat_service.last_message(c)
        rows.append({
            "convo": c,
            "other": c.other_party(g.user),
            "other_role": "worker" if c.role_of(g.user) == "client" else "client",
            "last": last,
            "unread": chat_service.unread_in(c, g.user),
        })
    return render_template("messages/inbox.html", rows=rows, active_tab="messages")


@bp.route("/<int:convo_id>")
@member_required
def thread(convo_id: int):
    convo = _get_convo(convo_id)
    other = convo.other_party(g.user)
    msgs = chat_service.messages_after(convo, g.user, 0)
    return render_template("messages/thread.html", convo=convo, other=other,
                           other_role="worker" if convo.role_of(g.user) == "client" else "client",
                           initial=[_to_json(m, g.user.id) for m in msgs],
                           back_url=url_for("messages.inbox"), active_tab="messages")


@bp.route("/<int:convo_id>/poll")
@member_required
def poll(convo_id: int):
    convo = _get_convo(convo_id)
    after = request.args.get("after", 0, type=int)
    msgs = chat_service.messages_after(convo, g.user, after)
    return jsonify(messages=[_to_json(m, g.user.id) for m in msgs])


@bp.route("/<int:convo_id>/send", methods=["POST"])
@member_required
def send(convo_id: int):
    convo = _get_convo(convo_id)
    try:
        msg = chat_service.send(convo, g.user, request.form.get("body"), request.files.get("image"))
    except (chat_service.ChatError, upload_service.UploadError) as err:
        return jsonify(error=str(err)), 400
    return jsonify(message=_to_json(msg, g.user.id))
