"""Tenant entity.

Represents a customer organization (PRD §10). Each tenant maps 1:1 to a Microsoft
Entra directory via ``entra_tenant_id`` (the directory/``tid`` claim). Row-Level
Security and full tenant lifecycle management are Sprint 2 concerns; Sprint 1 only
establishes the entity and JIT creation during sign-in.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class TenantStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class Tenant(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    entra_tenant_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        doc="Microsoft Entra directory (tenant) GUID.",
    )
    status: Mapped[TenantStatus] = mapped_column(
        SAEnum(
            TenantStatus,
            name="tenant_status",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        default=TenantStatus.ACTIVE,
        server_default=TenantStatus.ACTIVE.value,
    )

    users: Mapped[list["User"]] = relationship(
        back_populates="tenant",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Tenant id={self.id} name={self.name!r}>"
