"""Barangay boundary: quests can only be pinned inside Brgy. San Vicente.

The boundary polygon is the official administrative boundary from
OpenStreetMap (relation 15790886), saved in app/data/ so it works offline.
"""
import json
import math
import random
from functools import lru_cache
from pathlib import Path

BOUNDARY_FILE = Path(__file__).resolve().parent.parent / "data" / "san_vicente_boundary.geojson"
BARANGAY_NAME = "Brgy. San Vicente"


@lru_cache(maxsize=1)
def polygon() -> list[tuple[float, float]]:
    """Outer ring as [(lat, lng), ...]."""
    data = json.loads(BOUNDARY_FILE.read_text(encoding="utf-8"))
    ring = data["geometry"]["coordinates"][0]
    return [(lat, lng) for lng, lat in ring]


def latlngs() -> list[list[float]]:
    """For Leaflet: [[lat, lng], ...]."""
    return [[lat, lng] for lat, lng in polygon()]


def contains(lat: float, lng: float) -> bool:
    """Ray-casting point-in-polygon test."""
    try:
        lat, lng = float(lat), float(lng)
    except (TypeError, ValueError):
        return False
    pts = polygon()
    inside = False
    j = len(pts) - 1
    for i in range(len(pts)):
        yi, xi = pts[i]
        yj, xj = pts[j]
        if (yi > lat) != (yj > lat):
            x_cross = (xj - xi) * (lat - yi) / (yj - yi) + xi
            if lng < x_cross:
                inside = not inside
        j = i
    return inside


def center() -> tuple[float, float]:
    """A point inside the barangay (centroid of the bounding box, checked)."""
    pts = polygon()
    lat = (min(p[0] for p in pts) + max(p[0] for p in pts)) / 2
    lng = (min(p[1] for p in pts) + max(p[1] for p in pts)) / 2
    return (lat, lng) if contains(lat, lng) else pts[0]


def approximate_inside(lat: float, lng: float, meters: int, rng: random.Random | None = None
                       ) -> tuple[float, float]:
    """Privacy offset (meters/2..meters away) that still lands inside the barangay when possible."""
    from app.services.geo_service import approximate_point
    rng = rng or random.SystemRandom()
    for radius in (meters, meters * 2 // 3, meters // 2, meters // 3):
        for _ in range(25):
            a_lat, a_lng = approximate_point(lat, lng, max(radius, 40), rng)
            if contains(a_lat, a_lng):
                return a_lat, a_lng
    return approximate_point(lat, lng, max(meters // 3, 40), rng)


def nearest_inside_hint(lat: float, lng: float) -> float:
    """Distance (km) from a point to the barangay centre, for error messages."""
    from app.services.geo_service import haversine_km
    c_lat, c_lng = center()
    return haversine_km(lat, lng, c_lat, c_lng) if not math.isnan(lat) else 0.0
