"""Geolocation service — the main emerging technology of QuestFinder.

* Straight-line (great-circle) distance in kilometres using the haversine formula.
* Bounding-box pre-filter so the database only returns quests that can
  possibly fall inside the chosen radius; the exact radius check is then
  done with haversine.
* Approximate (privacy-preserving) location: a random point a few hundred
  metres from the real one, shown to everyone except the client and the
  accepted task worker.
"""
import math
import random

EARTH_RADIUS_KM = 6371.0088


def is_valid_coordinate(lat, lng) -> bool:
    try:
        lat, lng = float(lat), float(lng)
    except (TypeError, ValueError):
        return False
    if math.isnan(lat) or math.isnan(lng):
        return False
    return -90 <= lat <= 90 and -180 <= lng <= 180


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance between two points, in kilometres."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def bounding_box(lat: float, lng: float, radius_km: float) -> tuple[float, float, float, float]:
    """(min_lat, max_lat, min_lng, max_lng) that encloses a circle of radius_km."""
    d_lat = math.degrees(radius_km / EARTH_RADIUS_KM)
    cos_lat = max(math.cos(math.radians(lat)), 1e-6)
    d_lng = math.degrees(radius_km / (EARTH_RADIUS_KM * cos_lat))
    return lat - d_lat, lat + d_lat, lng - d_lng, lng + d_lng


def approximate_point(lat: float, lng: float, meters: int, rng: random.Random | None = None
                      ) -> tuple[float, float]:
    """Return a point between meters/2 and meters away from (lat, lng) in a random direction.

    The minimum offset guarantees the shown point is never the real one.
    """
    rng = rng or random.SystemRandom()
    distance_m = rng.uniform(meters / 2, meters)
    bearing = rng.uniform(0, 2 * math.pi)
    d_lat = (distance_m * math.cos(bearing)) / 111_320
    d_lng = (distance_m * math.sin(bearing)) / (111_320 * max(math.cos(math.radians(lat)), 1e-6))
    return round(lat + d_lat, 6), round(lng + d_lng, 6)


def format_km(km: float | None) -> str:
    if km is None:
        return "—"
    if km < 1:
        return f"{km:.2f} km"
    return f"{km:.1f} km"
