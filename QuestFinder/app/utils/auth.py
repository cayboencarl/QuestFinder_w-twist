"""Session-based authentication helpers and role-based access decorators."""
from functools import wraps

from flask import abort, current_app, flash, g, redirect, request, session, url_for

from app.extensions import db
from app.models.base import utcnow
from app.models.user import User


def load_current_user() -> None:
    """Run before every request: put the logged-in user (or None) on flask.g."""
    g.user = None
    user_id = session.get("user_id")
    if user_id is None:
        return
    user = db.session.get(User, user_id)
    if user is None or not user.is_active:
        session.clear()
        return
    if user.is_suspended:
        # Suspended while logged in: end the session right away.
        session.clear()
        flash(suspension_message(user), "danger")
        return
    g.user = user


def suspension_message(user: User) -> str:
    from app.utils.template_helpers import local_dt
    msg = f"Your account is suspended until {local_dt(user.suspended_until)}."
    if user.suspension_reason:
        msg += f" Reason: {user.suspension_reason}"
    return msg


def login_user(user: User) -> None:
    # Clear first so an old session can never be reused after login (session fixation).
    session.clear()
    session["user_id"] = user.id
    session.permanent = True
    user.last_login_at = utcnow()
    db.session.commit()


def logout_user() -> None:
    session.clear()


def _safe_next() -> str | None:
    nxt = request.full_path if request.method == "GET" else None
    return nxt if nxt and nxt.startswith("/") and not nxt.startswith("//") else None


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.get("user") is None:
            flash("Please log in first.", "info")
            return redirect(url_for("auth.login", next=_safe_next()))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not g.user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def member_required(view):
    """Marketplace pages are for members; the Barangay Admin uses the admin panel."""
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if g.user.is_admin:
            return redirect(url_for("admin.dashboard"))
        return view(*args, **kwargs)
    return wrapped


def verified_required(view):
    """Posting, accepting quests and moving money require an approved ID + face verification."""
    @wraps(view)
    @member_required
    def wrapped(*args, **kwargs):
        if current_app.config["REQUIRE_VERIFICATION"] and not g.user.is_verified:
            flash("Verify your identity first. It only takes a few minutes.", "warning")
            return redirect(url_for("verification.start"))
        return view(*args, **kwargs)
    return wrapped
