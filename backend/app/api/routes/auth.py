"""Authentication API endpoints.

- ``GET  /auth/me``     — the authenticated, JIT-provisioned FDMS user.
- ``POST /auth/logout`` — stateless acknowledgement; actual sign-out and token
  revocation happen at Entra ID via the client (MSAL). The endpoint exists as the
  server-side hook for future audit logging (Sprint 8).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from app.auth.dependencies import get_current_principal
from app.auth.principal import Principal
from app.schemas.auth import CurrentUserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=CurrentUserResponse, summary="Current user")
async def read_current_user(
    principal: Principal = Depends(get_current_principal),
) -> CurrentUserResponse:
    return CurrentUserResponse(
        id=principal.user_id,
        tenant_id=principal.tenant_id,
        tenant_name=principal.tenant_name,
        email=principal.email,
        display_name=principal.display_name,
        role=principal.role.value,
        is_active=True,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout (stateless acknowledgement)",
)
async def logout(_principal: Principal = Depends(get_current_principal)) -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)
