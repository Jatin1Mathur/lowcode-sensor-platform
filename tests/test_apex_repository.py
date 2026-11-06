"""ApexRepository against a fake ORDS session (no real Oracle needed)."""

from datetime import datetime, timezone

import pytest
import requests

from app import create_app
from app.repository import ApexRepository, DuplicateCycleError, UpstreamError

CYCLE = {
    "device_id": "esp32-rig-01",
    "cycle": 7,
    "timestamp": datetime(2026, 11, 6, 8, 0, tzinfo=timezone.utc),
    "readings": {"PS1": 160.4, "TS1": 45.2},
}


class FakeResponse:
    def __init__(self, status_code, body=None):
        self.status_code = status_code
        self._body = body or {}

    def json(self):
        return self._body


class FakeSession:
    def __init__(self, responses=None, error=None):
        self.headers = {}
        self.calls = []
        self.responses = list(responses or [])
        self.error = error

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if self.error:
            raise self.error
        return self.responses.pop(0)


def repo(session):
    return ApexRepository("https://apex.example.com/ords/ws/sensor/", token="tok", session=session)


def test_save_posts_oracle_friendly_payload():
    session = FakeSession([FakeResponse(201)])
    repo(session).save_cycle(CYCLE)
    method, url, kwargs = session.calls[0]
    assert (method, url) == ("POST", "https://apex.example.com/ords/ws/sensor/cycles/")
    assert kwargs["json"]["recorded_at"] == "2026-11-06 08:00:00"
    assert kwargs["timeout"] == 5.0
    assert session.headers["Authorization"] == "Bearer tok"


def test_save_duplicate_maps_to_409():
    with pytest.raises(DuplicateCycleError):
        repo(FakeSession([FakeResponse(409)])).save_cycle(CYCLE)


def test_save_server_error_raises_upstream():
    with pytest.raises(UpstreamError):
        repo(FakeSession([FakeResponse(500)])).save_cycle(CYCLE)


def test_network_error_raises_upstream():
    session = FakeSession(error=requests.ConnectionError("down"))
    with pytest.raises(UpstreamError):
        repo(session).save_cycle(CYCLE)


def test_get_cycle_builds_readings():
    rows = {"items": [
        {"recorded_at": "2026-11-06 08:00:00", "sensor_code": "PS1", "value": 160.4},
        {"recorded_at": "2026-11-06 08:00:00", "sensor_code": "TS1", "value": 45.2},
    ]}
    session = FakeSession([FakeResponse(200, rows)])
    record = repo(session).get_cycle("esp32 rig/01", 7)
    assert record["readings"] == {"PS1": 160.4, "TS1": 45.2}
    assert session.calls[0][1].endswith("/cycles/esp32%20rig%2F01/7")


def test_get_cycle_empty_is_none():
    assert repo(FakeSession([FakeResponse(200, {"items": []})])).get_cycle("a", 1) is None


def test_api_returns_502_when_apex_down(valid_payload):
    session = FakeSession(error=requests.Timeout("slow"))
    app = create_app({"DEVICE_API_KEY": None, "STORAGE_BACKEND": "apex"}, repository=repo(session))
    client = app.test_client()
    response = client.post("/api/readings", json=valid_payload)
    assert response.status_code == 502
    assert response.get_json()["error"]["code"] == "upstream_error"
    assert client.get("/api/health").status_code == 503


def test_apex_backend_requires_url():
    with pytest.raises(RuntimeError):
        create_app({"STORAGE_BACKEND": "apex", "APEX_ORDS_BASE_URL": ""})
