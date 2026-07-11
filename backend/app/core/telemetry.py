"""Azure Application Insights telemetry via OpenTelemetry.

Uses the official **Azure Monitor OpenTelemetry** distro (``configure_azure_monitor``)
as the export pipeline and OpenTelemetry as the instrumentation layer. On init this
wires up, for Application Insights:

- **Distributed tracing** + W3C trace-context propagation (request correlation).
- **Request tracing** — FastAPI server spans (via ``FastAPIInstrumentor``).
- **Dependency tracing** — SQLAlchemy DB spans, Azure SDK (Blob/Key Vault) spans, and
  outbound HTTP (requests/urllib) — the latter auto-enabled by the distro.
- **Exception tracking** — recorded on failed spans and via the log-export pipeline
  (our existing ``logger.exception(...)`` calls surface in the exceptions table).
- **Performance metrics** — HTTP server/duration metrics emitted by the instrumentors.
- **Log integration** — the distro attaches a log-export handler to the root logger,
  so existing structured (structlog) logs are *also* exported, without replacing the
  stdout handler.

Design (Azure Well-Architected):
- **Reliability:** every step is wrapped so a telemetry failure never crashes the app.
- **Operational excellence:** environment-driven enable/disable; nothing hard-coded.
- **Cost/perf:** inactive by default unless a connection string is present.
"""

from __future__ import annotations

from typing import Any

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_initialized = False


def init_telemetry(settings: Settings, *, app: Any = None, engine: Any = None) -> bool:
    """Initialise Application Insights telemetry. Returns True if activated.

    Idempotent and safe: if telemetry is disabled or any step fails, the function
    logs and returns without raising (requirement: telemetry must never crash the app).
    """
    global _initialized
    if _initialized:
        return True

    if not settings.telemetry_active:
        logger.info(
            "telemetry.disabled",
            enabled=settings.telemetry_enabled,
            connection_string_present=bool(settings.applicationinsights_connection_string),
        )
        return False

    try:
        from azure.monitor.opentelemetry import configure_azure_monitor
        from opentelemetry.sdk.resources import Resource

        configure_azure_monitor(
            connection_string=settings.applicationinsights_connection_string,
            resource=Resource.create(
                {
                    "service.name": settings.app_name,
                    "service.namespace": "fdms",
                    "deployment.environment": settings.environment,
                }
            ),
        )
    except Exception:
        logger.exception("telemetry.configure_failed")
        return False

    # SQLAlchemy: instrument the async engine's underlying sync engine.
    if engine is not None:
        try:
            from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

            SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
        except Exception:
            logger.exception("telemetry.sqlalchemy_instrument_failed")

    # FastAPI: instrument the concrete app instance (deterministic, no double-hook).
    if app is not None:
        try:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

            FastAPIInstrumentor.instrument_app(app)
        except Exception:
            logger.exception("telemetry.fastapi_instrument_failed")

    _initialized = True
    logger.info(
        "telemetry.initialised",
        service_name=settings.app_name,
        environment=settings.environment,
    )
    return True


def _flush_provider(provider: Any) -> None:
    for method in ("force_flush", "shutdown"):
        fn = getattr(provider, method, None)
        if callable(fn):
            fn()


def shutdown_telemetry() -> None:
    """Flush and shut down telemetry providers on application shutdown."""
    global _initialized
    if not _initialized:
        return

    try:
        from opentelemetry import metrics, trace
        from opentelemetry._logs import get_logger_provider

        _flush_provider(trace.get_tracer_provider())
        _flush_provider(get_logger_provider())
        _flush_provider(metrics.get_meter_provider())
    except Exception:
        logger.exception("telemetry.shutdown_failed")

    _initialized = False
    logger.info("telemetry.shutdown")
