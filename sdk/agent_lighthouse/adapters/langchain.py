"""
LangChain / LangGraph adapter using BaseCallbackHandler.
Fail-silent and safe to use when LangChain is not installed.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Optional

from ..tracer import get_tracer
from ..serialization import _capture_args, _capture_output
from ..pricing import get_cost_usd

logger = logging.getLogger("agent_lighthouse.adapters.langchain")

_REGISTERED = False


def _get_base_handler_class():
    try:
        from langchain.callbacks.base import BaseCallbackHandler  # type: ignore
        return BaseCallbackHandler
    except Exception:  # noqa: BLE001
        try:
            from langchain_core.callbacks import BaseCallbackHandler  # type: ignore
            return BaseCallbackHandler
        except Exception:  # noqa: BLE001
            return None


class LighthouseLangChainCallbackHandler:  # type: ignore[misc]
    """
    Minimal callback handler that creates spans from LangChain events.
    Uses direct client calls to avoid coupling to tracer context stack.
    """

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
            framework="langchain",
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

    def _end_span(
        self,
        run_id: str,
        status: str = "success",
        output_data: Optional[dict] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        model: Optional[str] = None,
    ) -> None:
        span_id = self._run_spans.pop(run_id, None)
        start = self._run_start.pop(run_id, None)
        trace_id = self.tracer.trace_id or self._run_traces.get(run_id)
        if not trace_id or not span_id:
            return

        duration_ms = None
        if start is not None:
            duration_ms = (time.perf_counter() - start) * 1000

        cost_usd = None
        if prompt_tokens is not None or completion_tokens is not None:
            pt = prompt_tokens or 0
            ct = completion_tokens or 0
            cost_usd = get_cost_usd(model, pt, ct)

        self.tracer.client.update_span(
            trace_id=trace_id,
            span_id=span_id,
            status=status,
            output_data=output_data,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=(prompt_tokens or 0) + (completion_tokens or 0)
            if prompt_tokens is not None or completion_tokens is not None
            else None,
            cost_usd=cost_usd,
            duration_ms=duration_ms,
        )

        if run_id in self._run_traces and self.tracer.trace_id is None:
            self.tracer.client.complete_trace(trace_id, "success" if status == "success" else "error")
            self._run_traces.pop(run_id, None)

    # ---- LLM callbacks ----
    def on_llm_start(self, serialized: dict, prompts: list[str], run_id: str, **kwargs: Any):
        model = serialized.get("name") if isinstance(serialized, dict) else None
        input_data = _capture_args((prompts,), kwargs)
        self._start_span(
            run_id=run_id,
            name="LLM Call (langchain)",
            kind="llm",
            input_data=input_data,
            attributes={"model": model} if model else {},
        )

    def on_chat_model_start(self, serialized: dict, messages: list, run_id: str, **kwargs: Any):
        """Handle modern Chat model calls (ChatOllama, ChatOpenAI, ChatAnthropic, etc.)."""
        model = serialized.get("name") if isinstance(serialized, dict) else None
        model = model or (serialized.get("kwargs", {}).get("model") if isinstance(serialized, dict) else None)
        # Flatten messages for input capture
        flat = []
        for msg_list in messages:
            for msg in (msg_list if isinstance(msg_list, list) else [msg_list]):
                try:
                    flat.append({"type": getattr(msg, "type", "unknown"), "content": str(getattr(msg, "content", msg))[:500]})
                except Exception:  # noqa: BLE001
                    flat.append({"content": str(msg)[:500]})
        input_data = {"messages": flat} if flat else None
        self._start_span(
            run_id=run_id,
            name=f"Chat Model ({model or 'langchain'})",
            kind="llm",
            input_data=input_data,
            attributes={"model": model, "provider": "langchain-chat"} if model else {"provider": "langchain-chat"},
        )

    def on_llm_end(self, response: Any, run_id: str, **kwargs: Any):
        usage = {}
        model = None
        try:
            llm_output = getattr(response, "llm_output", None) or {}
            usage = llm_output.get("token_usage", {}) if isinstance(llm_output, dict) else {}
            model = llm_output.get("model_name") if isinstance(llm_output, dict) else None
        except Exception:  # noqa: BLE001
            usage = {}

        prompt_tokens = usage.get("prompt_tokens") if isinstance(usage, dict) else None
        completion_tokens = usage.get("completion_tokens") if isinstance(usage, dict) else None

        output_data = _capture_output(response)
        self._end_span(
            run_id=run_id,
            status="success",
            output_data=output_data,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model=model,
        )

    def on_llm_error(self, error: Exception, run_id: str, **kwargs: Any):
        self._end_span(run_id=run_id, status="error", output_data={"error": str(error)})

    # ---- Chain callbacks ----
    def on_chain_start(self, serialized: dict, inputs: dict, run_id: str, **kwargs: Any):
        name = serialized.get("name", "Chain") if isinstance(serialized, dict) else "Chain"
        self._start_span(
            run_id=run_id,
            name=name,
            kind="chain",
            input_data=_capture_args((), inputs),
        )

    def on_chain_end(self, outputs: dict, run_id: str, **kwargs: Any):
        self._end_span(run_id=run_id, status="success", output_data=_capture_output(outputs))

    def on_chain_error(self, error: Exception, run_id: str, **kwargs: Any):
        self._end_span(run_id=run_id, status="error", output_data={"error": str(error)})

    # ---- Tool callbacks ----
    def on_tool_start(self, serialized: dict, input_str: str, run_id: str, **kwargs: Any):
        name = serialized.get("name", "Tool") if isinstance(serialized, dict) else "Tool"
        self._start_span(
            run_id=run_id,
            name=name,
            kind="tool",
            input_data=_capture_args((input_str,), kwargs),
        )

    def on_tool_end(self, output: Any, run_id: str, **kwargs: Any):
        self._end_span(run_id=run_id, status="success", output_data=_capture_output(output))

    def on_tool_error(self, error: Exception, run_id: str, **kwargs: Any):
        self._end_span(run_id=run_id, status="error", output_data={"error": str(error)})

    # ---- Agent callbacks ----
    def on_agent_start(self, serialized: dict, inputs: dict, run_id: str, **kwargs: Any):
        name = serialized.get("name", "Agent") if isinstance(serialized, dict) else "Agent"
        self._start_span(
            run_id=run_id,
            name=name,
            kind="agent",
            input_data=_capture_args((), inputs),
        )

    def on_agent_end(self, output: Any, run_id: str, **kwargs: Any):
        self._end_span(run_id=run_id, status="success", output_data=_capture_output(output))

    def on_agent_error(self, error: Exception, run_id: str, **kwargs: Any):
        self._end_span(run_id=run_id, status="error", output_data={"error": str(error)})


def register_langchain_callbacks() -> bool:
    global _REGISTERED
    if _REGISTERED:
        return True

    BaseHandler = _get_base_handler_class()
    if BaseHandler is None:
        return False

    try:
        from langchain.callbacks.manager import CallbackManager  # type: ignore
    except Exception:  # noqa: BLE001
        try:
            from langchain_core.callbacks.manager import CallbackManager  # type: ignore
        except Exception:  # noqa: BLE001
            return False

    HandlerCls = type(
        "LighthouseLangChainCallbackHandler",
        (BaseHandler, LighthouseLangChainCallbackHandler),
        {},
    )
    handler = HandlerCls()

    original_init = CallbackManager.__init__

    def patched_init(self, *args, **kwargs):  # type: ignore[no-redef]
        original_init(self, *args, **kwargs)
        try:
            if handler not in self.handlers:
                self.add_handler(handler)
        except Exception:  # noqa: BLE001
            logger.debug("Failed to auto-register LangChain callback handler", exc_info=True)

    CallbackManager.__init__ = patched_init  # type: ignore[assignment]
    _REGISTERED = True
    return True
