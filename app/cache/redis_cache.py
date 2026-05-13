import json
from typing import Any, Optional
from loguru import logger
from redis import Redis
from redis.exceptions import RedisError
from app.config import settings


_redis_client: Optional[Redis] = None


def get_redis() -> Optional[Redis]:
    """Return a Redis client or None if Redis is unavailable."""
    global _redis_client
    if _redis_client is None:
        try:
            client = Redis.from_url(settings.redis_url, decode_responses=True, socket_timeout=2)
            client.ping()
            _redis_client = client
            logger.info("Connected to Redis")
        except Exception as e:
            logger.warning(f"Redis unavailable — caching disabled. ({e})")
    return _redis_client


def cache_get(key: str) -> Optional[Any]:
    r = get_redis()
    if not r:
        return None
    try:
        raw = r.get(key)
        if raw:
            logger.debug(f"Cache HIT: {key}")
            return json.loads(raw)
    except RedisError as e:
        logger.error(f"Cache GET error [{key}]: {e}")
    return None


def cache_set(key: str, value: Any, expire: Optional[int] = None) -> None:
    r = get_redis()
    if not r:
        return
    try:
        ttl = expire or settings.cache_expire_seconds
        r.setex(key, ttl, json.dumps(value, default=str))
        logger.debug(f"Cache SET: {key} (ttl={ttl}s)")
    except RedisError as e:
        logger.error(f"Cache SET error [{key}]: {e}")


def cache_delete(*keys: str) -> None:
    r = get_redis()
    if not r:
        return
    try:
        r.delete(*keys)
        logger.debug(f"Cache DEL: {keys}")
    except RedisError as e:
        logger.error(f"Cache DEL error {keys}: {e}")


def cache_delete_pattern(pattern: str) -> None:
    """Delete all keys matching a glob pattern (e.g. 'posts:page:*')."""
    r = get_redis()
    if not r:
        return
    try:
        matched = r.keys(pattern)
        if matched:
            r.delete(*matched)
            logger.debug(f"Cache DEL pattern '{pattern}': {len(matched)} key(s) removed")
    except RedisError as e:
        logger.error(f"Cache DEL pattern error [{pattern}]: {e}")
