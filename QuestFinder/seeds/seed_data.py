"""Seed data and admin CLI commands.

    flask seed            # load demo data into an empty database
    flask seed --reset    # wipe every table first, then load demo data
    flask create-admin    # create a Barangay Admin account interactively

Passwords come from .env (SEED_USER_PASSWORD, ADMIN_PASSWORD); none are hard-coded.
"""
import os
import random
from datetime import date, timedelta
from decimal import Decimal

import click
from flask import current_app
from sqlalchemy import text

from app.extensions import db
from app.models import (
    Conversation, Message, Notification, Quest, QuestApplication, Rating, User,
)
from app.models.base import utcnow
from app.models.notification import NOTIF_QUEST_ACCEPTED_BY_WORKER, NOTIF_WORKER_CONFIRMED
from app.models.quest import APP_ACCEPTED, APP_PENDING, PAYMENT_HELD, PAYMENT_RELEASED, QUEST_COMPLETED
from app.models.user import ROLE_ADMIN, age_on
from app.services import wallet_service
from app.services.boundary_service import approximate_inside, contains

# Barangay San Vicente centre ≈ 16.3954, 120.5968 (PhilAtlas).
CENTER = (16.3954, 120.5968)

DEMO_USERS = [
    # key, first, last, email, birthdate, skills, offset (lat, lng) from centre
    ("carl", "Carl", "Cayboen", "carl@questfinder.test", date(1998, 4, 12),
     "Store helper, Inventory counting", (0.0012, -0.0009)),
    ("aldous", "Aldous", "Hernandez", "aldous@questfinder.test", date(2001, 9, 3),
     "Gardening, Cooking & food prep", (-0.0012, 0.0016)),
    ("marc", "Marc", "Icasiam", "marc@questfinder.test", date(2000, 1, 25),
     "Store helper, Computer & Wi-Fi setup", (-0.0008, 0.0024)),
    ("jake", "Jake", "Dela Cruz", "jake@questfinder.test", date(2004, 6, 18),
     "Plumbing, Gardening, Errands & grocery runs", (0.0016, -0.0016)),
    ("dave", "Dave", "Bautista", "dave@questfinder.test", date(1995, 11, 2),
     "Plumbing, Carpentry, Painting", (-0.0004, -0.0010)),
    ("bea", "Bea", "Santos", "bea@questfinder.test", date(2005, 2, 14),
     "House cleaning, Tutoring", (0.0014, -0.0004)),
]

# Bea is left unverified so the ID + face verification flow can be demonstrated.
UNVERIFIED = {"bea"}

TABLES = [
    "ratings", "messages", "conversations", "notifications", "transactions",
    "quest_applications", "quests", "wallets", "verification_requests", "users",
]


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise click.ClickException(f"{name} is not set. Add it to your .env file.")
    if len(value) < 8:
        raise click.ClickException(f"{name} must be at least 8 characters.")
    return value


def _point(offset):
    return round(CENTER[0] + offset[0], 6), round(CENTER[1] + offset[1], 6)


def _make_quest(rng, client, *, title, description, qualification, pay, minutes, offset, label,
                created_days_ago=0):
    lat, lng = _point(offset)
    assert contains(lat, lng), f"seed quest {title} must be inside Brgy. San Vicente"
    a_lat, a_lng = approximate_inside(lat, lng, current_app.config["APPROX_LOCATION_METERS"], rng)
    quest = Quest(
        client_id=client.id, title=title, description=description, qualification=qualification,
        pay=Decimal(pay), duration_minutes=minutes,
        latitude=lat, longitude=lng, location_label=label,
        approx_latitude=a_lat, approx_longitude=a_lng,
    )
    quest.created_at = utcnow() - timedelta(days=created_days_ago, hours=rng.randint(1, 8))
    db.session.add(quest)
    db.session.flush()
    return quest


def load_demo_data() -> dict:
    rng = random.Random(2026)  # deterministic approximate points
    password = _require_env("SEED_USER_PASSWORD")

    # --- Barangay Admin ---------------------------------------------------------
    admin = User(first_name="Barangay", last_name="Admin",
                 email=os.getenv("ADMIN_EMAIL", "admin@questfinder.test").lower(),
                 birthdate=date(1985, 1, 1), role=ROLE_ADMIN, is_verified=True, verified_at=utcnow())
    admin.set_password(_require_env("ADMIN_PASSWORD"))
    db.session.add(admin)

    # --- Members ------------------------------------------------------------------
    users = {}
    for key, first, last, email, bday, skills, offset in DEMO_USERS:
        assert age_on(bday, date.today()) >= 18, f"seed user {key} must be 18+"
        lat, lng = _point(offset)
        user = User(first_name=first, last_name=last, email=email, birthdate=bday, skills=skills,
                    phone="09" + "".join(str(rng.randint(0, 9)) for _ in range(9)))
        user.set_password(password)
        user.set_location(lat, lng, "Brgy. San Vicente, Baguio City")
        if key not in UNVERIFIED:
            user.is_verified = True
            user.verified_at = utcnow()
        db.session.add(user)
        users[key] = user
    db.session.flush()
    for user in users.values():
        wallet_service.get_or_create_wallet(user.id)

    carl, aldous, marc, jake, dave = (users[k] for k in ("carl", "aldous", "marc", "jake", "dave"))

    # --- Wallet top-ups -------------------------------------------------------------
    max_dep = current_app.config["MAX_DEPOSIT"]
    wallet_service.deposit(carl.id, "1821", "GCash", max_dep)
    wallet_service.deposit(aldous.id, "800", "Maya", max_dep)
    wallet_service.deposit(marc.id, "1500", "GCash", max_dep)

    # --- Open quests (samples from the prototype) -----------------------------------
    clean_roots = _make_quest(
        rng, carl, title="Clean Roots",
        description="Clean and remove weeds, dried leaves, and unwanted plants from the garden and front yard.",
        qualification="Physically fit, willing to do outdoor work, and able to use basic gardening tools. No experience required.",
        pay="160", minutes=60, offset=(0.0012, -0.0009), label="Near San Vicente Elementary School gate",
    )
    _make_quest(
        rng, marc, title="Router Config",
        description="Set up a new Wi-Fi router for the store, change the password, and connect two phones and a laptop.",
        qualification="Knows basic router and Wi-Fi settings. Must bring own phone for testing.",
        pay="260", minutes=45, offset=(-0.0008, 0.0024), label="Marc's sari-sari store, along the barangay road",
    )
    _make_quest(
        rng, aldous, title="Carry Groceries Uphill",
        description="Help carry 6 bags of groceries from the jeepney stop up the stairs to the house.",
        qualification="Able to carry up to 10 kg and climb stairs.",
        pay="120", minutes=30, offset=(-0.0012, 0.0016), label="Jeepney stop near the barangay hall",
        created_days_ago=1,
    )
    _make_quest(
        rng, marc, title="Repaint Store Sign",
        description="Repaint a 1 m × 2 m wooden store sign. Paint and brushes are provided.",
        qualification="Neat handwriting or basic lettering skills.",
        pay="450", minutes=180, offset=(-0.0006, 0.0027), label="Marc's sari-sari store",
        created_days_ago=2,
    )

    # Pending application: Jake accepted Clean Roots, waiting for Carl's decision.
    db.session.add(QuestApplication(quest_id=clean_roots.id, worker_id=jake.id, status=APP_PENDING,
                                    message="I can do this tomorrow morning.", distance_km=0.37))
    db.session.add(Notification(user_id=carl.id, kind=NOTIF_QUEST_ACCEPTED_BY_WORKER,
                                message="Jake Dela Cruz accepted your quest “Clean Roots”. Review it now.",
                                link=f"/quests/{clean_roots.id}/applicants"))

    # --- Assigned quest with an open chat (Carl ↔ Jake) ---------------------------------
    faucet = _make_quest(
        rng, carl, title="Fix Leaking Faucet",
        description="The kitchen faucet keeps dripping. Replace the washer or the faucet head.",
        qualification="Basic plumbing. Bring own wrench if possible.",
        pay="200", minutes=60, offset=(0.0012, -0.0009), label="Carl's house, blue gate beside the chapel",
        created_days_ago=1,
    )
    db.session.add(QuestApplication(quest_id=faucet.id, worker_id=jake.id, status=APP_ACCEPTED,
                                    message="I've fixed faucets before.", distance_km=0.38))
    faucet.mark_assigned(jake.id)
    wallet_service.hold_for_quest(carl.id, faucet)
    faucet.payment_status = PAYMENT_HELD
    convo = Conversation(quest_id=faucet.id, client_id=carl.id, worker_id=jake.id)
    db.session.add(convo)
    db.session.flush()
    for sender, body in [
        (carl, "Hi Jake! Can you come at 3 PM today?"),
        (jake, "Hello po! Yes, 3 PM works. I'll bring my wrench."),
        (carl, "Great, the blue gate beside the chapel."),
        (jake, "On my way po."),
    ]:
        db.session.add(Message(conversation_id=convo.id, sender_id=sender.id, body=body))
    convo.last_message_at = utcnow()
    db.session.add(Notification(user_id=jake.id, kind=NOTIF_WORKER_CONFIRMED, is_read=True,
                                message="Carl Cayboen accepted you for “Fix Leaking Faucet”. Chat is now open.",
                                link=f"/quests/{faucet.id}"))

    # --- Completed quest with two-way ratings (Carl ↔ Dave) ---------------------------------
    gate = _make_quest(
        rng, carl, title="Paint the Gate",
        description="Repaint the front steel gate. Sand off rust spots first.",
        qualification="Experience with painting metal surfaces.",
        pay="300", minutes=150, offset=(0.0012, -0.0009), label="Carl's house",
        created_days_ago=6,
    )
    db.session.add(QuestApplication(quest_id=gate.id, worker_id=dave.id, status=APP_ACCEPTED, distance_km=0.45))
    gate.mark_assigned(dave.id)
    wallet_service.hold_for_quest(carl.id, gate)
    wallet_service.release_to_worker(dave.id, gate)
    gate.status, gate.payment_status, gate.completed_at = QUEST_COMPLETED, PAYMENT_RELEASED, utcnow()
    db.session.add(Conversation(quest_id=gate.id, client_id=carl.id, worker_id=dave.id))
    db.session.add_all([
        Rating(quest_id=gate.id, rater_id=carl.id, ratee_id=dave.id, stars=5,
               comment="Fast and very neat work. Highly recommended!"),
        Rating(quest_id=gate.id, rater_id=dave.id, ratee_id=carl.id, stars=5,
               comment="Clear instructions and paid on time."),
    ])

    db.session.commit()
    return {"admin": admin.email, "members": [u.email for u in users.values()]}


def register_cli(app) -> None:
    @app.cli.command("seed")
    @click.option("--reset", is_flag=True, help="Delete ALL existing data before seeding.")
    def seed_command(reset: bool):
        """Load demo data (users, quests, wallets, chat, ratings)."""
        if reset:
            db.session.execute(text(f"TRUNCATE {', '.join(TABLES)} RESTART IDENTITY CASCADE"))
            db.session.commit()
            click.echo("All tables emptied.")
        elif db.session.query(User.id).first() is not None:
            raise click.ClickException("The database already has users. Use `flask seed --reset` to start over.")
        result = load_demo_data()
        click.secho("Demo data loaded.", fg="green")
        click.echo(f"  Barangay Admin : {result['admin']}  (password = ADMIN_PASSWORD in .env)")
        click.echo("  Members        : " + ", ".join(result["members"]))
        click.echo("                   (password = SEED_USER_PASSWORD in .env; bea@ is unverified)")

    @app.cli.command("create-admin")
    @click.option("--email", prompt=True)
    @click.option("--first-name", prompt=True, default="Barangay")
    @click.option("--last-name", prompt=True, default="Admin")
    @click.password_option()
    def create_admin(email, first_name, last_name, password):
        """Create a Barangay Admin account."""
        email = email.strip().lower()
        if User.query.filter_by(email=email).first():
            raise click.ClickException("That email is already registered.")
        if len(password) < 8:
            raise click.ClickException("Password must be at least 8 characters.")
        admin = User(first_name=first_name, last_name=last_name, email=email,
                     birthdate=date(1990, 1, 1), role=ROLE_ADMIN, is_verified=True, verified_at=utcnow())
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        click.secho(f"Barangay Admin {email} created.", fg="green")

