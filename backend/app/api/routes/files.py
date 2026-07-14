"""File API — upload (blob + metadata) and tenant-scoped listing.

Additive to prior sprints: uploads now persist a ``StoredFile`` metadata row in
PostgreSQL in addition to writing the blob. Listing is tenant-isolated, RBAC-gated,
paginated, and ordered by upload date. Download/delete/versioning/sharing are out of
scope for this sprint.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import StreamingResponse

from app.api.deps import DbSession, StorageServiceDep
from app.auth.authorization import require_role
from app.auth.principal import Principal
from app.models.role import RoleName
from app.schemas.files import (
    FileDetailResponse,
    FileDownloadResponse,
    FileListItem,
    FileListResponse,
    FileUploadResponse,
)
from app.services.file_service import (
    FileService,
    StoredFileForbiddenError,
    StoredFileNotFoundError,
)

router = APIRouter(prefix="/files", tags=["files"])


@router.post(
    "/upload",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document (Blob Storage + metadata)",
)
async def upload_file(
    file: UploadFile,
    # Auth/authz before storage so unauthenticated requests are rejected first.
    principal: Annotated[Principal, Depends(require_role(RoleName.CONTRIBUTOR))],
    storage: StorageServiceDep,
    db: DbSession,
) -> FileUploadResponse:
    service = FileService(db, storage)
    stored = await service.create_from_upload(principal, file)
    return FileUploadResponse(
        id=stored.id,
        container=stored.blob_container,
        blob_name=stored.blob_name,
        original_filename=stored.original_filename,
        size=stored.size_bytes,
        content_type=stored.content_type,
        etag=stored.etag,
        created_at=stored.created_at,
    )


@router.get(
    "",
    response_model=FileListResponse,
    summary="List the tenant's documents (paginated)",
)
async def list_files(
    principal: Annotated[Principal, Depends(require_role(RoleName.VIEWER))],
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    sort: Annotated[Literal["asc", "desc"], Query(description="By upload date.")] = "desc",
) -> FileListResponse:
    service = FileService(db)
    items, total = await service.list_files(
        principal, limit=limit, offset=offset, descending=sort == "desc"
    )
    return FileListResponse(
        items=[FileListItem.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{file_id}",
    response_model=FileDetailResponse,
    summary="Get a file's metadata (tenant-scoped)",
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "File belongs to another tenant."},
        status.HTTP_404_NOT_FOUND: {"description": "File does not exist."},
    },
)
async def get_file(
    file_id: uuid.UUID,
    principal: Annotated[Principal, Depends(require_role(RoleName.VIEWER))],
    db: DbSession,
) -> FileDetailResponse:
    service = FileService(db)
    try:
        stored, uploaded_by = await service.get_file(principal, file_id)
    except StoredFileNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found.") from exc
    except StoredFileForbiddenError as exc:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "You do not have access to this file."
        ) from exc

    return FileDetailResponse(
        id=stored.id,
        tenant_id=stored.tenant_id,
        original_filename=stored.original_filename,
        content_type=stored.content_type,
        size_bytes=stored.size_bytes,
        blob_container=stored.blob_container,
        blob_name=stored.blob_name,
        etag=stored.etag,
        uploaded_by_id=stored.uploaded_by_id,
        uploaded_by=uploaded_by,
        status="available",
        created_at=stored.created_at,
        updated_at=stored.updated_at,
    )


def _ascii_filename(value: str) -> str:
    return value.encode("ascii", "ignore").decode("ascii") or "download"


@router.get(
    "/{file_id}/download",
    response_model=FileDownloadResponse,
    summary="Get a short-lived download URL for a file (tenant-scoped)",
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "File belongs to another tenant."},
        status.HTTP_404_NOT_FOUND: {"description": "File does not exist."},
    },
)
async def download_file(
    file_id: uuid.UUID,
    principal: Annotated[Principal, Depends(require_role(RoleName.VIEWER))],
    db: DbSession,
    storage: StorageServiceDep,
) -> FileDownloadResponse | Response:
    service = FileService(db, storage)
    try:
        target = await service.get_download(principal, file_id)
    except StoredFileNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found.") from exc
    except StoredFileForbiddenError as exc:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "You do not have access to this file."
        ) from exc

    # Preferred: hand back a short-lived SAS URL (data-plane split; no bytes via API).
    if target.url is not None and target.expires_at is not None:
        return FileDownloadResponse(
            download_url=target.url,
            expires_at=target.expires_at,
            filename=target.filename,
        )

    # Fallback: stream the blob through the backend (e.g. SAS unavailable).
    downloader = await storage.download_stream(target.container, target.blob_name)
    return StreamingResponse(
        downloader.chunks(),
        media_type=target.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{_ascii_filename(target.filename)}"'
        },
    )
