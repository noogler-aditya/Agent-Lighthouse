"""
Authentication router — registration and login with PostgreSQL.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from config import get_settings
from security import (
    Principal,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    require_user_auth,
)
from services.user_service import (
    UsernameExistsError,
    authenticate_user,
    create_user,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3 or len(v) > 50:
            raise ValueError("Username must be 3-50 characters")
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username can only contain letters, numbers, hyphens, and underscores")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 4:
            raise ValueError("Password must be at least 4 characters")
        return v


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_at: int
    username: str
    api_key: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


def _build_token_response(
    user: dict,
    include_api_key: bool = False,
) -> TokenResponse:
    settings = get_settings()
    access_token = create_access_token(settings, subject=user["username"], user_id=user["id"])
    refresh_token = create_refresh_token(settings, subject=user["username"], user_id=user["id"])

    payload = decode_refresh_token(refresh_token, settings)
    now = int(datetime.now(timezone.utc).timestamp())
    expires_at = min(payload["exp"], now + settings.access_token_ttl_minutes * 60)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
        username=user["username"],
        api_key=user.get("api_key") if include_api_key else None,
    )


@router.post("/register", response_model=TokenResponse)
async def register(request: RegisterRequest):
    """Register a new user account."""
    try:
        user = await create_user(request.username, request.password)
    except UsernameExistsError:
        raise HTTPException(status_code=409, detail="Username is already taken")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # Return tokens + api_key (shown once at registration)
    return _build_token_response(user, include_api_key=True)


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Authenticate with username and password."""
    user = await authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    return _build_token_response(user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: RefreshRequest):
    """Refresh an expired access token."""
    settings = get_settings()
    payload = decode_refresh_token(request.refresh_token, settings)
    subject = payload["sub"]
    user_id = payload.get("uid")

    access_token = create_access_token(settings, subject=subject, user_id=user_id)
    refresh_token = create_refresh_token(settings, subject=subject, user_id=user_id)
    refreshed_payload = decode_refresh_token(refresh_token, settings)

    now = int(datetime.now(timezone.utc).timestamp())
    expires_at = min(refreshed_payload["exp"], now + settings.access_token_ttl_minutes * 60)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
        username=subject,
    )


@router.get("/me")
async def me(principal: Principal = Depends(require_user_auth)):
    return {
        "subject": principal.subject,
        "auth_type": principal.auth_type,
        "user_id": principal.user_id,
    }
