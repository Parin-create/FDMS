"""Dependency-injection foundation.

Central, reusable FastAPI dependencies exposed as ``Annotated`` aliases so route
signatures stay concise and consistent (e.g. ``db: DbSession``). This is the single
import surface for core request-scoped dependencies; feature-specific dependencies
(auth principals, etc.) live alongside their own modules and can be aliased here as
the surface grows.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.services.blob_storage import (
    BlobStorageService,
    StorageNotConfiguredError,
    get_storage_service,
)

#: Application settings (cached singleton).
SettingsDep = Annotated[Settings, Depends(get_settings)]

#: Transactional async database session, scoped to the request.
DbSession = Annotated[AsyncSession, Depends(get_db)]


def provide_storage_service(settings: SettingsDep) -> BlobStorageService:
    """Provide the Blob Storage service, or 503 if storage is not configured."""
    try:
        return get_storage_service(settings)
    except StorageNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Blob storage is not configured on this server.",
        ) from exc


#: Shared async Blob Storage service (singleton).
StorageServiceDep = Annotated[BlobStorageService, Depends(provide_storage_service)]

__all__ = ["SettingsDep", "DbSession", "StorageServiceDep"]
