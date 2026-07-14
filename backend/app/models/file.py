"""StoredFile entity — metadata for a document persisted to Azure Blob Storage.

Each row maps a Blob object to its owning tenant and the uploading user, plus the
display/content attributes needed for listing. Multi-tenant per PRD §10 (every row
carries ``tenant_id``); the table is RLS-ready for ADR-006. Download/delete/version
/share are intentionally out of scope for this sprint.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class StoredFile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "files"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "blob_container", "blob_name", name="uq_files_tenant_id_blob_name"
        ),
        # Supports tenant-scoped listing ordered by upload date (created_at).
        Index("ix_files_tenant_id_created_at", "tenant_id", "created_at"),
        # Partial index for the hot path: listing *live* files for a tenant.
        Index(
            "ix_files_tenant_live_created_at",
            "tenant_id",
            "created_at",
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE", name="fk_files_tenant_id_tenants"),
        nullable=False,
    )
    # Retained if the uploader is later removed (compliance): SET NULL, nullable.
    uploaded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL", name="fk_files_uploaded_by_id_users"),
        nullable=True,
    )
    blob_container: Mapped[str] = mapped_column(String(63), nullable=False)
    blob_name: Mapped[str] = mapped_column(String(128), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    etag: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Soft delete: NULL = live, a timestamp = logically deleted (row + blob retired).
    # A partial index keeps live-file listing fast without scanning deleted rows.
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<StoredFile id={self.id} name={self.original_filename!r} tenant={self.tenant_id}>"
