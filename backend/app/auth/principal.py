"""The authenticated principal.

A :class:`Principal` is the resolved, FDMS-side identity for the current request —
the bridge between a validated Entra token and a provisioned FDMS user, carrying the
tenant binding and RBAC role used by authorization. This is the value injected into
request handlers via the current-principal dependency.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.models.role import RoleName
from app.schemas.auth import TokenClaims


@dataclass(frozen=True, slots=True)
class Principal:
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    tenant_name: str
    entra_oid: str
    email: str
    display_name: str
    role: RoleName
    claims: TokenClaims
