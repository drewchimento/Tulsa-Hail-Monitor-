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
    # Match "hail" only when not preceded by "no " (handles "No hail expected.")
    if not re.search(r"(?<!no )hail", description):
        return False

    geometry = alert.get("geometry")
    if geometry:
        return alert_polygon_overlaps_tulsa(geometry)
    return areadesc_overlaps_tulsa(props.get("areaDesc"))
