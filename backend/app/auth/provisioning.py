"""User provisioning service (Just-In-Time, per PRD FR-AUTH-5).

On first sign-in, resolves the caller's Entra directory to an FDMS tenant and
creates the FDMS user with the default least-privilege role. On subsequent
sign-ins it updates lightweight profile fields and the last-login timestamp.

Tenant auto-creation is gated by ``auth_auto_provision_tenant``; full tenant
lifecycle/admin is Sprint 2. RLS enforcement is also Sprint 2 — this service
filters by ``tenant_id`` explicitly in the meantime.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.principal import Principal
from app.core.config import get_settings
from app.models.role import RoleName
from app.models.tenant import Tenant, TenantStatus
from app.models.user import User
from app.schemas.auth import TokenClaims

logger = logging.getLogger(__name__)


class ProvisioningError(Exception):
    """Base class for provisioning failures (mapped to HTTP 403)."""

    code = "provisioning_error"


class TenantNotProvisionedError(ProvisioningError):
    code = "tenant_not_provisioned"


class TenantSuspendedError(ProvisioningError):
    code = "tenant_suspended"


class UserInactiveError(ProvisioningError):
    code = "user_inactive"


class UserProvisioningService:
    """Resolves a validated token into a provisioned :class:`Principal`."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._settings = get_settings()

    async def resolve(self, claims: TokenClaims) -> Principal:
        tenant = await self._get_or_create_tenant(claims)
        if tenant.status is TenantStatus.SUSPENDED:
            raise TenantSuspendedError("tenant is suspended")

        user = await self._get_or_create_user(tenant, claims)
        if not user.is_active:
            raise UserInactiveError("user account is disabled")

        await self._db.commit()
        await self._db.refresh(user)

        return Principal(
            user_id=user.id,
            tenant_id=tenant.id,
            tenant_name=tenant.name,
            entra_oid=user.entra_oid,
            email=user.email,
            display_name=user.display_name,
            role=user.role,
            claims=claims,
        )

    async def _get_or_create_tenant(self, claims: TokenClaims) -> Tenant:
        result = await self._db.execute(
            select(Tenant).where(Tenant.entra_tenant_id == claims.directory_tenant_id)
        )
        tenant = result.scalar_one_or_none()
        if tenant is not None:
            return tenant

        if not self._settings.auth_auto_provision_tenant:
            raise TenantNotProvisionedError(
                "no FDMS tenant is registered for this directory"
            )

        tenant = Tenant(
            name=claims.directory_tenant_id,
            entra_tenant_id=claims.directory_tenant_id,
            status=TenantStatus.ACTIVE,
        )
        self._db.add(tenant)
        await self._db.flush()
        logger.info("provisioning.tenant_created", extra={"tenant_id": str(tenant.id)})
        return tenant

    async def _get_or_create_user(self, tenant: Tenant, claims: TokenClaims) -> User:
        result = await self._db.execute(
            select(User).where(
                User.tenant_id == tenant.id,
                User.entra_oid == claims.object_id,
            )
        )
        user = result.scalar_one_or_none()
        now = datetime.now(tz=timezone.utc)

        if user is None:
            user = User(
                tenant_id=tenant.id,
                entra_oid=claims.object_id,
                email=claims.email,
                display_name=claims.name or claims.email,
                role=self._default_role(),
                is_active=True,
                last_login_at=now,
            )
            self._db.add(user)
            await self._db.flush()
            logger.info(
                "provisioning.user_created",
                extra={"tenant_id": str(tenant.id), "user_id": str(user.id)},
            )
            return user

        # Existing user: sync lightweight profile fields + last login.
        user.last_login_at = now
        if claims.email and user.email != claims.email:
            user.email = claims.email
        if claims.name and user.display_name != claims.name:
            user.display_name = claims.name
        return user

    def _default_role(self) -> RoleName:
        return RoleName(self._settings.auth_default_role)
