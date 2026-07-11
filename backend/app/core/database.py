"""Database connection layer.

Async SQLAlchemy 2.x engine + session factory backed by **Azure PostgreSQL
Flexible Server** (asyncpg), per ADR-002 (PostgreSQL) and ADR-003 (async FastAPI).

Production concerns handled here:
- **TLS in transit** — Azure Flexible Server requires encrypted connections; the
  SSL behaviour is driven by ``POSTGRES_SSLMODE`` (+ optional CA bundle).
- **Connection pooling** — bounded pool with ``pool_pre_ping`` and ``pool_recycle``
  so connections dropped by Azure's idle timeout are transparently replaced.
- **Diagnostics** — an ``application_name`` is set so FDMS is identifiable in
  ``pg_stat_activity`` and Azure metrics.

All connection settings come from the environment (ADR-005); nothing is hard-coded.

Note: the row-level-security session context (``app.tenant_id``) is intentionally
NOT wired here — that is Sprint 2 / ADR-006 work.
"""

from __future__ import annotations

import ssl
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings, get_settings

settings = get_settings()


def _build_ssl(config: Settings) -> ssl.SSLContext | str | bool:
    """Translate ``POSTGRES_SSLMODE`` into an asyncpg ``ssl`` argument.

    - ``disable``                 -> ``False`` (no TLS; local dev only).
    - custom CA + verify mode     -> an :class:`ssl.SSLContext`.
    - any other mode w/o a CA     -> the libpq sslmode string, which asyncpg
      interprets using the system trust store (Azure's roots are included).
    """
    mode = config.postgres_sslmode.lower()

    if mode == "disable":
        return False

    if config.postgres_ssl_root_cert:
        context = ssl.create_default_context(cafile=config.postgres_ssl_root_cert)
        if mode == "verify-full":
            context.check_hostname = True
            context.verify_mode = ssl.CERT_REQUIRED
        elif mode == "verify-ca":
            context.check_hostname = False
            context.verify_mode = ssl.CERT_REQUIRED
        else:
            # A CA was supplied but the mode does not request verification:
            # encrypt without strict validation.
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        return context

    # No custom CA — let asyncpg build the context from the sslmode string,
    # validating (for verify-*) against the OS trust store.
    return mode


def build_connect_args(config: Settings | None = None) -> dict[str, Any]:
    """asyncpg connect arguments shared by the app engine and Alembic.

    Centralising this guarantees migrations connect to Azure with the same TLS
    and identification settings as the running application.
    """
    config = config or settings
    return {
        "ssl": _build_ssl(config),
        "timeout": config.db_connect_timeout,
        "server_settings": {"application_name": config.app_name},
    }


engine: AsyncEngine = create_async_engine(
    settings.sqlalchemy_url,
    echo=settings.db_echo,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
    pool_recycle=settings.db_pool_recycle,
    pool_pre_ping=True,
    connect_args=build_connect_args(settings),
)

SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a transactional async session."""
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def dispose_engine() -> None:
    """Dispose the engine's connection pool (call on application shutdown)."""
    await engine.dispose()
