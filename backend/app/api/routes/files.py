"""File upload API (Blob Storage).

Additive endpoints — existing routes are unchanged. Uploads stream to the
``documents`` container in chunks (no full-file buffering), so large files are
supported. The stored blob name is server-generated (UUID) to prevent collisions
and path traversal; the original filename and uploader/tenant identity are recorded
as blob metadata for later document indexing (Sprint 4).

Authorization is default-deny: at least the Contributor role is required (PRD §11).
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, UploadFile, status

from app.api.deps import StorageServiceDep
from app.auth.authorization import require_role
from app.auth.principal import Principal
from app.core.logging import get_logger
from app.models.role import RoleName
from app.schemas.files import FileUploadResponse
from app.services.blob_storage import guess_content_type

logger = get_logger(__name__)

router = APIRouter(prefix="/files", tags=["files"])

# 4 MiB read chunk for streaming uploads.
_CHUNK_SIZE = 4 * 1024 * 1024


def _ascii_safe(value: str) -> str:
    """Blob metadata must be ASCII and header-safe."""
    return value.encode("ascii", "ignore").decode("ascii").replace("\n", " ").replace("\r", " ")


async def _stream(file: UploadFile) -> AsyncIterator[bytes]:
    """Yield the upload in chunks so large files are never fully buffered."""
    while chunk := await file.read(_CHUNK_SIZE):
        yield chunk


@router.post(
    "/upload",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document to Blob Storage",
)
async def upload_file(
    file: UploadFile,
    # Authentication/authorization is declared before the storage dependency so an
    # unauthenticated request is rejected (401/403) before any server state is probed.
    principal: Annotated[Principal, Depends(require_role(RoleName.CONTRIBUTOR))],
    storage: StorageServiceDep,
) -> FileUploadResponse:
    original_name = file.filename or "unnamed"
    extension = os.path.splitext(original_name)[1]
    blob_name = f"{uuid4().hex}{extension}"
    content_type = file.content_type or guess_content_type(original_name)

    metadata = {
        "original_filename": _ascii_safe(original_name),
        "uploaded_by": str(principal.user_id),
        "tenant_id": str(principal.tenant_id),
    }

    result = await storage.upload(
        "documents",
        blob_name,
        _stream(file),
        content_type=content_type,
        metadata=metadata,
    )
    logger.info(
        "files.uploaded",
        blob=result.name,
        size=result.size,
        tenant_id=str(principal.tenant_id),
    )

    return FileUploadResponse(
        container=result.container,
        blob_name=result.name,
        original_filename=original_name,
        size=result.size,
        content_type=result.content_type,
        etag=result.etag,
    )
