"""files: soft-delete column

Revision ID: 0003_files_soft_delete
Revises: 0002_stored_files
Create Date: 2026-07-14

Adds a nullable ``deleted_at`` timestamp to ``files`` for soft delete (Sprint
4.4.3). NULL = live; a timestamp = logically deleted. A partial index keeps the
tenant live-file listing fast without scanning deleted rows. No schema redesign —
a single additive column plus one index.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_files_soft_delete"
down_revision: str | None = "0002_stored_files"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "files",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_files_tenant_live_created_at",
        "files",
        ["tenant_id", "created_at"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_files_tenant_live_created_at", table_name="files")
    op.drop_column("files", "deleted_at")
