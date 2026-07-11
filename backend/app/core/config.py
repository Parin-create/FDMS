"""Application configuration.

Settings are loaded from environment variables (and an optional ``.env`` file)
using Pydantic Settings, giving us validated, type-safe configuration. No secret
is ever hard-coded; per ADR-005 / Architecture.md secrets are supplied by the
environment (Key Vault + managed identity in Azure, ``.env`` locally).
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import (
    BaseSettings,
    NoDecode,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)
from sqlalchemy.engine import URL

from app.core.keyvault import KeyVaultSettingsSource

# libpq-compatible SSL modes accepted by asyncpg.
SslMode = Literal["disable", "allow", "prefer", "require", "verify-ca", "verify-full"]

Environment = Literal["local", "development", "staging", "production"]


class Settings(BaseSettings):
    """Strongly-typed application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Insert Key Vault below env/.env.

        Precedence (highest first): init args > environment > ``.env`` > Key Vault >
        file secrets. Explicit environment values therefore always win (useful for
        local overrides and backward compatibility); Key Vault fills in secrets not
        provided by the environment, which is the normal case in Azure.
        """
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            KeyVaultSettingsSource(settings_cls),
            file_secret_settings,
        )

    # --- Application -------------------------------------------------------
    app_name: str = "FDMS API"
    environment: Environment = "local"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # --- Logging -----------------------------------------------------------
    log_level: str = "INFO"
    # Emit structured JSON logs (true) or human-readable logs (false, useful in dev).
    log_json: bool = True

    # --- Database (Azure PostgreSQL Flexible Server, async via asyncpg) -----
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "fdms"
    postgres_password: str = "fdms"
    postgres_db: str = "fdms"
    # TLS mode. Azure Flexible Server requires encryption in transit — use
    # "require" (encrypt) or "verify-full" (encrypt + validate cert/hostname,
    # recommended for production with POSTGRES_SSL_ROOT_CERT set). Default
    # "prefer" negotiates TLS when available and still works against a local,
    # non-TLS PostgreSQL for development.
    postgres_sslmode: SslMode = "prefer"
    # Optional path to a CA bundle (PEM) for "verify-ca" / "verify-full".
    postgres_ssl_root_cert: str = ""
    db_echo: bool = False
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30
    # Recycle pooled connections before Azure's idle-timeout / gateway drops
    # them (seconds). Prevents "connection was closed" errors on reuse.
    db_pool_recycle: int = 1800
    # Connection establishment timeout (seconds).
    db_connect_timeout: int = 10

    # --- Observability: Azure Application Insights (OpenTelemetry) ----------
    # Connection string drives Azure Monitor export. From .env locally, from Key
    # Vault in Azure. Empty => telemetry is inactive (safe no-op).
    applicationinsights_connection_string: str = ""
    # Master switch so telemetry can be disabled even when a connection string is
    # present (e.g. troubleshooting).
    telemetry_enabled: bool = True

    # --- Azure Key Vault (secret retrieval) --------------------------------
    # Vault URI, e.g. https://<vault-name>.vault.azure.net. Empty locally (config
    # comes from .env); set in Azure to fetch secrets via managed identity. Never
    # hard-coded — always sourced from the environment.
    key_vault_url: str = ""

    # --- Azure Blob Storage ------------------------------------------------
    # Connection string is the primary auth path (secret): from .env locally, from
    # Key Vault in Azure. Optionally, an account URL enables managed-identity auth.
    azure_storage_connection_string: str = ""
    azure_storage_account_url: str = ""
    # Configurable container names (the account already provisions these).
    blob_container_documents: str = "documents"
    blob_container_thumbnails: str = "thumbnails"
    blob_container_temp: str = "temp"
    # Transient-failure retry attempts (SDK applies exponential backoff).
    azure_storage_max_retries: int = 3

    # --- CORS --------------------------------------------------------------
    # Accepts a comma-separated string or a JSON array via the environment.
    # ``NoDecode`` disables pydantic-settings' source-level JSON decoding so the
    # raw env string reaches the validator below (a bare "http://host" is not JSON).
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> object:
        """Parse ``CORS_ORIGINS`` from a comma-separated string or JSON array."""
        if isinstance(value, str):
            text = value.strip()
            if text.startswith("["):
                return json.loads(text)
            return [origin.strip() for origin in text.split(",") if origin.strip()]
        return value

    # --- Authentication (Microsoft Entra ID, per ADR-005) ------------------
    # Directory (tenant) GUID for single-tenant deployments, or "organizations"
    # / "common" for multi-tenant federation (Architecture.md §7).
    entra_tenant_id: str = ""
    # Client (application) ID of the *API* app registration — the token audience.
    entra_client_id: str = ""
    # Optional explicit audience override (e.g. "api://<client-id>"). Falls back
    # to ``entra_client_id`` when empty.
    entra_api_audience: str = ""
    # Default RBAC role assigned to JIT-provisioned users (least privilege).
    auth_default_role: str = "Viewer"
    # When a sign-in arrives from an unknown directory, auto-create the tenant
    # record. Full tenant lifecycle/admin is Sprint 2; this enables JIT in dev.
    auth_auto_provision_tenant: bool = True

    @field_validator("auth_default_role")
    @classmethod
    def _validate_default_role(cls, value: str) -> str:
        allowed = {"TenantAdmin", "Manager", "Contributor", "Viewer", "Guest"}
        if value not in allowed:
            raise ValueError(f"auth_default_role must be one of {sorted(allowed)}")
        return value

    @property
    def entra_authority(self) -> str:
        """OIDC authority URL for the configured directory."""
        tenant = self.entra_tenant_id or "organizations"
        return f"https://login.microsoftonline.com/{tenant}"

    @property
    def entra_jwks_uri(self) -> str:
        """JWKS (signing keys) endpoint for v2.0 tokens."""
        return f"{self.entra_authority}/discovery/v2.0/keys"

    @property
    def expected_audience(self) -> str:
        """Audience (``aud``) the API will accept on access tokens."""
        return self.entra_api_audience or self.entra_client_id

    @property
    def auth_configured(self) -> bool:
        """True when the minimum Entra settings are present."""
        return bool(self.entra_client_id)

    @property
    def is_single_tenant(self) -> bool:
        """True when locked to a specific directory GUID."""
        return self.entra_tenant_id.lower() not in {"", "common", "organizations", "consumers"}

    @property
    def sqlalchemy_url(self) -> URL:
        """Async SQLAlchemy/asyncpg connection URL (credentials safely encoded).

        Built with :meth:`URL.create` so special characters in an
        Azure-generated password are correctly escaped. TLS is configured via
        ``connect_args`` (see ``app.core.database``), not query parameters.
        """
        return URL.create(
            "postgresql+asyncpg",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )

    @property
    def database_url(self) -> str:
        """Rendered connection URL string (includes password; do not log)."""
        return self.sqlalchemy_url.render_as_string(hide_password=False)

    @property
    def database_url_safe(self) -> str:
        """Connection URL with the password masked — safe for logging."""
        return self.sqlalchemy_url.render_as_string(hide_password=True)

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def key_vault_enabled(self) -> bool:
        """True when Key Vault secret retrieval is active for this process."""
        return bool(self.key_vault_url)

    @property
    def telemetry_active(self) -> bool:
        """True when Application Insights telemetry should be initialised."""
        return self.telemetry_enabled and bool(self.applicationinsights_connection_string)

    @property
    def storage_configured(self) -> bool:
        """True when Blob Storage credentials are available."""
        return bool(self.azure_storage_connection_string or self.azure_storage_account_url)

    @property
    def blob_containers(self) -> dict[str, str]:
        """Logical container name -> configured actual container name."""
        return {
            "documents": self.blob_container_documents,
            "thumbnails": self.blob_container_thumbnails,
            "temp": self.blob_container_temp,
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton of the application settings."""
    return Settings()
