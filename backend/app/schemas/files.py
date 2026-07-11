"""Schemas for file/blob endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class FileUploadResponse(BaseModel):
    """Result of a successful upload to Blob Storage."""

    container: str = Field(..., description="Logical container the blob was stored in.")
    blob_name: str = Field(..., description="Generated, collision-safe blob name.")
    original_filename: str = Field(..., description="Client-provided file name.")
    size: int = Field(..., description="Stored size in bytes.")
    content_type: str = Field(..., description="Detected/declared MIME type.")
    etag: str | None = Field(default=None, description="Blob ETag for concurrency control.")
