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
