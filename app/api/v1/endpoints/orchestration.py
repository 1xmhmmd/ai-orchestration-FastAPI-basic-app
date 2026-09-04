import logging

from fastapi import APIRouter, Depends

from app.agents.orchestrator import Orchestrator
from app.api.deps import enforce_rate_limit, get_cache_service, get_orchestrator
from app.core.security import require_api_key
from app.schemas.agent import OrchestrationRequest, OrchestrationResponse
from app.schemas.common import ErrorResponse
from app.services.cache import CacheService, make_cache_key

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/orchestrate",
    response_model=OrchestrationResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid API key"},
        422: {"model": ErrorResponse, "description": "Invalid request payload"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        502: {"model": ErrorResponse, "description": "Upstream LLM provider error"},
    },
    summary="Run a multi-agent pipeline against a task",
    tags=["Orchestration"],
    dependencies=[Depends(require_api_key), Depends(enforce_rate_limit)],
)
async def orchestrate(
    payload: OrchestrationRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator),
    cache: CacheService = Depends(get_cache_service),
) -> OrchestrationResponse:
    """
    Runs the requested agents (default: researcher -> summarizer -> critic)
    sequentially against `task`, each building on the previous agent's
    output, and returns the consolidated final answer plus a per-step trace.

    Identical requests (same task + same agent list) are served from cache
    to avoid redundant LLM spend.
    """
    cache_key = make_cache_key(payload.task, ",".join(a.value for a in payload.agents))
    cached_result = await cache.get(cache_key)
    if cached_result is not None:
        return OrchestrationResponse(**cached_result, cached=True)

    result = await orchestrator.run(
        task=payload.task, agent_names=payload.agents, max_steps=payload.max_steps
    )
    await cache.set(cache_key, result.model_dump(exclude={"cached"}))
    return result
