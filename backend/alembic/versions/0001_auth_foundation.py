"""auth foundation: tenants and users

Revision ID: 0001_auth_foundation
Revises:
Create Date: 2026-06-23

Creates the Sprint 1 identity tables (tenants, users) and their enum types.
Row-Level Security policies are intentionally NOT added here — they are part of
Sprint 2 (multi-tenancy + RLS, per ADR-006).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_auth_foundation"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Enum types are created/dropped explicitly so we control their lifecycle.
role_name = postgresql.ENUM(
    "TenantAdmin",
    "Manager",
    "Contributor",
    "Viewer",
    "Guest",
    name="role_name",
    create_type=False,
)
tenant_status = postgresql.ENUM(
    "active",
    "suspended",
    name="tenant_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    role_name.create(bind, checkfirst=True)
    tenant_status.create(bind, checkfirst=True)

    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("entra_tenant_id", sa.String(length=64), nullable=False),
        sa.Column("status", tenant_status, server_default="active", nullable=False),
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
        sa.PrimaryKeyConstraint("id", name="pk_tenants"),
        sa.UniqueConstraint("entra_tenant_id", name="uq_tenants_entra_tenant_id"),
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entra_oid", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("role", role_name, server_default="Viewer", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_users_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("tenant_id", "entra_oid", name="uq_users_tenant_id_entra_oid"),
    )
    op.create_index("ix_users_email", "users", ["email"])


def downgrade() -> None:
    bind = op.get_bind()
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.drop_table("tenants")
    tenant_status.drop(bind, checkfirst=True)
    role_name.drop(bind, checkfirst=True)
