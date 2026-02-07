"""
Authentication helpers for HTTP and WebSocket access.
"""
import hmac
from typing import Optional
from fastapi import Header, HTTPException, WebSocket, status

from config import get_settings


def _check_api_key(value: Optional[str]) -> bool:
    settings = get_settings()
    if not settings.require_auth:
        return True
    return bool(value) and hmac.compare_digest(value, settings.api_key)


async def require_api_key(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")) -> None:
    if _check_api_key(x_api_key):
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API key",
    )


async def authenticate_websocket(websocket: WebSocket) -> bool:
    settings = get_settings()
    if not settings.require_auth:
        return True

    provided = websocket.headers.get("x-api-key") or websocket.query_params.get("api_key")
    if _check_api_key(provided):
        return True

    await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid or missing API key")
    return False
