"""Redis-backed request rate limiting utilities."""
from __future__ import annotations

from dataclasses import dataclass
from fastapi import Depends, HTTPException, Request, WebSocket, status

from config import get_settings


@dataclass
class RateLimitResult:
    key: str
    count: int
    limit: int


async def _enforce_limit(request: Request, bucket: str, limit: int) -> RateLimitResult | None:
    settings = get_settings()
    if not settings.rate_limit_enabled:
        return None

    redis_service = request.app.state.redis_service
    redis_client = getattr(redis_service, "redis", None)
    if redis_client is None:
        return None

    principal = getattr(request.state, "principal", None)
    subject = getattr(principal, "subject", None) or "anonymous"
    ip = request.client.host if request.client else "unknown"
    key = f"lighthouse:rl:{bucket}:{subject}:{ip}"

    count = await redis_client.incr(key)
    if count == 1:
        await redis_client.expire(key, settings.rate_limit_window_seconds)

    if count > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded for {bucket}",
        )

    return RateLimitResult(key=key, count=count, limit=limit)


async def _enforce_ws_limit(websocket: WebSocket, bucket: str, subject: str, limit: int) -> RateLimitResult | None:
    settings = get_settings()
    if not settings.rate_limit_enabled:
        return None

    redis_service = websocket.app.state.redis_service
    redis_client = getattr(redis_service, "redis", None)
    if redis_client is None:
        return None

    ip = websocket.client.host if websocket.client else "unknown"
    key = f"lighthouse:rl:{bucket}:{subject}:{ip}"
    count = await redis_client.incr(key)
    if count == 1:
        await redis_client.expire(key, settings.rate_limit_window_seconds)

    if count > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded for {bucket}",
        )
    return RateLimitResult(key=key, count=count, limit=limit)


async def enforce_read_rate_limit(request: Request):
    settings = get_settings()
    await _enforce_limit(request, "read", settings.rate_limit_read_per_window)


async def enforce_write_rate_limit(request: Request):
    settings = get_settings()
    await _enforce_limit(request, "write", settings.rate_limit_write_per_window)


def read_rate_limit_dependency():
    return Depends(enforce_read_rate_limit)


def write_rate_limit_dependency():
    return Depends(enforce_write_rate_limit)


async def enforce_ws_connect_limit(request: Request):
    settings = get_settings()
    await _enforce_limit(request, "ws-connect", settings.rate_limit_ws_connect_per_window)


async def enforce_ws_subscribe_limit(request: Request):
    settings = get_settings()
    await _enforce_limit(request, "ws-subscribe", settings.rate_limit_ws_subscribe_per_window)


async def enforce_ws_connect_limit_for_subject(websocket: WebSocket, subject: str):
    settings = get_settings()
    await _enforce_ws_limit(websocket, "ws-connect", subject, settings.rate_limit_ws_connect_per_window)


async def enforce_ws_subscribe_limit_for_subject(websocket: WebSocket, subject: str):
    settings = get_settings()
    await _enforce_ws_limit(websocket, "ws-subscribe", subject, settings.rate_limit_ws_subscribe_per_window)
