"""stored files: file metadata table

Revision ID: 0002_stored_files
Revises: 0001_auth_foundation
Create Date: 2026-07-11

Creates the ``files`` table (document metadata mapping a Blob object to its tenant
and uploader). No RLS policies here — that is ADR-006 (Sprint 2) work.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002_stored_files"
down_revision: str | None = "0001_auth_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "files",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("uploaded_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("blob_container", sa.String(length=63), nullable=False),
        sa.Column("blob_name", sa.String(length=128), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("etag", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_files"),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_files_tenant_id_tenants", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_id"], ["users.id"], name="fk_files_uploaded_by_id_users", ondelete="SET NULL"
        ),
        sa.UniqueConstraint(
            "tenant_id", "blob_container", "blob_name", name="uq_files_tenant_id_blob_name"
        ),
    )
    op.create_index("ix_files_tenant_id_created_at", "files", ["tenant_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_files_tenant_id_created_at", table_name="files")
    op.drop_table("files")
