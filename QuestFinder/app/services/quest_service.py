"""Quest business logic: post, search by distance, apply, accept, complete, cancel.

Location privacy: everyone except the client and the accepted task worker only
ever receives the approximate point (approx_latitude/longitude), and distances
for them are computed from that point too.
"""
from dataclasses import dataclass
from decimal import Decimal

from flask import current_app
from sqlalchemy import or_

from app.extensions import db
from app.models.base import utcnow
from app.models.messaging import Conversation
from app.models.notification import (
    NOTIF_QUEST_ACCEPTED_BY_WORKER, NOTIF_QUEST_COMPLETED, NOTIF_WORKER_CONFIRMED,
)
from app.models.user import User
from app.models.quest import (
    APP_ACCEPTED, APP_PENDING, APP_REJECTED, APP_WITHDRAWN, PAYMENT_HELD, PAYMENT_RELEASED,
    QUEST_ASSIGNED, QUEST_CANCELLED, QUEST_COMPLETED, QUEST_OPEN, Quest, QuestApplication,
)
from app.services import boundary_service, geo_service, notification_service, upload_service, wallet_service
from app.services.geo_service import approximate_point, bounding_box, haversine_km


class QuestError(Exception):
    """Business-rule violation, shown to the user."""


SORTS = {"nearest": "Nearest", "pay": "Highest pay", "newest": "Newest"}
RADII = [1, 2, 5, 10, 0]  # 0 = any distance


@dataclass
class QuestResult:
    quest: Quest
    distance_km: float | None
    lat: float
    lng: float
    applied_status: str | None = None


# --------------------------------------------------------------------------- posting

def create_quest(client, *, title, description, qualification, pay, duration_minutes,
                 latitude, longitude, location_label, photo=None) -> Quest:
    if not geo_service.is_valid_coordinate(latitude, longitude):
        raise QuestError("Set the quest location on the map.")
    if current_app.config["RESTRICT_QUESTS_TO_BARANGAY"] and not boundary_service.contains(latitude, longitude):
        raise QuestError(f"Quests can only be pinned inside {boundary_service.BARANGAY_NAME}. "
                         "Move the pin inside the green outline on the map.")
    pay = wallet_service.to_money(pay)
    lo, hi = current_app.config["MIN_QUEST_PAY"], current_app.config["MAX_QUEST_PAY"]
    if not Decimal(str(lo)) <= pay <= Decimal(str(hi)):
        raise QuestError(f"Offered pay must be between ₱{lo:,.0f} and ₱{hi:,.0f}.")

    photo_name = upload_service.save_image(photo, "quests") if photo else None
    lat, lng = float(latitude), float(longitude)
    meters = current_app.config["APPROX_LOCATION_METERS"]
    a_lat, a_lng = (boundary_service.approximate_inside(lat, lng, meters)
                    if current_app.config["RESTRICT_QUESTS_TO_BARANGAY"] else approximate_point(lat, lng, meters))
    quest = Quest(
        client_id=client.id, title=title.strip(), description=description.strip(),
        qualification=qualification.strip(), pay=pay, duration_minutes=int(duration_minutes),
        latitude=lat, longitude=lng, location_label=(location_label or "").strip()[:255] or "Pinned location",
        approx_latitude=a_lat, approx_longitude=a_lng, photo_filename=photo_name,
    )
    db.session.add(quest)
    db.session.commit()
    return quest


# --------------------------------------------------------------------------- viewing

def point_for(quest: Quest, viewer) -> tuple[float, float, bool]:
    """(lat, lng, is_exact) of the quest as this viewer may see it."""
    if quest.can_see_exact_location(viewer):
        return quest.latitude, quest.longitude, True
    return quest.approx_latitude, quest.approx_longitude, False


def distance_for(quest: Quest, viewer) -> float | None:
    if viewer is None or not viewer.has_location:
        return None
    lat, lng, _ = point_for(quest, viewer)
    return haversine_km(viewer.latitude, viewer.longitude, lat, lng)


def search_open_quests(viewer, *, radius_km: float = 5, sort: str = "nearest", q: str = "",
                       min_pay=None, limit: int = 100) -> list[QuestResult]:
    """Open quests near the viewer. The viewer's own quests are excluded (you can't take your own)."""
    query = Quest.query.filter(Quest.status == QUEST_OPEN, Quest.client_id != viewer.id)
    # Quests of a suspended client stay hidden until the suspension ends.
    now = utcnow()
    query = query.join(User, User.id == Quest.client_id).filter(
        or_(User.suspended_until.is_(None), User.suspended_until <= now))

    if q:
        like = f"%{q.strip()}%"
        query = query.filter(or_(Quest.title.ilike(like), Quest.description.ilike(like),
                                 Quest.qualification.ilike(like)))
    if min_pay:
        try:
            query = query.filter(Quest.pay >= wallet_service.to_money(min_pay))
        except wallet_service.WalletError:
            pass

    if radius_km and viewer.has_location:
        # Cheap bounding-box pre-filter in SQL; the exact circle check is done below.
        min_lat, max_lat, min_lng, max_lng = bounding_box(viewer.latitude, viewer.longitude, radius_km)
        query = query.filter(Quest.approx_latitude.between(min_lat, max_lat),
                             Quest.approx_longitude.between(min_lng, max_lng))

    applied = {a.quest_id: a.status for a in
               QuestApplication.query.filter_by(worker_id=viewer.id).all()}

    results = []
    for quest in query.limit(500).all():
        dist = distance_for(quest, viewer)
        if radius_km and dist is not None and dist > radius_km:
            continue
        results.append(QuestResult(quest, dist, quest.approx_latitude, quest.approx_longitude,
                                   applied.get(quest.id)))

    if sort == "pay":
        results.sort(key=lambda r: (-r.quest.pay, r.distance_km or 0))
    elif sort == "newest":
        results.sort(key=lambda r: r.quest.created_at, reverse=True)
    else:
        results.sort(key=lambda r: (r.distance_km is None, r.distance_km or 0))
    return results[:limit]


# --------------------------------------------------------------------------- task worker

def apply(quest: Quest, worker, message: str = "") -> QuestApplication:
    """Task worker taps ACCEPT QUEST."""
    if quest.client_id == worker.id:
        raise QuestError("You can't accept a quest that you posted.")
    if quest.status != QUEST_OPEN:
        raise QuestError("This quest is no longer open.")
    existing = QuestApplication.query.filter_by(quest_id=quest.id, worker_id=worker.id).first()
    if existing and existing.status in (APP_PENDING, APP_ACCEPTED):
        raise QuestError("You already accepted this quest. Wait for the client's response.")
    if existing and existing.status == APP_REJECTED:
        raise QuestError("The client already chose someone else or declined your offer.")

    dist = distance_for(quest, worker)
    if existing:  # previously withdrawn → re-apply
        existing.status, existing.message = APP_PENDING, (message or "").strip()[:300] or None
        existing.distance_km = dist
        app = existing
    else:
        app = QuestApplication(quest_id=quest.id, worker_id=worker.id, status=APP_PENDING,
                               message=(message or "").strip()[:300] or None, distance_km=dist)
        db.session.add(app)
    notification_service.notify(
        quest.client_id, NOTIF_QUEST_ACCEPTED_BY_WORKER,
        f"{worker.full_name} accepted your quest “{quest.title}”. Review and confirm.",
        f"/quests/{quest.id}/applicants")
    db.session.commit()
    return app


def withdraw(application: QuestApplication, worker) -> None:
    if application.worker_id != worker.id:
        raise QuestError("That is not your application.")
    if application.status != APP_PENDING:
        raise QuestError("Only a pending acceptance can be withdrawn.")
    application.status = APP_WITHDRAWN
    db.session.commit()


# --------------------------------------------------------------------------- client

def _locked_quest(quest_id: int) -> Quest:
    return Quest.query.filter_by(id=quest_id).with_for_update().one()


def accept_worker(quest: Quest, application: QuestApplication, client) -> Conversation:
    """Client confirms one worker: pay is reserved, chat opens, the worker is notified."""
    quest = _locked_quest(quest.id)  # lock so two accepts can't happen at once
    if quest.client_id != client.id:
        raise QuestError("Only the client who posted this quest can accept a worker.")
    if quest.status != QUEST_OPEN:
        raise QuestError("This quest already has a task worker.")
    if application.quest_id != quest.id or application.status != APP_PENDING:
        raise QuestError("This acceptance is no longer available.")
    if application.worker_id == client.id:
        raise QuestError("You can't hire yourself.")

    try:
        wallet_service.hold_for_quest(client.id, quest)
    except wallet_service.WalletError as err:
        db.session.rollback()
        raise QuestError(str(err))
    quest.payment_status = PAYMENT_HELD
    quest.mark_assigned(application.worker_id)
    application.status = APP_ACCEPTED
    for other in quest.applications.filter(QuestApplication.id != application.id,
                                           QuestApplication.status == APP_PENDING):
        other.status = APP_REJECTED

    convo = Conversation.query.filter_by(quest_id=quest.id).first()
    if convo is None:
        convo = Conversation(quest_id=quest.id, client_id=client.id, worker_id=application.worker_id)
        db.session.add(convo)
    notification_service.notify(
        application.worker_id, NOTIF_WORKER_CONFIRMED,
        f"{client.full_name} accepted you for “{quest.title}”. The exact location and chat are now open.",
        f"/quests/{quest.id}")
    db.session.commit()
    return convo


def decline_application(quest: Quest, application: QuestApplication, client) -> None:
    if quest.client_id != client.id or application.quest_id != quest.id:
        raise QuestError("You can't change this acceptance.")
    if application.status != APP_PENDING:
        raise QuestError("This acceptance was already handled.")
    application.status = APP_REJECTED
    db.session.commit()


def complete(quest: Quest, client) -> None:
    """Client confirms the work is done: the reserved pay goes to the worker."""
    quest = _locked_quest(quest.id)
    if quest.client_id != client.id:
        raise QuestError("Only the client can mark this quest as completed.")
    if quest.status != QUEST_ASSIGNED or quest.payment_status != PAYMENT_HELD:
        raise QuestError("Only an ongoing quest can be completed.")
    wallet_service.release_to_worker(quest.worker_id, quest)
    quest.status, quest.payment_status, quest.completed_at = QUEST_COMPLETED, PAYMENT_RELEASED, utcnow()
    notification_service.notify(
        quest.worker_id, NOTIF_QUEST_COMPLETED,
        f"“{quest.title}” is completed. {quest.pay:,.2f} pesos were added to your wallet.",
        f"/quests/{quest.id}/rate")
    db.session.commit()


def cancel(quest: Quest, client) -> None:
    """Client cancels a quest that has no task worker yet (nothing was reserved)."""
    quest = _locked_quest(quest.id)
    if quest.client_id != client.id:
        raise QuestError("Only the client can cancel this quest.")
    if quest.status != QUEST_OPEN:
        raise QuestError("Only an open quest (no task worker yet) can be cancelled.")
    quest.status, quest.cancelled_at = QUEST_CANCELLED, utcnow()
    for app in quest.applications.filter_by(status=APP_PENDING):
        app.status = APP_REJECTED
    db.session.commit()


def held_total(client_id: int) -> Decimal:
    total = db.session.query(db.func.coalesce(db.func.sum(Quest.pay), 0)) \
        .filter(Quest.client_id == client_id, Quest.payment_status == PAYMENT_HELD).scalar()
    return Decimal(total)

