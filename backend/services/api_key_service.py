"""
API key service for Supabase-authenticated users.
"""
from __future__ import annotations

from typing import Optional

from database import generate_api_key, get_pool


async def get_api_key(supabase_user_id: str) -> Optional[str]:
    pool = get_pool()
    row = await pool.fetchrow(
        "SELECT api_key FROM api_keys WHERE supabase_user_id = $1",
        supabase_user_id,
    )
    return row["api_key"] if row else None


async def get_or_create_api_key(supabase_user_id: str) -> str:
    existing = await get_api_key(supabase_user_id)
    if existing:
        return existing

    api_key = generate_api_key()
    pool = get_pool()
    await pool.execute(
        """
        INSERT INTO api_keys (supabase_user_id, api_key)
        VALUES ($1, $2)
        ON CONFLICT (supabase_user_id) DO NOTHING
        """,
        supabase_user_id,
        api_key,
    )
    return await get_api_key(supabase_user_id) or api_key


async def get_user_id_by_api_key(api_key: str) -> Optional[str]:
    """Reverse-lookup: resolve an API key to a supabase_user_id."""
    pool = get_pool()
    row = await pool.fetchrow(
        "SELECT supabase_user_id FROM api_keys WHERE api_key = $1",
        api_key.strip(),
    )
    return row["supabase_user_id"] if row else None
