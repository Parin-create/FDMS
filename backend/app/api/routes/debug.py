"""TEMPORARY deployment-debugging endpoint — REMOVE after diagnosing DB auth.

Exposes non-secret PostgreSQL connection diagnostics so we can confirm whether the
password is actually being loaded in Azure Container Apps. It NEVER returns the
password or any secret value — only whether one is present, its length, and whether
it equals the built-in default ("fdms").

Delete this file and its router registration (app/api/router.py) once debugging is
complete.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import SettingsDep

router = APIRouter(prefix="/debug", tags=["debug (temporary)"])

# The built-in default in Settings.postgres_password; used only for comparison,
# never printed as a live secret.
_DEFAULT_PASSWORD = "fdms"


@router.get(
    "/db-config",
    summary="TEMPORARY: PostgreSQL config diagnostics (no secrets)",
)
async def db_config(settings: SettingsDep) -> dict[str, object]:
    """Return non-secret DB connection diagnostics."""
    password = settings.postgres_password
    return {
        "postgres_host": settings.postgres_host,
        "postgres_port": settings.postgres_port,
        "postgres_db": settings.postgres_db,
        "postgres_user": settings.postgres_user,
        "postgres_sslmode": settings.postgres_sslmode,
        "password_present": bool(password),
        "password_length": len(password),
        "password_is_default": password == _DEFAULT_PASSWORD,
    }
