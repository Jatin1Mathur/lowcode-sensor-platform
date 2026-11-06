import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app  # noqa: E402
from app.repository import InMemoryRepository  # noqa: E402

API_KEY = "test-key"


@pytest.fixture
def valid_payload():
    return {
        "device_id": "esp32-rig-01",
        "cycle": 1,
        "timestamp": "2026-11-06T08:00:00Z",
        "readings": {"PS1": 160.4, "TS1": 45.2, "VS1": 0.61, "FS1": 6.8},
    }


@pytest.fixture
def app():
    return create_app(
        {"TESTING": True, "DEVICE_API_KEY": API_KEY, "STORAGE_BACKEND": "memory"},
        repository=InMemoryRepository(),
    )


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth():
    return {"X-API-Key": API_KEY}
