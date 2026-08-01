"""
Redis client for caching and pub/sub.
"""

import redis.asyncio as redis

from .config import get_settings

settings = get_settings()

# Redis connection pool
redis_pool = None


async def get_redis_pool():
    """Get or create Redis connection pool."""
    global redis_pool
    if redis_pool is None:
        redis_pool = redis.ConnectionPool.from_url(
            settings.redis_url,
            max_connections=settings.redis_max_connections,
            decode_responses=True,
        )
    return redis_pool


async def get_redis():
    """
    Get Redis client.

    Usage:
        redis_client = await get_redis()
        await redis_client.set("key", "value")
        value = await redis_client.get("key")
    """
    pool = await get_redis_pool()
    return redis.Redis(connection_pool=pool)


async def close_redis():
    """Close Redis connections."""
    global redis_pool
    if redis_pool:
        await redis_pool.disconnect()
        redis_pool = None
