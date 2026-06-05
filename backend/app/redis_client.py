"""Redis client for real-time lead state and pub/sub events."""
import json
from typing import Any, Optional

import redis.asyncio as redis

from app.config import settings


_redis_client: Optional[redis.Redis] = None


def get_redis() -> redis.Redis:
    """Singleton Redis connection."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def cache_set(key: str, value: Any, ttl_seconds: int = 3600) -> None:
    client = get_redis()
    await client.set(key, json.dumps(value), ex=ttl_seconds)


async def cache_get(key: str) -> Optional[Any]:
    client = get_redis()
    raw = await client.get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw


async def publish_event(channel: str, payload: dict) -> None:
    """Publish event for SSE/dashboard updates."""
    client = get_redis()
    await client.publish(channel, json.dumps(payload))


async def push_activity(event: dict, max_len: int = 200) -> None:
    """Push activity to capped list for live feed."""
    client = get_redis()
    await client.lpush("activity:feed", json.dumps(event))
    await client.ltrim("activity:feed", 0, max_len - 1)


async def get_recent_activity(limit: int = 50) -> list:
    client = get_redis()
    raw_items = await client.lrange("activity:feed", 0, limit - 1)
    return [json.loads(item) for item in raw_items]
