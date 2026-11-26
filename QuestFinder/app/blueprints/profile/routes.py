"""Profile (top-left of Home) and Settings (top-right of Home)."""
from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from app.blueprints.profile.forms import PasswordForm, ProfileForm
from app.extensions import db
from app.models.quest import QUEST_COMPLETED, Quest
from app.models.user import User
from app.services import rating_service, upload_service
from app.utils import skills as skill_list
from app.utils.auth import login_required, member_required

bp = Blueprint("profile", __name__)


@bp.route("/u/<int:user_id>")
@login_required
def view(user_id: int):
    person = db.session.get(User, user_id)
    if person is None or person.is_admin or not person.is_active:
        abort(404)
    stats = {
        "rating": rating_service.summary(person.id),
        "posted": person.posted_quests.count(),
        "completed": Quest.query.filter_by(worker_id=person.id, status=QUEST_COMPLETED).count(),
    }
    return render_template("profile/view.html", person=person, stats=stats,
                           reviews=rating_service.recent_reviews(person.id),
                           is_me=person.id == g.user.id, back_url=url_for("main.home"))


@bp.route("/profile/edit", methods=["GET", "POST"])
@member_required
def edit():
    user = g.user
    form = ProfileForm(obj=user)
    if request.method == "GET":
        form.skills.data = skill_list.parse(user.skills)
    if user.is_verified:
        # Names were checked against the ID; they can no longer be changed here.
        form.first_name.render_kw = form.last_name.render_kw = {"readonly": True}
    if form.validate_on_submit():
        if not user.is_verified:
            user.first_name, user.last_name = form.first_name.data, form.last_name.data
        user.phone = form.phone.data or None
        user.skills = skill_list.join(form.skills.data or [])
        user.bio = (form.bio.data or "").strip() or None
        if form.avatar.data:
            try:
                new_name = upload_service.save_image(form.avatar.data, "avatars")
            except upload_service.UploadError as err:
                form.avatar.errors.append(str(err))
                return render_template("profile/edit.html", form=form, skill_groups=skill_list.SKILL_GROUPS,
                                       back_url=url_for("profile.view", user_id=user.id))
            upload_service.delete("avatars", user.avatar_filename)
            user.avatar_filename = new_name
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("profile.view", user_id=user.id))
    return render_template("profile/edit.html", form=form, skill_groups=skill_list.SKILL_GROUPS,
                           back_url=url_for("profile.view", user_id=user.id))


@bp.route("/settings")
@login_required
def settings():
    return render_template("profile/settings.html", back_url=url_for("main.home"))


@bp.route("/settings/password", methods=["GET", "POST"])
@login_required
def change_password():
    form = PasswordForm()
    if form.validate_on_submit():
        if not g.user.check_password(form.current.data):
            form.current.errors.append("Your current password is incorrect.")
        else:
            g.user.set_password(form.new.data)
            db.session.commit()
            flash("Password changed.", "success")
            return redirect(url_for("profile.settings"))
    return render_template("profile/password.html", form=form, back_url=url_for("profile.settings"))
