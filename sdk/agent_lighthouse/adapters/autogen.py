"""
AutoGen adapter via logging handler.
Best-effort parsing of structured log records.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from ..tracer import get_tracer

logger = logging.getLogger("agent_lighthouse.adapters.autogen")

_REGISTERED = False


class _AutoGenLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self._spans: dict[str, tuple[str, float]] = {}
        self._traces: dict[str, str] = {}

    def _ensure_trace(self, event_id: str, name: str) -> Optional[str]:
        tracer = get_tracer()
        trace_id = tracer.trace_id
        if trace_id:
            return trace_id
        existing = self._traces.get(event_id)
        if existing:
            return existing
        trace = tracer.client.create_trace(
            name=name,
            framework="autogen",
            metadata={"event_id": event_id},
        )
        trace_id = trace.get("trace_id")
        if trace_id:
            self._traces[event_id] = trace_id
        return trace_id

    def emit(self, record: logging.LogRecord) -> None:
        try:
            data = record.__dict__
            event = data.get("event") or data.get("event_name")
            if not event:
                return

            event_id = (
                str(data.get("event_id") or data.get("run_id") or f"{record.created}-{event}")
            )
            tracer = get_tracer()
            kind = data.get("kind") or "internal"
            name = data.get("name") or data.get("agent_name") or event

            if event.endswith("_start"):
                trace_id = self._ensure_trace(event_id, f"{name} (autogen)")
                if not trace_id:
                    return
                span = tracer.client.create_span(
                    trace_id=trace_id,
                    name=name,
                    kind=kind,
                    parent_span_id=tracer.span_id,
                    input_data=data.get("input_data"),
                    attributes={"event": event},
                )
                span_id = span.get("span_id")
                if span_id:
                    self._spans[event_id] = (span_id, time.perf_counter())
                return

            if event.endswith("_end") or event.endswith("_error"):
                span_entry = self._spans.pop(event_id, None)
                trace_id = tracer.trace_id or self._traces.get(event_id)
                if not span_entry or not trace_id:
                    return
                span_id, start = span_entry
                duration_ms = (time.perf_counter() - start) * 1000
                status = "error" if event.endswith("_error") else "success"
                tracer.client.update_span(
                    trace_id=trace_id,
                    span_id=span_id,
                    status=status,
                    output_data=data.get("output_data"),
                    error_message=data.get("error_message"),
                    error_type=data.get("error_type"),
                    duration_ms=duration_ms,
                )
                if event_id in self._traces and tracer.trace_id is None:
                    tracer.client.complete_trace(
                        trace_id, "success" if status == "success" else "error"
                    )
                    self._traces.pop(event_id, None)
        except Exception:  # noqa: BLE001
            logger.debug("AutoGen log handling failed", exc_info=True)


def register_autogen_logging() -> bool:
    global _REGISTERED
    if _REGISTERED:
        return True
    try:
        import autogen  # type: ignore  # noqa: F401
    except Exception:  # noqa: BLE001
        return False

    handler = _AutoGenLogHandler()
    log = logging.getLogger("autogen")
    if handler not in log.handlers:
        log.addHandler(handler)
    _REGISTERED = True
    return True
