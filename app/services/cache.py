"""
Response cache for orchestration results.

LLM calls are slow and expensive — identical requests (same task + same
agent pipeline) should hit cache instead of re-running the whole
pipeline. Uses Redis when configured, otherwise an in-process dict so
the service still works with zero external infra for local dev/demo.
"""

import hashlib
import json
import logging
from typing import Any

from app.core.config import Settings

logger = logging.getLogger(__name__)


def make_cache_key(*parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return f"orchestration:{digest}"


class CacheService:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._redis = None
        self._memory: dict[str, str] = {}

        if settings.REDIS_URL:
            try:
                import redis.asyncio as redis

                self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
            except ImportError:
                logger.warning("REDIS_URL set but redis package not installed; using memory cache.")

    async def get(self, key: str) -> dict[str, Any] | None:
        try:
            raw = await self._redis.get(key) if self._redis else self._memory.get(key)
        except Exception:  # noqa: BLE001 — cache must never break the request path
            logger.exception("Cache read failed; treating as cache miss.")
            return None
        return json.loads(raw) if raw else None

    async def set(self, key: str, value: dict[str, Any]) -> None:
        raw = json.dumps(value)
        try:
            if self._redis:
                await self._redis.set(key, raw, ex=self._settings.CACHE_TTL_SECONDS)
            else:
                self._memory[key] = raw
        except Exception:  # noqa: BLE001
            logger.exception("Cache write failed; continuing without caching this result.")
