"""
CrewAI adapter with best-effort feature detection.
Fail-silent when CrewAI APIs are unavailable.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Optional

from ..tracer import get_tracer
from ..serialization import _capture_args, _capture_output

logger = logging.getLogger("agent_lighthouse.adapters.crewai")

_REGISTERED = False


class _CrewAIEventHandler:
    def __init__(self, tracer=None):
        self.tracer = tracer or get_tracer()
        self._run_spans: dict[str, str] = {}
        self._run_start: dict[str, float] = {}
        self._run_traces: dict[str, str] = {}

    def _ensure_trace(self, run_id: str, name: str) -> Optional[str]:
        trace_id = self.tracer.trace_id
        if trace_id:
            return trace_id
        existing = self._run_traces.get(run_id)
        if existing:
            return existing
        trace = self.tracer.client.create_trace(
            name=name,
            framework="crewai",
            metadata={"run_id": run_id},
        )
        trace_id = trace.get("trace_id")
        if trace_id:
            self._run_traces[run_id] = trace_id
        return trace_id

    def _start_span(
        self,
        run_id: str,
        name: str,
        kind: str,
        input_data: Optional[dict] = None,
        attributes: Optional[dict] = None,
    ) -> None:
        trace_id = self._ensure_trace(run_id, name)
        if not trace_id:
            return
        parent_span_id = self.tracer.span_id
        span = self.tracer.client.create_span(
            trace_id=trace_id,
            name=name,
            kind=kind,
            parent_span_id=parent_span_id,
            input_data=input_data,
            attributes=attributes or {},
        )
        span_id = span.get("span_id")
        if span_id:
            self._run_spans[run_id] = span_id
            self._run_start[run_id] = time.perf_counter()

    def _end_span(self, run_id: str, status: str, output_data: Optional[dict] = None) -> None:
        span_id = self._run_spans.pop(run_id, None)
        start = self._run_start.pop(run_id, None)
        trace_id = self.tracer.trace_id or self._run_traces.get(run_id)
        if not trace_id or not span_id:
            return
        duration_ms = None
        if start is not None:
            duration_ms = (time.perf_counter() - start) * 1000
        self.tracer.client.update_span(
            trace_id=trace_id,
            span_id=span_id,
            status=status,
            output_data=output_data,
            duration_ms=duration_ms,
        )
        if run_id in self._run_traces and self.tracer.trace_id is None:
            self.tracer.client.complete_trace(trace_id, "success" if status == "success" else "error")
            self._run_traces.pop(run_id, None)

    # Best-effort event handlers (method names depend on CrewAI version)
    def on_agent_start(self, agent_name: str, run_id: str, **kwargs: Any):
        self._start_span(
            run_id=run_id,
            name=agent_name or "CrewAI Agent",
            kind="agent",
            input_data=_capture_args((), kwargs),
        )

    def on_agent_end(self, output: Any, run_id: str, **kwargs: Any):
        self._end_span(run_id, "success", _capture_output(output))

    def on_agent_error(self, error: Exception, run_id: str, **kwargs: Any):
        self._end_span(run_id, "error", {"error": str(error)})

    def on_tool_start(self, tool_name: str, run_id: str, **kwargs: Any):
        self._start_span(
            run_id=run_id,
            name=tool_name or "CrewAI Tool",
            kind="tool",
            input_data=_capture_args((), kwargs),
        )

    def on_tool_end(self, output: Any, run_id: str, **kwargs: Any):
        self._end_span(run_id, "success", _capture_output(output))

    def on_tool_error(self, error: Exception, run_id: str, **kwargs: Any):
        self._end_span(run_id, "error", {"error": str(error)})

    def on_task_start(self, task_name: str, run_id: str, **kwargs: Any):
        self._start_span(
            run_id=run_id,
            name=task_name or "CrewAI Task",
            kind="chain",
            input_data=_capture_args((), kwargs),
        )

    def on_task_end(self, output: Any, run_id: str, **kwargs: Any):
        self._end_span(run_id, "success", _capture_output(output))

    def on_task_error(self, error: Exception, run_id: str, **kwargs: Any):
        self._end_span(run_id, "error", {"error": str(error)})


def register_crewai_hooks() -> bool:
    """
    Best-effort registration using available CrewAI telemetry/callback APIs.
    """
    global _REGISTERED
    if _REGISTERED:
        return True

    try:
        import crewai  # type: ignore
    except Exception:  # noqa: BLE001
        return False

    handler = _CrewAIEventHandler()

    # Telemetry hooks (if available)
    telemetry = getattr(crewai, "telemetry", None)
    if telemetry is not None:
        for attr in ("register_handler", "add_handler", "add_listener", "register"):
            if hasattr(telemetry, attr):
                try:
                    getattr(telemetry, attr)(handler)
                    _REGISTERED = True
                    return True
                except Exception:  # noqa: BLE001
                    logger.debug("CrewAI telemetry hook registration failed", exc_info=True)

    # Callback manager (if available)
    callbacks = getattr(crewai, "callbacks", None)
    if callbacks is not None:
        manager_cls = getattr(callbacks, "CallbackManager", None)
        if manager_cls is not None:
            original_init = manager_cls.__init__

            def patched_init(self, *args, **kwargs):  # type: ignore[no-redef]
                original_init(self, *args, **kwargs)
                try:
                    if hasattr(self, "add_handler"):
                        self.add_handler(handler)
                except Exception:  # noqa: BLE001
                    logger.debug("CrewAI callback registration failed", exc_info=True)

            manager_cls.__init__ = patched_init  # type: ignore[assignment]
            _REGISTERED = True
            return True

    logger.debug("CrewAI hooks not registered: unsupported API surface")
    return False
