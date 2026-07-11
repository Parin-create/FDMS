"""Secure JWT validation for Microsoft Entra ID access tokens.

Validates tokens at the API boundary (Architecture.md §7): RS256 signature via the
directory's JWKS, plus audience, expiry, and issuer checks. The issuer is verified
against the token's own ``tid`` so multi-tenant tokens are accepted only when their
issuer is internally consistent; single-tenant deployments additionally pin ``tid``.

No secrets are involved — validation relies solely on Entra's public signing keys.
"""

from __future__ import annotations

import logging
from functools import lru_cache

import jwt
from jwt import PyJWKClient

from app.core.config import Settings, get_settings
from app.schemas.auth import TokenClaims

logger = logging.getLogger(__name__)

_ALGORITHMS = ["RS256"]


class TokenValidationError(Exception):
    """Raised when an access token fails validation."""


class TokenValidator:
    """Validates Entra access tokens against the directory's published JWKS."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        # PyJWKClient caches signing keys after first fetch (key rotation safe).
        self._jwks_client = PyJWKClient(settings.entra_jwks_uri, cache_keys=True)

    def validate(self, token: str) -> TokenClaims:
        """Validate ``token`` and return normalized claims, or raise."""
        try:
            signing_key = self._jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=_ALGORITHMS,
                audience=self._settings.expected_audience,
                options={"require": ["exp", "iss", "aud", "sub"]},
            )
        except jwt.PyJWTError as exc:
            raise TokenValidationError(f"token decode failed: {exc}") from exc
        except Exception as exc:  # network/JWKS errors
            logger.exception("jwt.jwks_error")
            raise TokenValidationError("unable to retrieve signing keys") from exc

        directory_tenant_id = payload.get("tid")
        object_id = payload.get("oid")
        if not directory_tenant_id or not object_id:
            raise TokenValidationError("token missing required 'tid'/'oid' claims")

        # Issuer must match the token's own directory (defends against token swap).
        expected_issuer = f"https://login.microsoftonline.com/{directory_tenant_id}/v2.0"
        if payload.get("iss") != expected_issuer:
            raise TokenValidationError("issuer does not match token tenant")

        # Single-tenant deployments only accept their configured directory.
        if (
            self._settings.is_single_tenant
            and directory_tenant_id.lower() != self._settings.entra_tenant_id.lower()
        ):
            raise TokenValidationError("token issued by a non-permitted directory")

        email = payload.get("email") or payload.get("preferred_username") or ""
        name = payload.get("name") or email
        scopes = payload.get("scp", "")

        return TokenClaims(
            subject=str(payload["sub"]),
            object_id=str(object_id),
            directory_tenant_id=str(directory_tenant_id),
            email=str(email),
            name=str(name),
            issuer=str(payload["iss"]),
            scopes=scopes.split() if isinstance(scopes, str) else list(scopes),
            raw=payload,
        )


@lru_cache(maxsize=1)
def get_token_validator() -> TokenValidator:
    """Return the process-wide token validator (keys cached internally)."""
    return TokenValidator(get_settings())
