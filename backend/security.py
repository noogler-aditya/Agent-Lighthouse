"""
Authentication and authorization helpers for HTTP and WebSocket access.

Simplified: no role hierarchy. All authenticated users have equal access.
Machine API keys (X-API-Key) and user-generated API keys are both supported.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hmac
import logging
import secrets
from typing import Callable, Optional

import jwt
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


def _decode_token(token: str, settings: Settings, expected_type: str = "access") -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
        )
    except jwt.PyJWTError as exc:
        raise AuthError("Invalid or expired token") from exc

    if payload.get("typ") != expected_type:
        raise AuthError("Invalid token type")

    sub = payload.get("sub")
    if not sub:
        raise AuthError("Token missing required claims")

    return payload


def create_access_token(settings: Settings, subject: str, user_id: Optional[str] = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "typ": "access",
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.access_token_ttl_minutes)).timestamp()),
        "jti": secrets.token_urlsafe(12),
    }
    if user_id:
        payload["uid"] = user_id
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(settings: Settings, subject: str, user_id: Optional[str] = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "typ": "refresh",
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.refresh_token_ttl_minutes)).timestamp()),
        "jti": secrets.token_urlsafe(16),
    }
    if user_id:
        payload["uid"] = user_id
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_refresh_token(token: str, settings: Settings) -> dict:
    return _decode_token(token, settings, expected_type="refresh")


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
            logger.debug("User API key lookup failed, falling through to machine keys: %s", db_exc)

    # 2. Check machine API keys (env var — backward compatible)
    for known_key, scopes in settings.machine_api_keys_map.items():
        if hmac.compare_digest(key, known_key):
            return Principal(subject="machine", auth_type="machine", scopes=scopes)

    raise AuthError("Invalid API key")


def _user_principal(authorization: Optional[str], settings: Settings) -> Principal:
    token = _parse_bearer(authorization)
    payload = _decode_token(token, settings, expected_type="access")
    return Principal(
        subject=payload["sub"],
        auth_type="user",
        scopes={"ui"},
        user_id=payload.get("uid"),
    )


async def require_user_auth(
    request: Request,
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
) -> Principal:
    settings = get_settings()
    if not settings.require_auth:
        principal = Principal(subject="dev-user", auth_type="user", scopes={"*"})
    else:
        principal = _user_principal(authorization, settings)

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
                principal = _user_principal(authorization, settings)
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
        payload = _decode_token(token, settings, expected_type="access")
        principal = Principal(
            subject=payload["sub"],
            auth_type="user",
            scopes={"ui"},
            user_id=payload.get("uid"),
        )

    if enforce_rate_limit is not None:
        enforce_rate_limit(principal.subject)

    websocket.state.principal = principal
    return principal


def auth_health(settings: Settings) -> dict:
    unsafe_defaults = settings.jwt_secret_uses_default
    weak_machine = any(key.startswith("dev-") for key in settings.machine_api_keys_map)
    return {
        "require_auth": settings.require_auth,
        "jwt_algorithm": settings.jwt_algorithm,
        "issuer": settings.jwt_issuer,
        "audience": settings.jwt_audience,
        "unsafe_defaults": unsafe_defaults or weak_machine,
    }
