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
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

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


class StoredFileAlreadyDeletedError(Exception):
    """The file is already soft-deleted (mapped to HTTP 409)."""


# Short-lived read window for download SAS URLs.
_DOWNLOAD_EXPIRY_SECONDS = 300


@dataclass(slots=True)
class DownloadTarget:
    """How to deliver a file: a SAS ``url`` if available, else stream by blob ref."""

    filename: str
    content_type: str
    container: str
    blob_name: str
    url: str | None
    expires_at: datetime | None

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
        search: str | None = None,
        content_type: str | None = None,
    ) -> tuple[list[StoredFile], int]:
        """List the current tenant's files (paginated, filtered, ordered by date)."""
        return await self._repo.list_for_tenant(
            principal.tenant_id,
            limit=limit,
            offset=offset,
            descending=descending,
            search=search,
            content_type=content_type,
        )

    async def _get_owned_file(
        self, principal: Principal, file_id: uuid.UUID, *, include_deleted: bool = False
    ) -> StoredFile:
        """Load a file and enforce existence + tenant ownership (404/403).

        For read paths (``include_deleted=False``) a soft-deleted file is treated
        as gone (404). The delete path passes ``include_deleted=True`` so it can
        reach the row and report "already deleted" (409) instead.
        """
        stored = await self._repo.get_by_id(file_id)
        if stored is None:
            raise StoredFileNotFoundError
        if stored.tenant_id != principal.tenant_id:
            raise StoredFileForbiddenError
        if not include_deleted and stored.deleted_at is not None:
            raise StoredFileNotFoundError
        return stored

    async def get_file(
        self, principal: Principal, file_id: uuid.UUID
    ) -> tuple[StoredFile, str | None]:
        """Return a single file's metadata plus the uploader's email.

        Raises :class:`StoredFileNotFoundError` (404) when the id does not exist,
        or :class:`StoredFileForbiddenError` (403) when it belongs to another tenant.
        """
        stored = await self._get_owned_file(principal, file_id)
        uploaded_by = await self._resolve_uploader_email(stored.uploaded_by_id)
        return stored, uploaded_by

    async def get_download(self, principal: Principal, file_id: uuid.UUID) -> DownloadTarget:
        """Resolve a download target for a file: a short-lived SAS URL if possible."""
        if self._storage is None:  # pragma: no cover - guarded by DI in the route
            raise RuntimeError("FileService.get_download requires a storage client")

        stored = await self._get_owned_file(principal, file_id)
        url = await self._storage.generate_read_url(
            stored.blob_container,
            stored.blob_name,
            filename=stored.original_filename,
            expiry_seconds=_DOWNLOAD_EXPIRY_SECONDS,
        )
        expires_at = (
            datetime.now(tz=UTC) + timedelta(seconds=_DOWNLOAD_EXPIRY_SECONDS) if url else None
        )
        return DownloadTarget(
            filename=stored.original_filename,
            content_type=stored.content_type,
            container=stored.blob_container,
            blob_name=stored.blob_name,
            url=url,
            expires_at=expires_at,
        )

    async def delete_file(self, principal: Principal, file_id: uuid.UUID) -> None:
        """Soft-delete a file: stamp ``deleted_at``, then remove the backing blob.

        Raises :class:`StoredFileNotFoundError` (404), :class:`StoredFileForbiddenError`
        (403), or :class:`StoredFileAlreadyDeletedError` (409).

        Consistency: the metadata is the source of truth, so the row is stamped and
        committed *first* (making the file immediately invisible to reads/lists),
        then the blob is deleted best-effort. If the blob delete fails, the file is
        still logically gone and the orphaned blob is logged for later reaping — this
        is preferred over deleting the blob first, which could leave a live row
        pointing at missing bytes if the commit then failed.
        """
        if self._storage is None:  # pragma: no cover - guarded by DI in the route
            raise RuntimeError("FileService.delete_file requires a storage client")

        stored = await self._get_owned_file(principal, file_id, include_deleted=True)
        if stored.deleted_at is not None:
            raise StoredFileAlreadyDeletedError

        await self._repo.mark_deleted(stored, datetime.now(tz=UTC))
        await self._db.commit()

        try:
            await self._storage.delete(stored.blob_container, stored.blob_name)
        except Exception:  # pragma: no cover - best effort; row already retired
            logger.exception(
                "files.blob_delete_failed",
                file_id=str(stored.id),
                blob=stored.blob_name,
            )

        logger.info(
            "files.deleted",
            file_id=str(stored.id),
            tenant_id=str(principal.tenant_id),
        )

    async def _resolve_uploader_email(self, user_id: uuid.UUID | None) -> str | None:
        if user_id is None:
            return None
        result = await self._db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        return user.email if user is not None else None
