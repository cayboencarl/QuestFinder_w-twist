"""Notifications (bell icon beside Settings)."""
from flask import Blueprint, abort, g, redirect, render_template, url_for

from app.extensions import db
from app.models.notification import Notification
from app.utils.auth import member_required

bp = Blueprint("notifications", __name__, url_prefix="/notifications")


@bp.route("/")
@member_required
def index():
    items = g.user.notifications.order_by(Notification.created_at.desc()).limit(100).all()
    unread_ids = {n.id for n in items if not n.is_read}
    return render_template("notifications/index.html", items=items, unread_ids=unread_ids,
                           back_url=url_for("main.home"), active_tab="home")


@bp.route("/<int:note_id>/open")
@member_required
def open_link(note_id: int):
    note = db.session.get(Notification, note_id)
    if note is None or note.user_id != g.user.id:
        abort(404)
    note.is_read = True
    db.session.commit()
    link = note.link if note.link and note.link.startswith("/") and not note.link.startswith("//") else None
    return redirect(link or url_for("notifications.index"))


@bp.route("/read-all", methods=["POST"])
@member_required
def read_all():
    g.user.notifications.filter_by(is_read=False).update({"is_read": True})
    db.session.commit()
    return redirect(url_for("notifications.index"))
