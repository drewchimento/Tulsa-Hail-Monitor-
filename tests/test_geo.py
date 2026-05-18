"""Tests for geo.py — Tulsa 50-mile polygon and intersection logic."""
import math

import pytest
from shapely.geometry import Point

from geo import (
    TULSA_CENTER_LAT,
    TULSA_CENTER_LON,
    RADIUS_MILES,
    tulsa_circle,
    alert_polygon_overlaps_tulsa,
)


def test_tulsa_center_constants():
    assert TULSA_CENTER_LAT == pytest.approx(36.154)
    assert TULSA_CENTER_LON == pytest.approx(-95.993)
    assert RADIUS_MILES == 50.0


def test_tulsa_circle_contains_downtown():
    circle = tulsa_circle()
    downtown = Point(TULSA_CENTER_LON, TULSA_CENTER_LAT)
    assert circle.contains(downtown)


def test_tulsa_circle_excludes_oklahoma_city():
    # OKC is ~100 mi SW of Tulsa
    circle = tulsa_circle()
    okc = Point(-97.5164, 35.4676)
    assert not circle.contains(okc)


def test_tulsa_circle_includes_bartlesville():
    # Bartlesville is ~45 mi N of downtown Tulsa — should be inside the 50-mi radius
    circle = tulsa_circle()
    bartlesville = Point(-95.9808, 36.7473)
    assert circle.contains(bartlesville)


def test_tulsa_circle_excludes_dallas():
    circle = tulsa_circle()
    dallas = Point(-96.7970, 32.7767)
    assert not circle.contains(dallas)


def test_tulsa_circle_radius_north_is_about_50mi():
    """A point exactly 50 mi due north should be near the boundary."""
    circle = tulsa_circle()
    # 50 mi north ≈ 50/69.0 degrees of latitude
    north_50mi = Point(TULSA_CENTER_LON, TULSA_CENTER_LAT + (50.0 / 69.0))
    # Should be just inside or on the boundary
    assert circle.distance(north_50mi) < 0.01  # within ~0.6 mi of the edge
