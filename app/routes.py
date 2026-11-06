import hmac

from flask import Blueprint, current_app, jsonify, request

from .errors import ApiError
from .repository import DuplicateCycleError, UpstreamError
from .sensors import SENSORS
from .validation import validate_payload

api = Blueprint("api", __name__, url_prefix="/api")


def _repo():
    return current_app.extensions["sensor_repository"]


def _require_device_key():
    expected = current_app.config.get("DEVICE_API_KEY")
    if not expected:
        return
    provided = request.headers.get("X-API-Key", "")
    if not hmac.compare_digest(provided, expected):
        raise ApiError(401, "unauthorized", "Missing or invalid X-API-Key header")


def _json_body():
    if not request.is_json:
        raise ApiError(415, "unsupported_media_type", "Content-Type must be application/json")
    body = request.get_json(silent=True)
    if body is None:
        raise ApiError(400, "invalid_json", "Request body is not valid JSON")
    return body


def _store(payload) -> dict:
    result = validate_payload(payload)
    if not result.ok:
        raise ApiError(400, "validation_failed", "Payload validation failed", result.errors)
    try:
        return _repo().save_cycle(result.data)
    except DuplicateCycleError as exc:
        raise ApiError(409, "duplicate_cycle", str(exc)) from exc
    except UpstreamError as exc:
        current_app.logger.error("APEX error: %s", exc)
        raise ApiError(502, "upstream_error", "Could not store data in Oracle APEX") from exc


@api.get("/health")
def health():
    backend_ok = _repo().ping()
    status = 200 if backend_ok else 503
    return jsonify({
        "status": "ok" if backend_ok else "degraded",
        "storage_backend": current_app.config["STORAGE_BACKEND"],
    }), status


@api.get("/sensors")
def list_sensors():
    return jsonify({"count": len(SENSORS), "items": [s.to_dict() for s in SENSORS.values()]})


@api.post("/readings")
def create_reading():
    _require_device_key()
    record = _store(_json_body())
    current_app.logger.info("Stored cycle %s from %s", record["cycle"], record["device_id"])
    return jsonify(record), 201


@api.post("/readings/batch")
def create_readings_batch():
    """Store many cycles at once (e.g. a device catching up after offline time).

    Returns 201 if all items were stored, 207 if some failed, 400 if none were stored.
    """
    _require_device_key()
    body = _json_body()
    if not isinstance(body, list) or not body:
        raise ApiError(400, "validation_failed", "Body must be a non-empty JSON array")
    max_size = current_app.config["MAX_BATCH_SIZE"]
    if len(body) > max_size:
        raise ApiError(413, "batch_too_large", f"At most {max_size} items per batch")

    results = []
    for index, item in enumerate(body):
        try:
            record = _store(item)
            results.append({"index": index, "status": 201,
                            "device_id": record["device_id"], "cycle": record["cycle"]})
        except ApiError as err:
            entry = {"index": index, "status": err.status, "code": err.code, "message": err.message}
            if err.details:
                entry["details"] = err.details
            results.append(entry)

    stored = sum(1 for r in results if r["status"] == 201)
    status = 201 if stored == len(results) else (400 if stored == 0 else 207)
    return jsonify({"stored": stored, "rejected": len(results) - stored, "results": results}), status


@api.get("/cycles")
def list_cycles():
    raw_limit = request.args.get("limit", "50")
    limit = int(raw_limit) if raw_limit.isdigit() else 0
    if not 1 <= limit <= 500:
        raise ApiError(400, "validation_failed", "limit must be between 1 and 500")
    device_id = request.args.get("device_id")
    try:
        items = _repo().list_cycles(device_id=device_id, limit=limit)
    except UpstreamError as exc:
        raise ApiError(502, "upstream_error", "Could not read data from Oracle APEX") from exc
    return jsonify({"count": len(items), "items": items})


@api.get("/cycles/<device_id>/<int:cycle>")
def get_cycle(device_id: str, cycle: int):
    try:
        record = _repo().get_cycle(device_id, cycle)
    except UpstreamError as exc:
        raise ApiError(502, "upstream_error", "Could not read data from Oracle APEX") from exc
    if record is None:
        raise ApiError(404, "not_found", f"No cycle {cycle} for device {device_id}")
    return jsonify(record)
