"""Authentication-related schemas."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TokenClaims(BaseModel):
    """Validated, normalized claims extracted from an Entra access token."""

    model_config = ConfigDict(frozen=True)

    subject: str = Field(..., description="Token subject (sub).")
    object_id: str = Field(..., description="Entra user object id (oid).")
    directory_tenant_id: str = Field(..., description="Entra directory id (tid).")
    email: str = Field(default="", description="User email / UPN.")
    name: str = Field(default="", description="User display name.")
    issuer: str = Field(..., description="Token issuer (iss).")
    scopes: list[str] = Field(default_factory=list, description="Delegated scopes (scp).")
    raw: dict[str, Any] = Field(default_factory=dict, exclude=True, repr=False)


class CurrentUserResponse(BaseModel):
    """The authenticated, provisioned FDMS user."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    tenant_name: str
    email: str
    display_name: str
    role: str
    is_active: bool
