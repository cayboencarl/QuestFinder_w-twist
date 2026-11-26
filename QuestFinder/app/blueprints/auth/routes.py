"""Register, log in, log out."""
import time

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from sqlalchemy.exc import IntegrityError

from app.blueprints.auth.forms import LoginForm, RegisterForm
from app.extensions import db
from app.models.user import User
from app.services import wallet_service
from app.utils.auth import login_user, logout_user, suspension_message

bp = Blueprint("auth", __name__, url_prefix="/auth")

MAX_FAILED_LOGINS = 5
LOCKOUT_SECONDS = 5 * 60


def _safe_next(default: str) -> str:
    nxt = request.args.get("next", "")
    return nxt if nxt.startswith("/") and not nxt.startswith("//") else default


@bp.route("/register", methods=["GET", "POST"])
def register():
    if g.user:
        return redirect(url_for("main.home"))
    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        if User.query.filter_by(email=email).first():
            form.email.errors.append("This email is already registered. Try logging in.")
        else:
            user = User(first_name=form.first_name.data, last_name=form.last_name.data, email=email,
                        phone=form.phone.data or None, birthdate=form.birthdate.data)
            user.set_password(form.password.data)
            db.session.add(user)
            try:
                db.session.flush()
                wallet_service.get_or_create_wallet(user.id)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                form.email.errors.append("This email is already registered. Try logging in.")
            else:
                login_user(user)
                flash("Welcome to QuestFinder! Verify your identity to start posting and accepting quests.",
                      "success")
                return redirect(url_for("verification.start"))
    return render_template("auth/register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("main.home"))
    form = LoginForm()
    locked_until = session.get("login_locked_until", 0)
    if form.validate_on_submit():
        if time.time() < locked_until:
            wait = int((locked_until - time.time()) // 60) + 1
            flash(f"Too many failed attempts. Try again in {wait} minute(s).", "danger")
            return render_template("auth/login.html", form=form), 429

        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user and user.is_active and user.check_password(form.password.data):
            if user.is_suspended:
                session.pop("login_fails", None)
                flash(suspension_message(user), "danger")
                return render_template("auth/login.html", form=form), 403
            login_user(user)  # also clears the failed-attempt counter
            return redirect(_safe_next(url_for("main.home")))

        fails = session.get("login_fails", 0) + 1
        session["login_fails"] = fails
        if fails >= MAX_FAILED_LOGINS:
            session["login_locked_until"] = time.time() + LOCKOUT_SECONDS
            session["login_fails"] = 0
        flash("Incorrect email or password.", "danger")
    return render_template("auth/login.html", form=form)


@bp.route("/logout", methods=["POST"])
def logout():
    logout_user()
    flash("You have logged out.", "info")
    return redirect(url_for("auth.login"))
