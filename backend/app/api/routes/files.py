"""File API — upload (blob + metadata) and tenant-scoped listing.

Additive to prior sprints: uploads now persist a ``StoredFile`` metadata row in
PostgreSQL in addition to writing the blob. Listing is tenant-isolated, RBAC-gated,
paginated, and ordered by upload date. Download/delete/versioning/sharing are out of
scope for this sprint.
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, UploadFile, status

from app.api.deps import DbSession, StorageServiceDep
from app.auth.authorization import require_role
from app.auth.principal import Principal
from app.models.role import RoleName
from app.schemas.files import FileListItem, FileListResponse, FileUploadResponse
from app.services.file_service import FileService

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
