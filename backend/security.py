"""
Authentication and authorization helpers for HTTP and WebSocket access.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hmac
import logging
from functools import lru_cache
from typing import Callable, Optional
import secrets

import jwt
from jwt import PyJWKClient
from fastapi import Depends, Header, HTTPException, Request, WebSocket, status

from config import Settings, get_settings
from services.api_key_service import get_user_principal_by_api_key

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


@lru_cache(maxsize=4)
def _get_jwks_client(jwks_url: str) -> PyJWKClient:
    return PyJWKClient(jwks_url)


def _extract_claim(payload: dict, path: str):
    current = payload
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _decode_supabase_access_token(token: str, settings: Settings) -> dict:
    if not settings.supabase_configured:
        raise AuthError("Supabase auth is not configured", status.HTTP_503_SERVICE_UNAVAILABLE)

    try:
        signing_key = _get_jwks_client(settings.supabase_jwks_url).get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.supabase_jwt_audience,
            issuer=settings.supabase_effective_issuer,
            options={"require": ["sub", "exp", "iat"]},
        )
    except Exception as exc:  # noqa: BLE001
        if settings.app_env.lower() == "test" and settings.supabase_test_jwt_secret:
            try:
                return jwt.decode(
                    token,
                    settings.supabase_test_jwt_secret,
                    algorithms=["HS256"],
                    audience=settings.supabase_jwt_audience,
                    issuer=settings.supabase_effective_issuer or "http://localhost:54321/auth/v1",
                )
            except Exception as test_exc:  # noqa: BLE001
                raise AuthError("Invalid or expired token") from test_exc
        raise AuthError("Invalid or expired token") from exc

    return payload


def _resolve_supabase_role(payload: dict, settings: Settings) -> str:
    mapped_role = None

    candidates = [
        _extract_claim(payload, settings.supabase_role_claim),
        payload.get("role"),
        _extract_claim(payload, "app_metadata.role"),
    ]
    for candidate in candidates:
        if not isinstance(candidate, str):
            continue
        raw = candidate.strip()
        if not raw:
            continue
        mapped_role = settings.supabase_role_map_dict.get(raw, raw)
        break

    if not mapped_role:
        mapped_role = "viewer"

    return _assert_role(mapped_role)


def create_access_token(settings: Settings, subject: str, role: str) -> str:
    """
    Test helper for integration/unit tests in APP_ENV=test.
    Production auth path always verifies Supabase-issued tokens.
    """
    if settings.app_env.lower() != "test" or not settings.supabase_test_jwt_secret:
        raise RuntimeError("create_access_token is only available for test environment")
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "role": role,
        "aud": settings.supabase_jwt_audience,
        "iss": settings.supabase_effective_issuer or "http://localhost:54321/auth/v1",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=30)).timestamp()),
        "app_metadata": {"role": role},
        "typ": "access",
        "jti": secrets.token_urlsafe(10),
    }
    return jwt.encode(payload, settings.supabase_test_jwt_secret, algorithm="HS256")


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
    payload = _decode_supabase_access_token(token, settings)
    role = _resolve_supabase_role(payload, settings)
    subject = payload.get("sub")
    if not subject:
        raise AuthError("Token missing required claims")
    return Principal(subject=subject, role=role, auth_type="user", scopes={"ui"})


async def _resolve_api_key(
    request: Request,
    api_key: str,
    settings: Settings,
    required_scope: Optional[str],
    minimum_role: str,
) -> Principal:
    key = _normalize(api_key)
    if not key:
        raise AuthError("Missing API key")

    redis_service = getattr(request.app.state, "redis_service", None)
    if redis_service is None:
        return _machine_principal(key, settings, required_scope)

    try:
        principal_data = await get_user_principal_by_api_key(redis_service, key)
    except Exception:  # noqa: BLE001
        logger.warning("API key lookup failed; falling back to machine keys", exc_info=True)
        principal_data = None

    if principal_data:
        subject, role = principal_data
        resolved_role = _assert_role(role)
        scopes = {"trace:read"} if resolved_role == "viewer" else {"trace:read", "trace:write"}
        if required_scope and required_scope not in scopes:
            raise AuthError("API key missing required scope", status.HTTP_403_FORBIDDEN)
        principal = Principal(subject=subject, role=resolved_role, auth_type="api_key", scopes=scopes)
        _ensure_role(principal, minimum_role)
        return principal

    return _machine_principal(key, settings, required_scope)


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
                candidate = _user_principal(authorization, settings)
                _ensure_role(candidate, minimum_role)
                principal = candidate
            except Exception as exc:  # noqa: BLE001
                user_auth_error = exc

        if principal is None and x_api_key:
            principal = await _resolve_api_key(request, x_api_key, settings, scope, minimum_role)

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
        payload = _decode_supabase_access_token(token, settings)
        role = _resolve_supabase_role(payload, settings)
        subject = payload.get("sub")
        if not subject:
            raise AuthError("Token missing required claims")
        principal = Principal(subject=subject, role=role, auth_type="user", scopes={"ui"})
        _ensure_role(principal, minimum_role)

    if enforce_rate_limit is not None:
        enforce_rate_limit(principal.subject)

    websocket.state.principal = principal
    return principal


def auth_health(settings: Settings) -> dict:
    return {
        "require_auth": settings.require_auth,
        "provider": "supabase",
        "issuer": settings.supabase_effective_issuer,
        "audience": settings.supabase_jwt_audience,
        "unsafe_defaults": not settings.supabase_configured,
    }
