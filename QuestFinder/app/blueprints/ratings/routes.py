"""Rate the other person after a quest is completed."""
from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from app.extensions import db
from app.models.quest import Quest
from app.models.rating import Rating
from app.services import rating_service
from app.utils.auth import member_required

bp = Blueprint("ratings", __name__, url_prefix="/quests")


@bp.route("/<int:quest_id>/rate", methods=["GET", "POST"])
@member_required
def rate(quest_id: int):
    quest = db.session.get(Quest, quest_id)
    if quest is None or not quest.is_participant(g.user):
        abort(404)
    other = quest.worker if g.user.id == quest.client_id else quest.client
    existing = Rating.query.filter_by(quest_id=quest.id, rater_id=g.user.id).first()
    if request.method == "POST":
        try:
            rating_service.submit(quest, g.user, request.form.get("stars", type=int) or 0,
                                  request.form.get("comment"))
        except rating_service.RatingError as err:
            flash(str(err), "warning")
            return redirect(url_for("ratings.rate", quest_id=quest.id))
        flash(f"Thanks! Your rating for {other.first_name} was saved.", "success")
        return redirect(url_for("quests.detail", quest_id=quest.id))
    return render_template("ratings/rate.html", quest=quest, other=other, existing=existing,
                           role="task worker" if g.user.id == quest.client_id else "client",
                           back_url=url_for("quests.detail", quest_id=quest.id), active_tab="home")
