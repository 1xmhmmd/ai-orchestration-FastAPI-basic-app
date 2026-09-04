"""
Fixed-window rate limiting, keyed by API key (falls back to client IP).

Uses Redis when configured (correct behaviour across multiple replicas
of the service) and falls back to a per-process in-memory counter for
local development so the project runs with zero external dependencies.

This is intentionally a *fixed-window* limiter for simplicity/readability.
The interface (`RateLimiter.hit`) is small enough to swap in a
sliding-window or token-bucket implementation later without touching
call sites.
"""

import time
from collections import defaultdict

from app.core.config import Settings
from app.core.exceptions import RateLimitExceededError


class _InMemoryStore:
    def __init__(self) -> None:
        self._counters: dict[str, tuple[int, float]] = defaultdict(lambda: (0, 0.0))

    async def incr_with_window(self, key: str, window_seconds: int) -> int:
        count, window_start = self._counters[key]
        now = time.time()
        if now - window_start >= window_seconds:
            count, window_start = 0, now
        count += 1
        self._counters[key] = (count, window_start)
        return count


class RateLimiter:
    """Async rate limiter; backend chosen automatically from settings."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._window_seconds = 60
        self._redis = None
        self._memory_store = _InMemoryStore()

        if settings.REDIS_URL:
            try:
                import redis.asyncio as redis  # local import: optional dependency

                self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
            except ImportError:
                # redis package not installed — degrade gracefully to in-memory.
                self._redis = None

    async def check(self, identity: str) -> None:
        limit = self._settings.RATE_LIMIT_PER_MINUTE
        key = f"ratelimit:{identity}"

        if self._redis is not None:
            count = await self._redis.incr(key)
            if count == 1:
                await self._redis.expire(key, self._window_seconds)
        else:
            count = await self._memory_store.incr_with_window(key, self._window_seconds)

        if count > limit:
            raise RateLimitExceededError(f"Rate limit of {limit} requests/minute exceeded.")
