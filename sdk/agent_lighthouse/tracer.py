"""
Tracer and decorators for instrumenting multi-agent code.

Enterprise-grade with:
- Thread-safe span tracking via ContextVar
- Async + sync decorator support
- Automatic output capture
- Client-side timing (perf_counter)
- Fail-silent wrapping at every boundary
- Safe serialization of arguments/return values
"""
from __future__ import annotations

import asyncio
import functools
import logging
import time
import uuid
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar
from typing import Any, Callable, Optional

from .client import LighthouseClient
from .serialization import _capture_args, _capture_output

logger = logging.getLogger("agent_lighthouse.tracer")

# ---------------------------------------------------------------------------
# Context variables for thread-safe span tracking
# ---------------------------------------------------------------------------
_active_tracer: ContextVar[Optional[LighthouseTracer]] = ContextVar(
    "active_lighthouse_tracer", default=None
)
_active_trace_id: ContextVar[Optional[str]] = ContextVar(
    "active_trace_id", default=None
)
_active_span_stack: ContextVar[list[str]] = ContextVar(
    "active_span_stack",  # each async task / thread gets its own stack
)


class LighthouseTracer:
    """
    Tracer for instrumenting multi-agent systems.

    Thread-safe, async-ready, and fail-silent by default.
    Uses ContextVar for span stack isolation across threads/tasks.

    Usage::

        tracer = LighthouseTracer()

        with tracer.trace("My Agent Workflow"):
            with tracer.span("Agent 1", kind="agent"):
                # Agent logic
                pass

    Async usage::

        async with tracer.atrace("My Async Workflow"):
            async with tracer.aspan("Agent 1", kind="agent"):
                pass
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        framework: Optional[str] = None,
        auto_pause_check: bool = True,
        api_key: Optional[str] = None,
        fail_silent: bool = True,
        max_retries: int = 3,
        capture_output: bool = True,
    ):
        import os
        resolved_url = base_url or os.getenv("LIGHTHOUSE_BASE_URL", "https://agent-lighthouse.onrender.com")
        self.client = LighthouseClient(
            base_url=resolved_url,
            api_key=api_key,
            fail_silent=fail_silent,
            max_retries=max_retries,
        )
        self.framework = framework
        self.auto_pause_check = auto_pause_check
        self.fail_silent = fail_silent
        self.capture_output_enabled = capture_output

    # ------------------------------------------------------------------
    # Properties (thread-safe via ContextVar)
    # ------------------------------------------------------------------

    @property
    def trace_id(self) -> Optional[str]:
        """Get the current trace ID (thread/task-local)."""
        return _active_trace_id.get(None)

    @property
    def span_id(self) -> Optional[str]:
        """Get the current span ID (thread/task-local)."""
        stack = self._get_span_stack()
        return stack[-1] if stack else None

    def _get_span_stack(self) -> list[str]:
        """Get the span stack for the current thread/task."""
        try:
            return _active_span_stack.get()
        except LookupError:
            stack: list[str] = []
            _active_span_stack.set(stack)
            return stack

    # ------------------------------------------------------------------
    # Sync context managers
    # ------------------------------------------------------------------

    @contextmanager
    def trace(
        self,
        name: str,
        description: Optional[str] = None,
        metadata: Optional[dict] = None,
    ):
        """
        Context manager for creating a trace.

        with tracer.trace("My Workflow"):
            # All spans created here belong to this trace
            pass
        """
        trace_data = self.client.create_trace(
            name=name,
            description=description,
            framework=self.framework,
            metadata=metadata or {},
        )

        trace_id = trace_data.get("trace_id")
        if not trace_id:
            # Backend unreachable — yield empty data, don't crash
            logger.warning("Failed to create trace '%s' — backend may be unreachable", name)
            yield {"trace_id": None, "name": name}
            return

        # Set context vars
        tracer_token = _active_tracer.set(self)
        trace_token = _active_trace_id.set(trace_id)
        stack = self._get_span_stack()
        prev_stack = stack.copy()
        stack.clear()

        try:
            yield trace_data
            self.client.complete_trace(trace_id, "success")
        except Exception:
            self.client.complete_trace(trace_id, "error")
            raise
        finally:
            # Restore context
            _active_tracer.reset(tracer_token)
            _active_trace_id.reset(trace_token)
            stack.clear()
            stack.extend(prev_stack)

    @contextmanager
    def span(
        self,
        name: str,
        kind: str = "internal",
        agent_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        input_data: Optional[dict] = None,
        attributes: Optional[dict] = None,
    ):
        """
        Context manager for creating a span within a trace.

        with tracer.span("Process Data", kind="tool"):
            # Tool execution
            pass
        """
        trace_id = self.trace_id
        if not trace_id:
            # No active trace — just run the code without tracing
            yield {}
            return

        # Check for pause if enabled
        if self.auto_pause_check:
            self.client.wait_if_paused(trace_id)

        stack = self._get_span_stack()
        parent_span_id = stack[-1] if stack else None

        # Client-side timing
        start_time = time.perf_counter()

        span_data = self.client.create_span(
            trace_id=trace_id,
            name=name,
            kind=kind,
            parent_span_id=parent_span_id,
            agent_id=agent_id,
            agent_name=agent_name,
            input_data=input_data,
            attributes=attributes or {},
        )

        span_id = span_data.get("span_id")
        if not span_id:
            # Span creation failed — run code without tracking
            yield span_data
            return

        stack.append(span_id)

        try:
            yield span_data

            duration_ms = (time.perf_counter() - start_time) * 1000
            self.client.update_span(
                trace_id=trace_id,
                span_id=span_id,
                status="success",
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self.client.update_span(
                trace_id=trace_id,
                span_id=span_id,
                status="error",
                error_message=str(e)[:500],
                error_type=type(e).__name__,
                duration_ms=duration_ms,
            )
            raise
        finally:
            if stack and stack[-1] == span_id:
                stack.pop()

    # ------------------------------------------------------------------
    # Async context managers
    # ------------------------------------------------------------------

    @asynccontextmanager
    async def atrace(
        self,
        name: str,
        description: Optional[str] = None,
        metadata: Optional[dict] = None,
    ):
        """Async version of trace() context manager."""
        # Run sync client calls in thread pool to avoid blocking event loop
        loop = asyncio.get_running_loop()
        trace_data = await loop.run_in_executor(
            None,
            lambda: self.client.create_trace(
                name=name,
                description=description,
                framework=self.framework,
                metadata=metadata or {},
            ),
        )

        trace_id = trace_data.get("trace_id")
        if not trace_id:
            logger.warning("Failed to create async trace '%s'", name)
            yield {"trace_id": None, "name": name}
            return

        tracer_token = _active_tracer.set(self)
        trace_token = _active_trace_id.set(trace_id)
        stack = self._get_span_stack()
        prev_stack = stack.copy()
        stack.clear()

        try:
            yield trace_data
            await loop.run_in_executor(
                None, lambda: self.client.complete_trace(trace_id, "success")
            )
        except Exception:
            await loop.run_in_executor(
                None, lambda: self.client.complete_trace(trace_id, "error")
            )
            raise
        finally:
            _active_tracer.reset(tracer_token)
            _active_trace_id.reset(trace_token)
            stack.clear()
            stack.extend(prev_stack)

    @asynccontextmanager
    async def aspan(
        self,
        name: str,
        kind: str = "internal",
        agent_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        input_data: Optional[dict] = None,
        attributes: Optional[dict] = None,
    ):
        """Async version of span() context manager."""
        trace_id = self.trace_id
        if not trace_id:
            yield {}
            return

        loop = asyncio.get_running_loop()

        if self.auto_pause_check:
            await loop.run_in_executor(
                None, lambda: self.client.wait_if_paused(trace_id)
            )

        stack = self._get_span_stack()
        parent_span_id = stack[-1] if stack else None

        start_time = time.perf_counter()

        span_data = await loop.run_in_executor(
            None,
            lambda: self.client.create_span(
                trace_id=trace_id,
                name=name,
                kind=kind,
                parent_span_id=parent_span_id,
                agent_id=agent_id,
                agent_name=agent_name,
                input_data=input_data,
                attributes=attributes or {},
            ),
        )

        span_id = span_data.get("span_id")
        if not span_id:
            yield span_data
            return

        stack.append(span_id)

        try:
            yield span_data

            duration_ms = (time.perf_counter() - start_time) * 1000
            await loop.run_in_executor(
                None,
                lambda: self.client.update_span(
                    trace_id=trace_id,
                    span_id=span_id,
                    status="success",
                    duration_ms=duration_ms,
                ),
            )
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            error_message = str(e)[:500]
            error_type = type(e).__name__
            await loop.run_in_executor(
                None,
                lambda: self.client.update_span(
                    trace_id=trace_id,
                    span_id=span_id,
                    status="error",
                    error_message=error_message,
                    error_type=error_type,
                    duration_ms=duration_ms,
                ),
            )
            raise
        finally:
            if stack and stack[-1] == span_id:
                stack.pop()

    # ------------------------------------------------------------------
    # Recording helpers
    # ------------------------------------------------------------------

    def record_tokens(
        self,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        cost_usd: float = 0.0,
        model: Optional[str] = None,
    ) -> None:
        """Record token usage for the current span."""
        trace_id = self.trace_id
        span_id = self.span_id
        if not trace_id or not span_id:
            return

        self.client.update_span(
            trace_id=trace_id,
            span_id=span_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost_usd=cost_usd,
        )

    def record_output(self, output_data: dict) -> None:
        """Explicitly record output data for the current span."""
        trace_id = self.trace_id
        span_id = self.span_id
        if not trace_id or not span_id:
            return

        self.client.update_span(
            trace_id=trace_id,
            span_id=span_id,
            output_data=output_data,
        )

    def update_state(
        self,
        memory: Optional[dict] = None,
        context: Optional[dict] = None,
        variables: Optional[dict] = None,
    ) -> None:
        """Update the trace state for inspection from the dashboard."""
        trace_id = self.trace_id
        if not trace_id:
            return

        self.client.update_state(
            trace_id=trace_id,
            memory=memory,
            context=context,
            variables=variables,
        )

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Release resources held by the tracer."""
        self.client.close()


# ======================================================================
# Global tracer singleton
# ======================================================================

_global_tracer: Optional[LighthouseTracer] = None


def get_tracer(
    base_url: Optional[str] = None,
    framework: Optional[str] = None,
    api_key: Optional[str] = None,
    fail_silent: bool = True,
) -> LighthouseTracer:
    """Get or create the global tracer instance."""
    # Prefer the context-local tracer (set inside a with trace() block)
    active = _active_tracer.get(None)
    if active is not None:
        return active

    global _global_tracer
    if _global_tracer is None:
        import os
        resolved_url = base_url or os.getenv("LIGHTHOUSE_BASE_URL", "https://agent-lighthouse.onrender.com")
        _global_tracer = LighthouseTracer(
            base_url=resolved_url,
            framework=framework,
            api_key=api_key,
            fail_silent=fail_silent,
        )
    return _global_tracer


def reset_global_tracer() -> None:
    """Reset the global tracer (useful in tests)."""
    global _global_tracer
    if _global_tracer is not None:
        _global_tracer.close()
        _global_tracer = None


# ======================================================================
# Decorators — support both sync and async functions
# ======================================================================

def trace_agent(
    name: Optional[str] = None,
    agent_id: Optional[str] = None,
    capture_output: bool = True,
):
    """
    Decorator to trace an agent function. Works with both sync and async.

    @trace_agent("Research Agent")
    def research_agent(query):
        return result

    @trace_agent("Async Agent")
    async def async_agent(query):
        return await result
    """
    def decorator(func: Callable) -> Callable:
        agent_name = name or func.__name__
        _agent_id = agent_id or f"agent-{func.__name__}"

        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                tracer = get_tracer()
                input_data = _capture_args(args, kwargs)

                if not tracer.trace_id:
                    # Auto-create a per-call trace so standalone decorated functions work
                    async with tracer.atrace(name=agent_name, metadata={"auto_trace": True}):
                        async with tracer.aspan(
                            name=agent_name,
                            kind="agent",
                            agent_id=_agent_id,
                            agent_name=agent_name,
                            input_data=input_data,
                        ):
                            result = await func(*args, **kwargs)
                            if capture_output and tracer.capture_output_enabled:
                                tracer.record_output(_capture_output(result) or {})
                            return result
                else:
                    async with tracer.aspan(
                        name=agent_name,
                        kind="agent",
                        agent_id=_agent_id,
                        agent_name=agent_name,
                        input_data=input_data,
                    ):
                        result = await func(*args, **kwargs)
                        if capture_output and tracer.capture_output_enabled:
                            tracer.record_output(_capture_output(result) or {})
                        return result
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                tracer = get_tracer()
                input_data = _capture_args(args, kwargs)

                if not tracer.trace_id:
                    # Auto-create a per-call trace so standalone decorated functions work
                    with tracer.trace(name=agent_name, metadata={"auto_trace": True}):
                        with tracer.span(
                            name=agent_name,
                            kind="agent",
                            agent_id=_agent_id,
                            agent_name=agent_name,
                            input_data=input_data,
                        ):
                            result = func(*args, **kwargs)
                            if capture_output and tracer.capture_output_enabled:
                                tracer.record_output(_capture_output(result) or {})
                            return result
                else:
                    with tracer.span(
                        name=agent_name,
                        kind="agent",
                        agent_id=_agent_id,
                        agent_name=agent_name,
                        input_data=input_data,
                    ):
                        result = func(*args, **kwargs)
                        if capture_output and tracer.capture_output_enabled:
                            tracer.record_output(_capture_output(result) or {})
                        return result
            return sync_wrapper
    return decorator


def trace_tool(name: Optional[str] = None, capture_output: bool = True):
    """
    Decorator to trace a tool function. Works with both sync and async.

    @trace_tool("Web Search")
    def search_web(query):
        return results
    """
    def decorator(func: Callable) -> Callable:
        tool_name = name or func.__name__

        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                tracer = get_tracer()
                input_data = _capture_args(args, kwargs)

                if not tracer.trace_id:
                    async with tracer.atrace(name=tool_name, metadata={"auto_trace": True}):
                        async with tracer.aspan(
                            name=tool_name,
                            kind="tool",
                            input_data=input_data,
                        ):
                            result = await func(*args, **kwargs)
                            if capture_output and tracer.capture_output_enabled:
                                tracer.record_output(_capture_output(result) or {})
                            return result
                else:
                    async with tracer.aspan(
                        name=tool_name,
                        kind="tool",
                        input_data=input_data,
                    ):
                        result = await func(*args, **kwargs)
                        if capture_output and tracer.capture_output_enabled:
                            tracer.record_output(_capture_output(result) or {})
                        return result
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                tracer = get_tracer()
                input_data = _capture_args(args, kwargs)

                if not tracer.trace_id:
                    with tracer.trace(name=tool_name, metadata={"auto_trace": True}):
                        with tracer.span(
                            name=tool_name,
                            kind="tool",
                            input_data=input_data,
                        ):
                            result = func(*args, **kwargs)
                            if capture_output and tracer.capture_output_enabled:
                                tracer.record_output(_capture_output(result) or {})
                            return result
                else:
                    with tracer.span(
                        name=tool_name,
                        kind="tool",
                        input_data=input_data,
                    ):
                        result = func(*args, **kwargs)
                        if capture_output and tracer.capture_output_enabled:
                            tracer.record_output(_capture_output(result) or {})
                        return result
            return sync_wrapper
    return decorator


def trace_llm(
    name: str = "LLM Call",
    model: Optional[str] = None,
    cost_per_1k_prompt: float = 0.0,
    cost_per_1k_completion: float = 0.0,
    capture_output: bool = True,
):
    """
    Decorator to trace an LLM call. Works with both sync and async.
    Automatically extracts token usage from OpenAI-style responses.

    @trace_llm("GPT-4 Call", model="gpt-4", cost_per_1k_prompt=0.03)
    def call_gpt4(prompt):
        response = openai.chat(...)
        return response
    """
    def decorator(func: Callable) -> Callable:

        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                tracer = get_tracer()
                input_data = _capture_args(args, kwargs)

                if not tracer.trace_id:
                    async with tracer.atrace(name=name, metadata={"auto_trace": True, "model": model}):
                        async with tracer.aspan(
                            name=name,
                            kind="llm",
                            input_data=input_data,
                            attributes={"model": model} if model else {},
                        ):
                            result = await func(*args, **kwargs)
                            _extract_and_record_tokens(
                                tracer, result, model, cost_per_1k_prompt, cost_per_1k_completion
                            )
                            if capture_output and tracer.capture_output_enabled:
                                tracer.record_output(_capture_output(result) or {})
                            return result
                else:
                    async with tracer.aspan(
                        name=name,
                        kind="llm",
                        input_data=input_data,
                        attributes={"model": model} if model else {},
                    ):
                        result = await func(*args, **kwargs)
                        _extract_and_record_tokens(
                            tracer, result, model, cost_per_1k_prompt, cost_per_1k_completion
                        )
                        if capture_output and tracer.capture_output_enabled:
                            tracer.record_output(_capture_output(result) or {})
                        return result
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                tracer = get_tracer()
                input_data = _capture_args(args, kwargs)

                if not tracer.trace_id:
                    with tracer.trace(name=name, metadata={"auto_trace": True, "model": model}):
                        with tracer.span(
                            name=name,
                            kind="llm",
                            input_data=input_data,
                            attributes={"model": model} if model else {},
                        ):
                            result = func(*args, **kwargs)
                            _extract_and_record_tokens(
                                tracer, result, model, cost_per_1k_prompt, cost_per_1k_completion
                            )
                            if capture_output and tracer.capture_output_enabled:
                                tracer.record_output(_capture_output(result) or {})
                            return result
                else:
                    with tracer.span(
                        name=name,
                        kind="llm",
                        input_data=input_data,
                        attributes={"model": model} if model else {},
                    ):
                        result = func(*args, **kwargs)
                        _extract_and_record_tokens(
                            tracer, result, model, cost_per_1k_prompt, cost_per_1k_completion
                        )
                        if capture_output and tracer.capture_output_enabled:
                            tracer.record_output(_capture_output(result) or {})
                        return result
            return sync_wrapper
    return decorator


def _extract_and_record_tokens(
    tracer: LighthouseTracer,
    result: Any,
    model: Optional[str],
    cost_per_1k_prompt: float,
    cost_per_1k_completion: float,
) -> None:
    """Safely extract token usage from an OpenAI-style response."""
    try:
        if not hasattr(result, "usage"):
            return
        usage = result.usage
        prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
        completion_tokens = getattr(usage, "completion_tokens", 0) or 0

        cost = (
            (prompt_tokens / 1000) * cost_per_1k_prompt
            + (completion_tokens / 1000) * cost_per_1k_completion
        )

        tracer.record_tokens(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost,
            model=model,
        )
    except Exception:  # noqa: BLE001
        logger.debug("Could not extract token usage from LLM result", exc_info=True)
