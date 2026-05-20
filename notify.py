"""Email formatting and HTTP send (via Resend) for the Tulsa hail monitor."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import requests

from nws import extract_hail_size

log = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"
RESEND_TIMEOUT_SECONDS = 30
DEFAULT_SENDER = "onboarding@resend.dev"
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


def send_email(
    *,
    subject: str,
    body: str,
    sender: str,
    recipient: str,
    api_key: str,
) -> None:
    """Send a plain-text email via the Resend HTTP API. Raises on any failure."""
    response = requests.post(
        RESEND_API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "from": sender,
            "to": recipient,
            "subject": subject,
            "text": body,
        },
        timeout=RESEND_TIMEOUT_SECONDS,
    )
    if not response.ok:
        log.error("Resend rejected request (status=%s): %s",
                  response.status_code, response.text)
    response.raise_for_status()
