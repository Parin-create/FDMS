"""Request-scoped context.

Holds the correlation ID for the current request in a context variable so it can
be attached to every log record without threading it through call signatures.
Per Architecture.md (Observability), all telemetry carries a ``correlation_id``.
"""

from __future__ import annotations

from contextvars import ContextVar

#: Correlation ID for the in-flight request; empty string when out of request scope.
correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    """Return the correlation ID bound to the current context (may be empty)."""
    return correlation_id_ctx.get()


def set_correlation_id(value: str) -> None:
    """Bind a correlation ID to the current context."""
    correlation_id_ctx.set(value)
