"""
API key issuance for authenticated users.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from dependencies import get_redis
from security import Principal, require_user_auth
from services.api_key_service import get_or_create_api_key
from services.redis_service import RedisService

router = APIRouter(prefix="/api/auth", tags=["auth"])


class ApiKeyResponse(BaseModel):
    api_key: str


@router.post("/api-key", response_model=ApiKeyResponse)
async def get_api_key(
    principal: Principal = Depends(require_user_auth),
    redis: RedisService = Depends(get_redis),
):
    api_key = await get_or_create_api_key(redis, principal.subject, principal.role)
    return ApiKeyResponse(api_key=api_key)
