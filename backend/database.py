"""
PostgreSQL database layer for user storage.

Manages connection pool lifecycle and provides schema migration on startup.
"""
import logging
import secrets
from typing import Optional

import asyncpg

logger = logging.getLogger("agent_lighthouse.database")

# Module-level pool reference
_pool: Optional[asyncpg.Pool] = None

# Schema migration — runs on every startup (idempotent)
_SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username        VARCHAR(50) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    api_key         VARCHAR(64) UNIQUE NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    last_login      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_api_key ON users(api_key);
"""


async def init_db(database_url: str) -> asyncpg.Pool:
    """
    Create connection pool and run schema migrations.

    Call this once during application startup (lifespan).
    """
    global _pool

    logger.info("Connecting to PostgreSQL...")
    _pool = await asyncpg.create_pool(
        database_url,
        min_size=2,
        max_size=10,
        command_timeout=10,
    )

    # Run migrations
    async with _pool.acquire() as conn:
        await conn.execute(_SCHEMA_SQL)

    logger.info("PostgreSQL connected and schema migrated")
    return _pool


async def close_db():
    """Close the connection pool. Call during shutdown."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("PostgreSQL connection pool closed")


def get_pool() -> asyncpg.Pool:
    """
    Get the active connection pool.

    Raises RuntimeError if the database hasn't been initialized yet.
    """
    if _pool is None:
        raise RuntimeError("Database not initialized — call init_db() first")
    return _pool


def generate_api_key() -> str:
    """Generate a cryptographically secure API key for SDK access."""
    return f"lh_{secrets.token_urlsafe(32)}"
