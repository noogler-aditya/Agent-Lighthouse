"""
Safe serialization helpers shared across tracer and auto-instrumentation.
"""
from __future__ import annotations

from typing import Any, Optional

_MAX_CAPTURE_LEN = 2000  # max chars for captured input/output


def _safe_serialize(value: Any, max_len: int = _MAX_CAPTURE_LEN) -> Any:
    """
    Safely convert a value to a JSON-serializable dict/string.
    Never raises — returns a truncated string representation on failure.
    """
    if value is None:
        return None

    try:
        if isinstance(value, dict):
            serialized = str(value)
        elif isinstance(value, (list, tuple)):
            serialized = str(value)
        elif isinstance(value, (str, int, float, bool)):
            serialized = str(value)
        elif hasattr(value, "model_dump"):
            # Pydantic model support
            serialized = str(value.model_dump())
        elif hasattr(value, "__dict__"):
            serialized = str(value.__dict__)
        else:
            serialized = repr(value)
    except Exception:  # noqa: BLE001
        serialized = f"<unserializable: {type(value).__name__}>"

    if len(serialized) > max_len:
        return {"_truncated": True, "value": serialized[:max_len] + "..."}
    return {"value": serialized}


def _capture_args(args: tuple, kwargs: dict) -> dict:
    """Capture function arguments safely."""
    try:
        result = {}
        if args:
            result["args"] = _safe_serialize(args)
        if kwargs:
            result["kwargs"] = _safe_serialize(kwargs)
        return result
    except Exception:  # noqa: BLE001
        return {"_capture_error": "Failed to capture arguments"}


def _capture_output(value: Any) -> Optional[dict]:
    """Capture function return value safely."""
    try:
        if value is None:
            return None
        return {"result": _safe_serialize(value)}
    except Exception:  # noqa: BLE001
        return {"_capture_error": "Failed to capture output"}
