"""Quests: Post (client), Quest list + map (task worker), details, applicants, my quests."""
from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, url_for

from app.blueprints.quests.forms import ApplyForm, QuestForm
from app.extensions import db
from app.models.quest import (
    APP_PENDING, QUEST_ASSIGNED, QUEST_COMPLETED, QUEST_OPEN, Quest, QuestApplication,
)
from app.models.rating import Rating
from app.services import quest_service, rating_service, upload_service, wallet_service
from app.utils.auth import member_required, verified_required

bp = Blueprint("quests", __name__, url_prefix="/quests")


def _get_quest(quest_id: int) -> Quest:
    quest = db.session.get(Quest, quest_id)
    if quest is None:
        abort(404)
    return quest


# --------------------------------------------------------------------------- Post (client)

@bp.route("/new", methods=["GET", "POST"])
@verified_required
def new():
    form = QuestForm()
    if request.method == "GET" and g.user.has_location:
        form.latitude.data, form.longitude.data = g.user.latitude, g.user.longitude
        if g.user.location_label and g.user.location_label != "Pinned location":
            form.location_label.data = g.user.location_label
    if form.validate_on_submit():
        try:
            quest = quest_service.create_quest(
                g.user, title=form.title.data, description=form.description.data,
                qualification=form.qualification.data, pay=form.pay.data,
                duration_minutes=form.duration_minutes.data, latitude=form.latitude.data,
                longitude=form.longitude.data, location_label=form.location_label.data,
                photo=form.photo.data or None,
            )
        except (quest_service.QuestError, upload_service.UploadError, wallet_service.WalletError) as err:
            flash(str(err), "danger")
        else:
            flash("Your quest is published! Nearby task workers can now see it.", "success")
            return redirect(url_for("quests.detail", quest_id=quest.id))
    balance = wallet_service.get_or_create_wallet(g.user.id).balance
    return render_template("quests/new.html", form=form, balance=balance,
                           back_url=url_for("main.home"), active_tab="home")


# --------------------------------------------------------------------------- Quest (task worker)

@bp.route("/")
@member_required
def browse():
    if not g.user.has_location:
        flash("Set your location first so we can show how far each quest is.", "info")
        return redirect(url_for("location.set_location", next=url_for("quests.browse")))
    try:
        radius = float(request.args.get("radius", current_app.config["DEFAULT_RADIUS_KM"]))
    except ValueError:
        radius = current_app.config["DEFAULT_RADIUS_KM"]
    sort = request.args.get("sort", "nearest")
    if sort not in quest_service.SORTS:
        sort = "nearest"
    q = (request.args.get("q") or "").strip()[:60]
    min_pay = request.args.get("min_pay") or None
    results = quest_service.search_open_quests(g.user, radius_km=radius, sort=sort, q=q, min_pay=min_pay)
    markers = [{"id": r.quest.id, "lat": r.lat, "lng": r.lng, "title": r.quest.title,
                "pay": float(r.quest.pay), "km": round(r.distance_km, 2) if r.distance_km is not None else None,
                "url": url_for("quests.detail", quest_id=r.quest.id)} for r in results]
    return render_template("quests/browse.html", results=results, markers=markers, radius=radius,
                           sort=sort, q=q, min_pay=min_pay or "", sorts=quest_service.SORTS,
                           radii=quest_service.RADII, back_url=url_for("main.home"), active_tab="home")


@bp.route("/<int:quest_id>")
@member_required
def detail(quest_id: int):
    quest = _get_quest(quest_id)
    me = g.user
    is_client = quest.client_id == me.id
    is_worker = quest.worker_id == me.id
    # Cancelled/finished quests are only visible to the people involved.
    if quest.status != QUEST_OPEN and not (is_client or is_worker):
        flash("This quest is no longer available.", "info")
        return redirect(url_for("quests.browse"))

    lat, lng, exact = quest_service.point_for(quest, me)
    my_app = QuestApplication.query.filter_by(quest_id=quest.id, worker_id=me.id).first()
    already_rated = Rating.query.filter_by(quest_id=quest.id, rater_id=me.id).first() is not None
    return render_template(
        "quests/detail.html", quest=quest, is_client=is_client, is_worker=is_worker,
        point={"lat": lat, "lng": lng, "exact": exact,
               "radius": current_app.config["APPROX_LOCATION_METERS"]},
        distance=quest_service.distance_for(quest, me), my_app=my_app,
        pending_count=quest.applications.filter_by(status=APP_PENDING).count(),
        client_rating=rating_service.summary(quest.client_id), already_rated=already_rated,
        apply_form=ApplyForm(), back_url=request.referrer if request.referrer and "/quests" in request.referrer
        else url_for("quests.browse"), active_tab="home",
    )


@bp.route("/<int:quest_id>/accept", methods=["POST"])
@verified_required
def apply(quest_id: int):
    quest = _get_quest(quest_id)
    form = ApplyForm()
    if not form.validate_on_submit():
        abort(400)
    try:
        quest_service.apply(quest, g.user, form.message.data or "")
    except quest_service.QuestError as err:
        flash(str(err), "warning")
    else:
        flash("Quest accepted! The client will review it. You'll get a notification once they confirm you.",
              "success")
    return redirect(url_for("quests.detail", quest_id=quest.id))


@bp.route("/applications/<int:app_id>/withdraw", methods=["POST"])
@member_required
def withdraw(app_id: int):
    application = db.session.get(QuestApplication, app_id) or abort(404)
    try:
        quest_service.withdraw(application, g.user)
    except quest_service.QuestError as err:
        flash(str(err), "warning")
    else:
        flash("You withdrew from this quest.", "info")
    return redirect(url_for("quests.detail", quest_id=application.quest_id))


# --------------------------------------------------------------------------- client actions

@bp.route("/<int:quest_id>/applicants")
@member_required
def applicants(quest_id: int):
    quest = _get_quest(quest_id)
    if quest.client_id != g.user.id:
        abort(403)
    apps = quest.applications.order_by(QuestApplication.status != APP_PENDING,
                                       QuestApplication.distance_km.asc().nulls_last()).all()
    ratings = {a.worker_id: rating_service.summary(a.worker_id) for a in apps}
    balance = wallet_service.get_or_create_wallet(g.user.id).balance
    return render_template("quests/applicants.html", quest=quest, apps=apps, ratings=ratings,
                           balance=balance, back_url=url_for("quests.detail", quest_id=quest.id),
                           active_tab="home")


@bp.route("/<int:quest_id>/applicants/<int:app_id>/<any(accept, decline):action>", methods=["POST"])
@verified_required
def decide(quest_id: int, app_id: int, action: str):
    quest = _get_quest(quest_id)
    application = db.session.get(QuestApplication, app_id) or abort(404)
    try:
        if action == "accept":
            convo = quest_service.accept_worker(quest, application, g.user)
            flash(f"{application.worker.full_name} is your task worker. ₱{quest.pay:,.2f} is reserved "
                  "from your wallet until you mark the quest as completed.", "success")
            return redirect(url_for("messages.thread", convo_id=convo.id))
        quest_service.decline_application(quest, application, g.user)
        flash("Declined.", "info")
    except quest_service.QuestError as err:
        flash(str(err), "danger")
    return redirect(url_for("quests.applicants", quest_id=quest.id))


@bp.route("/<int:quest_id>/complete", methods=["POST"])
@member_required
def complete(quest_id: int):
    quest = _get_quest(quest_id)
    try:
        quest_service.complete(quest, g.user)
    except quest_service.QuestError as err:
        flash(str(err), "danger")
        return redirect(url_for("quests.detail", quest_id=quest.id))
    flash("Quest completed and the pay was released to your task worker. Please rate them.", "success")
    return redirect(url_for("ratings.rate", quest_id=quest.id))


@bp.route("/<int:quest_id>/cancel", methods=["POST"])
@member_required
def cancel(quest_id: int):
    quest = _get_quest(quest_id)
    try:
        quest_service.cancel(quest, g.user)
    except quest_service.QuestError as err:
        flash(str(err), "danger")
        return redirect(url_for("quests.detail", quest_id=quest.id))
    flash("Quest cancelled.", "info")
    return redirect(url_for("quests.mine"))


# --------------------------------------------------------------------------- My quests

@bp.route("/mine")
@member_required
def mine():
    tab = request.args.get("tab", "posted")
    posted = g.user.posted_quests.order_by(
        db.case((Quest.status == QUEST_ASSIGNED, 0), (Quest.status == QUEST_OPEN, 1), else_=2),
        Quest.created_at.desc()).all()
    pending_counts = dict(
        db.session.query(QuestApplication.quest_id, db.func.count(QuestApplication.id))
        .filter(QuestApplication.status == APP_PENDING,
                QuestApplication.quest_id.in_([q.id for q in posted] or [0]))
        .group_by(QuestApplication.quest_id).all())
    applications = g.user.applications.join(Quest).order_by(QuestApplication.updated_at.desc()).all()
    rated = {r.quest_id for r in Rating.query.filter_by(rater_id=g.user.id).all()}
    return render_template("quests/mine.html", tab=tab, posted=posted, pending_counts=pending_counts,
                           applications=applications, rated=rated, QUEST_COMPLETED=QUEST_COMPLETED,
                           back_url=url_for("main.home"), active_tab="home")
