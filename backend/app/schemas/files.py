"""Schemas for file/blob endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FileUploadResponse(BaseModel):
    """Result of a successful upload (blob written + metadata persisted)."""

    id: uuid.UUID = Field(..., description="StoredFile metadata id.")
    container: str = Field(..., description="Logical container the blob was stored in.")
    blob_name: str = Field(..., description="Generated, collision-safe blob name.")
    original_filename: str = Field(..., description="Client-provided file name.")
    size: int = Field(..., description="Stored size in bytes.")
    content_type: str = Field(..., description="Detected/declared MIME type.")
    etag: str | None = Field(default=None, description="Blob ETag for concurrency control.")
    created_at: datetime = Field(..., description="When the metadata row was created.")


class FileListItem(BaseModel):
    """A single file in the tenant's file list."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str
    content_type: str
    size_bytes: int
    blob_name: str
    etag: str | None = None
    uploaded_by_id: uuid.UUID | None = None
    created_at: datetime


class FileListResponse(BaseModel):
    """Paginated list of the tenant's files."""

    items: list[FileListItem]
    total: int = Field(..., description="Total files for the tenant.")
    limit: int = Field(..., description="Page size used.")
    offset: int = Field(..., description="Offset used.")


class FileDetailResponse(BaseModel):
    """Full metadata for a single file (no content)."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    original_filename: str
    content_type: str
    size_bytes: int
    blob_container: str
    blob_name: str
    etag: str | None = None
    uploaded_by_id: uuid.UUID | None = None
    uploaded_by: str | None = Field(default=None, description="Uploader email, if known.")
    status: str = Field(..., description="Lifecycle status (e.g. 'available').")
    created_at: datetime
    updated_at: datetime
