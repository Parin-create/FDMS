"""FastAPI authentication dependencies.

Chain: extract bearer token -> validate (JWKS, off the event loop) -> resolve/
provision the FDMS user -> :class:`Principal`. These are the building blocks every
protected endpoint depends on. Authorization (role checks) lives in
``authorization.py`` and builds on ``get_current_principal``.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import TokenValidationError, get_token_validator
from app.auth.principal import Principal
from app.auth.provisioning import ProvisioningError, UserProvisioningService
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.schemas.auth import TokenClaims

_bearer_scheme = HTTPBearer(auto_error=False, description="Entra ID access token")
_UNAUTHENTICATED_HEADERS = {"WWW-Authenticate": "Bearer"}


async def get_token_claims(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> TokenClaims:
    """Validate the bearer token and return its normalized claims."""
    if not settings.auth_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured on this server.",
        )

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header.",
            headers=_UNAUTHENTICATED_HEADERS,
        )

    validator = get_token_validator()
    try:
        # JWKS lookup / crypto is synchronous; keep it off the event loop.
        return await run_in_threadpool(validator.validate, credentials.credentials)
    except TokenValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers=_UNAUTHENTICATED_HEADERS,
        ) from exc


async def get_current_principal(
    claims: TokenClaims = Depends(get_token_claims),
    db: AsyncSession = Depends(get_db),
) -> Principal:
    """Resolve (and JIT-provision) the FDMS user for the validated token."""
    service = UserProvisioningService(db)
    try:
        return await service.resolve(claims)
    except ProvisioningError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc) or "Access denied.",
        ) from exc
