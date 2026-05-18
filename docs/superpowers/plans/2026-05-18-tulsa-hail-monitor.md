# Tulsa Hail Monitor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a small Python service that emails drew@bytedreams.ai every time the NWS issues a Severe Thunderstorm Warning containing hail inside a 50-mile circle around downtown Tulsa, OK. Run it for free on GitHub Actions cron every 10 minutes.

**Architecture:** Single-repo Python project with five focused modules (`geo`, `nws`, `state`, `notify`, `monitor`). GitHub Actions runs `python monitor.py` on a 10-minute cron, commits the updated state file back to the repo. All secrets via GitHub Secrets (production) or local `.env` (dev). Pytest-driven TDD, ~600 lines of code + tests total.

**Tech Stack:** Python 3.11, `requests`, `shapely`, stdlib `smtplib`, `pytest` (dev), GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-05-17-tulsa-hail-monitor-design.md`

**GitHub repo (already created):** https://github.com/drewchimento/Tulsa-Hail-Monitor-.git

---

## File Structure (built across these tasks)

```
Hail Alert/
├── .git/                                       (exists)
├── .gitignore                                  (exists)
├── .github/
│   └── workflows/
│       └── hail-monitor.yml                    Task 14
├── docs/superpowers/
│   ├── specs/2026-05-17-tulsa-hail-monitor-design.md  (exists)
│   ├── plans/2026-05-18-tulsa-hail-monitor.md         (this file)
│   └── .env/                                   (user's password stash, gitignored)
├── monitor.py                                  Task 12
├── geo.py                                      Tasks 2-4
├── nws.py                                      Tasks 5-7
├── state.py                                    Task 8
├── notify.py                                   Tasks 9-10
├── seen_alerts.json                            Task 8 (empty init)
├── requirements.txt                            Task 1
├── requirements-dev.txt                        Task 1
├── .env.example                                Task 1
├── README.md                                   Task 13
└── tests/
    ├── __init__.py                             Task 1
    ├── conftest.py                             Task 1
    ├── fixtures/
    │   ├── alert_tulsa_hail.json               Task 2
    │   ├── alert_dallas_hail.json              Task 2
    │   ├── alert_no_hail.json                  Task 5
    │   └── alert_no_geometry.json              Task 4
    ├── test_geo.py                             Tasks 2-4
    ├── test_nws.py                             Tasks 5-7
    ├── test_state.py                           Task 8
    ├── test_notify.py                          Tasks 9-10
    └── test_monitor.py                         Task 12
```

Module responsibilities:
- `geo.py` — Build the 50-mile Tulsa polygon. Check alert polygon vs Tulsa polygon. County-name fallback when geometry is missing.
- `nws.py` — Fetch from `api.weather.gov`. Filter for SVR-warning + "hail". Parse hail size from description.
- `state.py` — Load, save, and prune `seen_alerts.json`.
- `notify.py` — Format email subject + body from an alert. Send via Gmail SMTP.
- `monitor.py` — Entry point. CLI flags (`--dry-run`, `--self-test`). Orchestrates the above.

---

## Task 1: Project Skeleton + Python Environment

**Files:**
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `.env.example`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/fixtures/.gitkeep`

- [ ] **Step 1: Verify Python 3.11+ is installed**

Run: `python --version`
Expected: `Python 3.11.x` or higher. If it says 3.10.x or lower, install 3.11+ from python.org first, then re-run.

- [ ] **Step 2: Create virtual environment**

Run: `python -m venv .venv`
Then activate it. On Windows PowerShell: `.venv\Scripts\Activate.ps1`. On Git Bash: `source .venv/Scripts/activate`. Confirm by running `python -c "import sys; print(sys.prefix)"` — should print a path containing `.venv`.

- [ ] **Step 3: Create `requirements.txt`**

```
requests==2.32.3
shapely==2.0.6
python-dotenv==1.0.1
```

- [ ] **Step 4: Create `requirements-dev.txt`**

```
-r requirements.txt
pytest==8.3.3
pytest-mock==3.14.0
responses==0.25.3
freezegun==1.5.1
```

- [ ] **Step 5: Install dev dependencies**

Run: `pip install -r requirements-dev.txt`
Expected: clean install, no errors. Confirm with `python -m pytest --version` → prints `pytest 8.3.3`.

- [ ] **Step 6: Create `.env.example`**

```
# Copy this file to .env and fill in real values for local testing.
# In production, these come from GitHub Secrets, not from a .env file.

SMTP_USER=drew@bytedreams.ai
SMTP_APP_PASSWORD=replace-with-16-char-google-app-password
ALERT_TO_EMAIL=drew@bytedreams.ai
```

- [ ] **Step 7: Create `tests/__init__.py`**

(empty file)

- [ ] **Step 8: Create `tests/conftest.py`**

```python
"""Shared pytest fixtures for the hail monitor."""
import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    """Load a JSON fixture by filename."""
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


@pytest.fixture
def fixture_loader():
    """Returns the load_fixture function."""
    return load_fixture
```

- [ ] **Step 9: Create `tests/fixtures/.gitkeep`**

(empty file — placeholder so git tracks the directory before real fixtures land)

- [ ] **Step 10: Verify pytest discovers the empty test suite**

Run: `python -m pytest tests/ -v`
Expected: `no tests ran in 0.0Xs` (zero tests, exit 5 — totally fine, means pytest works).

- [ ] **Step 11: Commit**

```bash
git add requirements.txt requirements-dev.txt .env.example tests/__init__.py tests/conftest.py tests/fixtures/.gitkeep
git commit -m "Add project skeleton, deps, and pytest config"
```

---

## Task 2: Geometry — Build the 50-Mile Tulsa Polygon

**Files:**
- Create: `geo.py`
- Create: `tests/test_geo.py`
- Create: `tests/fixtures/alert_tulsa_hail.json`
- Create: `tests/fixtures/alert_dallas_hail.json`

- [ ] **Step 1: Create the two geometry fixtures**

Write `tests/fixtures/alert_tulsa_hail.json`:

```json
{
  "id": "urn:oid:2.49.0.1.840.0.test.tulsa.hail",
  "type": "Feature",
  "geometry": {
    "type": "Polygon",
    "coordinates": [[
      [-96.10, 36.10],
      [-95.85, 36.10],
      [-95.85, 36.25],
      [-96.10, 36.25],
      [-96.10, 36.10]
    ]]
  },
  "properties": {
    "id": "urn:oid:2.49.0.1.840.0.test.tulsa.hail",
    "event": "Severe Thunderstorm Warning",
    "headline": "Severe Thunderstorm Warning issued for Tulsa County until 8 PM CDT",
    "description": "At 715 PM CDT, severe thunderstorms were located along a line over Tulsa County. HAZARD - 60 mph wind gusts and quarter size hail (1.00 inch).",
    "areaDesc": "Tulsa, OK; Rogers, OK",
    "expires": "2026-05-18T20:00:00-05:00"
  }
}
```

Write `tests/fixtures/alert_dallas_hail.json`:

```json
{
  "id": "urn:oid:2.49.0.1.840.0.test.dallas.hail",
  "type": "Feature",
  "geometry": {
    "type": "Polygon",
    "coordinates": [[
      [-96.90, 32.65],
      [-96.65, 32.65],
      [-96.65, 32.85],
      [-96.90, 32.85],
      [-96.90, 32.65]
    ]]
  },
  "properties": {
    "id": "urn:oid:2.49.0.1.840.0.test.dallas.hail",
    "event": "Severe Thunderstorm Warning",
    "headline": "Severe Thunderstorm Warning issued for Dallas County until 9 PM CDT",
    "description": "Quarter-sized hail and 60 mph wind gusts.",
    "areaDesc": "Dallas, TX",
    "expires": "2026-05-18T21:00:00-06:00"
  }
}
```

- [ ] **Step 2: Write failing test for `tulsa_circle()` shape**

Write `tests/test_geo.py`:

```python
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
```

- [ ] **Step 3: Run the test, confirm it fails**

Run: `python -m pytest tests/test_geo.py -v`
Expected: `ImportError` / `ModuleNotFoundError: No module named 'geo'`. All tests fail because `geo.py` does not exist.

- [ ] **Step 4: Create `geo.py` with the minimal implementation**

Write `geo.py`:

```python
"""Geometry helpers for the Tulsa hail monitor.

Builds the 50-mile circle around downtown Tulsa as a polygon and
checks whether NWS alert geometries overlap it.
"""
from __future__ import annotations

import math
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
```

- [ ] **Step 5: Run the tests, confirm they pass**

Run: `python -m pytest tests/test_geo.py -v`
Expected: all 6 tests pass.

- [ ] **Step 6: Commit**

```bash
git add geo.py tests/test_geo.py tests/fixtures/alert_tulsa_hail.json tests/fixtures/alert_dallas_hail.json
git commit -m "Add geo module: 50-mile Tulsa circle polygon"
```

---

## Task 3: Geometry — Alert Polygon Overlap Detection

**Files:**
- Modify: `tests/test_geo.py` (append)

- [ ] **Step 1: Add failing tests for alert overlap**

Append to `tests/test_geo.py`:

```python
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
```

- [ ] **Step 2: Run the tests**

Run: `python -m pytest tests/test_geo.py -v`
Expected: all 13 tests pass (the 6 from Task 2 plus the 7 new ones). The overlap logic already exists in `geo.py`, so these should pass without code changes.

If any fail, check `alert_polygon_overlaps_tulsa` in `geo.py` against the test expectations and fix.

- [ ] **Step 3: Commit**

```bash
git add tests/test_geo.py
git commit -m "Add overlap tests for alert geometries"
```

---

## Task 4: Geometry — County-Name Fallback for Missing Geometry

**Files:**
- Modify: `geo.py` (append `areadesc_overlaps_tulsa`)
- Modify: `tests/test_geo.py` (append tests)
- Create: `tests/fixtures/alert_no_geometry.json`

- [ ] **Step 1: Create the no-geometry fixture**

Write `tests/fixtures/alert_no_geometry.json`:

```json
{
  "id": "urn:oid:2.49.0.1.840.0.test.nogeom",
  "type": "Feature",
  "geometry": null,
  "properties": {
    "id": "urn:oid:2.49.0.1.840.0.test.nogeom",
    "event": "Severe Thunderstorm Warning",
    "headline": "Severe Thunderstorm Warning for Tulsa County",
    "description": "Half dollar size hail reported.",
    "areaDesc": "Tulsa, OK; Wagoner, OK",
    "expires": "2026-05-18T20:00:00-05:00"
  }
}
```

- [ ] **Step 2: Add failing tests for the fallback**

Append to `tests/test_geo.py`:

```python
from geo import areadesc_overlaps_tulsa, TULSA_METRO_COUNTIES


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
```

- [ ] **Step 3: Run the tests, confirm they fail**

Run: `python -m pytest tests/test_geo.py -v`
Expected: 8 new tests fail with `ImportError` for `areadesc_overlaps_tulsa` and `TULSA_METRO_COUNTIES`.

- [ ] **Step 4: Add the fallback to `geo.py`**

Append to `geo.py`:

```python
import re

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
```

- [ ] **Step 5: Run the tests, confirm they pass**

Run: `python -m pytest tests/test_geo.py -v`
Expected: all 21 tests pass.

- [ ] **Step 6: Commit**

```bash
git add geo.py tests/test_geo.py tests/fixtures/alert_no_geometry.json
git commit -m "Add county-name fallback for alerts with no geometry"
```

---

## Task 5: NWS — Fetch Alerts From The API

**Files:**
- Create: `nws.py`
- Create: `tests/test_nws.py`
- Create: `tests/fixtures/alert_no_hail.json`

- [ ] **Step 1: Create the no-hail fixture**

Write `tests/fixtures/alert_no_hail.json`:

```json
{
  "id": "urn:oid:2.49.0.1.840.0.test.windonly",
  "type": "Feature",
  "geometry": {
    "type": "Polygon",
    "coordinates": [[
      [-96.10, 36.10], [-95.85, 36.10], [-95.85, 36.25],
      [-96.10, 36.25], [-96.10, 36.10]
    ]]
  },
  "properties": {
    "id": "urn:oid:2.49.0.1.840.0.test.windonly",
    "event": "Severe Thunderstorm Warning",
    "headline": "Severe Thunderstorm Warning issued for Tulsa County",
    "description": "60 mph wind gusts. No hail expected.",
    "areaDesc": "Tulsa, OK",
    "expires": "2026-05-18T20:00:00-05:00"
  }
}
```

- [ ] **Step 2: Write failing test for `fetch_alerts`**

Write `tests/test_nws.py`:

```python
"""Tests for nws.py — fetching and filtering NWS alerts."""
from unittest.mock import patch

import pytest
import responses

from nws import fetch_alerts, NWS_ALERTS_URL


@responses.activate
def test_fetch_alerts_returns_features_list():
    responses.add(
        responses.GET,
        NWS_ALERTS_URL,
        json={"type": "FeatureCollection", "features": [{"id": "a"}, {"id": "b"}]},
        status=200,
    )
    result = fetch_alerts()
    assert result == [{"id": "a"}, {"id": "b"}]


@responses.activate
def test_fetch_alerts_sends_polite_user_agent():
    responses.add(
        responses.GET,
        NWS_ALERTS_URL,
        json={"features": []},
        status=200,
    )
    fetch_alerts()
    assert len(responses.calls) == 1
    ua = responses.calls[0].request.headers.get("User-Agent", "")
    assert "Tulsa-Hail-Monitor" in ua
    assert "drew@bytedreams.ai" in ua


@responses.activate
def test_fetch_alerts_filters_to_oklahoma():
    responses.add(
        responses.GET,
        NWS_ALERTS_URL,
        json={"features": []},
        status=200,
    )
    fetch_alerts()
    assert responses.calls[0].request.params.get("area") == "OK"


@responses.activate
def test_fetch_alerts_returns_empty_on_500():
    responses.add(responses.GET, NWS_ALERTS_URL, status=500)
    assert fetch_alerts() == []


@responses.activate
def test_fetch_alerts_returns_empty_on_timeout():
    responses.add(
        responses.GET,
        NWS_ALERTS_URL,
        body=Exception("connection timeout"),
    )
    assert fetch_alerts() == []


@responses.activate
def test_fetch_alerts_returns_empty_on_invalid_json():
    responses.add(
        responses.GET,
        NWS_ALERTS_URL,
        body="not json",
        status=200,
    )
    assert fetch_alerts() == []
```

- [ ] **Step 3: Run the test, confirm it fails**

Run: `python -m pytest tests/test_nws.py -v`
Expected: `ModuleNotFoundError: No module named 'nws'`.

- [ ] **Step 4: Create `nws.py` with `fetch_alerts`**

Write `nws.py`:

```python
"""NWS API client and alert filtering for the Tulsa hail monitor."""
from __future__ import annotations

import logging
from typing import Any

import requests

NWS_ALERTS_URL = "https://api.weather.gov/alerts/active"
USER_AGENT = "Tulsa-Hail-Monitor/1.0 (drew@bytedreams.ai)"
REQUEST_TIMEOUT_SECONDS = 30

log = logging.getLogger(__name__)


def fetch_alerts() -> list[dict[str, Any]]:
    """Fetch active NWS alerts for Oklahoma.

    Returns a list of alert feature dicts. Returns an empty list on any
    error (timeout, 5xx, malformed JSON) so the next cron run can retry.
    """
    try:
        response = requests.get(
            NWS_ALERTS_URL,
            params={"area": "OK"},
            headers={"User-Agent": USER_AGENT, "Accept": "application/geo+json"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        return payload.get("features", [])
    except (requests.RequestException, ValueError, Exception) as exc:
        log.warning("Failed to fetch NWS alerts: %s", exc)
        return []
```

- [ ] **Step 5: Run the tests, confirm they pass**

Run: `python -m pytest tests/test_nws.py -v`
Expected: all 6 tests pass.

- [ ] **Step 6: Commit**

```bash
git add nws.py tests/test_nws.py tests/fixtures/alert_no_hail.json
git commit -m "Add NWS fetch_alerts with polite user agent"
```

---

## Task 6: NWS — Filter For Hail-Bearing SVR Warnings In Tulsa Radius

**Files:**
- Modify: `nws.py` (append `is_relevant_hail_alert`)
- Modify: `tests/test_nws.py` (append tests)

- [ ] **Step 1: Add failing tests for the filter**

Append to `tests/test_nws.py`:

```python
from nws import is_relevant_hail_alert


def test_svr_warning_with_hail_in_tulsa_passes(fixture_loader):
    alert = fixture_loader("alert_tulsa_hail.json")
    assert is_relevant_hail_alert(alert) is True


def test_svr_warning_no_hail_skipped(fixture_loader):
    alert = fixture_loader("alert_no_hail.json")
    assert is_relevant_hail_alert(alert) is False


def test_svr_warning_with_hail_outside_radius_skipped(fixture_loader):
    alert = fixture_loader("alert_dallas_hail.json")
    assert is_relevant_hail_alert(alert) is False


def test_tornado_warning_with_hail_mention_skipped():
    alert = {
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[-96.1, 36.1], [-95.85, 36.1], [-95.85, 36.25], [-96.1, 36.25], [-96.1, 36.1]]],
        },
        "properties": {
            "id": "x",
            "event": "Tornado Warning",
            "description": "Tornado with hail.",
            "areaDesc": "Tulsa, OK",
        },
    }
    assert is_relevant_hail_alert(alert) is False


def test_flood_warning_skipped():
    alert = {
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[-96.1, 36.1], [-95.85, 36.1], [-95.85, 36.25], [-96.1, 36.25], [-96.1, 36.1]]],
        },
        "properties": {
            "id": "x",
            "event": "Flood Warning",
            "description": "Flooding expected.",
            "areaDesc": "Tulsa, OK",
        },
    }
    assert is_relevant_hail_alert(alert) is False


def test_alert_with_null_geometry_falls_back_to_areadesc(fixture_loader):
    alert = fixture_loader("alert_no_geometry.json")
    # The fixture mentions hail and has areaDesc "Tulsa, OK; Wagoner, OK"
    assert is_relevant_hail_alert(alert) is True


def test_alert_with_null_geometry_and_no_metro_county_skipped():
    alert = {
        "geometry": None,
        "properties": {
            "id": "x",
            "event": "Severe Thunderstorm Warning",
            "description": "Quarter sized hail.",
            "areaDesc": "Beaver, OK",  # not a Tulsa metro county
        },
    }
    assert is_relevant_hail_alert(alert) is False


def test_case_insensitive_hail_match():
    alert = {
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[-96.1, 36.1], [-95.85, 36.1], [-95.85, 36.25], [-96.1, 36.25], [-96.1, 36.1]]],
        },
        "properties": {
            "id": "x",
            "event": "Severe Thunderstorm Warning",
            "description": "HAIL up to one inch.",  # uppercase
            "areaDesc": "Tulsa, OK",
        },
    }
    assert is_relevant_hail_alert(alert) is True


def test_missing_properties_returns_false():
    assert is_relevant_hail_alert({"geometry": None, "properties": {}}) is False


def test_completely_empty_alert_returns_false():
    assert is_relevant_hail_alert({}) is False
```

- [ ] **Step 2: Run the tests, confirm they fail**

Run: `python -m pytest tests/test_nws.py -v`
Expected: 10 new tests fail with `ImportError` for `is_relevant_hail_alert`.

- [ ] **Step 3: Add the filter to `nws.py`**

Append to `nws.py`:

```python
from geo import alert_polygon_overlaps_tulsa, areadesc_overlaps_tulsa

RELEVANT_EVENT_TYPES = {"Severe Thunderstorm Warning"}


def is_relevant_hail_alert(alert: dict[str, Any]) -> bool:
    """Return True if the alert is a hail-bearing SVR warning in our radius."""
    if not alert:
        return False
    props = alert.get("properties") or {}
    event = props.get("event") or ""
    description = (props.get("description") or "").lower()

    if event not in RELEVANT_EVENT_TYPES:
        return False
    if "hail" not in description:
        return False

    geometry = alert.get("geometry")
    if geometry:
        return alert_polygon_overlaps_tulsa(geometry)
    return areadesc_overlaps_tulsa(props.get("areaDesc"))
```

- [ ] **Step 4: Run the tests, confirm they pass**

Run: `python -m pytest tests/test_nws.py -v`
Expected: all 16 tests pass.

- [ ] **Step 5: Commit**

```bash
git add nws.py tests/test_nws.py
git commit -m "Add NWS alert filter: SVR + hail + Tulsa radius"
```

---

## Task 7: NWS — Extract Hail Size From Description

**Files:**
- Modify: `nws.py` (append `extract_hail_size`)
- Modify: `tests/test_nws.py` (append tests)

- [ ] **Step 1: Add failing tests**

Append to `tests/test_nws.py`:

```python
from nws import extract_hail_size


@pytest.mark.parametrize("description,expected", [
    ("quarter size hail (1.00 inch)", "1.00 inch"),
    ("up to one inch hail", "1 inch"),
    ("HAIL UP TO 1.5 INCHES", "1.5 inches"),
    ("ping pong ball size hail", "ping pong ball size"),
    ("golf ball sized hail", "golf ball size"),
    ("baseball-sized hail and 80 mph winds", "baseball size"),
    ("quarter-sized hail", "quarter size"),
    ("half dollar size hail", "half dollar size"),
    ("hail of 2 inches", "2 inches"),
])
def test_extract_hail_size_known_phrasings(description, expected):
    assert extract_hail_size(description) == expected


def test_extract_hail_size_no_match_returns_unknown():
    assert extract_hail_size("severe thunderstorm with damaging winds") == "size unknown"


def test_extract_hail_size_empty_string():
    assert extract_hail_size("") == "size unknown"


def test_extract_hail_size_none():
    assert extract_hail_size(None) == "size unknown"
```

- [ ] **Step 2: Run, confirm they fail**

Run: `python -m pytest tests/test_nws.py -v -k extract_hail_size`
Expected: `ImportError` for `extract_hail_size`.

- [ ] **Step 3: Add the extractor to `nws.py`**

Append to `nws.py`:

```python
import re

# Numeric hail size: "1 inch", "1.5 inches", "2.00 inch"
_NUMERIC_HAIL_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(inch(?:es)?)",
    re.IGNORECASE,
)

# "one inch" / "two inch" word-number variant
_WORD_NUMBER_HAIL_RE = re.compile(
    r"\b(one|two|three|four|five)\s+inch(?:es)?\b",
    re.IGNORECASE,
)
_WORD_TO_NUM = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5"}

# Common descriptive sizes, ordered from largest to smallest so we don't
# accidentally match "ping pong" inside a description that also mentions "golf ball".
_DESCRIPTIVE_SIZES = [
    "baseball",
    "softball",
    "tennis ball",
    "golf ball",
    "ping pong ball",
    "half dollar",
    "quarter",
    "nickel",
    "dime",
    "pea",
]


def extract_hail_size(description: str | None) -> str:
    """Return a human-readable hail size phrase, or 'size unknown'."""
    if not description:
        return "size unknown"
    text = description

    numeric = _NUMERIC_HAIL_RE.search(text)
    if numeric:
        number, unit = numeric.group(1), numeric.group(2).lower()
        return f"{number} {unit}"

    word_match = _WORD_NUMBER_HAIL_RE.search(text)
    if word_match:
        word = word_match.group(1).lower()
        return f"{_WORD_TO_NUM[word]} inch"

    lower = text.lower()
    for size in _DESCRIPTIVE_SIZES:
        if size in lower:
            return f"{size} size"

    return "size unknown"
```

- [ ] **Step 4: Run, confirm they pass**

Run: `python -m pytest tests/test_nws.py -v`
Expected: all 29 tests pass.

- [ ] **Step 5: Commit**

```bash
git add nws.py tests/test_nws.py
git commit -m "Add hail size extractor for email body"
```

---

## Task 8: State — Load, Save, Prune Seen Alerts

**Files:**
- Create: `state.py`
- Create: `tests/test_state.py`
- Create: `seen_alerts.json` (initial empty state)

- [ ] **Step 1: Create the initial empty state file**

Write `seen_alerts.json`:

```json
{
  "alerts": {},
  "last_updated": null
}
```

- [ ] **Step 2: Write failing tests**

Write `tests/test_state.py`:

```python
"""Tests for state.py — seen_alerts.json persistence."""
from datetime import datetime, timezone, timedelta
import json

import pytest
from freezegun import freeze_time

from state import load_seen, save_seen, mark_seen, prune_old


def test_load_seen_returns_empty_when_file_missing(tmp_path):
    state_file = tmp_path / "nope.json"
    assert load_seen(state_file) == {}


def test_load_seen_returns_empty_when_file_corrupt(tmp_path):
    state_file = tmp_path / "broken.json"
    state_file.write_text("not valid json {", encoding="utf-8")
    assert load_seen(state_file) == {}


def test_load_seen_reads_existing_alerts(tmp_path):
    state_file = tmp_path / "good.json"
    state_file.write_text(
        json.dumps({
            "alerts": {"id-a": "2026-05-18T12:00:00+00:00"},
            "last_updated": "2026-05-18T12:00:00+00:00",
        }),
        encoding="utf-8",
    )
    result = load_seen(state_file)
    assert result == {"id-a": "2026-05-18T12:00:00+00:00"}


def test_save_seen_writes_alerts_and_timestamp(tmp_path):
    state_file = tmp_path / "out.json"
    save_seen(state_file, {"id-a": "2026-05-18T12:00:00+00:00"})
    data = json.loads(state_file.read_text(encoding="utf-8"))
    assert data["alerts"] == {"id-a": "2026-05-18T12:00:00+00:00"}
    assert data["last_updated"] is not None


def test_save_seen_atomic_write_no_partial_file(tmp_path, monkeypatch):
    """If the rename fails, the target file should not be partially written."""
    state_file = tmp_path / "out.json"
    state_file.write_text(json.dumps({"alerts": {"old": "x"}, "last_updated": None}), encoding="utf-8")

    # Force os.replace to fail
    import os
    real_replace = os.replace

    def boom(src, dst):
        raise OSError("simulated rename failure")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        save_seen(state_file, {"id-new": "2026-05-18T12:00:00+00:00"})

    # Original file should be intact
    data = json.loads(state_file.read_text(encoding="utf-8"))
    assert data["alerts"] == {"old": "x"}
    monkeypatch.setattr(os, "replace", real_replace)


def test_mark_seen_adds_current_timestamp():
    seen = {}
    with freeze_time("2026-05-18 12:34:56", tz_offset=0):
        mark_seen(seen, "id-new")
    assert seen["id-new"].startswith("2026-05-18T12:34:56")


def test_prune_old_removes_entries_older_than_48_hours():
    now = datetime(2026, 5, 18, 12, 0, 0, tzinfo=timezone.utc)
    seen = {
        "fresh": (now - timedelta(hours=1)).isoformat(),
        "edge": (now - timedelta(hours=47)).isoformat(),
        "stale": (now - timedelta(hours=49)).isoformat(),
        "ancient": (now - timedelta(days=30)).isoformat(),
    }
    with freeze_time(now):
        prune_old(seen)
    assert set(seen.keys()) == {"fresh", "edge"}


def test_prune_old_handles_malformed_timestamps():
    """A bad timestamp should be treated as stale and pruned."""
    seen = {"good": datetime.now(timezone.utc).isoformat(), "bad": "garbage"}
    prune_old(seen)
    assert "good" in seen
    assert "bad" not in seen
```

- [ ] **Step 3: Run the tests, confirm they fail**

Run: `python -m pytest tests/test_state.py -v`
Expected: `ModuleNotFoundError: No module named 'state'`.

- [ ] **Step 4: Create `state.py`**

Write `state.py`:

```python
"""Persistence layer for the seen_alerts.json state file."""
from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Mapping

log = logging.getLogger(__name__)

STATE_RETENTION_HOURS = 48


def load_seen(state_file: Path) -> dict[str, str]:
    """Load the seen-alerts map. Returns empty dict if missing/corrupt."""
    try:
        raw = state_file.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        log.warning("seen_alerts.json is corrupt — starting fresh")
        return {}
    alerts = payload.get("alerts") or {}
    if not isinstance(alerts, dict):
        return {}
    return dict(alerts)


def save_seen(state_file: Path, seen: Mapping[str, str]) -> None:
    """Atomically write seen-alerts to disk.

    Uses tempfile + os.replace so a crash mid-write cannot corrupt
    the existing file.
    """
    payload = {
        "alerts": dict(seen),
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
    serialized = json.dumps(payload, indent=2, sort_keys=True)

    state_file.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=".seen_alerts_",
        suffix=".json.tmp",
        dir=str(state_file.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(serialized)
        os.replace(tmp_path, state_file)
    except Exception:
        # Clean up the tempfile on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def mark_seen(seen: dict[str, str], alert_id: str) -> None:
    """Add an alert ID to the seen map with the current timestamp."""
    seen[alert_id] = datetime.now(timezone.utc).isoformat()


def prune_old(seen: dict[str, str]) -> None:
    """Remove entries older than 48 hours, or with unparseable timestamps."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=STATE_RETENTION_HOURS)
    to_remove = []
    for alert_id, ts in seen.items():
        try:
            parsed = datetime.fromisoformat(ts)
        except (ValueError, TypeError):
            to_remove.append(alert_id)
            continue
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        if parsed < cutoff:
            to_remove.append(alert_id)
    for k in to_remove:
        seen.pop(k, None)
```

- [ ] **Step 5: Run the tests, confirm they pass**

Run: `python -m pytest tests/test_state.py -v`
Expected: all 8 tests pass.

- [ ] **Step 6: Commit**

```bash
git add state.py tests/test_state.py seen_alerts.json
git commit -m "Add state module: load/save/prune seen_alerts.json"
```

---

## Task 9: Notify — Format Email Subject And Body

**Files:**
- Create: `notify.py`
- Create: `tests/test_notify.py`

- [ ] **Step 1: Write failing tests for `format_alert_email`**

Write `tests/test_notify.py`:

```python
"""Tests for notify.py — email formatting and SMTP send."""
from unittest.mock import patch, MagicMock

import pytest

from notify import format_alert_email, send_email


def test_format_subject_includes_event_and_expires(fixture_loader):
    alert = fixture_loader("alert_tulsa_hail.json")
    subject, body = format_alert_email(alert)
    assert "Hail Alert" in subject
    assert "Severe Thunderstorm Warning" in subject
    # Expires at 2026-05-18T20:00:00-05:00 → 8:00 PM CDT
    assert "8:00 PM" in subject or "20:00" in subject


def test_format_body_includes_headline(fixture_loader):
    alert = fixture_loader("alert_tulsa_hail.json")
    _, body = format_alert_email(alert)
    assert "Severe Thunderstorm Warning issued for Tulsa County until 8 PM CDT" in body


def test_format_body_includes_hail_size(fixture_loader):
    alert = fixture_loader("alert_tulsa_hail.json")
    _, body = format_alert_email(alert)
    assert "1.00 inch" in body  # extracted from "quarter size hail (1.00 inch)"


def test_format_body_includes_areas(fixture_loader):
    alert = fixture_loader("alert_tulsa_hail.json")
    _, body = format_alert_email(alert)
    assert "Tulsa, OK" in body
    assert "Rogers, OK" in body


def test_format_body_includes_official_link(fixture_loader):
    alert = fixture_loader("alert_tulsa_hail.json")
    _, body = format_alert_email(alert)
    assert "alerts.weather.gov" in body
    assert alert["properties"]["id"] in body


def test_format_body_handles_missing_fields_gracefully():
    minimal = {
        "geometry": None,
        "properties": {
            "id": "x",
            "event": "Severe Thunderstorm Warning",
            "description": "hail",
        },
    }
    subject, body = format_alert_email(minimal)
    assert "Hail Alert" in subject
    # Should not raise; should produce a sensible body
    assert "Severe Thunderstorm Warning" in body


def test_format_subject_falls_back_when_expires_missing():
    alert = {
        "properties": {
            "id": "x",
            "event": "Severe Thunderstorm Warning",
            "description": "hail",
        },
    }
    subject, _ = format_alert_email(alert)
    assert "Hail Alert" in subject
```

- [ ] **Step 2: Run, confirm they fail**

Run: `python -m pytest tests/test_notify.py -v`
Expected: `ModuleNotFoundError: No module named 'notify'`.

- [ ] **Step 3: Create `notify.py` with the formatter**

Write `notify.py`:

```python
"""Email formatting and SMTP send for the Tulsa hail monitor."""
from __future__ import annotations

import logging
import smtplib
from datetime import datetime
from email.message import EmailMessage
from typing import Any
from zoneinfo import ZoneInfo

from nws import extract_hail_size

log = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
CENTRAL_TZ = ZoneInfo("America/Chicago")
NWS_ALERT_URL_TEMPLATE = "https://alerts.weather.gov/cap/wwacapget.php?x={alert_id}"


def _format_expiration(expires_iso: str | None) -> str:
    """Format an ISO timestamp as a Central-time 12-hour string.

    Portable across Windows and POSIX (avoids %-I/%#I divergence).
    """
    if not expires_iso:
        return "time unknown"
    try:
        dt = datetime.fromisoformat(expires_iso)
    except ValueError:
        return expires_iso
    central = dt.astimezone(CENTRAL_TZ)
    hour_12 = central.hour % 12 or 12
    ampm = "AM" if central.hour < 12 else "PM"
    tz_abbrev = central.strftime("%Z")
    return f"{hour_12}:{central.minute:02d} {ampm} {tz_abbrev}"


def format_alert_email(alert: dict[str, Any]) -> tuple[str, str]:
    """Build the (subject, body) tuple for an alert email."""
    props = alert.get("properties") or {}
    event = props.get("event") or "Severe Weather Alert"
    headline = props.get("headline") or "(no headline provided)"
    description = props.get("description") or ""
    area_desc = props.get("areaDesc") or "(area not specified)"
    expires = _format_expiration(props.get("expires"))
    alert_id = props.get("id") or alert.get("id") or ""

    hail_size = extract_hail_size(description)

    subject = f"Hail Alert — {event} until {expires}"
    link = NWS_ALERT_URL_TEMPLATE.format(alert_id=alert_id) if alert_id else "(no link)"

    body = (
        f"{headline}\n"
        f"\n"
        f"Event:        {event}\n"
        f"Hail size:    {hail_size}\n"
        f"Affected:     {area_desc}\n"
        f"Expires:      {expires}\n"
        f"\n"
        f"Official NWS alert page:\n"
        f"  {link}\n"
        f"\n"
        f"--- Full NWS description ---\n"
        f"{description}\n"
    )
    return subject, body
```

Note: `_format_expiration` uses manual hour/minute arithmetic instead of strftime's `%-I` (POSIX) or `%#I` (Windows) to stay portable across both platforms.

- [ ] **Step 4: Run the tests, confirm they pass**

Run: `python -m pytest tests/test_notify.py -v`
Expected: all 7 tests pass.

- [ ] **Step 5: Commit**

```bash
git add notify.py tests/test_notify.py
git commit -m "Add email formatter for hail alerts"
```

---

## Task 10: Notify — SMTP Send

**Files:**
- Modify: `notify.py` (append `send_email`)
- Modify: `tests/test_notify.py` (append tests)

- [ ] **Step 1: Add failing tests for `send_email`**

Append to `tests/test_notify.py`:

```python
def test_send_email_uses_smtp_gmail_587(monkeypatch):
    captured = {}

    class FakeSMTP:
        def __init__(self, host, port):
            captured["host"] = host
            captured["port"] = port

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def starttls(self):
            captured["starttls"] = True

        def login(self, user, password):
            captured["user"] = user
            captured["password"] = password

        def send_message(self, msg):
            captured["msg"] = msg

    monkeypatch.setattr("notify.smtplib.SMTP", FakeSMTP)

    send_email(
        subject="Hail Alert — test",
        body="body text",
        sender="drew@bytedreams.ai",
        recipient="drew@bytedreams.ai",
        password="abcd efgh ijkl mnop",
    )

    assert captured["host"] == "smtp.gmail.com"
    assert captured["port"] == 587
    assert captured["starttls"] is True
    assert captured["user"] == "drew@bytedreams.ai"
    assert captured["password"] == "abcd efgh ijkl mnop"
    assert captured["msg"]["Subject"] == "Hail Alert — test"
    assert captured["msg"]["From"] == "drew@bytedreams.ai"
    assert captured["msg"]["To"] == "drew@bytedreams.ai"
    assert captured["msg"].get_content().strip() == "body text"


def test_send_email_raises_on_smtp_failure(monkeypatch):
    import smtplib

    class FailingSMTP:
        def __init__(self, host, port):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def starttls(self):
            pass

        def login(self, user, password):
            raise smtplib.SMTPAuthenticationError(535, b"Auth failed")

        def send_message(self, msg):
            pass

    monkeypatch.setattr("notify.smtplib.SMTP", FailingSMTP)
    with pytest.raises(smtplib.SMTPAuthenticationError):
        send_email(
            subject="x", body="y",
            sender="a@b.com", recipient="c@d.com",
            password="bad",
        )
```

- [ ] **Step 2: Run, confirm they fail**

Run: `python -m pytest tests/test_notify.py -v`
Expected: 2 new tests fail with `ImportError` for `send_email`.

- [ ] **Step 3: Add `send_email` to `notify.py`**

Append to `notify.py`:

```python
def send_email(
    *,
    subject: str,
    body: str,
    sender: str,
    recipient: str,
    password: str,
) -> None:
    """Send a plain-text email via Gmail SMTP. Raises on any failure."""
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    msg.set_content(body)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(sender, password)
        smtp.send_message(msg)
```

- [ ] **Step 4: Run, confirm tests pass**

Run: `python -m pytest tests/test_notify.py -v`
Expected: all 9 tests pass.

- [ ] **Step 5: Commit**

```bash
git add notify.py tests/test_notify.py
git commit -m "Add SMTP send for Gmail with App Password"
```

---

## Task 11: Monitor — Main Pipeline (No CLI Yet)

**Files:**
- Create: `monitor.py`
- Create: `tests/test_monitor.py`

- [ ] **Step 1: Write failing tests for the pipeline**

Write `tests/test_monitor.py`:

```python
"""Tests for monitor.py — main orchestration pipeline."""
from unittest.mock import patch, MagicMock, call
from pathlib import Path

import pytest

from monitor import run_once, Config


@pytest.fixture
def cfg(tmp_path):
    return Config(
        state_file=tmp_path / "seen_alerts.json",
        sender="drew@bytedreams.ai",
        recipient="drew@bytedreams.ai",
        password="test-password",
        dry_run=False,
    )


def test_run_once_emails_new_relevant_alerts(cfg, fixture_loader, monkeypatch):
    tulsa = fixture_loader("alert_tulsa_hail.json")
    dallas = fixture_loader("alert_dallas_hail.json")

    monkeypatch.setattr("monitor.fetch_alerts", lambda: [tulsa, dallas])
    sent = []
    monkeypatch.setattr(
        "monitor.send_email",
        lambda **kwargs: sent.append(kwargs),
    )

    run_once(cfg)

    assert len(sent) == 1
    assert "Hail Alert" in sent[0]["subject"]
    assert sent[0]["recipient"] == "drew@bytedreams.ai"


def test_run_once_skips_already_seen(cfg, fixture_loader, monkeypatch):
    tulsa = fixture_loader("alert_tulsa_hail.json")

    # Pre-populate seen state
    from state import save_seen
    save_seen(cfg.state_file, {tulsa["properties"]["id"]: "2026-05-18T00:00:00+00:00"})

    monkeypatch.setattr("monitor.fetch_alerts", lambda: [tulsa])
    sent = []
    monkeypatch.setattr("monitor.send_email", lambda **k: sent.append(k))

    run_once(cfg)

    assert sent == []


def test_run_once_persists_newly_seen_alert(cfg, fixture_loader, monkeypatch):
    tulsa = fixture_loader("alert_tulsa_hail.json")
    monkeypatch.setattr("monitor.fetch_alerts", lambda: [tulsa])
    monkeypatch.setattr("monitor.send_email", lambda **k: None)

    run_once(cfg)

    from state import load_seen
    seen = load_seen(cfg.state_file)
    assert tulsa["properties"]["id"] in seen


def test_run_once_does_not_persist_when_email_fails(cfg, fixture_loader, monkeypatch):
    tulsa = fixture_loader("alert_tulsa_hail.json")
    monkeypatch.setattr("monitor.fetch_alerts", lambda: [tulsa])

    def boom(**kwargs):
        raise RuntimeError("smtp down")

    monkeypatch.setattr("monitor.send_email", boom)

    # Should not raise — error is logged and execution continues
    run_once(cfg)

    from state import load_seen
    seen = load_seen(cfg.state_file)
    assert tulsa["properties"]["id"] not in seen


def test_run_once_dry_run_does_not_call_send_email(cfg, fixture_loader, monkeypatch):
    import dataclasses
    cfg = dataclasses.replace(cfg, dry_run=True)
    tulsa = fixture_loader("alert_tulsa_hail.json")
    monkeypatch.setattr("monitor.fetch_alerts", lambda: [tulsa])

    sent = []
    monkeypatch.setattr("monitor.send_email", lambda **k: sent.append(k))

    run_once(cfg)

    assert sent == []


def test_run_once_with_no_alerts_does_nothing(cfg, monkeypatch):
    monkeypatch.setattr("monitor.fetch_alerts", lambda: [])
    sent = []
    monkeypatch.setattr("monitor.send_email", lambda **k: sent.append(k))

    run_once(cfg)

    assert sent == []
```

- [ ] **Step 2: Run, confirm they fail**

Run: `python -m pytest tests/test_monitor.py -v`
Expected: `ModuleNotFoundError: No module named 'monitor'`.

- [ ] **Step 3: Create `monitor.py` with the orchestration**

Write `monitor.py`:

```python
"""Tulsa Hail Monitor — entry point and main pipeline.

Fetches active NWS alerts for Oklahoma, filters for hail-bearing
Severe Thunderstorm Warnings inside a 50-mile circle around downtown
Tulsa, deduplicates against state, and emails new alerts.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from dataclasses import dataclass, replace
from pathlib import Path

from dotenv import load_dotenv

from nws import fetch_alerts, is_relevant_hail_alert
from notify import format_alert_email, send_email
from state import load_seen, save_seen, mark_seen, prune_old

log = logging.getLogger("hail-monitor")


@dataclass(frozen=True)
class Config:
    state_file: Path
    sender: str
    recipient: str
    password: str
    dry_run: bool = False


def run_once(cfg: Config) -> None:
    """Run one polling cycle: fetch, filter, dedupe, notify, save."""
    seen = load_seen(cfg.state_file)
    prune_old(seen)

    alerts = fetch_alerts()
    log.info("Fetched %d active OK alerts", len(alerts))

    new_count = 0
    for alert in alerts:
        try:
            if not is_relevant_hail_alert(alert):
                continue
            alert_id = (alert.get("properties") or {}).get("id") or alert.get("id")
            if not alert_id:
                continue
            if alert_id in seen:
                continue

            subject, body = format_alert_email(alert)

            if cfg.dry_run:
                print("=" * 70)
                print(f"[DRY-RUN] Would send to {cfg.recipient}:")
                print(f"Subject: {subject}")
                print()
                print(body)
                print("=" * 70)
            else:
                send_email(
                    subject=subject,
                    body=body,
                    sender=cfg.sender,
                    recipient=cfg.recipient,
                    password=cfg.password,
                )
                mark_seen(seen, alert_id)
                log.info("Sent hail alert email for %s", alert_id)
            new_count += 1
        except Exception as exc:
            log.exception("Failed to handle alert %s: %s",
                          (alert.get("properties") or {}).get("id", "?"), exc)

    save_seen(cfg.state_file, seen)
    log.info("Run complete: %d new alerts processed", new_count)


def _config_from_env(dry_run: bool) -> Config:
    sender = os.environ["SMTP_USER"]
    return Config(
        state_file=Path("seen_alerts.json"),
        sender=sender,
        recipient=os.environ["ALERT_TO_EMAIL"],
        password=os.environ["SMTP_APP_PASSWORD"],
        dry_run=dry_run,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Tulsa Hail Monitor")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print emails instead of sending them.")
    parser.add_argument("--self-test", action="store_true",
                        help="Send a single test email and exit.")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    load_dotenv()

    if args.self_test:
        cfg = _config_from_env(dry_run=False)
        send_email(
            subject="Hail Alert — Self-test email",
            body="If you got this, the Tulsa Hail Monitor is wired up correctly.\n",
            sender=cfg.sender,
            recipient=cfg.recipient,
            password=cfg.password,
        )
        log.info("Self-test email sent to %s", cfg.recipient)
        return 0

    cfg = _config_from_env(dry_run=args.dry_run)
    run_once(cfg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: all tests across all modules pass.

- [ ] **Step 5: Commit**

```bash
git add monitor.py tests/test_monitor.py
git commit -m "Add monitor.py entry point and run_once pipeline"
```

---

## Task 12: Local Dry-Run Smoke Test

**Files:** (no new files; uses everything from above)

- [ ] **Step 1: Create a local `.env` for testing**

Create `.env` at the project root (this file is gitignored — it will not be committed):

```
SMTP_USER=drew@bytedreams.ai
SMTP_APP_PASSWORD=<paste the 16-char password from docs/superpowers/.env/ here>
ALERT_TO_EMAIL=drew@bytedreams.ai
```

Verify it's gitignored. Run: `git check-ignore .env` — expected output: `.env`. If git says nothing, the file is NOT ignored and you must fix `.gitignore` before continuing.

- [ ] **Step 2: Run the dry-run mode against live NWS data**

Run: `python monitor.py --dry-run`
Expected: the script logs how many OK alerts were fetched. If there's currently a Tulsa-area hail warning, it prints the email content. If there isn't (the common case), it just logs "Run complete: 0 new alerts processed".

- [ ] **Step 3: Verify the script handles "no alerts" cleanly**

Confirm: no crash, no traceback, `seen_alerts.json` may or may not be updated (it's updated with current timestamp even if no new alerts).

- [ ] **Step 4: (Optional) Send a self-test email locally**

Run: `python monitor.py --self-test`
Expected: an email arrives at drew@bytedreams.ai with subject "Hail Alert — Self-test email". If you get an `SMTPAuthenticationError`, the App Password is wrong — regenerate it from Google.

If the email arrives: SMTP wiring is correct.
If you'd rather skip this step locally and let GitHub Actions do the self-test, that's fine — proceed.

- [ ] **Step 5: Commit any changes (if seen_alerts.json was updated)**

```bash
git add seen_alerts.json
git diff --staged --quiet || git commit -m "Initialize seen_alerts state after dry-run"
```

---

## Task 13: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write `README.md`**

```markdown
# Tulsa Hail Monitor

Emails drew@bytedreams.ai every time the National Weather Service issues a
Severe Thunderstorm Warning mentioning hail inside a 50-mile circle around
downtown Tulsa, OK.

Runs free on GitHub Actions cron every 10 minutes. Total monthly cost: $0.

## How it works

```
NWS API → filter for SVR-warning + "hail" + Tulsa 50-mi radius
        → dedupe against seen_alerts.json
        → email new alerts via Gmail SMTP
```

## Local development

1. `python -m venv .venv && source .venv/Scripts/activate` (or `.venv\Scripts\Activate.ps1` on PowerShell)
2. `pip install -r requirements-dev.txt`
3. Copy `.env.example` to `.env` and fill in your real Gmail App Password.
4. `python -m pytest tests/ -v`
5. `python monitor.py --dry-run` to see what would be sent against live NWS data.

## Production deploy

Lives in GitHub Actions. The workflow at `.github/workflows/hail-monitor.yml`
runs every 10 minutes and uses three repository secrets:

- `SMTP_USER` = drew@bytedreams.ai
- `SMTP_APP_PASSWORD` = 16-char Google App Password
- `ALERT_TO_EMAIL` = drew@bytedreams.ai

To regenerate the App Password (if compromised or expired):
1. https://myaccount.google.com/apppasswords
2. Revoke "Tulsa Hail Monitor", create a new one
3. Update the `SMTP_APP_PASSWORD` secret in GitHub settings

## Files

- `monitor.py` — entry point, CLI, orchestration
- `nws.py` — NWS API client + filter logic
- `geo.py` — 50-mile Tulsa polygon + geometry checks
- `notify.py` — email formatting + SMTP send
- `state.py` — seen_alerts.json persistence
- `seen_alerts.json` — committed state of which alerts have been emailed
- `.github/workflows/hail-monitor.yml` — cron workflow
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "Add README with local dev and deploy instructions"
```

---

## Task 14: GitHub Actions Workflow

**Files:**
- Create: `.github/workflows/hail-monitor.yml`

- [ ] **Step 1: Create the workflow file**

Write `.github/workflows/hail-monitor.yml`:

```yaml
name: Tulsa Hail Monitor

on:
  schedule:
    - cron: "*/10 * * * *"
  workflow_dispatch:
    inputs:
      mode:
        description: "Run mode"
        required: false
        default: "normal"
        type: choice
        options:
          - normal
          - dry-run
          - self-test

permissions:
  contents: write

jobs:
  monitor:
    runs-on: ubuntu-latest
    timeout-minutes: 5

    steps:
      - name: Checkout repo
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run monitor
        env:
          SMTP_USER: ${{ secrets.SMTP_USER }}
          SMTP_APP_PASSWORD: ${{ secrets.SMTP_APP_PASSWORD }}
          ALERT_TO_EMAIL: ${{ secrets.ALERT_TO_EMAIL }}
        run: |
          if [ "${{ github.event.inputs.mode }}" = "self-test" ]; then
            python monitor.py --self-test
          elif [ "${{ github.event.inputs.mode }}" = "dry-run" ]; then
            python monitor.py --dry-run
          else
            python monitor.py
          fi

      - name: Commit updated state
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add seen_alerts.json
          if git diff --staged --quiet; then
            echo "No state changes to commit"
          else
            git commit -m "chore: update seen_alerts.json [skip ci]"
            git push
          fi
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/hail-monitor.yml
git commit -m "Add GitHub Actions cron workflow (every 10 min)"
```

---

## Task 15: Connect Local Repo To GitHub And Push

**Files:** (no files modified; git config + push)

- [ ] **Step 1: Add the remote**

Run: `git remote add origin https://github.com/drewchimento/Tulsa-Hail-Monitor-.git`
Then verify: `git remote -v`
Expected: `origin  https://github.com/drewchimento/Tulsa-Hail-Monitor-.git (fetch)` and `(push)`.

- [ ] **Step 2: Confirm `.env` is NOT staged**

Run: `git status`
Expected output: `.env` should NOT appear (it's gitignored). The `docs/superpowers/.env/` folder also should NOT appear. If either does, STOP and fix the gitignore before pushing.

- [ ] **Step 3: Push to GitHub**

Run: `git push -u origin main`
Expected: push succeeds. If prompted for credentials, use a GitHub Personal Access Token (Classic) with `repo` scope, or the GitHub CLI (`gh auth login`).

If push fails with "non-fast-forward" because the GitHub repo was initialized with a README:
- Run `git pull --rebase origin main` first, resolve any conflicts, then `git push -u origin main`.

- [ ] **Step 4: Verify the workflow file appeared on GitHub**

Open https://github.com/drewchimento/Tulsa-Hail-Monitor-/actions in a browser. You should see "Tulsa Hail Monitor" listed. It will not have run yet because secrets are not configured.

---

## Task 16: Configure GitHub Repository Secrets

**Files:** (no code; UI work in the GitHub web interface)

- [ ] **Step 1: Open repo Settings → Secrets and variables → Actions**

Direct link: https://github.com/drewchimento/Tulsa-Hail-Monitor-/settings/secrets/actions

- [ ] **Step 2: Add three repository secrets**

Click **"New repository secret"** three times and add:

| Name | Value |
| --- | --- |
| `SMTP_USER` | `drew@bytedreams.ai` |
| `SMTP_APP_PASSWORD` | (paste the 16-char string from `docs/superpowers/.env/Tulsa Hail Monitor Google App Passw.txt` — remove any internal spaces; Gmail accepts it either way but it's cleaner without spaces) |
| `ALERT_TO_EMAIL` | `drew@bytedreams.ai` |

- [ ] **Step 3: Verify all three appear in the secrets list**

The Secrets page should show three rows: `ALERT_TO_EMAIL`, `SMTP_APP_PASSWORD`, `SMTP_USER`. Values are masked — you cannot read them back, which is correct.

---

## Task 17: Manual Self-Test Run In GitHub Actions

**Files:** (no code; UI run in GitHub Actions)

- [ ] **Step 1: Trigger the workflow manually in self-test mode**

Go to https://github.com/drewchimento/Tulsa-Hail-Monitor-/actions/workflows/hail-monitor.yml → click **"Run workflow"** → select branch `main` → select **mode: self-test** → click **"Run workflow"**.

- [ ] **Step 2: Watch the run**

The run appears within ~10 seconds. Click into it. Wait for the "Run monitor" step to complete (it takes about 20–30 seconds). The step should succeed (green checkmark).

- [ ] **Step 3: Verify the email arrived at drew@bytedreams.ai**

Check the inbox for an email with subject `Hail Alert — Self-test email`. Should arrive within 30 seconds of the workflow completing.

If it didn't arrive:
- Check Spam folder
- Check the workflow logs for `SMTPAuthenticationError` → App Password is wrong or expired
- Check for `SMTPSenderRefused` → Workspace settings may block App Passwords; pivot to Resend per the spec's contingency

- [ ] **Step 4: Trigger a dry-run against live NWS data**

Same Actions page → Run workflow → **mode: dry-run** → Run.

The logs will show how many OK alerts are currently active and (if any are Tulsa-relevant) print what the email would look like. Confirm no traceback, no SMTP error.

---

## Task 18: Enable Production Cron And Validate

**Files:** (no code; verification)

- [ ] **Step 1: Confirm the cron schedule is active**

The cron is enabled the moment the workflow file is on the `main` branch. Within the next 10 minutes you should see an automatic run on the Actions page (not a manual run — one triggered by `schedule`).

If after 15 minutes no scheduled run has appeared:
- GitHub sometimes delays cron triggers on free tier; this is normal. Wait 30 min.
- If still nothing, check that the workflow file is syntactically valid (the Actions tab usually shows a parsing error).

- [ ] **Step 2: Watch the first scheduled run complete cleanly**

Open the most recent scheduled run. The "Run monitor" step should show "Fetched N active OK alerts" and "Run complete: 0 new alerts processed" (assuming no current hail). The "Commit updated state" step should usually say "No state changes to commit" (since the state file might be unchanged when no new alerts).

- [ ] **Step 3: Mark the monitor as live**

The service is now running. Cron will continue every 10 minutes. When NWS issues a hail SVR warning in the Tulsa 50-mile radius, you will receive an email at drew@bytedreams.ai within ~10 minutes of the warning being issued.

- [ ] **Step 4: Add a calendar reminder to validate during the next real storm**

Set a personal reminder: "Next time there's an Oklahoma severe thunderstorm forecast, check that the monitor caught the warning(s)." This is the real-world validation step the spec calls out in §10.5.

- [ ] **Step 5: Final commit (if anything in the working tree changed)**

```bash
git status
```

If clean: done. If not: stage and commit any remaining files with a descriptive message.

---

## Summary Of What's Live At Plan Completion

- Cron runs every 10 minutes, 24/7
- Sends email to drew@bytedreams.ai for every hail-bearing SVR warning in the Tulsa 50-mile radius
- $0 ongoing cost
- Test suite covers geometry, filtering, hail-size parsing, state persistence, email formatting, and the run pipeline
- State file in repo so duplicate alerts are not re-emailed even across workflow restarts
- Manual workflow trigger available for ad-hoc dry-runs or self-tests

## What's Intentionally NOT Built (Per Spec §3)

- SMS / push / non-email channels
- A web dashboard or history UI
- Hail size threshold filtering (NWS only issues SVR warnings for ≥1" hail, so this is implicit)
- Real-time (<1 min) detection
- Multi-recipient broadcast
