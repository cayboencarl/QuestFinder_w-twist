"""QuestFinder application factory."""
import logging
import os

from flask import Flask, render_template
from flask_wtf.csrf import CSRFError

from app.config import get_config
from app.extensions import csrf, db, migrate


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(get_config(config_name))

    _check_required_settings(app)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db, directory=os.path.join(os.path.dirname(app.root_path), "migrations"))
    csrf.init_app(app)

    from app import models  # noqa: F401  (register models with SQLAlchemy)

    _register_blueprints(app)
    _register_request_hooks(app)
    _register_error_handlers(app)

    from app.utils import template_helpers
    template_helpers.register(app)

    from seeds.seed_data import register_cli
    register_cli(app)

    logging.basicConfig(level=logging.INFO)
    return app


def _check_required_settings(app: Flask) -> None:
    missing = [k for k in ("SECRET_KEY", "SQLALCHEMY_DATABASE_URI") if not app.config.get(k)]
    if missing:
        names = ", ".join("DATABASE_URL" if k == "SQLALCHEMY_DATABASE_URI" else k for k in missing)
        raise RuntimeError(f"Missing required setting(s): {names}. Copy .env.example to .env and fill it in.")


def _register_blueprints(app: Flask) -> None:
    from app.blueprints import ALL_BLUEPRINTS
    for blueprint in ALL_BLUEPRINTS:
        app.register_blueprint(blueprint)


def _register_request_hooks(app: Flask) -> None:
    from app.utils.auth import load_current_user
    app.before_request(load_current_user)

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        # OpenStreetMap tiles require a Referer, so send the origin (not the full URL) cross-site.
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        # Camera is needed for ID/face scanning, geolocation for quest discovery.
        response.headers.setdefault("Permissions-Policy", "camera=(self), geolocation=(self)")
        return response


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(CSRFError)
    def csrf_error(err):
        return render_template("errors/error.html", code=400,
                               message="Your session expired. Go back, refresh the page and try again."), 400

    @app.errorhandler(403)
    def forbidden(err):
        return render_template("errors/error.html", code=403,
                               message="You don't have permission to open this page."), 403

    @app.errorhandler(404)
    def not_found(err):
        return render_template("errors/error.html", code=404, message="Page not found."), 404

    @app.errorhandler(413)
    def too_large(err):
        mb = app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)
        return render_template("errors/error.html", code=413,
                               message=f"That file is too large. The limit is {mb} MB."), 413

    @app.errorhandler(500)
    def server_error(err):
        db.session.rollback()
        return render_template("errors/error.html", code=500,
                               message="Something went wrong on our side. Please try again."), 500
