from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.schemas.common import HealthStatus

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthStatus,
    summary="Liveness / readiness check",
    tags=["Health"],
)
async def health_check(settings: Settings = Depends(get_settings)) -> HealthStatus:
    """
    Basic liveness probe for orchestration platforms (Docker, k8s, ECS).

    Deliberately unauthenticated and dependency-free so a load balancer
    can hit it cheaply and frequently without needing an API key.
    """
    return HealthStatus(status="ok", environment=settings.ENVIRONMENT, version="1.0.0")
