"""
API key issuance for Supabase-authenticated users.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from security import Principal, require_user_auth
from services.api_key_service import get_or_create_api_key

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/api-key")
async def get_api_key(principal: Principal = Depends(require_user_auth)):
    if not principal.user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing user id")
    api_key = await get_or_create_api_key(principal.user_id)
    return {"api_key": api_key}
