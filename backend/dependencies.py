"""
Shared dependency providers.
"""
from fastapi import Request

from config import Settings, get_settings
from services.connection_manager import ConnectionManager
from services.redis_service import RedisService


def get_redis(request: Request) -> RedisService:
    return request.app.state.redis_service


def get_connection_manager(request: Request) -> ConnectionManager:
    return request.app.state.connection_manager


def get_app_settings() -> Settings:
    return get_settings()

