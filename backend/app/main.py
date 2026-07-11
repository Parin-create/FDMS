"""FastAPI application entrypoint.

Wires together configuration, structured logging, correlation-ID middleware,
CORS, centralised error handling, and the versioned API router. The app is
stateless (ADR-009) so it can scale horizontally on Azure Container Apps.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.database import dispose_engine, engine
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import CorrelationIdMiddleware, register_timing_logger
from app.core.telemetry import init_telemetry, shutdown_telemetry
from app.services.blob_storage import close_storage_service

settings = get_settings()
logger = get_logger("app")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application startup/shutdown lifecycle.

    Logging and telemetry are initialised in ``create_app`` (so the telemetry
    log-export handler is attached exactly once, after logging is configured, and
    is never cleared by a second ``configure_logging`` call). Shutdown flushes
    telemetry, then closes storage and the DB engine.
    """
    logger.info(
        "application.startup",
        environment=settings.environment,
        app_name=settings.app_name,
    )
    yield
    shutdown_telemetry()
    await close_storage_service()
    await dispose_engine()
    logger.info("application.shutdown")


def create_app() -> FastAPI:
    """Application factory."""
    # Configure logging eagerly so import-time/startup logs are formatted too.
    configure_logging(level=settings.log_level, json_logs=settings.log_json)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        lifespan=lifespan,
    )

    # Middleware (outermost first): correlation ID -> request timing -> CORS.
    app.add_middleware(CorrelationIdMiddleware)
    app.middleware("http")(register_timing_logger(logger))
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Correlation-ID"],
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    # Initialise Application Insights AFTER logging is configured and the app is
    # built, so FastAPI/SQLAlchemy are instrumented and the log-export handler is
    # attached once. No-op (and never raises) when telemetry is inactive.
    init_telemetry(settings, app=app, engine=engine)

    return app


app = create_app()
