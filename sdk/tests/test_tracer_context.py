import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import agent_lighthouse.tracer as tracer_module


class FakeClient:
    def __init__(self) -> None:
        self.traces_created = 0
        self.spans_created = 0
        self.updated_spans = 0
        self.completed_traces: list[str] = []
        self.last_trace_id: str | None = None
        self.last_span_trace_id: str | None = None

    def create_trace(self, name: str, description=None, framework=None, metadata=None) -> dict:
        del name, description, framework, metadata
        self.traces_created += 1
        self.last_trace_id = f"trace-{self.traces_created}"
        return {"trace_id": self.last_trace_id}

    def complete_trace(self, trace_id: str, status: str) -> dict:
        self.completed_traces.append(f"{trace_id}:{status}")
        return {"trace_id": trace_id, "status": status}

    def wait_if_paused(self, trace_id: str) -> bool:
        del trace_id
        return False

    def create_span(
        self,
        trace_id: str,
        name: str,
        kind: str,
        parent_span_id=None,
        agent_id=None,
        agent_name=None,
        input_data=None,
        attributes=None,
    ) -> dict:
        del name, kind, parent_span_id, agent_id, agent_name, input_data, attributes
        self.spans_created += 1
        self.last_span_trace_id = trace_id
        return {"span_id": f"span-{self.spans_created}"}

    def update_span(self, trace_id: str, span_id: str, **kwargs) -> dict:
        del trace_id, span_id, kwargs
        self.updated_spans += 1
        return {"ok": True}

    def update_state(self, trace_id: str, memory=None, context=None, variables=None) -> dict:
        del trace_id, memory, context, variables
        return {"ok": True}


def _new_fake_tracer() -> tuple[tracer_module.LighthouseTracer, FakeClient]:
    tracer = tracer_module.LighthouseTracer(base_url="http://localhost:9999", api_key="test-key")
    fake_client = FakeClient()
    tracer.client = fake_client
    return tracer, fake_client


def setup_function():
    tracer_module._global_tracer = None


def teardown_function():
    tracer_module._global_tracer = None


def test_get_tracer_prefers_active_context():
    tracer, fake_client = _new_fake_tracer()
    assert fake_client.traces_created == 0

    with tracer.trace("workflow"):
        active = tracer_module.get_tracer()
        assert active is tracer
        assert fake_client.last_trace_id == tracer.trace_id


def test_trace_tool_decorator_uses_active_trace_context():
    tracer, fake_client = _new_fake_tracer()

    @tracer_module.trace_tool("lookup")
    def lookup_tool(x: int) -> int:
        return x + 1

    with tracer.trace("decorated-workflow"):
        result = lookup_tool(2)
        assert result == 3

    assert fake_client.spans_created == 1
    assert fake_client.last_span_trace_id == fake_client.last_trace_id
    assert fake_client.updated_spans >= 1


def test_trace_tool_no_active_trace_auto_creates_trace():
    """When no trace is active, decorators should auto-create a trace and span
    so that data is never silently dropped (the empty-dashboard bug fix)."""
    tracer, fake_client = _new_fake_tracer()
    tracer_module._global_tracer = tracer

    @tracer_module.trace_tool("auto-traced")
    def plain_tool(x: int) -> int:
        return x * 2

    assert plain_tool(3) == 6
    # A trace and span should both be auto-created
    assert fake_client.traces_created == 1
    assert fake_client.spans_created == 1
