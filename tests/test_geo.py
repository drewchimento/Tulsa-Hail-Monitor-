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
    areadesc_overlaps_tulsa,
    TULSA_METRO_COUNTIES,
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


def test_alert_polygon_over_tulsa_overlaps(fixture_loader):
    alert = fixture_loader("alert_tulsa_hail.json")
    assert alert_polygon_overlaps_tulsa(alert["geometry"]) is True


def test_alert_polygon_over_dallas_does_not_overlap(fixture_loader):
    alert = fixture_loader("alert_dallas_hail.json")
    assert alert_polygon_overlaps_tulsa(alert["geometry"]) is False


def test_alert_polygon_clipping_50mi_edge_overlaps():
    """A polygon centered near Bartlesville should clip the 50-mi radius."""
    geometry = {
        "type": "Polygon",
        "coordinates": [[
            [-96.10, 36.70],
            [-95.85, 36.70],
            [-95.85, 36.80],
            [-96.10, 36.80],
            [-96.10, 36.70],
        ]],
    }
    assert alert_polygon_overlaps_tulsa(geometry) is True


def test_null_geometry_returns_false():
    assert alert_polygon_overlaps_tulsa(None) is False


def test_empty_dict_geometry_returns_false():
    assert alert_polygon_overlaps_tulsa({}) is False


def test_point_geometry_returns_false():
    """Geometries that aren't polygons (e.g. Point) should not match."""
    geometry = {"type": "Point", "coordinates": [-95.993, 36.154]}
    assert alert_polygon_overlaps_tulsa(geometry) is False


def test_multipolygon_with_one_overlapping_part():
    geometry = {
        "type": "MultiPolygon",
        "coordinates": [
            [[[-96.90, 32.65], [-96.65, 32.65], [-96.65, 32.85], [-96.90, 32.85], [-96.90, 32.65]]],
            [[[-96.10, 36.10], [-95.85, 36.10], [-95.85, 36.25], [-96.10, 36.25], [-96.10, 36.10]]],
        ],
    }
    assert alert_polygon_overlaps_tulsa(geometry) is True


def test_tulsa_metro_counties_includes_known_counties():
    expected = {"Tulsa", "Rogers", "Wagoner", "Creek", "Osage",
                "Mayes", "Okmulgee", "Pawnee", "Washington", "Nowata"}
    assert expected.issubset(TULSA_METRO_COUNTIES)


def test_areadesc_with_tulsa_returns_true():
    assert areadesc_overlaps_tulsa("Tulsa, OK") is True


def test_areadesc_with_multiple_counties_returns_true():
    assert areadesc_overlaps_tulsa("Wagoner, OK; Mayes, OK") is True


def test_areadesc_with_dallas_returns_false():
    assert areadesc_overlaps_tulsa("Dallas, TX") is False


def test_areadesc_empty_returns_false():
    assert areadesc_overlaps_tulsa("") is False


def test_areadesc_none_returns_false():
    assert areadesc_overlaps_tulsa(None) is False


def test_areadesc_case_insensitive():
    assert areadesc_overlaps_tulsa("tulsa, ok") is True


def test_areadesc_only_matches_whole_word():
    """'Tulsahoma' (made up) should NOT match 'Tulsa'."""
    assert areadesc_overlaps_tulsa("Tulsahoma County, OK") is False
