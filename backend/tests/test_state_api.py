def test_state_pause_resume_flow(client_and_store, auth_headers):
    client, _, _ = client_and_store
    create_trace = client.post("/api/traces", json={"name": "state-trace"}, headers=auth_headers)
    trace_id = create_trace.json()["trace_id"]

    init_response = client.post(
        f"/api/state/{trace_id}",
        json={"memory": {"step": 1}, "context": {"agent": "research"}, "variables": {"enabled": True}},
        headers=auth_headers,
    )
    assert init_response.status_code == 200
    assert init_response.json()["memory"]["step"] == 1

    pause_response = client.post(f"/api/state/{trace_id}/pause", headers=auth_headers)
    assert pause_response.status_code == 200
    assert pause_response.json()["status"] == "paused"

    resume_response = client.post(f"/api/state/{trace_id}/resume", headers=auth_headers)
    assert resume_response.status_code == 200
    assert resume_response.json()["status"] == "running"


def test_state_patch_rejects_invalid_path(client_and_store, auth_headers):
    client, _, _ = client_and_store
    create_trace = client.post("/api/traces", json={"name": "state-modify-trace"}, headers=auth_headers)
    trace_id = create_trace.json()["trace_id"]
    client.post(f"/api/state/{trace_id}", json={}, headers=auth_headers)

    modify_response = client.patch(
        f"/api/state/{trace_id}",
        json={"path": "badpath", "value": 123},
        headers=auth_headers,
    )
    assert modify_response.status_code == 400
    assert modify_response.json()["detail"] == "Invalid state path"
