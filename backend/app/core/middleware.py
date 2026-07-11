"""HTTP middleware.

The correlation-ID middleware assigns (or honours an inbound) request identifier,
binds it to the logging context, and echoes it back on the response. This is the
foundation for tenant-aware, traceable observability (Architecture.md).
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable

from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core.context import set_correlation_id

CORRELATION_HEADER = "X-Correlation-ID"

# Type alias for an ASGI HTTP middleware handler registered via @app.middleware.
HttpMiddleware = Callable[[Request, Callable[[Request], Awaitable[Response]]], Awaitable[Response]]


class CorrelationIdMiddleware:
    """Pure-ASGI middleware that manages the request correlation ID."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:  # type: ignore[no-untyped-def]
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        correlation_id = request.headers.get(CORRELATION_HEADER) or uuid.uuid4().hex
        set_correlation_id(correlation_id)

        async def send_with_header(message):  # type: ignore[no-untyped-def]
            if message["type"] == "http.response.start":
                headers = message.setdefault("headers", [])
                headers.append(
                    (CORRELATION_HEADER.encode("latin-1"), correlation_id.encode("latin-1"))
                )
            await send(message)

        await self.app(scope, receive, send_with_header)


def register_timing_logger(logger) -> HttpMiddleware:  # type: ignore[no-untyped-def]
    """Build a ``@app.middleware('http')`` handler that logs request timing."""

    async def log_requests(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "request.completed",
            http_method=request.method,
            http_path=request.url.path,
            http_status=response.status_code,
            duration_ms=duration_ms,
        )
        return response

    return log_requests
