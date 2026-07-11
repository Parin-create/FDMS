"""User entity.

A user belongs to exactly one tenant (PRD §10, MT-1) and is identified by the
stable Entra object id (``oid`` claim). Users are JIT-provisioned on first sign-in
(PRD FR-AUTH-5). A single RBAC role is stored per user as the authorization
foundation; group→role mapping and resource-level permissions come later.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy import true as sa_true
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.role import RoleName

if TYPE_CHECKING:
    from app.models.tenant import Tenant


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("tenant_id", "entra_oid", name="uq_users_tenant_id_entra_oid"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE", name="fk_users_tenant_id_tenants"),
        nullable=False,
    )
    entra_oid: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        doc="Microsoft Entra user object id (stable per directory).",
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[RoleName] = mapped_column(
        SAEnum(
            RoleName,
            name="role_name",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        default=RoleName.VIEWER,
        server_default=RoleName.VIEWER.value,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=sa_true()
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="users")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<User id={self.id} email={self.email!r} role={self.role.value}>"
