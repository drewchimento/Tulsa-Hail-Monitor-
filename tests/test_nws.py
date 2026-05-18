"""Tests for nws.py — fetching and filtering NWS alerts."""
from unittest.mock import patch

import pytest
import responses

from nws import fetch_alerts, NWS_ALERTS_URL


@responses.activate
def test_fetch_alerts_returns_features_list():
    responses.add(
        responses.GET,
        NWS_ALERTS_URL,
        json={"type": "FeatureCollection", "features": [{"id": "a"}, {"id": "b"}]},
        status=200,
    )
    result = fetch_alerts()
    assert result == [{"id": "a"}, {"id": "b"}]


@responses.activate
def test_fetch_alerts_sends_polite_user_agent():
    responses.add(
        responses.GET,
        NWS_ALERTS_URL,
        json={"features": []},
        status=200,
    )
    fetch_alerts()
    assert len(responses.calls) == 1
    ua = responses.calls[0].request.headers.get("User-Agent", "")
    assert "Tulsa-Hail-Monitor" in ua
    assert "drew@bytedreams.ai" in ua


@responses.activate
def test_fetch_alerts_filters_to_oklahoma():
    responses.add(
        responses.GET,
        NWS_ALERTS_URL,
        json={"features": []},
        status=200,
    )
    fetch_alerts()
    assert responses.calls[0].request.params.get("area") == "OK"


@responses.activate
def test_fetch_alerts_returns_empty_on_500():
    responses.add(responses.GET, NWS_ALERTS_URL, status=500)
    assert fetch_alerts() == []


@responses.activate
def test_fetch_alerts_returns_empty_on_timeout():
    responses.add(
        responses.GET,
        NWS_ALERTS_URL,
        body=Exception("connection timeout"),
    )
    assert fetch_alerts() == []


@responses.activate
def test_fetch_alerts_returns_empty_on_invalid_json():
    responses.add(
        responses.GET,
        NWS_ALERTS_URL,
        body="not json",
        status=200,
    )
    assert fetch_alerts() == []


from nws import is_relevant_hail_alert


def test_svr_warning_with_hail_in_tulsa_passes(fixture_loader):
    alert = fixture_loader("alert_tulsa_hail.json")
    assert is_relevant_hail_alert(alert) is True


def test_svr_warning_no_hail_skipped(fixture_loader):
    alert = fixture_loader("alert_no_hail.json")
    assert is_relevant_hail_alert(alert) is False


def test_svr_warning_with_hail_outside_radius_skipped(fixture_loader):
    alert = fixture_loader("alert_dallas_hail.json")
    assert is_relevant_hail_alert(alert) is False


def test_tornado_warning_with_hail_mention_skipped():
    alert = {
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[-96.1, 36.1], [-95.85, 36.1], [-95.85, 36.25], [-96.1, 36.25], [-96.1, 36.1]]],
        },
        "properties": {
            "id": "x",
            "event": "Tornado Warning",
            "description": "Tornado with hail.",
            "areaDesc": "Tulsa, OK",
        },
    }
    assert is_relevant_hail_alert(alert) is False


def test_flood_warning_skipped():
    alert = {
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[-96.1, 36.1], [-95.85, 36.1], [-95.85, 36.25], [-96.1, 36.25], [-96.1, 36.1]]],
        },
        "properties": {
            "id": "x",
            "event": "Flood Warning",
            "description": "Flooding expected.",
            "areaDesc": "Tulsa, OK",
        },
    }
    assert is_relevant_hail_alert(alert) is False


def test_alert_with_null_geometry_falls_back_to_areadesc(fixture_loader):
    alert = fixture_loader("alert_no_geometry.json")
    # The fixture mentions hail and has areaDesc "Tulsa, OK; Wagoner, OK"
    assert is_relevant_hail_alert(alert) is True


def test_alert_with_null_geometry_and_no_metro_county_skipped():
    alert = {
        "geometry": None,
        "properties": {
            "id": "x",
            "event": "Severe Thunderstorm Warning",
            "description": "Quarter sized hail.",
            "areaDesc": "Beaver, OK",  # not a Tulsa metro county
        },
    }
    assert is_relevant_hail_alert(alert) is False


def test_case_insensitive_hail_match():
    alert = {
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[-96.1, 36.1], [-95.85, 36.1], [-95.85, 36.25], [-96.1, 36.25], [-96.1, 36.1]]],
        },
        "properties": {
            "id": "x",
            "event": "Severe Thunderstorm Warning",
            "description": "HAIL up to one inch.",  # uppercase
            "areaDesc": "Tulsa, OK",
        },
    }
    assert is_relevant_hail_alert(alert) is True


def test_missing_properties_returns_false():
    assert is_relevant_hail_alert({"geometry": None, "properties": {}}) is False


def test_completely_empty_alert_returns_false():
    assert is_relevant_hail_alert({}) is False
