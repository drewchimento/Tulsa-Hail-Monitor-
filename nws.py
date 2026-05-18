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
