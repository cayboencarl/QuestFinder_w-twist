"""Jinja filters and globals."""
from datetime import datetime, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from flask import g, url_for
from werkzeug.routing import BuildError

from app.services.geo_service import format_km

LOCAL_TZ = ZoneInfo("Asia/Manila")


def peso(value) -> str:
    if value is None:
        return "₱0"
    value = Decimal(str(value))
    if value == value.to_integral_value():
        return f"₱{value:,.0f}"
    return f"₱{value:,.2f}"


def local_dt(value: datetime | None, fmt: str = "%b %d, %Y %I:%M %p") -> str:
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(LOCAL_TZ).strftime(fmt)


def time_ago(value: datetime | None) -> str:
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    seconds = int((datetime.now(timezone.utc) - value).total_seconds())
    if seconds < 60:
        return "just now"
    for unit, size in (("d", 86400), ("h", 3600), ("m", 60)):
        if seconds >= size:
            return f"{seconds // size}{unit} ago"
    return ""


def duration(minutes: int | None) -> str:
    if not minutes:
        return ""
    if minutes < 60:
        return f"{minutes} mins"
    hours, mins = divmod(minutes, 60)
    label = f"{hours} hr" + ("s" if hours > 1 else "")
    return f"{label} {mins} mins" if mins else label


def link_to(endpoint: str, **values) -> str:
    """url_for that returns '#' for a page that is not built yet (used only in shared layout)."""
    try:
        return url_for(endpoint, **values)
    except BuildError:
        return "#"


def register(app) -> None:
    app.jinja_env.filters.update(peso=peso, local_dt=local_dt, time_ago=time_ago,
                                 duration=duration, km=format_km)
    from app.services import boundary_service
    app.jinja_env.globals.update(link_to=link_to, barangay_boundary=boundary_service.latlngs,
                                 barangay_name=boundary_service.BARANGAY_NAME)

    @app.context_processor
    def inject_globals():
        user = g.get("user")
        unread_notifications = unread_messages = 0
        if user is not None and not user.is_admin:
            from app.services.chat_service import unread_count
            unread_notifications = user.notifications.filter_by(is_read=False).count()
            unread_messages = unread_count(user)
        return {
            "current_user": user,
            "unread_notifications": unread_notifications,
            "unread_messages": unread_messages,
            "map_defaults": {
                "lat": app.config["DEFAULT_MAP_LAT"],
                "lng": app.config["DEFAULT_MAP_LNG"],
                "zoom": app.config["DEFAULT_MAP_ZOOM"],
            },
            "map_tiles": {
                "url": app.config["MAP_TILE_URL"],
                "attribution": app.config["MAP_TILE_ATTRIBUTION"],
            },
        }
