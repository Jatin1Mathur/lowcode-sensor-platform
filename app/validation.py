"""Validation of incoming sensor payloads.

A payload is rejected unless it has all required fields, the correct
data types and values inside each sensor's allowed range. All problems
are collected so the device (or tester) sees every issue at once.
"""

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .sensors import SENSORS

REQUIRED_FIELDS = ("device_id", "cycle", "timestamp", "readings")
MAX_DEVICE_ID_LENGTH = 64


@dataclass
class ValidationResult:
    errors: list[dict] = field(default_factory=list)
    data: dict | None = None

    @property
    def ok(self) -> bool:
        return not self.errors

    def add(self, field_name: str, issue: str) -> None:
        self.errors.append({"field": field_name, "issue": issue})


def _is_number(value) -> bool:
    # bool is a subclass of int in Python, so exclude it explicitly
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _parse_timestamp(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def validate_payload(payload) -> ValidationResult:
    """Validate one cycle payload and return a normalised copy if valid."""
    result = ValidationResult()

    if not isinstance(payload, dict):
        result.add("body", "must be a JSON object")
        return result

    for name in REQUIRED_FIELDS:
        if name not in payload or payload[name] is None:
            result.add(name, "is required")

    unknown = sorted(set(payload) - set(REQUIRED_FIELDS))
    for name in unknown:
        result.add(name, "is not an allowed field")

    device_id = payload.get("device_id")
    if device_id is not None:
        if not isinstance(device_id, str) or not device_id.strip():
            result.add("device_id", "must be a non-empty string")
        elif len(device_id) > MAX_DEVICE_ID_LENGTH:
            result.add("device_id", f"must be at most {MAX_DEVICE_ID_LENGTH} characters")

    cycle = payload.get("cycle")
    if cycle is not None:
        if not isinstance(cycle, int) or isinstance(cycle, bool):
            result.add("cycle", "must be an integer")
        elif cycle < 1:
            result.add("cycle", "must be 1 or greater")

    timestamp = payload.get("timestamp")
    parsed_ts = None
    if timestamp is not None:
        if not isinstance(timestamp, str):
            result.add("timestamp", "must be an ISO 8601 string")
        else:
            parsed_ts = _parse_timestamp(timestamp)
            if parsed_ts is None:
                result.add("timestamp", "must be ISO 8601 with a time zone, e.g. 2026-11-06T08:00:00Z")

    readings = payload.get("readings")
    clean_readings: dict[str, float] = {}
    if readings is not None:
        if not isinstance(readings, dict):
            result.add("readings", "must be an object of sensor code to value")
        elif not readings:
            result.add("readings", "must contain at least one sensor value")
        else:
            for code, value in readings.items():
                path = f"readings.{code}"
                sensor = SENSORS.get(code)
                if sensor is None:
                    result.add(path, "unknown sensor code")
                    continue
                if not _is_number(value):
                    result.add(path, "must be a number")
                    continue
                if not math.isfinite(value):
                    result.add(path, "must be a finite number")
                    continue
                if not sensor.min_value <= value <= sensor.max_value:
                    result.add(
                        path,
                        f"out of range [{sensor.min_value}, {sensor.max_value}] {sensor.unit}",
                    )
                    continue
                clean_readings[code] = float(value)

    if result.ok:
        result.data = {
            "device_id": device_id.strip(),
            "cycle": cycle,
            "timestamp": parsed_ts,
            "readings": clean_readings,
        }
    return result
