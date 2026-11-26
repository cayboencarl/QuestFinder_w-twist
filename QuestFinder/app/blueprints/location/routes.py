"""Set my location: GPS (Geolocation API) with a manual map-pin fallback."""
from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from app.extensions import db
from app.services.geo_service import is_valid_coordinate
from app.utils.auth import member_required

bp = Blueprint("location", __name__, url_prefix="/location")


def _safe_next(default: str) -> str:
    nxt = request.values.get("next", "")
    return nxt if nxt.startswith("/") and not nxt.startswith("//") else default


@bp.route("/", methods=["GET", "POST"])
@member_required
def set_location():
    next_url = _safe_next(url_for("profile.settings"))
    if request.method == "POST":
        lat, lng = request.form.get("latitude"), request.form.get("longitude")
        label = (request.form.get("label") or "").strip()[:255] or "Pinned location"
        if not is_valid_coordinate(lat, lng):
            flash("Set your location with GPS or by placing the pin on the map.", "warning")
            return redirect(url_for("location.set_location", next=next_url))
        g.user.set_location(float(lat), float(lng), label)
        db.session.commit()
        flash("Location saved. Quests are now sorted by distance from here.", "success")
        return redirect(next_url)
    return render_template("location/set.html", next_url=next_url, back_url=url_for("profile.settings"))
