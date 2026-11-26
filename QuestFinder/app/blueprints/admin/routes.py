"""Barangay Admin: review identity verifications (ID scan + face scan), view posted
quests, view registered users, and suspend or delete member accounts."""
from datetime import date

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for
from sqlalchemy import func, or_

from app.extensions import db
from app.models.base import utcnow
from app.models.quest import QUEST_STATUSES, Quest, QuestApplication
from app.models.rating import Rating
from app.models.user import ROLE_MEMBER, User, age_on
from app.models.verification import VERIFICATION_PENDING, VerificationRequest
from app.services import admin_service, verification_service, wallet_service
from app.services.quest_service import held_total
from app.utils.template_helpers import local_dt
from app.utils.auth import admin_required

bp = Blueprint("admin", __name__, url_prefix="/admin")

REJECT_REASONS = [
    "The ID photo is blurry or cut off.",
    "The face scan does not match the ID photo.",
    "The name or birthdate does not match the ID.",
    "The ID is expired or not accepted.",
    "The ID shows the user is under 18.",
]


@bp.route("/")
@admin_required
def dashboard():
    status = request.args.get("status", VERIFICATION_PENDING)
    if status not in ("pending", "approved", "rejected"):
        status = VERIFICATION_PENDING
    requests_ = VerificationRequest.query.filter_by(status=status) \
        .order_by(VerificationRequest.submitted_at.asc() if status == VERIFICATION_PENDING
                  else VerificationRequest.reviewed_at.desc()).limit(200).all()
    counts = {s: VerificationRequest.query.filter_by(status=s).count()
              for s in ("pending", "approved", "rejected")}
    members = User.query.filter_by(role="member").count()
    verified = User.query.filter_by(role="member", is_verified=True).count()
    return render_template("admin/dashboard.html", items=requests_, status=status, counts=counts,
                           members=members, verified=verified)


@bp.route("/verifications/<int:req_id>", methods=["GET", "POST"])
@admin_required
def review(req_id: int):
    req = db.session.get(VerificationRequest, req_id)
    if req is None:
        abort(404)
    if request.method == "POST":
        action = request.form.get("action")
        try:
            if action == "approve":
                verification_service.approve(req, g.user)
                flash(f"{req.user.full_name} is now verified.", "success")
            elif action == "reject":
                reason = request.form.get("reason") or request.form.get("other_reason", "")
                if not reason.strip():
                    flash("Choose or type a reason for rejecting.", "warning")
                    return redirect(url_for("admin.review", req_id=req.id))
                verification_service.reject(req, g.user, reason)
                flash(f"Verification of {req.user.full_name} was rejected.", "info")
            else:
                abort(400)
        except verification_service.VerificationError as err:
            flash(str(err), "danger")
            return redirect(url_for("admin.review", req_id=req.id))
        return redirect(url_for("admin.dashboard"))

    today = date.today()
    checks = {
        "age_on_id": age_on(req.birthdate_on_id, today),
        "is_adult": age_on(req.birthdate_on_id, today) >= 18,
        "birthdate_matches": req.birthdate_on_id == req.user.birthdate,
        "name_matches": " ".join(req.name_on_id.lower().split()) == " ".join(req.user.full_name.lower().split()),
        "similarity": max(0, round((1 - (req.face_match_distance or 1)) * 100)),
    }
    return render_template("admin/review.html", req=req, checks=checks, reasons=REJECT_REASONS)



# --------------------------------------------------------------------------- posted quests

@bp.route("/quests")
@admin_required
def quests():
    status = request.args.get("status", "all")
    if status != "all" and status not in QUEST_STATUSES:
        status = "all"
    q = (request.args.get("q") or "").strip()[:80]
    query = Quest.query.join(User, User.id == Quest.client_id)
    if status != "all":
        query = query.filter(Quest.status == status)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Quest.title.ilike(like), Quest.location_label.ilike(like),
                                 User.first_name.ilike(like), User.last_name.ilike(like),
                                 User.email.ilike(like)))
    items = query.order_by(Quest.created_at.desc()).limit(300).all()
    counts = dict(db.session.query(Quest.status, func.count(Quest.id)).group_by(Quest.status).all())
    counts["all"] = sum(counts.values())
    return render_template("admin/quests.html", items=items, status=status, q=q, counts=counts,
                           statuses=("all",) + QUEST_STATUSES)


@bp.route("/quests/<int:quest_id>")
@admin_required
def quest_detail(quest_id: int):
    quest = db.session.get(Quest, quest_id)
    if quest is None:
        abort(404)
    applications = quest.applications.order_by(QuestApplication.created_at.asc()).all()
    return render_template("admin/quest_detail.html", quest=quest, applications=applications)


# --------------------------------------------------------------------------- users

USER_FILTERS = {"all": "All", "verified": "Verified", "unverified": "Not verified", "suspended": "Suspended"}


@bp.route("/users")
@admin_required
def users():
    show = request.args.get("show", "all")
    if show not in USER_FILTERS:
        show = "all"
    q = (request.args.get("q") or "").strip()[:80]
    now = utcnow()
    query = User.query.filter(User.role == ROLE_MEMBER)
    if show == "verified":
        query = query.filter(User.is_verified.is_(True))
    elif show == "unverified":
        query = query.filter(User.is_verified.is_(False))
    elif show == "suspended":
        query = query.filter(User.suspended_until > now)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(User.first_name.ilike(like), User.last_name.ilike(like),
                                 User.email.ilike(like), User.phone.ilike(like)))
    items = query.order_by(User.created_at.desc()).limit(300).all()
    base = User.query.filter(User.role == ROLE_MEMBER)
    counts = {
        "all": base.count(),
        "verified": base.filter(User.is_verified.is_(True)).count(),
        "unverified": base.filter(User.is_verified.is_(False)).count(),
        "suspended": base.filter(User.suspended_until > now).count(),
    }
    return render_template("admin/users.html", items=items, show=show, q=q, counts=counts,
                           filters=USER_FILTERS)


def _member_or_404(user_id: int) -> User:
    user = db.session.get(User, user_id)
    if user is None or user.is_admin:
        abort(404)
    return user


@bp.route("/users/<int:user_id>")
@admin_required
def user_detail(user_id: int):
    user = _member_or_404(user_id)
    wallet = wallet_service.get_or_create_wallet(user.id)
    db.session.commit()
    rating_avg, rating_count = db.session.query(func.avg(Rating.stars), func.count(Rating.id)) \
        .filter(Rating.ratee_id == user.id).one()
    stats = {
        "posted": user.posted_quests.count(),
        "doing": Quest.query.filter_by(worker_id=user.id).count(),
        "applications": user.applications.count(),
        "rating": round(float(rating_avg), 1) if rating_avg else None,
        "rating_count": rating_count,
    }
    recent_quests = user.posted_quests.order_by(Quest.created_at.desc()).limit(10).all()
    return render_template("admin/user_detail.html", user=user, wallet=wallet, stats=stats,
                           recent_quests=recent_quests, held=held_total(user.id),
                           units=admin_service.DURATION_UNITS)


@bp.route("/users/<int:user_id>/suspend", methods=["POST"])
@admin_required
def suspend_user(user_id: int):
    user = _member_or_404(user_id)
    try:
        admin_service.suspend(user, g.user, request.form.get("amount"), request.form.get("unit", ""),
                              request.form.get("reason", ""))
    except admin_service.AdminError as err:
        flash(str(err), "danger")
        return redirect(url_for("admin.user_detail", user_id=user.id))
    db.session.commit()
    flash(f"{user.full_name} is suspended until {local_dt(user.suspended_until)}.", "success")
    return redirect(url_for("admin.user_detail", user_id=user.id))


@bp.route("/users/<int:user_id>/unsuspend", methods=["POST"])
@admin_required
def unsuspend_user(user_id: int):
    user = _member_or_404(user_id)
    try:
        admin_service.lift_suspension(user, g.user)
    except admin_service.AdminError as err:
        flash(str(err), "danger")
        return redirect(url_for("admin.user_detail", user_id=user.id))
    db.session.commit()
    flash(f"{user.full_name}'s suspension was lifted. They can log in again.", "success")
    return redirect(url_for("admin.user_detail", user_id=user.id))


@bp.route("/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id: int):
    user = _member_or_404(user_id)
    name, email = user.full_name, user.email
    if (request.form.get("confirm_email") or "").strip().lower() != email.lower():
        flash("Type the user's email exactly to confirm deleting the account.", "warning")
        return redirect(url_for("admin.user_detail", user_id=user.id))
    try:
        summary = admin_service.delete_user(user, g.user)
    except admin_service.AdminError as err:
        db.session.rollback()
        flash(str(err), "danger")
        return redirect(url_for("admin.user_detail", user_id=user_id))
    extra = []
    if summary["removed_quests"]:
        extra.append(f"{summary['removed_quests']} posted quest(s) removed")
    if summary["reopened"]:
        extra.append(f"{summary['reopened']} quest(s) they were doing reopened and refunded to the clients")
    flash(f"The account of {name} ({email}) was deleted." + (" " + "; ".join(extra) + "." if extra else ""),
          "success")
    return redirect(url_for("admin.users"))
