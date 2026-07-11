"""RBAC role definitions and hierarchy.

The standard role set (PRD §11). This is the *authorization foundation* only —
document/resource-level permissions are introduced in later sprints. Roles are an
ordered hierarchy so authorization checks can express "at least Manager", etc.
Custom tenant-defined roles (FR-RBAC-5) are out of scope for Sprint 1.
"""

from __future__ import annotations

from enum import Enum


class RoleName(str, Enum):
    """Canonical RBAC roles, ordered least → most privileged by hierarchy below."""

    TENANT_ADMIN = "TenantAdmin"
    MANAGER = "Manager"
    CONTRIBUTOR = "Contributor"
    VIEWER = "Viewer"
    GUEST = "Guest"


#: Numeric rank for each role; higher means more privileged.
ROLE_HIERARCHY: dict[RoleName, int] = {
    RoleName.GUEST: 0,
    RoleName.VIEWER: 1,
    RoleName.CONTRIBUTOR: 2,
    RoleName.MANAGER: 3,
    RoleName.TENANT_ADMIN: 4,
}


def role_at_least(role: RoleName, minimum: RoleName) -> bool:
    """Return True if ``role`` meets or exceeds ``minimum`` in the hierarchy."""
    return ROLE_HIERARCHY[role] >= ROLE_HIERARCHY[minimum]
