"""Blueprint registry. Each feature lives in its own package with routes (and forms)."""
from app.blueprints.admin.routes import bp as admin_bp
from app.blueprints.auth.routes import bp as auth_bp
from app.blueprints.files.routes import bp as files_bp
from app.blueprints.location.routes import bp as location_bp
from app.blueprints.main.routes import bp as main_bp
from app.blueprints.messages.routes import bp as messages_bp
from app.blueprints.notifications.routes import bp as notifications_bp
from app.blueprints.profile.routes import bp as profile_bp
from app.blueprints.quests.routes import bp as quests_bp
from app.blueprints.ratings.routes import bp as ratings_bp
from app.blueprints.verification.routes import bp as verification_bp
from app.blueprints.wallet.routes import bp as wallet_bp

ALL_BLUEPRINTS = [
    main_bp,
    auth_bp,
    profile_bp,
    verification_bp,
    location_bp,
    quests_bp,
    ratings_bp,
    wallet_bp,
    messages_bp,
    notifications_bp,
    admin_bp,
    files_bp,
]
