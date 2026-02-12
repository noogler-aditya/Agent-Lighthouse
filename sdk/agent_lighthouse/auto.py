"""
Zero-touch auto-instrumentation for popular LLM clients and frameworks.
Importing this module triggers instrumentation by default.
"""
from __future__ import annotations

import asyncio
import importlib
import logging
import os
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar
from typing import Any, Callable, Optional
from urllib.parse import urlparse

from .pricing import get_cost_usd
from .serialization import _capture_args, _capture_output
from .tracer import get_tracer
from .adapters import (
    register_autogen_logging,
    register_crewai_hooks,
    register_langchain_callbacks,
)

logger = logging.getLogger("agent_lighthouse.auto")

_INSTRUMENTED = False
_ORIGINALS: dict[str, Any] = {}
_REENTRANCY_GUARD: ContextVar[bool] = ContextVar(
    "lighthouse_auto_instrument_guard", default=False
)


def _should_capture_content(tracer) -> bool:
    env = os.getenv("LIGHTHOUSE_CAPTURE_CONTENT", "false").lower()
    if env in ("1", "true", "yes"):
        return True
    return False


@contextmanager
def _span_context(
    name: str,
    kind: str,
    *,
    attributes: Optional[dict] = None,
    input_data: Optional[dict] = None,
):
    tracer = get_tracer()
    if tracer.trace_id:
        with tracer.span(name=name, kind=kind, input_data=input_data, attributes=attributes):
            yield tracer
        return

    # Per-call trace
    with tracer.trace(name=name, metadata=attributes or {}, description=None):
        with tracer.span(name=name, kind=kind, input_data=input_data, attributes=attributes):
            yield tracer


@asynccontextmanager
async def _aspan_context(
    name: str,
    kind: str,
    *,
    attributes: Optional[dict] = None,
    input_data: Optional[dict] = None,
):
    tracer = get_tracer()
    if tracer.trace_id:
        async with tracer.aspan(name=name, kind=kind, input_data=input_data, attributes=attributes):
            yield tracer
        return

    async with tracer.atrace(name=name, metadata=attributes or {}, description=None):
        async with tracer.aspan(
            name=name, kind=kind, input_data=input_data, attributes=attributes
        ):
            yield tracer


def _extract_openai_usage(result: Any) -> tuple[int, int]:
    usage = None
    if hasattr(result, "usage"):
        usage = result.usage
    elif isinstance(result, dict):
        usage = result.get("usage")

    if usage is None:
        return 0, 0

    if isinstance(usage, dict):
        return int(usage.get("prompt_tokens", 0) or 0), int(
            usage.get("completion_tokens", 0) or 0
        )
    return int(getattr(usage, "prompt_tokens", 0) or 0), int(
        getattr(usage, "completion_tokens", 0) or 0
    )


def _extract_anthropic_usage(result: Any) -> tuple[int, int]:
    usage = None
    if hasattr(result, "usage"):
        usage = result.usage
    elif isinstance(result, dict):
        usage = result.get("usage")
    if usage is None:
        return 0, 0

    if isinstance(usage, dict):
        return int(usage.get("input_tokens", 0) or 0), int(
            usage.get("output_tokens", 0) or 0
        )
    return int(getattr(usage, "input_tokens", 0) or 0), int(
        getattr(usage, "output_tokens", 0) or 0
    )


def _compute_and_record(tracer, model: Optional[str], prompt_tokens: int, completion_tokens: int):
    cost = get_cost_usd(model, prompt_tokens, completion_tokens)
    tracer.record_tokens(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=cost,
        model=model,
    )


def _patch_openai() -> bool:
    try:
        openai = importlib.import_module("openai")
    except Exception:  # noqa: BLE001
        return False

    patched = False

    # Legacy: openai.ChatCompletion.create
    legacy = getattr(openai, "ChatCompletion", None)
    if legacy and hasattr(legacy, "create"):
        key = "openai.ChatCompletion.create"
        if key not in _ORIGINALS:
            _ORIGINALS[key] = legacy.create

        original = _ORIGINALS[key]

        if asyncio.iscoroutinefunction(original):
            async def async_wrapper(*args, **kwargs):
                if _REENTRANCY_GUARD.get(False):
                    return await original(*args, **kwargs)
                token = _REENTRANCY_GUARD.set(True)
                try:
                    model = kwargs.get("model")
                    input_data = _capture_args(args, kwargs) if _should_capture_content(get_tracer()) else None
                    async with _aspan_context(
                        name="LLM Call (openai)",
                        kind="llm",
                        attributes={"provider": "openai", "model": model, "endpoint": "ChatCompletion.create"},
                        input_data=input_data,
                    ) as tracer:
                        result = await original(*args, **kwargs)
                        pt, ct = _extract_openai_usage(result)
                        _compute_and_record(tracer, model, pt, ct)
                        if _should_capture_content(tracer):
                            tracer.record_output(_capture_output(result) or {})
                        return result
                finally:
                    _REENTRANCY_GUARD.reset(token)
            legacy.create = async_wrapper  # type: ignore[assignment]
        else:
            def wrapper(*args, **kwargs):
                if _REENTRANCY_GUARD.get(False):
                    return original(*args, **kwargs)
                token = _REENTRANCY_GUARD.set(True)
                try:
                    return _openai_sync_wrapper(
                        original,
                        args,
                        kwargs,
                        "ChatCompletion.create",
                    )
                finally:
                    _REENTRANCY_GUARD.reset(token)
            legacy.create = wrapper  # type: ignore[assignment]
        patched = True

    # Current: openai.chat.completions.create
    chat = getattr(openai, "chat", None)
    completions = getattr(chat, "completions", None) if chat else None
    if completions and hasattr(completions, "create"):
        key = "openai.chat.completions.create"
        if key not in _ORIGINALS:
            _ORIGINALS[key] = completions.create

        original = _ORIGINALS[key]

        if asyncio.iscoroutinefunction(original):
            async def async_wrapper(*args, **kwargs):
                if _REENTRANCY_GUARD.get(False):
                    return await original(*args, **kwargs)
                token = _REENTRANCY_GUARD.set(True)
                try:
                    model = kwargs.get("model")
                    input_data = _capture_args(args, kwargs) if _should_capture_content(get_tracer()) else None
                    async with _aspan_context(
                        name="LLM Call (openai)",
                        kind="llm",
                        attributes={"provider": "openai", "model": model, "endpoint": "chat.completions.create"},
                        input_data=input_data,
                    ) as tracer:
                        result = await original(*args, **kwargs)
                        pt, ct = _extract_openai_usage(result)
                        _compute_and_record(tracer, model, pt, ct)
                        if _should_capture_content(tracer):
                            tracer.record_output(_capture_output(result) or {})
                        return result
                finally:
                    _REENTRANCY_GUARD.reset(token)
            completions.create = async_wrapper  # type: ignore[assignment]
        else:
            def wrapper(*args, **kwargs):
                if _REENTRANCY_GUARD.get(False):
                    return original(*args, **kwargs)
                token = _REENTRANCY_GUARD.set(True)
                try:
                    return _openai_sync_wrapper(
                        original,
                        args,
                        kwargs,
                        "chat.completions.create",
                    )
                finally:
                    _REENTRANCY_GUARD.reset(token)
            completions.create = wrapper  # type: ignore[assignment]
        patched = True

    return patched


def _openai_sync_wrapper(original: Callable, args: tuple, kwargs: dict, endpoint: str):
    tracer = get_tracer()
    model = kwargs.get("model")
    input_data = _capture_args(args, kwargs) if _should_capture_content(tracer) else None
    with _span_context(
        name="LLM Call (openai)",
        kind="llm",
        attributes={"provider": "openai", "model": model, "endpoint": endpoint},
        input_data=input_data,
    ) as tracer_ctx:
        result = original(*args, **kwargs)
        pt, ct = _extract_openai_usage(result)
        _compute_and_record(tracer_ctx, model, pt, ct)
        if _should_capture_content(tracer_ctx):
            tracer_ctx.record_output(_capture_output(result) or {})
        return result


def _patch_anthropic() -> bool:
    try:
        anthropic = importlib.import_module("anthropic")
    except Exception:  # noqa: BLE001
        return False

    patched = False

    messages = getattr(anthropic, "messages", None)
    if messages and hasattr(messages, "create"):
        key = "anthropic.messages.create"
        if key not in _ORIGINALS:
            _ORIGINALS[key] = messages.create
        original = _ORIGINALS[key]

        if asyncio.iscoroutinefunction(original):
            async def async_wrapper(*args, **kwargs):
                if _REENTRANCY_GUARD.get(False):
                    return await original(*args, **kwargs)
                token = _REENTRANCY_GUARD.set(True)
                try:
                    model = kwargs.get("model")
                    input_data = _capture_args(args, kwargs) if _should_capture_content(get_tracer()) else None
                    async with _aspan_context(
                        name="LLM Call (anthropic)",
                        kind="llm",
                        attributes={"provider": "anthropic", "model": model, "endpoint": "messages.create"},
                        input_data=input_data,
                    ) as tracer:
                        result = await original(*args, **kwargs)
                        pt, ct = _extract_anthropic_usage(result)
                        _compute_and_record(tracer, model, pt, ct)
                        if _should_capture_content(tracer):
                            tracer.record_output(_capture_output(result) or {})
                        return result
                finally:
                    _REENTRANCY_GUARD.reset(token)
            messages.create = async_wrapper  # type: ignore[assignment]
        else:
            def wrapper(*args, **kwargs):
                if _REENTRANCY_GUARD.get(False):
                    return original(*args, **kwargs)
                token = _REENTRANCY_GUARD.set(True)
                try:
                    return _anthropic_sync_wrapper(
                        original,
                        args,
                        kwargs,
                    )
                finally:
                    _REENTRANCY_GUARD.reset(token)
            messages.create = wrapper  # type: ignore[assignment]
        patched = True

    client_cls = getattr(anthropic, "Anthropic", None)
    if client_cls and hasattr(client_cls, "__init__"):
        key = "anthropic.Anthropic.__init__"
        if key not in _ORIGINALS:
            _ORIGINALS[key] = client_cls.__init__
        original_init = _ORIGINALS[key]

        def patched_init(self, *args, **kwargs):  # type: ignore[no-redef]
            original_init(self, *args, **kwargs)
            try:
                if hasattr(self, "messages") and hasattr(self.messages, "create"):
                    self.messages.create = _wrap_anthropic_create(self.messages.create)
            except Exception:  # noqa: BLE001
                logger.debug("Failed to patch Anthropic client instance", exc_info=True)

        client_cls.__init__ = patched_init  # type: ignore[assignment]
        patched = True

    return patched


def _wrap_anthropic_create(original: Callable) -> Callable:
    if asyncio.iscoroutinefunction(original):
        async def async_wrapper(*args, **kwargs):
            if _REENTRANCY_GUARD.get(False):
                return await original(*args, **kwargs)
            token = _REENTRANCY_GUARD.set(True)
            try:
                model = kwargs.get("model")
                input_data = _capture_args(args, kwargs) if _should_capture_content(get_tracer()) else None
                async with _aspan_context(
                    name="LLM Call (anthropic)",
                    kind="llm",
                    attributes={"provider": "anthropic", "model": model, "endpoint": "messages.create"},
                    input_data=input_data,
                ) as tracer:
                    result = await original(*args, **kwargs)
                    pt, ct = _extract_anthropic_usage(result)
                    _compute_and_record(tracer, model, pt, ct)
                    if _should_capture_content(tracer):
                        tracer.record_output(_capture_output(result) or {})
                    return result
            finally:
                _REENTRANCY_GUARD.reset(token)
        return async_wrapper

    def wrapper(*args, **kwargs):
        if _REENTRANCY_GUARD.get(False):
            return original(*args, **kwargs)
        token = _REENTRANCY_GUARD.set(True)
        try:
            return _anthropic_sync_wrapper(original, args, kwargs)
        finally:
            _REENTRANCY_GUARD.reset(token)

    return wrapper


def _anthropic_sync_wrapper(original: Callable, args: tuple, kwargs: dict):
    tracer = get_tracer()
    model = kwargs.get("model")
    input_data = _capture_args(args, kwargs) if _should_capture_content(tracer) else None
    with _span_context(
        name="LLM Call (anthropic)",
        kind="llm",
        attributes={"provider": "anthropic", "model": model, "endpoint": "messages.create"},
        input_data=input_data,
    ) as tracer_ctx:
        result = original(*args, **kwargs)
        pt, ct = _extract_anthropic_usage(result)
        _compute_and_record(tracer_ctx, model, pt, ct)
        if _should_capture_content(tracer_ctx):
            tracer_ctx.record_output(_capture_output(result) or {})
        return result


def _default_llm_allowlist() -> list[str]:
    allow = ["api.openai.com", "api.anthropic.com", "*.openai.azure.com"]
    extra = os.getenv("LIGHTHOUSE_LLM_HOSTS", "")
    if extra:
        allow.extend([h.strip() for h in extra.split(",") if h.strip()])
    return allow


def _host_allowed(host: Optional[str], allowlist: list[str]) -> bool:
    if not host:
        return False
    for entry in allowlist:
        if entry.startswith("*.") and host.endswith(entry[1:]):
            return True
        if host == entry:
            return True
    return False


def _patch_requests() -> bool:
    try:
        import requests  # type: ignore
    except Exception:  # noqa: BLE001
        return False

    key = "requests.sessions.Session.request"
    if key not in _ORIGINALS:
        _ORIGINALS[key] = requests.sessions.Session.request
    original = _ORIGINALS[key]

    allowlist = _default_llm_allowlist()

    def wrapper(self, method: str, url: str, *args, **kwargs):  # type: ignore[no-redef]
        if _REENTRANCY_GUARD.get(False):
            return original(self, method, url, *args, **kwargs)

        if (method or "").upper() != "POST":
            return original(self, method, url, *args, **kwargs)

        host = urlparse(url).hostname
        if not _host_allowed(host, allowlist):
            return original(self, method, url, *args, **kwargs)

        token = _REENTRANCY_GUARD.set(True)
        try:
            tracer = get_tracer()
            input_data = _capture_args((method, url), kwargs) if _should_capture_content(tracer) else None
            with _span_context(
                name="LLM HTTP Call",
                kind="llm",
                attributes={
                    "provider": "http",
                    "host": host,
                    "path": urlparse(url).path,
                },
                input_data=input_data,
            ) as tracer_ctx:
                response = original(self, method, url, *args, **kwargs)
                output = {"status_code": getattr(response, "status_code", None)}
                if _should_capture_content(tracer_ctx):
                    try:
                        output["response_json"] = response.json()
                    except Exception:  # noqa: BLE001
                        output["response_text"] = getattr(response, "text", None)
                tracer_ctx.record_output(output)
                return response
        finally:
            _REENTRANCY_GUARD.reset(token)

    requests.sessions.Session.request = wrapper  # type: ignore[assignment]
    return True


def _register_framework_adapters() -> None:
    disabled = os.getenv("LIGHTHOUSE_DISABLE_FRAMEWORKS", "")
    disabled_set = {x.strip().lower() for x in disabled.split(",") if x.strip()}

    if "langchain" not in disabled_set and "langgraph" not in disabled_set:
        try:
            register_langchain_callbacks()
        except Exception:  # noqa: BLE001
            logger.debug("LangChain adapter registration failed", exc_info=True)

    if "crewai" not in disabled_set:
        try:
            register_crewai_hooks()
        except Exception:  # noqa: BLE001
            logger.debug("CrewAI adapter registration failed", exc_info=True)

    if "autogen" not in disabled_set:
        try:
            register_autogen_logging()
        except Exception:  # noqa: BLE001
            logger.debug("AutoGen adapter registration failed", exc_info=True)


def instrument() -> bool:
    """
    Apply auto-instrumentation. Idempotent.
    Returns True if any instrumentation was applied.
    """
    global _INSTRUMENTED
    if _INSTRUMENTED:
        return True

    if os.getenv("LIGHTHOUSE_AUTO_INSTRUMENT", "1").lower() in ("0", "false", "no"):
        return False

    applied = False
    try:
        applied |= _patch_openai()
        applied |= _patch_anthropic()
        applied |= _patch_requests()
        _register_framework_adapters()
    except Exception:  # noqa: BLE001
        logger.debug("Auto-instrumentation failed", exc_info=True)

    _INSTRUMENTED = applied
    return applied


def uninstrument() -> None:
    global _INSTRUMENTED
    if not _INSTRUMENTED:
        return

    for key, original in list(_ORIGINALS.items()):
        try:
            if key == "openai.ChatCompletion.create":
                openai = importlib.import_module("openai")
                openai.ChatCompletion.create = original
            elif key == "openai.chat.completions.create":
                openai = importlib.import_module("openai")
                openai.chat.completions.create = original
            elif key == "anthropic.messages.create":
                anthropic = importlib.import_module("anthropic")
                anthropic.messages.create = original
            elif key == "anthropic.Anthropic.__init__":
                anthropic = importlib.import_module("anthropic")
                anthropic.Anthropic.__init__ = original
            elif key == "requests.sessions.Session.request":
                import requests  # type: ignore
                requests.sessions.Session.request = original
        except Exception:  # noqa: BLE001
            logger.debug("Failed to restore %s", key, exc_info=True)
        finally:
            _ORIGINALS.pop(key, None)

    _INSTRUMENTED = False


def is_instrumented() -> bool:
    return _INSTRUMENTED


# Trigger on import
instrument()
