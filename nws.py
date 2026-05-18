"""NWS API client and alert filtering for the Tulsa hail monitor."""
from __future__ import annotations

import logging
import re
from typing import Any

import requests

from geo import alert_polygon_overlaps_tulsa, areadesc_overlaps_tulsa

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
