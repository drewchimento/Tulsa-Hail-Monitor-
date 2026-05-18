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
