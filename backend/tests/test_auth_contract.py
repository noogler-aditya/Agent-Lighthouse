from config import get_settings
from security import create_access_token


def _bearer(role: str) -> dict[str, str]:
    settings = get_settings()
    token = create_access_token(settings, subject=f"test-{role}", role=role)
    return {"Authorization": f"Bearer {token}"}


def test_viewer_can_read_but_cannot_write(client_and_store):
    client, _, _ = client_and_store

    read = client.get("/api/traces", headers=_bearer("viewer"))
    assert read.status_code == 200

    write = client.post("/api/traces", headers=_bearer("viewer"), json={"name": "blocked"})
    assert write.status_code == 403


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
    assert state_write.status_code == 401
