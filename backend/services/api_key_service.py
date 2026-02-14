"""
API key helpers backed by Redis.
"""
from __future__ import annotations

import hashlib
import json
import logging
import secrets
from typing import Optional

from config import get_settings
from services.redis_service import RedisService

logger = logging.getLogger(__name__)

API_KEY_PREFIX = "lighthouse:api_key:"
USER_API_KEY_PREFIX = "lighthouse:user_api_key:"


def _get_client(redis_service: RedisService):
    client = getattr(redis_service, "redis", None)
    if client is not None:
        return client
    if hasattr(redis_service, "get") and hasattr(redis_service, "set"):
        return redis_service
    raise RuntimeError("Redis client is not available")


def _generate_api_key() -> str:
    return f"lh_{secrets.token_urlsafe(32)}"


def _hash_api_key(api_key: str) -> str:
    settings = get_settings()
    salt = settings.api_key_hash_salt.encode("utf-8")
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        api_key.encode("utf-8"),
        salt,
        settings.api_key_hash_iterations,
    )
    return digest.hex()


async def get_user_principal_by_api_key(redis_service: RedisService, api_key: str) -> Optional[tuple[str, str]]:
    client = _get_client(redis_service)
    key = f"{API_KEY_PREFIX}{_hash_api_key(api_key)}"
    record = await client.get(key)
    if not record:
        return None
    try:
        payload = json.loads(record)
        subject = str(payload.get("subject", "")).strip()
        role = str(payload.get("role", "viewer")).strip()
        if not subject:
            return None
        return subject, role or "viewer"
    except Exception:  # noqa: BLE001
        # Backward compatibility with legacy value format (subject string only).
        return str(record), "viewer"


async def get_or_create_api_key(redis_service: RedisService, subject: str, role: str) -> str:
    client = _get_client(redis_service)
    user_key = f"{USER_API_KEY_PREFIX}{subject}"
    existing_hash = await client.get(user_key)
    if existing_hash and hasattr(client, "delete"):
        await client.delete(f"{API_KEY_PREFIX}{existing_hash}")

    for _ in range(5):
        api_key = _generate_api_key()
        key_hash = _hash_api_key(api_key)
        key = f"{API_KEY_PREFIX}{key_hash}"
        if await client.get(key):
            continue
        await client.set(user_key, key_hash)
        await client.set(key, json.dumps({"subject": subject, "role": role}))
        return api_key

    logger.error("Failed to allocate API key for subject=%s", subject)
    raise RuntimeError("Unable to allocate API key")
