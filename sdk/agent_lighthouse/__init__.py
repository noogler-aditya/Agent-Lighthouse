"""
Agent Lighthouse SDK
Multi-Agent Observability for AI Systems

Features:
- Framework-agnostic tracing for any multi-agent system
- Sync + async support
- Thread-safe span tracking
- Fail-silent mode (never crashes host application)
- Automatic output capture
- OpenAI-style token extraction
"""
from .tracer import (
    LighthouseTracer,
    get_tracer,
    reset_global_tracer,
    trace_agent,
    trace_tool,
    trace_llm,
)
from .client import LighthouseClient

__version__ = "0.3.0"
__all__ = [
    "LighthouseTracer",
    "LighthouseClient",
    "get_tracer",
    "reset_global_tracer",
    "trace_agent",
    "trace_tool",
    "trace_llm",
    "instrument",
    "uninstrument",
    "is_instrumented",
]


def instrument() -> bool:
    from .auto import instrument as _instrument
    return _instrument()


def uninstrument() -> None:
    from .auto import uninstrument as _uninstrument
    return _uninstrument()


def is_instrumented() -> bool:
    from .auto import is_instrumented as _is_instrumented
    return _is_instrumented()
