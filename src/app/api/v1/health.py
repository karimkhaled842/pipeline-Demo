"""Health-check endpoint."""

import time

from fastapi import APIRouter
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from src.app.core.config import get_settings
from src.app.db.session import check_db_connection
from src.app.schemas.schemas import ComponentHealth, HealthResponse
from src.app.services.cache import check_redis_connection

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Application health check",
    description="Returns the health status of the application and its dependencies.",
)
async def health_check() -> HealthResponse:
    """Return overall health of app, database, and Redis."""
    settings = get_settings()
    components: dict[str, ComponentHealth] = {}

    # Database
    t0 = time.monotonic()
    db_ok = await check_db_connection()
    db_latency = round((time.monotonic() - t0) * 1000, 2)
    components["database"] = ComponentHealth(
        status="healthy" if db_ok else "unhealthy",
        latency_ms=db_latency,
    )

    # Redis
    t0 = time.monotonic()
    redis_ok = await check_redis_connection()
    redis_latency = round((time.monotonic() - t0) * 1000, 2)
    components["redis"] = ComponentHealth(
        status="healthy" if redis_ok else "unhealthy",
        latency_ms=redis_latency,
    )

    overall = "healthy" if db_ok and redis_ok else "degraded"

    return HealthResponse(
        status=overall,
        version=settings.app_version,
        environment=settings.environment,
        components=components,
    )


@router.get("/health/live", summary="Liveness probe")
async def liveness() -> dict:
    """Kubernetes liveness probe — always 200 if process is running."""
    return {"status": "alive"}


@router.get("/health/ready", summary="Readiness probe")
async def readiness() -> dict:
    """Kubernetes readiness probe — 200 only when DB + Redis are reachable."""
    db_ok = await check_db_connection()
    redis_ok = await check_redis_connection()
    if not db_ok or not redis_ok:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready",
        )
    return {"status": "ready"}


@router.get("/metrics", summary="Prometheus metrics", include_in_schema=False)
async def metrics() -> Response:
    """Expose Prometheus metrics for scraping."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
