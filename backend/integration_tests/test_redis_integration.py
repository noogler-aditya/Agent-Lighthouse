import os
import sys
from pathlib import Path

import pytest
import redis as redis_sync
from fastapi.testclient import TestClient

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("DATABASE_URL", "postgresql://lighthouse:lighthouse@localhost:5432/lighthouse")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:5173")
os.environ.setdefault("SUPABASE_URL", "http://localhost:54321")
os.environ.setdefault("SUPABASE_JWT_ISSUER", "http://localhost:54321/auth/v1")
os.environ.setdefault("SUPABASE_JWT_AUDIENCE", "authenticated")
os.environ.setdefault("SUPABASE_TEST_JWT_SECRET", "integration-test-secret")
os.environ.setdefault("MACHINE_API_KEYS", "itest-key:trace:write|trace:read")
os.environ.setdefault("RATE_LIMIT_WINDOW_SECONDS", "60")
os.environ.setdefault("RATE_LIMIT_WRITE_PER_WINDOW", "3")
os.environ.setdefault("RATE_LIMIT_READ_PER_WINDOW", "20")
os.environ.setdefault("SUPABASE_URL", "test")
os.environ.setdefault("SUPABASE_ANON_KEY", "test")

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from config import get_settings  # noqa: E402
from main import app  # noqa: E402


def _flush_redis():
    client = redis_sync.Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
    client.flushdb()
    client.close()


def _auth_headers(subject: str) -> dict[str, str]:
    del subject
    return {"Authorization": "Bearer test-token"}


@pytest.fixture(autouse=True)
def _reset_state():
    get_settings.cache_clear()
    _flush_redis()
    yield
    _flush_redis()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health_contracts_include_dependency_details(client):
    live = client.get("/health/live")
    assert live.status_code == 200
    assert live.json()["status"] == "alive"

    ready = client.get("/health/ready")
    assert ready.status_code == 200
    ready_payload = ready.json()
    assert "dependencies" in ready_payload
    assert "redis" in ready_payload["dependencies"]
    assert "auth" in ready_payload["dependencies"]

    health = client.get("/health")
    assert health.status_code == 200
    payload = health.json()
    assert "build_version" in payload
    assert "request_id" in payload
    assert "dependencies" in payload


def test_trace_write_and_read_with_real_redis(client):
    user_headers = _auth_headers("integration-user")

    create_trace = client.post(
        "/api/traces",
        headers=user_headers,
        json={"name": "integration-trace", "metadata": {"suite": "integration"}},
    )
    assert create_trace.status_code == 200
    trace_id = create_trace.json()["trace_id"]

    create_span = client.post(
        f"/api/traces/{trace_id}/spans",
        headers=user_headers,
        json={"name": "tool-span", "kind": "tool"},
    )
    assert create_span.status_code == 200

    read_trace = client.get(f"/api/traces/{trace_id}", headers=user_headers)
    assert read_trace.status_code == 200
    payload = read_trace.json()
    assert payload["trace_id"] == trace_id
    assert len(payload["spans"]) == 1


def test_write_rate_limit_enforced(client):
    headers = _auth_headers("rate-limit-user")
    statuses: list[int] = []
    for idx in range(6):
        response = client.post(
            "/api/traces",
            headers=headers,
            json={"name": f"trace-{idx}"},
        )
        statuses.append(response.status_code)

    assert 429 in statuses
