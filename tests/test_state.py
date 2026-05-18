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
