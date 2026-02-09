from config import Settings


def test_traces_endpoint_requires_authorization(client_and_store):
    client, _, _ = client_and_store

    response = client.get("/api/traces")

    assert response.status_code == 401
    assert response.json()["detail"] == "Unauthorized"


def test_create_and_list_trace(client_and_store, auth_headers):
    client, _, _ = client_and_store
    payload = {"name": "test-trace", "description": "trace from unit test"}

    create_response = client.post("/api/traces", json=payload, headers=auth_headers)
    assert create_response.status_code == 200
    created = create_response.json()
    assert created["name"] == "test-trace"
    assert created["status"] == "running"

    list_response = client.get("/api/traces", headers=auth_headers)
    assert list_response.status_code == 200
    listed = list_response.json()
    assert listed["total"] == 1
    assert listed["traces"][0]["trace_id"] == created["trace_id"]


def test_create_span_then_patch_updates_metrics(client_and_store, auth_headers):
    client, _, _ = client_and_store
    create_response = client.post("/api/traces", json={"name": "trace-with-span"}, headers=auth_headers)
    trace_id = create_response.json()["trace_id"]

    span_response = client.post(
        f"/api/traces/{trace_id}/spans",
        json={"name": "call_tool", "kind": "tool"},
        headers=auth_headers,
    )
    assert span_response.status_code == 200
    span_id = span_response.json()["span_id"]

    patch_response = client.patch(
        f"/api/traces/{trace_id}/spans/{span_id}",
        json={"status": "success", "prompt_tokens": 30, "completion_tokens": 20, "total_tokens": 50, "cost_usd": 0.05},
        headers=auth_headers,
    )
    assert patch_response.status_code == 200

    trace_response = client.get(f"/api/traces/{trace_id}", headers=auth_headers)
    assert trace_response.status_code == 200
    trace = trace_response.json()
    assert trace["total_tokens"] == 50
    assert trace["tool_calls"] == 1
    assert trace["total_cost_usd"] == 0.05

    metrics_response = client.get(f"/api/traces/{trace_id}/metrics", headers=auth_headers)
    assert metrics_response.status_code == 200
    metrics = metrics_response.json()
    assert metrics["total_tokens"] == 50
    assert metrics["tool_calls"] == 1


def test_allowed_origins_parsing_from_csv():
    settings = Settings(ALLOWED_ORIGINS="http://localhost:5173, https://example.com")

    assert settings.allowed_origins_list == ["http://localhost:5173", "https://example.com"]
