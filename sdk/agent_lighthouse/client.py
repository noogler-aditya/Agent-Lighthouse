"""
HTTP Client for Agent Lighthouse API.

Enterprise-grade with:
- Fail-silent mode (never crash the instrumented application)
- Retry with exponential backoff
- Circuit breaker pattern for backend failures
- Request timeout management
- Batch span ingestion
- Comprehensive structured logging
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any, Optional

import httpx

logger = logging.getLogger("agent_lighthouse.client")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
_DEFAULT_MAX_RETRIES = 3
_DEFAULT_BACKOFF_BASE = 0.3          # seconds
_DEFAULT_BACKOFF_MAX = 10.0          # seconds
_CIRCUIT_OPEN_THRESHOLD = 5          # consecutive failures before opening
_CIRCUIT_HALF_OPEN_AFTER = 30.0      # seconds before trying again

# Sentinel returned when fail_silent swallows an error
_EMPTY: dict = {}


class LighthouseClient:
    """
    Sync/Async HTTP client for Agent Lighthouse backend.

    Key design principle: **never crash the host application**.
    When ``fail_silent=True`` (default), all network/server errors are
    logged and swallowed, returning safe fallback values so the
    instrumented agent code continues running without interruption.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: float = 10.0,
        api_key: Optional[str] = None,
        fail_silent: bool = True,
        max_retries: int = _DEFAULT_MAX_RETRIES,
        backoff_base: float = _DEFAULT_BACKOFF_BASE,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.api_key = api_key or os.getenv("LIGHTHOUSE_API_KEY")
        self.fail_silent = fail_silent
        self.max_retries = max_retries
        self.backoff_base = backoff_base

        self._client: Optional[httpx.Client] = None

        # Circuit breaker state
        self._consecutive_failures = 0
        self._circuit_open_until = 0.0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @property
    def _default_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"User-Agent": "agent-lighthouse-sdk/0.2.0"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    @property
    def client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout,
                headers=self._default_headers,
            )
        return self._client

    def _is_circuit_open(self) -> bool:
        """Check if the circuit breaker is open (backend assumed down)."""
        if self._consecutive_failures < _CIRCUIT_OPEN_THRESHOLD:
            return False
        if time.monotonic() >= self._circuit_open_until:
            # Half-open: allow one request through
            return False
        return True

    def _record_success(self) -> None:
        self._consecutive_failures = 0

    def _record_failure(self) -> None:
        self._consecutive_failures += 1
        if self._consecutive_failures >= _CIRCUIT_OPEN_THRESHOLD:
            self._circuit_open_until = time.monotonic() + _CIRCUIT_HALF_OPEN_AFTER
            logger.warning(
                "Circuit breaker OPEN — backend unreachable after %d consecutive failures. "
                "Will retry in %.0fs.",
                self._consecutive_failures,
                _CIRCUIT_HALF_OPEN_AFTER,
            )

    def _safe_request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[dict | list] = None,
        params: Optional[dict] = None,
        fallback: Any = None,
    ) -> Any:
        """
        Central request method with retry, circuit breaker, and fail-silent.

        Returns the parsed JSON response on success, or *fallback* on failure
        (when ``fail_silent`` is ``True``).
        """
        if self._is_circuit_open():
            logger.debug("Circuit breaker open — skipping %s %s", method, path)
            if self.fail_silent:
                return fallback if fallback is not None else _EMPTY
            raise ConnectionError("Agent Lighthouse backend unreachable (circuit open)")

        last_exc: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.client.request(
                    method, path, json=json, params=params,
                )

                if response.status_code < 400:
                    self._record_success()
                    return response.json()

                # Retryable server errors
                if response.status_code in _RETRYABLE_STATUS_CODES and attempt < self.max_retries:
                    wait = min(self.backoff_base * (2 ** (attempt - 1)), _DEFAULT_BACKOFF_MAX)
                    logger.warning(
                        "Retryable %d from %s %s (attempt %d/%d), backoff %.2fs",
                        response.status_code, method, path, attempt, self.max_retries, wait,
                    )
                    time.sleep(wait)
                    continue

                # Non-retryable client/server error
                self._record_success()  # server is reachable, just returned an error
                if self.fail_silent:
                    logger.warning(
                        "HTTP %d from %s %s — %s",
                        response.status_code, method, path,
                        response.text[:200],
                    )
                    return fallback if fallback is not None else _EMPTY
                response.raise_for_status()

            except httpx.TimeoutException as exc:
                last_exc = exc
                self._record_failure()
                if attempt < self.max_retries:
                    wait = min(self.backoff_base * (2 ** (attempt - 1)), _DEFAULT_BACKOFF_MAX)
                    logger.warning(
                        "Timeout on %s %s (attempt %d/%d), backoff %.2fs",
                        method, path, attempt, self.max_retries, wait,
                    )
                    time.sleep(wait)
                    continue

            except (httpx.ConnectError, httpx.NetworkError, OSError) as exc:
                last_exc = exc
                self._record_failure()
                if attempt < self.max_retries:
                    wait = min(self.backoff_base * (2 ** (attempt - 1)), _DEFAULT_BACKOFF_MAX)
                    logger.warning(
                        "Connection error on %s %s (attempt %d/%d): %s, backoff %.2fs",
                        method, path, attempt, self.max_retries, exc, wait,
                    )
                    time.sleep(wait)
                    continue

            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                self._record_failure()
                break

        # All retries exhausted
        if self.fail_silent:
            logger.error(
                "All %d retries exhausted for %s %s: %s",
                self.max_retries, method, path, last_exc,
            )
            return fallback if fallback is not None else _EMPTY
        raise last_exc  # type: ignore[misc]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the HTTP client and release resources."""
        if self._client and not self._client.is_closed:
            try:
                self._client.close()
            except Exception as exc:  # noqa: BLE001
                logger.debug("Error closing HTTP client: %s", exc)
            self._client = None

    def __del__(self) -> None:
        self.close()

    # ==================================================================
    # TRACES
    # ==================================================================

    def create_trace(
        self,
        name: str,
        description: Optional[str] = None,
        framework: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Create a new trace. Returns ``{"trace_id": ...}`` on success."""
        result = self._safe_request(
            "POST", "/api/traces",
            json={
                "name": name,
                "description": description,
                "framework": framework,
                "metadata": metadata or {},
            },
            fallback={"trace_id": None},
        )
        return result

    def get_trace(self, trace_id: str) -> Optional[dict]:
        """Get a trace by ID."""
        result = self._safe_request("GET", f"/api/traces/{trace_id}", fallback=None)
        return result

    def list_traces(self, offset: int = 0, limit: int = 50) -> dict:
        """List all traces with pagination."""
        return self._safe_request(
            "GET", "/api/traces",
            params={"offset": offset, "limit": limit},
            fallback={"traces": [], "total": 0, "offset": offset, "limit": limit},
        )

    def complete_trace(self, trace_id: str, status: str = "success") -> dict:
        """Mark a trace as complete."""
        return self._safe_request(
            "POST", f"/api/traces/{trace_id}/complete",
            params={"status": status},
        )

    # ==================================================================
    # SPANS
    # ==================================================================

    def create_span(
        self,
        trace_id: str,
        name: str,
        kind: str,
        parent_span_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        input_data: Optional[dict] = None,
        attributes: Optional[dict] = None,
    ) -> dict:
        """Create a new span within a trace."""
        return self._safe_request(
            "POST", f"/api/traces/{trace_id}/spans",
            json={
                "name": name,
                "kind": kind,
                "parent_span_id": parent_span_id,
                "agent_id": agent_id,
                "agent_name": agent_name,
                "input_data": input_data,
                "attributes": attributes or {},
            },
            fallback={"span_id": None},
        )

    def update_span(
        self,
        trace_id: str,
        span_id: str,
        status: Optional[str] = None,
        output_data: Optional[dict] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        cost_usd: Optional[float] = None,
        error_message: Optional[str] = None,
        error_type: Optional[str] = None,
        duration_ms: Optional[float] = None,
    ) -> dict:
        """Update a span with results, tokens, errors, or timing."""
        data: dict[str, Any] = {}
        if status:
            data["status"] = status
        if output_data:
            data["output_data"] = output_data
        if prompt_tokens is not None:
            data["prompt_tokens"] = prompt_tokens
        if completion_tokens is not None:
            data["completion_tokens"] = completion_tokens
        if total_tokens is not None:
            data["total_tokens"] = total_tokens
        if cost_usd is not None:
            data["cost_usd"] = cost_usd
        if error_message:
            data["error_message"] = error_message
            data["error_type"] = error_type
        if duration_ms is not None:
            data["duration_ms"] = duration_ms

        return self._safe_request(
            "PATCH", f"/api/traces/{trace_id}/spans/{span_id}",
            json=data,
        )

    def batch_create_spans(
        self,
        trace_id: str,
        spans: list[dict],
    ) -> dict:
        """
        Create multiple spans in a single request (batch ingestion).
        Falls back to sequential creation if the backend doesn't support it.
        """
        result = self._safe_request(
            "POST", f"/api/traces/{trace_id}/spans/batch",
            json={"spans": spans},
            fallback=None,
        )
        if result is None:
            # Fallback: send individually
            results = []
            for span_data in spans:
                r = self.create_span(trace_id=trace_id, **span_data)
                results.append(r)
            return {"spans": results, "fallback": True}
        return result

    # ==================================================================
    # STATE
    # ==================================================================

    def get_state(self, trace_id: str) -> Optional[dict]:
        """Get state for a trace."""
        result = self._safe_request("GET", f"/api/state/{trace_id}", fallback=None)
        return result

    def initialize_state(
        self,
        trace_id: str,
        memory: Optional[dict] = None,
        context: Optional[dict] = None,
        variables: Optional[dict] = None,
    ) -> dict:
        """Initialize state for a trace."""
        return self._safe_request(
            "POST", f"/api/state/{trace_id}",
            json={
                "memory": memory or {},
                "context": context or {},
                "variables": variables or {},
            },
        )

    def update_state(
        self,
        trace_id: str,
        memory: Optional[dict] = None,
        context: Optional[dict] = None,
        variables: Optional[dict] = None,
    ) -> dict:
        """Update state. Auto-initializes if state doesn't exist."""
        data: dict[str, Any] = {}
        if memory is not None:
            data["memory"] = memory
        if context is not None:
            data["context"] = context
        if variables is not None:
            data["variables"] = variables

        result = self._safe_request("PUT", f"/api/state/{trace_id}", json=data)

        # If state doesn't exist yet, initialize and retry
        if isinstance(result, dict) and not result:
            self.initialize_state(
                trace_id=trace_id,
                memory=memory,
                context=context,
                variables=variables,
            )
            result = self._safe_request("PUT", f"/api/state/{trace_id}", json=data)

        return result

    # ==================================================================
    # EXECUTION CONTROL
    # ==================================================================

    def get_control_status(self, trace_id: str) -> dict:
        """Check if execution is paused."""
        return self._safe_request(
            "GET", f"/api/state/{trace_id}/control",
            fallback={"status": "running", "resume_requested": False},
        )

    def wait_if_paused(
        self,
        trace_id: str,
        poll_interval: float = 0.5,
        max_wait: float = 300.0,
    ) -> bool:
        """
        Block until execution is resumed or max_wait is exceeded.

        Returns True if was paused and now resumed.
        Returns False if was never paused or max_wait was exceeded.
        """
        deadline = time.monotonic() + max_wait

        while time.monotonic() < deadline:
            status = self.get_control_status(trace_id)

            if status.get("status") == "paused":
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    logger.warning(
                        "max_wait (%.0fs) exceeded while paused for trace %s — resuming",
                        max_wait, trace_id,
                    )
                    return False
                time.sleep(min(poll_interval, remaining))
                continue

            if status.get("resume_requested"):
                return True

            # Not paused
            return False

        logger.warning("max_wait exceeded for trace %s", trace_id)
        return False
