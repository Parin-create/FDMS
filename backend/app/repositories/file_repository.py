"""Data access for :class:`StoredFile`.

Every method is **tenant-scoped** — a ``tenant_id`` is required and filtered on
every query — enforcing multi-tenant isolation until RLS (ADR-006) is enabled.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file import StoredFile


def _escape_like(value: str) -> str:
    """Escape LIKE/ILIKE wildcards so user input is matched literally."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class FileRepository:
    """Async repository for stored-file metadata."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def add(self, stored_file: StoredFile) -> None:
        """Stage a new row and flush (id/defaults populated)."""
        self._db.add(stored_file)
        await self._db.flush()

    async def get_by_id(self, file_id: uuid.UUID) -> StoredFile | None:
        """Fetch a file by primary key (NOT tenant-scoped; includes soft-deleted).

        The service performs the tenant check so it can distinguish "does not
        exist" (404) from "exists in another tenant" (403), and inspects
        ``deleted_at`` to distinguish "already deleted" (409) from live.
        """
        result = await self._db.execute(select(StoredFile).where(StoredFile.id == file_id))
        return result.scalar_one_or_none()

    async def mark_deleted(self, stored_file: StoredFile, deleted_at: datetime) -> None:
        """Stamp a row as soft-deleted and flush (caller commits)."""
        stored_file.deleted_at = deleted_at
        await self._db.flush()

    async def list_for_tenant(
        self,
        tenant_id: uuid.UUID,
        *,
        limit: int,
        offset: int,
        descending: bool = True,
        search: str | None = None,
        content_type: str | None = None,
    ) -> tuple[list[StoredFile], int]:
        """Return a page of files for the tenant plus the total count.

        Ordered by ``created_at`` (upload date); ``id`` is a stable tiebreaker so
        pagination is deterministic. Soft-deleted rows (``deleted_at`` set) are
        excluded from both the page and the total.

        Optional filters (applied to both the page and the total so pagination
        stays correct):
        - ``search``: case-insensitive substring match on the original filename.
        - ``content_type``: case-insensitive prefix match on the MIME type
          (e.g. ``"image/"`` matches all images, ``"application/pdf"`` matches PDFs).
        """
        filters = [StoredFile.tenant_id == tenant_id, StoredFile.deleted_at.is_(None)]
        if search:
            filters.append(
                StoredFile.original_filename.ilike(f"%{_escape_like(search)}%", escape="\\")
            )
        if content_type:
            filters.append(
                StoredFile.content_type.ilike(f"{_escape_like(content_type)}%", escape="\\")
            )

        order = StoredFile.created_at.desc() if descending else StoredFile.created_at.asc()

        page_result = await self._db.execute(
            select(StoredFile)
            .where(*filters)
            .order_by(order, StoredFile.id)
            .limit(limit)
            .offset(offset)
        )
        items = list(page_result.scalars().all())

        count_result = await self._db.execute(
            select(func.count()).select_from(StoredFile).where(*filters)
        )
        total = count_result.scalar_one()

        return items, total
