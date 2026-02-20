"""
Authentication and authorization helpers for HTTP and WebSocket access.

Simplified: no role hierarchy. All authenticated users have equal access.
Machine API keys (X-API-Key) and user-generated API keys are both supported.
"""
from __future__ import annotations

from dataclasses import dataclass
import hmac
import logging
from typing import Callable, Optional

import httpx
from fastapi import Depends, Header, HTTPException, Request, WebSocket, status

from config import Settings, get_settings

logger = logging.getLogger(__name__)


@dataclass
class Principal:
    subject: str
    auth_type: str  # "user", "machine", or "api_key"
    scopes: set[str]
    user_id: Optional[str] = None


class AuthError(HTTPException):
    def __init__(self, detail: str, status_code: int = status.HTTP_401_UNAUTHORIZED):
        super().__init__(status_code=status_code, detail=detail)


def _normalize(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip()
    if len(normalized) >= 2 and normalized[0] == normalized[-1] and normalized[0] in {'"', "'"}:
        normalized = normalized[1:-1].strip()
    return normalized or None


def _parse_bearer(authorization: Optional[str]) -> str:
    value = _normalize(authorization)
    if not value:
        raise AuthError("Missing Authorization header")
    scheme, _, token = value.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise AuthError("Invalid Authorization header")
    return token.strip()


async def _supabase_get_user(token: str, settings: Settings) -> dict:
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise AuthError("Supabase auth not configured")

    if settings.supabase_url == "test" and settings.supabase_anon_key == "test":
        return {"id": "test-user", "email": "test-user@example.com"}

    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/user"
    headers = {
        "Authorization": f"Bearer {token}",
        "apikey": settings.supabase_anon_key,
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, headers=headers)
    if resp.status_code != 200:
        raise AuthError("Invalid or expired token")
    return resp.json()


async def _resolve_api_key(api_key: str, settings: Settings) -> Principal:
    """
    Resolve an API key to a Principal.
    Checks user-generated keys (PostgreSQL) first, then machine keys (env var).
    """
    key = _normalize(api_key)
    if not key:
        raise AuthError("Missing API key")

    # 1. Check user-generated API keys (from PostgreSQL)
    if key.startswith("lh_"):
        # 1a. Check the "users" table (username/password registration flow)
        try:
            from services.user_service import get_user_by_api_key
            user = await get_user_by_api_key(key)
            if user:
                return Principal(
                    subject=user["username"],
                    auth_type="api_key",
                    scopes={"trace:write", "trace:read"},
                    user_id=user["id"],
                )
        except Exception as db_exc:
            logger.debug("User API key lookup failed, falling through: %s", db_exc)

        # 1b. Check the "api_keys" table (Supabase authentication flow)
        try:
            from services.api_key_service import get_user_id_by_api_key
            supabase_user_id = await get_user_id_by_api_key(key)
            if supabase_user_id:
                return Principal(
                    subject=supabase_user_id,
                    auth_type="api_key",
                    scopes={"trace:write", "trace:read"},
                    user_id=supabase_user_id,
                )
        except Exception as db_exc:
            logger.debug("Supabase API key lookup failed, falling through to machine keys: %s", db_exc)

    # 2. Check machine API keys (env var — backward compatible)
    for known_key, scopes in settings.machine_api_keys_map.items():
        if hmac.compare_digest(key, known_key):
            return Principal(subject="machine", auth_type="machine", scopes=scopes)

    raise AuthError("Invalid API key")


async def _user_principal(authorization: Optional[str], settings: Settings) -> Principal:
    token = _parse_bearer(authorization)
    payload = await _supabase_get_user(token, settings)
    subject = payload.get("email") or payload.get("id") or "user"
    return Principal(
        subject=subject,
        auth_type="user",
        scopes={"ui"},
        user_id=payload.get("id"),
    )


async def require_user_auth(
    request: Request,
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
) -> Principal:
    settings = get_settings()
    if not settings.require_auth:
        principal = Principal(subject="dev-user", auth_type="user", scopes={"*"})
    else:
        principal = await _user_principal(authorization, settings)

    request.state.principal = principal
    return principal


def require_auth() -> Callable:
    """Require any authenticated user (no role check)."""
    async def _dependency(principal: Principal = Depends(require_user_auth)) -> Principal:
        return principal
    return _dependency


def require_user_or_machine(scope: str) -> Callable:
    """Allow either a user (Bearer token) or machine (X-API-Key) with the given scope."""
    async def _dependency(
        request: Request,
        authorization: Optional[str] = Header(default=None, alias="Authorization"),
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    ) -> Principal:
        settings = get_settings()
        if not settings.require_auth:
            principal = Principal(subject="dev-user", auth_type="user", scopes={"*"})
            request.state.principal = principal
            return principal

        user_auth_error: Optional[Exception] = None
        principal: Optional[Principal] = None

        if authorization:
            try:
                principal = await _user_principal(authorization, settings)
            except Exception as exc:
                user_auth_error = exc

        if principal is None and x_api_key:
            principal = await _resolve_api_key(x_api_key, settings)

        if principal is None:
            raise user_auth_error if isinstance(user_auth_error, HTTPException) else AuthError("Unauthorized")

        if principal.auth_type in {"machine", "api_key"}:
            if "*" not in principal.scopes and scope not in principal.scopes:
                raise AuthError("Forbidden", status_code=status.HTTP_403_FORBIDDEN)

        request.state.principal = principal
        return principal

    return _dependency


def _parse_ws_bearer(websocket: WebSocket) -> str:
    raw = websocket.headers.get("sec-websocket-protocol", "")
    protocols = [part.strip() for part in raw.split(",") if part.strip()]
    if len(protocols) < 2:
        raise AuthError("Missing websocket bearer token")
    if protocols[0].lower() != "bearer":
        raise AuthError("Invalid websocket auth protocol")
    return protocols[1]


async def authenticate_websocket(
    websocket: WebSocket,
    enforce_rate_limit: Optional[Callable[[str], None]] = None,
) -> Principal:
    settings = get_settings()
    if not settings.require_auth:
        principal = Principal(subject="dev-user", auth_type="user", scopes={"*"})
    else:
        token = _parse_ws_bearer(websocket)
        payload = await _supabase_get_user(token, settings)
        principal = Principal(
            subject=payload.get("email") or payload.get("id") or "user",
            auth_type="user",
            scopes={"ui"},
            user_id=payload.get("id"),
        )

    if enforce_rate_limit is not None:
        enforce_rate_limit(principal.subject)

    websocket.state.principal = principal
    return principal


def auth_health(settings: Settings) -> dict:
    unsafe_defaults = settings.jwt_secret_uses_default
    weak_machine = any(key.startswith("dev-") for key in settings.machine_api_keys_map)
    supabase_ready = bool(settings.supabase_url and settings.supabase_anon_key)
    return {
        "require_auth": settings.require_auth,
        "jwt_algorithm": settings.jwt_algorithm,
        "issuer": settings.jwt_issuer,
        "audience": settings.jwt_audience,
        "unsafe_defaults": unsafe_defaults or weak_machine or (settings.is_production and not supabase_ready),
        "supabase_configured": supabase_ready,
    }
