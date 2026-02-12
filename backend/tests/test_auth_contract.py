from config import get_settings


def _bearer() -> dict[str, str]:
    return {"Authorization": "Bearer test-token"}


def test_user_can_read_and_write(client_and_store):
    client, _, _ = client_and_store

    headers = _bearer()
    read = client.get("/api/traces", headers=headers)
    assert read.status_code == 200

    write = client.post("/api/traces", headers=headers, json={"name": "allowed"})
    assert write.status_code == 200


def test_machine_key_scope_allows_trace_ingestion_only(client_and_store):
    client, _, _ = client_and_store
    settings = get_settings()
    machine_key = next(iter(settings.machine_api_keys_map.keys()))

    create_trace = client.post(
        "/api/traces",
        headers={"X-API-Key": machine_key},
        json={"name": "machine-trace"},
    )
    assert create_trace.status_code == 200
    trace_id = create_trace.json()["trace_id"]

    state_write = client.post(f"/api/state/{trace_id}/pause", headers={"X-API-Key": machine_key})
    assert state_write.status_code == 200
