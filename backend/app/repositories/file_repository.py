"""Data access for :class:`StoredFile`.

Every method is **tenant-scoped** — a ``tenant_id`` is required and filtered on
every query — enforcing multi-tenant isolation until RLS (ADR-006) is enabled.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file import StoredFile


class FileRepository:
    """Async repository for stored-file metadata."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def add(self, stored_file: StoredFile) -> None:
        """Stage a new row and flush (id/defaults populated)."""
        self._db.add(stored_file)
        await self._db.flush()

    async def list_for_tenant(
        self,
        tenant_id: uuid.UUID,
        *,
        limit: int,
        offset: int,
        descending: bool = True,
    ) -> tuple[list[StoredFile], int]:
        """Return a page of files for the tenant plus the total count.

        Ordered by ``created_at`` (upload date); ``id`` is a stable tiebreaker so
        pagination is deterministic.
        """
        order = StoredFile.created_at.desc() if descending else StoredFile.created_at.asc()

        page_result = await self._db.execute(
            select(StoredFile)
            .where(StoredFile.tenant_id == tenant_id)
            .order_by(order, StoredFile.id)
            .limit(limit)
            .offset(offset)
        )
        items = list(page_result.scalars().all())

        count_result = await self._db.execute(
            select(func.count()).select_from(StoredFile).where(StoredFile.tenant_id == tenant_id)
        )
        total = count_result.scalar_one()

        return items, total
