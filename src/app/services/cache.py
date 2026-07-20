"""Redis cache client."""

import json
from typing import Any

import redis.asyncio as aioredis

from src.app.core.config import get_settings
from src.app.core.logging import get_logger

logger = get_logger(__name__)

_redis_client: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    """Return a singleton async Redis client."""
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = aioredis.from_url(
            settings.redis_url,
            max_connections=settings.redis_max_connections,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
        )
    return _redis_client


async def cache_get(key: str) -> Any | None:
    """Retrieve a JSON-serialised value from Redis; return None on miss."""
    try:
        client = get_redis()
        value = await client.get(key)
        if value is None:
            return None
        return json.loads(value)
    except Exception as exc:
        logger.warning("cache_get_failed", key=key, error=str(exc))
        return None


async def cache_set(key: str, value: Any, ttl: int | None = None) -> bool:
    """Serialise and store *value* in Redis under *key* with an optional TTL."""
    settings = get_settings()
    ttl = ttl if ttl is not None else settings.cache_ttl
    try:
        client = get_redis()
        serialised = json.dumps(value, default=str)
        await client.set(key, serialised, ex=ttl if ttl > 0 else None)
        return True
    except Exception as exc:
        logger.warning("cache_set_failed", key=key, error=str(exc))
        return False


async def cache_delete(key: str) -> bool:
    """Delete a key from Redis."""
    try:
        client = get_redis()
        await client.delete(key)
        return True
    except Exception as exc:
        logger.warning("cache_delete_failed", key=key, error=str(exc))
        return False


async def cache_exists(key: str) -> bool:
    """Return True if *key* exists in Redis."""
    try:
        client = get_redis()
        return bool(await client.exists(key))
    except Exception as exc:
        logger.warning("cache_exists_failed", key=key, error=str(exc))
        return False


async def check_redis_connection() -> bool:
    """Return True if Redis is reachable."""
    try:
        client = get_redis()
        return await client.ping()
    except Exception as exc:
        logger.error("redis_connection_failed", error=str(exc))
        return False
