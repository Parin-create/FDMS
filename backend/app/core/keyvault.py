"""Azure Key Vault integration.

Retrieves secrets via the Azure SDK using ``DefaultAzureCredential`` and exposes a
Pydantic Settings **source** so secrets flow into :class:`~app.core.config.Settings`
transparently — no call site needs to know whether a value came from Key Vault or
the environment.

Behaviour (Azure Well-Architected: Security + Operational Excellence):
- **Local development:** ``KEY_VAULT_URL`` is unset → the source is inactive and all
  configuration comes from ``.env`` (fully backward compatible).
- **Azure deployment:** ``KEY_VAULT_URL`` is set → secrets are fetched from Key Vault
  using the Container App's managed identity and cached for the process lifetime.

Best practices applied:
- A single ``DefaultAzureCredential`` and one ``SecretClient`` per vault (reused).
- In-memory caching, including **negative caching**, so a given secret is fetched at
  most once — no repeated Key Vault API calls (the settings singleton is built once).
- Structured logging of lifecycle/outcomes; **secret values are never logged**.
- The Azure SDK is imported lazily so the package is only touched when Key Vault is
  actually used.
"""

from __future__ import annotations

import os
from typing import Any

from pydantic.fields import FieldInfo
from pydantic_settings import PydanticBaseSettingsSource

from app.core.logging import get_logger

logger = get_logger(__name__)

#: Environment variable holding the vault URI (never hard-coded).
KEY_VAULT_URL_ENV = "KEY_VAULT_URL"

# Settings field name -> Key Vault secret name. Values MUST match the secrets that
# exist in Azure Key Vault exactly. FDMS secrets are canonically prefixed "fdms-"
# and use hyphens (Key Vault names allow only [0-9a-zA-Z-]). Extend this map as new
# secrets are introduced, keeping the "fdms-" prefix.
SECRET_FIELD_TO_KV_NAME: dict[str, str] = {
    "postgres_password": "fdms-postgres-password",
    "azure_storage_connection_string": "fdms-storage-connection-string",
    "applicationinsights_connection_string": "fdms-appinsights-connection-string",
}

# Process-lifetime singletons + cache.
_credential: Any = None
_clients: dict[str, Any] = {}
_secret_cache: dict[tuple[str, str], str | None] = {}


def is_configured() -> bool:
    """True when a Key Vault URL is present in the environment."""
    return bool(os.environ.get(KEY_VAULT_URL_ENV, "").strip())


def _get_credential() -> Any:
    """Lazily create and reuse a single ``DefaultAzureCredential``."""
    global _credential
    if _credential is None:
        from azure.identity import DefaultAzureCredential

        _credential = DefaultAzureCredential()
        logger.info("keyvault.credential_initialised")
    return _credential


def _get_client(vault_url: str) -> Any:
    """Lazily create and reuse one ``SecretClient`` per vault URL."""
    client = _clients.get(vault_url)
    if client is None:
        from azure.keyvault.secrets import SecretClient

        client = SecretClient(vault_url=vault_url, credential=_get_credential())
        _clients[vault_url] = client
        logger.info("keyvault.client_initialised", vault_url=vault_url)
    return client


def get_secret(vault_url: str, secret_name: str) -> str | None:
    """Return a secret's value, cached after the first retrieval.

    Returns ``None`` (and caches it) when the secret does not exist, so callers can
    fall back to other configuration sources. Unexpected errors (auth/transport) are
    logged and re-raised — a misconfigured vault should fail fast, not silently.
    """
    cache_key = (vault_url, secret_name)
    if cache_key in _secret_cache:
        return _secret_cache[cache_key]

    from azure.core.exceptions import ResourceNotFoundError

    try:
        secret = _get_client(vault_url).get_secret(secret_name)
        value: str | None = secret.value
        logger.info("keyvault.secret_loaded", secret_name=secret_name)
    except ResourceNotFoundError:
        value = None
        logger.warning("keyvault.secret_not_found", secret_name=secret_name)
    except Exception:
        logger.exception("keyvault.fetch_failed", secret_name=secret_name)
        raise

    _secret_cache[cache_key] = value
    return value


def clear_cache() -> None:
    """Clear cached secrets and clients (primarily for tests)."""
    _secret_cache.clear()
    _clients.clear()


class KeyVaultSettingsSource(PydanticBaseSettingsSource):
    """Pydantic Settings source that resolves known secret fields from Key Vault.

    Only fields listed in :data:`SECRET_FIELD_TO_KV_NAME` are queried, so the number
    of Key Vault calls is bounded and predictable. Inactive (returns ``{}``) when
    ``KEY_VAULT_URL`` is not set.
    """

    def __init__(self, settings_cls: type) -> None:
        super().__init__(settings_cls)
        self._vault_url = os.environ.get(KEY_VAULT_URL_ENV, "").strip()

    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        # Values are produced in __call__; this abstract method is required but unused.
        return None, field_name, False

    def __call__(self) -> dict[str, Any]:
        if not self._vault_url:
            return {}

        resolved: dict[str, Any] = {}
        for field_name, secret_name in SECRET_FIELD_TO_KV_NAME.items():
            if field_name not in self.settings_cls.model_fields:
                continue
            value = get_secret(self._vault_url, secret_name)
            if value is not None:
                resolved[field_name] = value

        logger.info(
            "keyvault.settings_source_evaluated",
            vault_configured=True,
            fields_loaded=sorted(resolved.keys()),
        )
        return resolved
