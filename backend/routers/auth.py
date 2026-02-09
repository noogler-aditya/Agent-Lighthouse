"""
Authentication router for user/session flows.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from config import get_settings
from security import (
    Principal,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    require_user_auth,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_at: int
    role: str


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    settings = get_settings()
    users = settings.auth_users_map
    user = users.get(request.username)
    if not user or user["password"] != request.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    role = user["role"]
    access_token = create_access_token(settings, subject=request.username, role=role)
    refresh_token = create_refresh_token(settings, subject=request.username, role=role)

    payload = decode_refresh_token(refresh_token, settings)
    now = int(datetime.now(timezone.utc).timestamp())
    expires_at = min(payload["exp"], now + settings.access_token_ttl_minutes * 60)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
        role=role,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: RefreshRequest):
    settings = get_settings()
    payload = decode_refresh_token(request.refresh_token, settings)
    role = payload["role"]
    subject = payload["sub"]

    access_token = create_access_token(settings, subject=subject, role=role)
    refresh_token = create_refresh_token(settings, subject=subject, role=role)
    refreshed_payload = decode_refresh_token(refresh_token, settings)

    now = int(datetime.now(timezone.utc).timestamp())
    expires_at = min(refreshed_payload["exp"], now + settings.access_token_ttl_minutes * 60)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
        role=role,
    )


@router.get("/me")
async def me(principal: Principal = Depends(require_user_auth)):
    return {
        "subject": principal.subject,
        "role": principal.role,
        "auth_type": principal.auth_type,
    }
