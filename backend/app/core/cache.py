"""Optional Redis cache wrapper with a no-op fallback when REDIS_URL is empty."""

import logging
from functools import lru_cache
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


class _NoopCache:
    """Used when Redis is not configured/available. Every get misses."""

    def get(self, key: str) -> Optional[str]:
        return None

    def set(self, key: str, value: str, ttl: int = 3600) -> None:
        return None


class _RedisCache:
    def __init__(self, url: str):
        import redis  # imported lazily

        self._client = redis.Redis.from_url(url, decode_responses=True)
        # Fail fast if unreachable so we can fall back to no-op.
        self._client.ping()

    def get(self, key: str) -> Optional[str]:
        try:
            return self._client.get(key)
        except Exception as exc:  # noqa: BLE001
            logger.warning("cache get başarısız: %s", exc)
            return None

    def set(self, key: str, value: str, ttl: int = 3600) -> None:
        try:
            self._client.set(key, value, ex=ttl)
        except Exception as exc:  # noqa: BLE001
            logger.warning("cache set başarısız: %s", exc)


@lru_cache
def get_cache():
    settings = get_settings()
    if not settings.redis_url:
        return _NoopCache()
    try:
        return _RedisCache(settings.redis_url)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis bağlanamadı, cache devre dışı: %s", exc)
        return _NoopCache()
