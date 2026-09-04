"""
Dependency-injection wiring for the API layer.

FastAPI's `Depends` system is used deliberately instead of module-level
globals: it makes every endpoint's dependencies explicit, keeps services
easily mockable in tests (`app.dependency_overrides[...]`), and avoids
hidden shared state between requests.
"""

from functools import lru_cache

from fastapi import Depends, Request

from app.agents.orchestrator import Orchestrator
from app.core.config import get_settings
from app.core.rate_limit import RateLimiter
from app.core.security import require_api_key
from app.services.cache import CacheService
from app.services.llm_client import LLMClient


@lru_cache
def get_llm_client() -> LLMClient:
    return LLMClient(get_settings())


@lru_cache
def get_cache_service() -> CacheService:
    return CacheService(get_settings())


@lru_cache
def get_rate_limiter() -> RateLimiter:
    return RateLimiter(get_settings())


@lru_cache
def get_orchestrator() -> Orchestrator:
    return Orchestrator(get_llm_client(), get_settings())


async def enforce_rate_limit(
    request: Request,
    api_key: str = Depends(require_api_key),
    limiter: RateLimiter = Depends(get_rate_limiter),
) -> None:
    identity = (
        api_key
        if api_key != "dev-mode-no-auth"
        else (request.client.host if request.client else "anonymous")
    )
    await limiter.check(identity)
