"""Centralised exception handling.

Translates exceptions into the standard :class:`ErrorResponse` envelope, ensuring
the frontend always receives a predictable error shape and that every error
carries the correlation ID for traceability (Architecture.md, Observability).
"""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.context import get_correlation_id
from app.core.logging import get_logger
from app.schemas.error import ErrorDetail, ErrorResponse

logger = get_logger(__name__)


def _envelope(code: str, message: str) -> dict:
    return ErrorResponse(
        error=ErrorDetail(
            code=code,
            message=message,
            correlation_id=get_correlation_id(),
        )
    ).model_dump()


def register_exception_handlers(app: FastAPI) -> None:
    """Attach JSON error handlers to the application."""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        _request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(code=f"http_{exc.status_code}", message=str(exc.detail)),
            # Preserve response headers set on the exception (e.g. WWW-Authenticate).
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_envelope(
                code="validation_error",
                message="Request validation failed.",
            )
            | {"details": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        _request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception("unhandled_exception", error_type=type(exc).__name__)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_envelope(
                code="internal_server_error",
                message="An unexpected error occurred.",
            ),
        )
