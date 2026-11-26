"""Application configuration.

Every secret and environment-specific value is read from environment
variables (loaded from .env in development). Nothing sensitive is
hard-coded here.
"""
import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


class BaseConfig:
    # --- Core -------------------------------------------------------------
    SECRET_KEY = os.getenv("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # --- Sessions & cookies ----------------------------------------------
    PERMANENT_SESSION_LIFETIME = timedelta(hours=int(os.getenv("SESSION_HOURS", "12")))
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _bool("SESSION_COOKIE_SECURE", False)

    # --- CSRF (Flask-WTF) ---------------------------------------------------
    WTF_CSRF_TIME_LIMIT = None  # token valid for the whole session

    # --- Uploads ------------------------------------------------------------
    # Uploads live in instance/uploads, which is NOT a public static folder.
    # Files are served through an access-checked route instead.
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", str(BASE_DIR / "instance" / "uploads"))
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_UPLOAD_MB", "8")) * 1024 * 1024
    ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}

    # --- Business rules -----------------------------------------------------
    MINIMUM_AGE = 18  # strict: task workers and clients must be 18+
    REQUIRE_VERIFICATION = _bool("REQUIRE_VERIFICATION", True)
    FACE_MATCH_THRESHOLD = _float("FACE_MATCH_THRESHOLD", 0.55)  # max descriptor distance

    # --- Geolocation (Barangay San Vicente, Baguio City) -------------------
    DEFAULT_MAP_LAT = _float("DEFAULT_MAP_LAT", 16.3954)
    DEFAULT_MAP_LNG = _float("DEFAULT_MAP_LNG", 120.5968)
    DEFAULT_MAP_ZOOM = int(os.getenv("DEFAULT_MAP_ZOOM", "16"))
    APPROX_LOCATION_METERS = int(os.getenv("APPROX_LOCATION_METERS", "300"))
    DEFAULT_RADIUS_KM = _float("DEFAULT_RADIUS_KM", 5)
    # Quests can only be pinned inside the barangay boundary (app/data/san_vicente_boundary.geojson).
    RESTRICT_QUESTS_TO_BARANGAY = _bool("RESTRICT_QUESTS_TO_BARANGAY", True)
    MAP_TILE_URL = os.getenv("MAP_TILE_URL", "https://tile.openstreetmap.org/{z}/{x}/{y}.png")
    MAP_TILE_ATTRIBUTION = os.getenv(
        "MAP_TILE_ATTRIBUTION",
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors')

    # --- Wallet (simulated) -------------------------------------------------
    MAX_DEPOSIT = _float("MAX_DEPOSIT", 50000)
    MAX_WITHDRAW = _float("MAX_WITHDRAW", 50000)
    MIN_QUEST_PAY = _float("MIN_QUEST_PAY", 50)
    MAX_QUEST_PAY = _float("MAX_QUEST_PAY", 20000)


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class TestingConfig(BaseConfig):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URL", os.getenv("DATABASE_URL"))


class ProductionConfig(BaseConfig):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


CONFIGS = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(name: str | None = None):
    name = name or os.getenv("FLASK_ENV_NAME", "development")
    return CONFIGS.get(name, DevelopmentConfig)
