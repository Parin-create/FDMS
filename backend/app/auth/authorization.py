"""Authorization helpers (RBAC foundation, default-deny per PRD §11 / RBAC-2).

Dependency factories that gate endpoints by role. These operate on the resolved
:class:`Principal` and the role hierarchy. Document/resource-level permissions are
intentionally NOT implemented in Sprint 1 — this is the role-based foundation only.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Depends, HTTPException, status

from app.auth.dependencies import get_current_principal
from app.auth.principal import Principal
from app.models.role import RoleName, role_at_least

PrincipalDependency = Callable[..., Awaitable[Principal]]


def require_role(minimum: RoleName) -> PrincipalDependency:
    """Require the principal's role to be at least ``minimum`` in the hierarchy."""

    async def _dependency(
        principal: Principal = Depends(get_current_principal),
    ) -> Principal:
        if not role_at_least(principal.role, minimum):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role '{minimum.value}' or higher.",
            )
        return principal

    return _dependency


def require_any_role(*allowed: RoleName) -> PrincipalDependency:
    """Require the principal's role to be one of ``allowed`` exactly."""
    allowed_set = set(allowed)

    async def _dependency(
        principal: Principal = Depends(get_current_principal),
    ) -> Principal:
        if principal.role not in allowed_set:
            names = ", ".join(role.value for role in allowed)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {names}.",
            )
        return principal

    return _dependency


# Convenience, pre-built dependencies for common thresholds.
require_tenant_admin = require_role(RoleName.TENANT_ADMIN)
require_manager = require_role(RoleName.MANAGER)
require_contributor = require_role(RoleName.CONTRIBUTOR)
require_viewer = require_role(RoleName.VIEWER)
