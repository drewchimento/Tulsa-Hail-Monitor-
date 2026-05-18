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
