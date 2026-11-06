import copy


def post(client, payload, headers):
    return client.post("/api/readings", json=payload, headers=headers)


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json()["storage_backend"] == "memory"


def test_sensor_catalog(client):
    body = client.get("/api/sensors").get_json()
    assert body["count"] == 17
    assert {"code", "unit", "min_value", "max_value"} <= set(body["items"][0])


def test_create_reading(client, auth, valid_payload):
    response = post(client, valid_payload, auth)
    assert response.status_code == 201
    body = response.get_json()
    assert body["recorded_at"] == "2026-11-06 08:00:00"
    assert body["readings"]["TS1"] == 45.2


def test_missing_api_key(client, valid_payload):
    response = post(client, valid_payload, {})
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "unauthorized"


def test_wrong_api_key(client, valid_payload):
    assert post(client, valid_payload, {"X-API-Key": "nope"}).status_code == 401


def test_api_key_optional_when_not_configured(valid_payload):
    from app import create_app
    from app.repository import InMemoryRepository
    app = create_app({"DEVICE_API_KEY": None}, repository=InMemoryRepository())
    assert app.test_client().post("/api/readings", json=valid_payload).status_code == 201


def test_invalid_json(client, auth):
    response = client.post("/api/readings", data="{bad json",
                           content_type="application/json", headers=auth)
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_json"


def test_wrong_content_type(client, auth):
    response = client.post("/api/readings", data="x", content_type="text/plain", headers=auth)
    assert response.status_code == 415


def test_validation_error_format(client, auth, valid_payload):
    valid_payload["readings"]["PS1"] = 999
    del valid_payload["timestamp"]
    response = post(client, valid_payload, auth)
    assert response.status_code == 400
    error = response.get_json()["error"]
    assert error["code"] == "validation_failed"
    assert {d["field"] for d in error["details"]} == {"timestamp", "readings.PS1"}


def test_duplicate_cycle(client, auth, valid_payload):
    assert post(client, valid_payload, auth).status_code == 201
    response = post(client, valid_payload, auth)
    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "duplicate_cycle"


def test_get_cycle(client, auth, valid_payload):
    post(client, valid_payload, auth)
    response = client.get("/api/cycles/esp32-rig-01/1")
    assert response.status_code == 200
    assert response.get_json()["readings"]["PS1"] == 160.4


def test_get_unknown_cycle(client):
    response = client.get("/api/cycles/esp32-rig-01/99")
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "not_found"


def test_list_cycles_filter_and_limit(client, auth, valid_payload):
    for cycle in range(1, 6):
        payload = copy.deepcopy(valid_payload)
        payload["cycle"] = cycle
        post(client, payload, auth)
    other = copy.deepcopy(valid_payload)
    other["device_id"] = "esp32-rig-02"
    post(client, other, auth)

    body = client.get("/api/cycles?device_id=esp32-rig-01&limit=3").get_json()
    assert body["count"] == 3
    assert [c["cycle"] for c in body["items"]] == [1, 2, 3]
    assert all(c["sensor_count"] == 4 for c in body["items"])


def test_list_cycles_bad_limit(client):
    assert client.get("/api/cycles?limit=0").status_code == 400
    assert client.get("/api/cycles?limit=abc").status_code == 400


def test_batch_all_stored(client, auth, valid_payload):
    batch = []
    for cycle in range(1, 4):
        item = copy.deepcopy(valid_payload)
        item["cycle"] = cycle
        batch.append(item)
    response = client.post("/api/readings/batch", json=batch, headers=auth)
    assert response.status_code == 201
    assert response.get_json()["stored"] == 3


def test_batch_partial(client, auth, valid_payload):
    bad = copy.deepcopy(valid_payload)
    bad["cycle"] = 2
    bad["readings"]["VS1"] = 50
    response = client.post("/api/readings/batch", json=[valid_payload, bad], headers=auth)
    assert response.status_code == 207
    body = response.get_json()
    assert body["stored"] == 1 and body["rejected"] == 1
    assert body["results"][1]["details"][0]["field"] == "readings.VS1"


def test_batch_none_stored(client, auth):
    response = client.post("/api/readings/batch", json=[{}, {"cycle": 1}], headers=auth)
    assert response.status_code == 400
    assert response.get_json()["stored"] == 0


def test_batch_must_be_list(client, auth, valid_payload):
    assert client.post("/api/readings/batch", json=valid_payload, headers=auth).status_code == 400


def test_batch_size_limit(app, auth, valid_payload):
    app.config["MAX_BATCH_SIZE"] = 2
    response = app.test_client().post("/api/readings/batch",
                                      json=[valid_payload] * 3, headers=auth)
    assert response.status_code == 413


def test_unknown_route_uses_json_error(client):
    response = client.get("/api/nope")
    assert response.status_code == 404
    assert "error" in response.get_json()
