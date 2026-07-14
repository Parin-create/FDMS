"""File service — orchestrates Blob Storage + PostgreSQL metadata.

Per-request service (mirrors ``UserProvisioningService``): built with the request's
``AsyncSession`` and (for uploads) the shared ``BlobStorageService``. Uploads stream
to Blob then persist a :class:`StoredFile` row; if the DB write fails after the blob
is written, the orphan blob is best-effort deleted (compensating action).
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.principal import Principal
from app.core.logging import get_logger
from app.models.file import StoredFile
from app.models.user import User
from app.repositories.file_repository import FileRepository
from app.services.blob_storage import BlobStorageService, guess_content_type

logger = get_logger(__name__)


class StoredFileNotFoundError(Exception):
    """The requested file id does not exist (mapped to HTTP 404)."""


class StoredFileForbiddenError(Exception):
    """The file exists but belongs to another tenant (mapped to HTTP 403)."""

# Logical container documents are stored in (configurable via BLOB_CONTAINER_DOCUMENTS).
_DOCUMENTS_CONTAINER = "documents"
_CHUNK_SIZE = 4 * 1024 * 1024  # 4 MiB streaming chunks


def _ascii_safe(value: str) -> str:
    """Blob metadata must be ASCII and header-safe."""
    return value.encode("ascii", "ignore").decode("ascii").replace("\n", " ").replace("\r", " ")


async def _stream(file: UploadFile) -> AsyncIterator[bytes]:
    while chunk := await file.read(_CHUNK_SIZE):
        yield chunk


class FileService:
    """Create and list stored files for the current principal."""

    def __init__(self, db: AsyncSession, storage: BlobStorageService | None = None) -> None:
        self._db = db
        self._storage = storage
        self._repo = FileRepository(db)

    async def create_from_upload(self, principal: Principal, file: UploadFile) -> StoredFile:
        """Stream the upload to Blob Storage, then persist its metadata row."""
        if self._storage is None:  # pragma: no cover - guarded by DI in the route
            raise RuntimeError("FileService.create_from_upload requires a storage client")

        original_name = file.filename or "unnamed"
        extension = os.path.splitext(original_name)[1]
        blob_name = f"{uuid.uuid4().hex}{extension}"
        content_type = file.content_type or guess_content_type(original_name)
        metadata = {
            "original_filename": _ascii_safe(original_name),
            "uploaded_by": str(principal.user_id),
            "tenant_id": str(principal.tenant_id),
        }

        result = await self._storage.upload(
            _DOCUMENTS_CONTAINER,
            blob_name,
            _stream(file),
            content_type=content_type,
            metadata=metadata,
        )

        stored = StoredFile(
            tenant_id=principal.tenant_id,
            uploaded_by_id=principal.user_id,
            blob_container=result.container,
            blob_name=result.name,
            original_filename=original_name,
            content_type=result.content_type,
            size_bytes=result.size,
            etag=result.etag,
        )
        try:
            await self._repo.add(stored)
            await self._db.commit()
            await self._db.refresh(stored)
        except Exception:
            await self._db.rollback()
            # Compensating action: remove the orphaned blob so storage and DB stay consistent.
            try:
                await self._storage.delete(_DOCUMENTS_CONTAINER, blob_name)
            except Exception:  # pragma: no cover - best effort
                logger.exception("files.orphan_blob_cleanup_failed", blob=blob_name)
            logger.exception("files.metadata_persist_failed", blob=blob_name)
            raise

        logger.info(
            "files.created",
            file_id=str(stored.id),
            size=stored.size_bytes,
            tenant_id=str(principal.tenant_id),
        )
        return stored

    async def list_files(
        self,
        principal: Principal,
        *,
        limit: int,
        offset: int,
        descending: bool = True,
    ) -> tuple[list[StoredFile], int]:
        """List the current tenant's files (paginated, ordered by upload date)."""
        return await self._repo.list_for_tenant(
            principal.tenant_id, limit=limit, offset=offset, descending=descending
        )

    async def get_file(
        self, principal: Principal, file_id: uuid.UUID
    ) -> tuple[StoredFile, str | None]:
        """Return a single file's metadata plus the uploader's email.

        Raises :class:`StoredFileNotFoundError` (404) when the id does not exist,
        or :class:`StoredFileForbiddenError` (403) when it belongs to another tenant.
        """
        stored = await self._repo.get_by_id(file_id)
        if stored is None:
            raise StoredFileNotFoundError
        if stored.tenant_id != principal.tenant_id:
            raise StoredFileForbiddenError
        uploaded_by = await self._resolve_uploader_email(stored.uploaded_by_id)
        return stored, uploaded_by

    async def _resolve_uploader_email(self, user_id: uuid.UUID | None) -> str | None:
        if user_id is None:
            return None
        result = await self._db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        return user.email if user is not None else None
