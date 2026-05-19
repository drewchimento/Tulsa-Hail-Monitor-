"""Tests for monitor.py — main orchestration pipeline."""
from unittest.mock import patch, MagicMock, call
from pathlib import Path

import pytest

from monitor import run_once, Config


@pytest.fixture
def cfg(tmp_path):
    return Config(
        state_file=tmp_path / "seen_alerts.json",
        sender="onboarding@resend.dev",
        recipient="drew@bytedreams.ai",
        api_key="re_test_key",
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
