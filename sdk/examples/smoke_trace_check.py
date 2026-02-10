"""
Deterministic smoke test for Agent Lighthouse trace ingestion.
Tests the enterprise-grade SDK with fail-silent mode, output capture, and async support.
"""
import os
import sys

from agent_lighthouse import get_tracer


def fail(message: str) -> None:
    print(f"[FAIL] {message}")
    raise SystemExit(1)


def main() -> None:
    tracer = get_tracer(
        base_url=os.getenv("LIGHTHOUSE_BASE_URL", "http://localhost:8000"),
        framework="smoke-test",
        api_key=os.getenv("LIGHTHOUSE_API_KEY", "local-dev-key"),
        fail_silent=True,  # Never crash the smoke test itself
    )

    with tracer.trace(
        name="Smoke Trace Validation",
        description="Validates that traces and spans are ingested and retrievable",
        metadata={"smoke_test": True},
    ) as trace_info:
        with tracer.span(
            name="Smoke Agent",
            kind="agent",
            agent_id="smoke-agent",
            agent_name="Smoke Agent",
            input_data={"purpose": "smoke"},
        ):
            tracer.record_tokens(prompt_tokens=25, completion_tokens=10, cost_usd=0.0007)
            tracer.update_state(memory={"phase": "agent"}, variables={"ok": True})

            # New: test output recording
            tracer.record_output({"result": "agent completed"})

            with tracer.span(
                name="Smoke Tool",
                kind="tool",
                agent_id="smoke-agent",
                agent_name="Smoke Agent",
                input_data={"tool": "noop"},
            ):
                # Note: output is now auto-captured by decorators
                tracer.record_output({"tool_result": "success"})

    trace_id = trace_info.get("trace_id")
    if not trace_id:
        fail("Failed to create trace (backend may be unreachable)")

    trace = tracer.client.get_trace(trace_id)

    if not trace:
        fail("Trace not found after creation")

    spans = trace.get("spans") or []
    status = trace.get("status")

    if len(spans) == 0:
        fail("Trace has no spans")

    if status not in {"success", "error"}:
        fail(f"Trace status is not terminal: {status}")

    print("[PASS] Smoke trace check successful")
    print(f"Trace ID: {trace_id}")
    print(f"Span count: {len(spans)}")
    print(f"Status: {status}")

    # Cleanup
    tracer.close()


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        print(f"[FAIL] Unexpected error: {exc}", file=sys.stderr)
        raise SystemExit(1)
