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
