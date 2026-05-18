"""Geometry helpers for the Tulsa hail monitor.

Builds the 50-mile circle around downtown Tulsa as a polygon and
checks whether NWS alert geometries overlap it.
"""
from __future__ import annotations

import math
import re
from functools import lru_cache
from typing import Any

from shapely.geometry import Point, Polygon, MultiPolygon, shape

TULSA_CENTER_LAT = 36.154
TULSA_CENTER_LON = -95.993
RADIUS_MILES = 50.0

# Conversion constants
MILES_PER_DEG_LATITUDE = 69.0  # ~constant globally


def _miles_per_deg_longitude(latitude_deg: float) -> float:
    """Miles per degree of longitude at a given latitude."""
    return MILES_PER_DEG_LATITUDE * math.cos(math.radians(latitude_deg))


@lru_cache(maxsize=1)
def tulsa_circle() -> Polygon:
    """Return a 72-vertex polygon approximating a 50-mile circle around Tulsa.

    The polygon is computed in (lon, lat) coordinate space with a
    latitude correction so east-west distances are not stretched.
    """
    points = []
    miles_per_deg_lon = _miles_per_deg_longitude(TULSA_CENTER_LAT)
    for angle_deg in range(0, 360, 5):
        angle_rad = math.radians(angle_deg)
        d_lat_deg = (RADIUS_MILES * math.cos(angle_rad)) / MILES_PER_DEG_LATITUDE
        d_lon_deg = (RADIUS_MILES * math.sin(angle_rad)) / miles_per_deg_lon
        points.append((TULSA_CENTER_LON + d_lon_deg, TULSA_CENTER_LAT + d_lat_deg))
    # Close the ring
    points.append(points[0])
    return Polygon(points)


def alert_polygon_overlaps_tulsa(geometry: dict[str, Any] | None) -> bool:
    """Return True if the GeoJSON geometry intersects the 50-mile Tulsa circle."""
    if not geometry:
        return False
    try:
        alert_shape = shape(geometry)
    except Exception:
        return False
    if not isinstance(alert_shape, (Polygon, MultiPolygon)):
        return False
    return alert_shape.intersects(tulsa_circle())


# Counties whose territory is within 50 miles of downtown Tulsa.
# Used as a fallback when an alert has no geometry.
TULSA_METRO_COUNTIES = frozenset({
    "Tulsa", "Rogers", "Wagoner", "Creek", "Osage",
    "Mayes", "Okmulgee", "Pawnee", "Washington", "Nowata",
})

# Match a county name as a standalone word (so "Tulsahoma" won't match "Tulsa").
_COUNTY_WORD_RE = re.compile(r"\b([A-Za-z]+)\b")


def areadesc_overlaps_tulsa(area_desc: str | None) -> bool:
    """Return True if any Tulsa-metro county name appears in the area description."""
    if not area_desc:
        return False
    words = {w.title() for w in _COUNTY_WORD_RE.findall(area_desc)}
    return bool(words & TULSA_METRO_COUNTIES)
