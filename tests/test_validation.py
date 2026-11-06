import copy

import pytest

from app.sensors import SENSORS
from app.validation import validate_payload


def fields(result):
    return {e["field"] for e in result.errors}


def test_valid_payload_is_normalised(valid_payload):
    result = validate_payload(valid_payload)
    assert result.ok
    assert result.data["timestamp"].isoformat() == "2026-11-06T08:00:00+00:00"
    assert result.data["readings"]["PS1"] == 160.4


def test_all_17_sensors_accepted(valid_payload):
    payload = copy.deepcopy(valid_payload)
    payload["readings"] = {code: (s.min_value + s.max_value) / 2 for code, s in SENSORS.items()}
    result = validate_payload(payload)
    assert result.ok
    assert len(result.data["readings"]) == 17


def test_catalog_has_17_sensors():
    assert len(SENSORS) == 17


@pytest.mark.parametrize("missing", ["device_id", "cycle", "timestamp", "readings"])
def test_missing_required_field(valid_payload, missing):
    del valid_payload[missing]
    result = validate_payload(valid_payload)
    assert not result.ok
    assert missing in fields(result)


def test_body_must_be_object():
    assert fields(validate_payload([1, 2])) == {"body"}


def test_unknown_top_level_field(valid_payload):
    valid_payload["debug"] = True
    assert "debug" in fields(validate_payload(valid_payload))


@pytest.mark.parametrize("cycle", ["7", 1.5, True, 0, -3])
def test_invalid_cycle(valid_payload, cycle):
    valid_payload["cycle"] = cycle
    assert "cycle" in fields(validate_payload(valid_payload))


@pytest.mark.parametrize("ts", ["yesterday", "2026-11-06T08:00:00", 1730880000])
def test_invalid_timestamp(valid_payload, ts):
    valid_payload["timestamp"] = ts
    assert "timestamp" in fields(validate_payload(valid_payload))


@pytest.mark.parametrize("device_id", ["", "   ", 42, "x" * 65])
def test_invalid_device_id(valid_payload, device_id):
    valid_payload["device_id"] = device_id
    assert "device_id" in fields(validate_payload(valid_payload))


@pytest.mark.parametrize("value", ["160", None, True, float("nan"), float("inf")])
def test_reading_must_be_finite_number(valid_payload, value):
    valid_payload["readings"]["PS1"] = value
    assert "readings.PS1" in fields(validate_payload(valid_payload))


@pytest.mark.parametrize("code,value", [("PS1", 250), ("PS1", -1), ("TS1", 120), ("VS1", 5.01)])
def test_reading_out_of_range(valid_payload, code, value):
    valid_payload["readings"][code] = value
    result = validate_payload(valid_payload)
    assert f"readings.{code}" in fields(result)
    assert "out of range" in result.errors[0]["issue"]


def test_boundary_values_accepted(valid_payload):
    valid_payload["readings"] = {"PS1": 0, "TS1": 100, "VS1": 5}
    assert validate_payload(valid_payload).ok


def test_unknown_sensor_code(valid_payload):
    valid_payload["readings"]["XX9"] = 1.0
    assert "readings.XX9" in fields(validate_payload(valid_payload))


@pytest.mark.parametrize("readings", [{}, [], "PS1=1"])
def test_invalid_readings_container(valid_payload, readings):
    valid_payload["readings"] = readings
    assert "readings" in fields(validate_payload(valid_payload))


def test_all_errors_reported_together(valid_payload):
    payload = {"cycle": "seven", "readings": {"PS1": 999, "TS1": "hot", "XX9": 1}}
    result = validate_payload(payload)
    assert {"device_id", "timestamp", "cycle", "readings.PS1",
            "readings.TS1", "readings.XX9"} <= fields(result)
