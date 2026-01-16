"""Retail Product Agent Backend Healthcheck Routes Module."""

from fastapi import APIRouter

from app.v1.models.healthcheck import HealthCheckResponse
from app.v1.services.healthcheck import get_qdrant_collections, get_redis_keys

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Health Check",
    description="Check the health of the backend and its dependencies.",
)
async def health_check() -> HealthCheckResponse:
    """
    Check the health of services needed for the application.

    Args:
        None

    Returns:
        Dictionary containing health status information.
    """
    health_check = {
        "backend_status": "Running",
        "qdrant_collections": await get_qdrant_collections(),
        "redis_keys": await get_redis_keys(),
    }
    return HealthCheckResponse(**health_check)
