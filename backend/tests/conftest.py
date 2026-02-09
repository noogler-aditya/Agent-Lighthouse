import sys
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import get_settings  # noqa: E402
from dependencies import get_connection_manager, get_redis  # noqa: E402
from main import app  # noqa: E402
from models.trace import Trace  # noqa: E402
from security import create_access_token  # noqa: E402


class FakeRedisService:
    def __init__(self) -> None:
        self.traces: dict[str, Trace] = {}
        self.states: dict[str, object] = {}

    async def list_traces(self, offset: int = 0, limit: int = 50, status: Optional[str] = None) -> list[Trace]:
        traces = sorted(self.traces.values(), key=lambda t: t.start_time, reverse=True)
        if status is not None:
            traces = [trace for trace in traces if trace.status.value == status]
        return traces[offset : offset + limit]

    async def count_traces(self, status: Optional[str] = None) -> int:
        if status is None:
            return len(self.traces)
        return len([trace for trace in self.traces.values() if trace.status.value == status])

    async def save_trace(self, trace: Trace, ttl_hours: Optional[int] = None, event_type: Optional[str] = None) -> bool:
        del ttl_hours, event_type
        self.traces[trace.trace_id] = trace
        return True

    async def get_trace(self, trace_id: str) -> Optional[Trace]:
        return self.traces.get(trace_id)

    async def delete_trace(self, trace_id: str) -> bool:
        self.traces.pop(trace_id, None)
        self.states.pop(trace_id, None)
        return True

    async def update_trace(self, trace: Trace) -> bool:
        if trace.trace_id not in self.traces:
            return False
        self.traces[trace.trace_id] = trace
        return True

    async def add_span(self, span) -> bool:
        trace = self.traces.get(span.trace_id)
        if not trace:
            return False
        trace.add_span(span)
        self.traces[trace.trace_id] = trace
        return True

    async def update_span(self, trace_id: str, span) -> bool:
        trace = self.traces.get(trace_id)
        if not trace:
            return False
        for idx, existing in enumerate(trace.spans):
            if existing.span_id == span.span_id:
                trace.spans[idx] = span
                trace.recalculate_aggregates()
                self.traces[trace_id] = trace
                return True
        return False

    async def get_metrics_summary(self, trace_id: str) -> Optional[dict]:
        trace = self.traces.get(trace_id)
        if not trace:
            return None
        return {
            "trace_id": trace.trace_id,
            "total_tokens": trace.total_tokens,
            "total_cost_usd": trace.total_cost_usd,
            "agent_count": trace.agent_count,
            "tool_calls": trace.tool_calls,
            "llm_calls": trace.llm_calls,
        }

    async def save_state(self, state) -> bool:
        self.states[state.trace_id] = state
        return True

    async def get_state(self, trace_id: str):
        return self.states.get(trace_id)

    async def delete_state(self, trace_id: str) -> bool:
        self.states.pop(trace_id, None)
        return True


class FakeConnectionManager:
    def __init__(self) -> None:
        self.active_connections = []
        self.events: list[dict] = []

    async def broadcast_span_event(self, trace_id: str, span_id: str, event_type: str, data: dict) -> None:
        self.events.append(
            {"trace_id": trace_id, "span_id": span_id, "event_type": event_type, "data": data}
        )

    async def broadcast_state_change(self, trace_id: str, control_status: str, state_data: Optional[dict] = None) -> None:
        self.events.append(
            {"trace_id": trace_id, "event_type": "state_change", "status": control_status, "state": state_data}
        )


@pytest.fixture
def auth_headers() -> dict[str, str]:
    settings = get_settings()
    token = create_access_token(settings, subject="test-operator", role="operator")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client_and_store():
    fake_redis = FakeRedisService()
    fake_manager = FakeConnectionManager()

    @asynccontextmanager
    async def _no_op_lifespan(_app):
        yield

    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = _no_op_lifespan
    app.dependency_overrides[get_redis] = lambda: fake_redis
    app.dependency_overrides[get_connection_manager] = lambda: fake_manager

    with TestClient(app) as client:
        yield client, fake_redis, fake_manager

    app.dependency_overrides.clear()
    app.router.lifespan_context = original_lifespan
