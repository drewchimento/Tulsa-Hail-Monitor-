"""Tests for notify.py — email formatting and Resend HTTP send."""
import json

import pytest
import requests
import responses

from notify import RESEND_API_URL, format_alert_email, send_email


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
    assert "1.00 inch" in body


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


@responses.activate
def test_send_email_posts_to_resend_with_bearer_auth():
    responses.add(
        responses.POST,
        RESEND_API_URL,
        json={"id": "test-message-id"},
        status=200,
    )

    send_email(
        subject="Hail Alert — test",
        body="body text",
        sender="onboarding@resend.dev",
        recipient="drew@bytedreams.ai",
        api_key="re_test_key_123",
    )

    assert len(responses.calls) == 1
    request = responses.calls[0].request
    assert request.headers["Authorization"] == "Bearer re_test_key_123"
    assert request.headers["Content-Type"] == "application/json"
    payload = json.loads(request.body)
    assert payload["from"] == "onboarding@resend.dev"
    assert payload["to"] == "drew@bytedreams.ai"
    assert payload["subject"] == "Hail Alert — test"
    assert payload["text"] == "body text"


@responses.activate
def test_send_email_raises_on_4xx_response():
    responses.add(
        responses.POST,
        RESEND_API_URL,
        json={"message": "Invalid API key", "name": "validation_error"},
        status=401,
    )

    with pytest.raises(requests.HTTPError):
        send_email(
            subject="x", body="y",
            sender="onboarding@resend.dev",
            recipient="drew@bytedreams.ai",
            api_key="re_bad_key",
        )


@responses.activate
def test_send_email_raises_on_5xx_response():
    responses.add(
        responses.POST,
        RESEND_API_URL,
        json={"message": "internal error"},
        status=500,
    )

    with pytest.raises(requests.HTTPError):
        send_email(
            subject="x", body="y",
            sender="onboarding@resend.dev",
            recipient="drew@bytedreams.ai",
            api_key="re_any_key",
        )
