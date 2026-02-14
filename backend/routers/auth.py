"""
Authentication router for Supabase-backed user/session flows.
"""

from fastapi import APIRouter, Depends

from security import Principal, require_user_auth

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/me")
async def me(principal: Principal = Depends(require_user_auth)):
    return {
        "subject": principal.subject,
        "role": principal.role,
        "auth_type": principal.auth_type,
    }
