"""
User service — CRUD operations against PostgreSQL.

Handles password hashing with bcrypt, user creation, authentication,
and API key management.
"""
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import asyncpg
import bcrypt

from database import generate_api_key, get_pool

logger = logging.getLogger("agent_lighthouse.user_service")


class UsernameExistsError(Exception):
    """Raised when attempting to register a username that already exists."""
    pass


def _hash_password(password: str) -> str:
    """Hash a password with bcrypt (auto-generates salt)."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a bcrypt hash."""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def _row_to_dict(row: asyncpg.Record) -> dict:
    """Convert an asyncpg Record to a plain dict."""
    return {
        "id": str(row["id"]),
        "username": row["username"],
        "api_key": row["api_key"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "last_login": row["last_login"].isoformat() if row["last_login"] else None,
    }


async def create_user(username: str, password: str) -> dict:
    """
    Register a new user.

    Args:
        username: Unique username (3-50 characters).
        password: Plain-text password (min 4 characters).

    Returns:
        User dict with id, username, api_key, created_at.

    Raises:
        UsernameExistsError: If the username is already taken.
        ValueError: If validation fails.
    """
    # Validate
    username = username.strip()
    if len(username) < 3 or len(username) > 50:
        raise ValueError("Username must be 3-50 characters")
    if len(password) < 4:
        raise ValueError("Password must be at least 4 characters")

    password_hash = _hash_password(password)
    api_key = generate_api_key()
    pool = get_pool()

    try:
        row = await pool.fetchrow(
            """
            INSERT INTO users (username, password_hash, api_key)
            VALUES ($1, $2, $3)
            RETURNING id, username, api_key, created_at, last_login
            """,
            username,
            password_hash,
            api_key,
        )
    except asyncpg.UniqueViolationError:
        raise UsernameExistsError(f"Username '{username}' is already taken")

    logger.info("User created: %s", username)
    return _row_to_dict(row)


async def authenticate_user(username: str, password: str) -> Optional[dict]:
    """
    Authenticate a user by username and password.

    Returns:
        User dict if credentials are valid, None otherwise.
    """
    pool = get_pool()
    row = await pool.fetchrow(
        "SELECT id, username, password_hash, api_key, created_at, last_login FROM users WHERE username = $1",
        username.strip(),
    )

    if not row:
        return None

    if not _verify_password(password, row["password_hash"]):
        return None

    # Update last_login timestamp
    await pool.execute(
        "UPDATE users SET last_login = $1 WHERE id = $2",
        datetime.now(timezone.utc),
        row["id"],
    )

    logger.info("User authenticated: %s", username)
    return _row_to_dict(row)


async def get_user_by_api_key(api_key: str) -> Optional[dict]:
    """Look up a user by their SDK API key."""
    pool = get_pool()
    row = await pool.fetchrow(
        "SELECT id, username, api_key, created_at, last_login FROM users WHERE api_key = $1",
        api_key.strip(),
    )
    return _row_to_dict(row) if row else None


async def get_user_by_id(user_id: str) -> Optional[dict]:
    """Look up a user by their UUID."""
    pool = get_pool()
    try:
        uid = UUID(user_id)
    except ValueError:
        return None

    row = await pool.fetchrow(
        "SELECT id, username, api_key, created_at, last_login FROM users WHERE id = $1",
        uid,
    )
    return _row_to_dict(row) if row else None
