"""Health and readiness endpoints.

- ``/health/live``  — liveness: the process is running (no dependency checks).
- ``/health/ready`` — readiness: dependencies (PostgreSQL) are reachable.

These map to container/orchestrator probes and the SLO/observability foundation
described in Architecture.md and SprintPlan Sprint 0.
"""

from __future__ import annotations

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.api.deps import DbSession, SettingsDep
from app.core.logging import get_logger
from app.schemas.health import LivenessResponse, ReadinessResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", response_model=LivenessResponse, summary="Liveness probe")
async def liveness(settings: SettingsDep) -> LivenessResponse:
    """Return 200 as long as the process can serve requests."""
    return LivenessResponse(
        service=settings.app_name,
        version="0.1.0",
        environment=settings.environment,
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness probe",
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadinessResponse}},
)
async def readiness(response: Response, db: DbSession) -> ReadinessResponse:
    """Verify database connectivity before declaring the service ready."""
    try:
        await db.execute(text("SELECT 1"))
    except Exception:  # pragma: no cover - exercised via integration env
        logger.exception("readiness.database_check_failed")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadinessResponse(status="degraded", database="error")

    return ReadinessResponse(status="ready", database="ok")
