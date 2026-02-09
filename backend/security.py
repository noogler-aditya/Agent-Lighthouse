"""
Authentication and authorization helpers for HTTP and WebSocket access.
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

ROLE_ORDER = {
    "viewer": 10,
    "operator": 20,
    "admin": 30,
}


@dataclass
class Principal:
    subject: str
    role: str
    auth_type: str
    scopes: set[str]


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


def _assert_role(value: str) -> str:
    role = value.strip().lower()
    if role not in ROLE_ORDER:
        raise AuthError(f"Unsupported role: {value}", status.HTTP_403_FORBIDDEN)
    return role


def _ensure_role(principal: Principal, minimum_role: str):
    required = _assert_role(minimum_role)
    principal_role = _assert_role(principal.role)
    if ROLE_ORDER[principal_role] < ROLE_ORDER[required]:
        raise AuthError("Insufficient role", status.HTTP_403_FORBIDDEN)


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

    role = payload.get("role")
    sub = payload.get("sub")
    if not role or not sub:
        raise AuthError("Token missing required claims")

    payload["role"] = _assert_role(role)
    return payload


def create_access_token(settings: Settings, subject: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "role": _assert_role(role),
        "typ": "access",
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.access_token_ttl_minutes)).timestamp()),
        "jti": secrets.token_urlsafe(12),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(settings: Settings, subject: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "role": _assert_role(role),
        "typ": "refresh",
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.refresh_token_ttl_minutes)).timestamp()),
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_refresh_token(token: str, settings: Settings) -> dict:
    return _decode_token(token, settings, expected_type="refresh")


def _machine_principal(api_key: str, settings: Settings, required_scope: Optional[str]) -> Principal:
    key = _normalize(api_key)
    if not key:
        raise AuthError("Missing machine API key")

    for known_key, scopes in settings.machine_api_keys_map.items():
        if hmac.compare_digest(key, known_key):
            if required_scope and required_scope not in scopes:
                raise AuthError("Machine API key missing required scope", status.HTTP_403_FORBIDDEN)
            return Principal(subject="machine", role="operator", auth_type="machine", scopes=scopes)

    raise AuthError("Invalid machine API key")


def _user_principal(authorization: Optional[str], settings: Settings) -> Principal:
    token = _parse_bearer(authorization)
    payload = _decode_token(token, settings, expected_type="access")
    return Principal(
        subject=payload["sub"],
        role=payload["role"],
        auth_type="user",
        scopes={"ui"},
    )


async def require_user_auth(
    request: Request,
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
) -> Principal:
    settings = get_settings()
    if not settings.require_auth:
        principal = Principal(subject="dev-user", role="admin", auth_type="user", scopes={"*"})
    else:
        principal = _user_principal(authorization, settings)

    request.state.principal = principal
    return principal


async def require_machine_key(
    request: Request,
    required_scope: Optional[str] = None,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> Principal:
    settings = get_settings()
    principal = _machine_principal(x_api_key, settings, required_scope)
    request.state.principal = principal
    return principal


def require_role(minimum_role: str) -> Callable:
    async def _dependency(principal: Principal = Depends(require_user_auth)) -> Principal:
        _ensure_role(principal, minimum_role)
        return principal

    return _dependency


def require_user_or_machine(minimum_role: str, scope: str) -> Callable:
    async def _dependency(
        request: Request,
        authorization: Optional[str] = Header(default=None, alias="Authorization"),
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    ) -> Principal:
        settings = get_settings()
        if not settings.require_auth:
            principal = Principal(subject="dev-user", role="admin", auth_type="user", scopes={"*"})
            request.state.principal = principal
            return principal

        user_auth_error: Optional[Exception] = None
        principal: Optional[Principal] = None

        if authorization:
            try:
                principal = _user_principal(authorization, settings)
                _ensure_role(principal, minimum_role)
            except Exception as exc:  # noqa: BLE001
                user_auth_error = exc

        if principal is None and x_api_key:
            principal = _machine_principal(x_api_key, settings, scope)

        if principal is None:
            raise user_auth_error if isinstance(user_auth_error, HTTPException) else AuthError("Unauthorized")

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
    minimum_role: str = "viewer",
    enforce_rate_limit: Optional[Callable[[str], None]] = None,
) -> Principal:
    settings = get_settings()
    if not settings.require_auth:
        principal = Principal(subject="dev-user", role="admin", auth_type="user", scopes={"*"})
    else:
        token = _parse_ws_bearer(websocket)
        payload = _decode_token(token, settings, expected_type="access")
        principal = Principal(
            subject=payload["sub"],
            role=payload["role"],
            auth_type="user",
            scopes={"ui"},
        )
        _ensure_role(principal, minimum_role)

    if enforce_rate_limit is not None:
        enforce_rate_limit(principal.subject)

    websocket.state.principal = principal
    return principal


def auth_health(settings: Settings) -> dict:
    unsafe_defaults = settings.jwt_secret == "change-me-jwt-secret"
    weak_machine = any(key.startswith("local-dev-key") for key in settings.machine_api_keys_map)
    return {
        "require_auth": settings.require_auth,
        "jwt_algorithm": settings.jwt_algorithm,
        "issuer": settings.jwt_issuer,
        "audience": settings.jwt_audience,
        "unsafe_defaults": unsafe_defaults or weak_machine,
    }
