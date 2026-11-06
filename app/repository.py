"""Storage backends.

`ApexRepository` forwards validated cycles to Oracle APEX through the
RESTful (ORDS) module defined in `apex/ords_module.sql`.
`InMemoryRepository` is used for local development and tests.
"""

from datetime import datetime
import json
from threading import Lock
from urllib.parse import quote

import requests


class DuplicateCycleError(Exception):
    """The device already reported this cycle."""


class UpstreamError(Exception):
    """Oracle APEX could not be reached or returned an unexpected error."""


def _serialise(cycle: dict) -> dict:
    ts: datetime = cycle["timestamp"]
    return {
        "device_id": cycle["device_id"],
        "cycle": cycle["cycle"],
        # Oracle-friendly UTC format, parsed in the ORDS handler
        "recorded_at": ts.strftime("%Y-%m-%d %H:%M:%S"),
        "readings": cycle["readings"],
    }


class InMemoryRepository:
    def __init__(self):
        self._cycles: dict[tuple[str, int], dict] = {}
        self._lock = Lock()

    def save_cycle(self, cycle: dict) -> dict:
        key = (cycle["device_id"], cycle["cycle"])
        record = _serialise(cycle)
        with self._lock:
            if key in self._cycles:
                raise DuplicateCycleError(f"cycle {key[1]} already stored for {key[0]}")
            self._cycles[key] = record
        return record

    def get_cycle(self, device_id: str, cycle: int) -> dict | None:
        return self._cycles.get((device_id, cycle))

    def list_cycles(self, device_id: str | None = None, limit: int = 50) -> list[dict]:
        items = [
            {"device_id": c["device_id"], "cycle": c["cycle"],
             "recorded_at": c["recorded_at"], "sensor_count": len(c["readings"])}
            for c in self._cycles.values()
            if device_id is None or c["device_id"] == device_id
        ]
        items.sort(key=lambda c: (c["device_id"], c["cycle"]))
        return items[:limit]

    def ping(self) -> bool:
        return True


class ApexRepository:
    def __init__(self, base_url: str, token: str | None = None,
                 timeout: float = 5.0, session: requests.Session | None = None):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers["Accept"] = "application/json"
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        try:
            return self.session.request(method, f"{self.base_url}{path}",
                                        timeout=self.timeout, **kwargs)
        except requests.RequestException as exc:
            raise UpstreamError(f"Oracle APEX not reachable: {exc}") from exc

    def save_cycle(self, cycle: dict) -> dict:
        record = _serialise(cycle)
        response = self._request("POST", "/cycles/", json=record)
        if response.status_code == 409:
            raise DuplicateCycleError(
                f"cycle {record['cycle']} already stored for {record['device_id']}")
        if response.status_code not in (200, 201):
            raise UpstreamError(f"Oracle APEX returned HTTP {response.status_code}")
        return record

    def get_cycle(self, device_id: str, cycle: int) -> dict | None:
        response = self._request("GET", f"/cycles/{quote(device_id, safe='')}/{cycle}")
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise UpstreamError(f"Oracle APEX returned HTTP {response.status_code}")
        rows = response.json().get("items", [])
        if not rows:
            return None
        return {
            "device_id": device_id,
            "cycle": cycle,
            "recorded_at": rows[0]["recorded_at"],
            "readings": {r["sensor_code"]: r["value"] for r in rows},
        }

    def list_cycles(self, device_id: str | None = None, limit: int = 50) -> list[dict]:
        params = {"limit": limit}
        if device_id:
            # ORDS filter object syntax
            params["q"] = json.dumps({"device_id": device_id})
        response = self._request("GET", "/cycles/", params=params)
        if response.status_code != 200:
            raise UpstreamError(f"Oracle APEX returned HTTP {response.status_code}")
        return response.json().get("items", [])

    def ping(self) -> bool:
        try:
            return self._request("GET", "/cycles/", params={"limit": 1}).status_code == 200
        except UpstreamError:
            return False
