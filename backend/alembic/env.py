"""Alembic migration environment (async).

Uses the application's :class:`Settings` for the database URL and the project's
``Base.metadata`` as the autogenerate target, keeping migrations consistent with
the running application (ADR-002). Runs in async mode against asyncpg.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

# Import the model metadata. Importing the package registers all models on
# Base.metadata for autogenerate.
import app.models  # noqa: F401
from app.core.config import get_settings
from app.core.database import build_connect_args
from app.models.base import Base

settings = get_settings()
config = context.config

# Record the (masked) target for logging / offline SQL generation. The live
# connection is created from the Settings URL object below so credentials are
# never written into alembic's in-memory config.
config.set_main_option("sqlalchemy.url", settings.database_url_safe)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL without a DBAPI connection)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode using an async engine.

    Uses the Settings URL object and the shared asyncpg connect args so
    migrations connect to Azure PostgreSQL over TLS exactly like the app.
    ``NullPool`` avoids holding connections open for the short-lived migration
    process.
    """
    connectable = create_async_engine(
        settings.sqlalchemy_url,
        poolclass=pool.NullPool,
        connect_args=build_connect_args(settings),
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
