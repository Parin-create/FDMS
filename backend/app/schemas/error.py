"""Standard error envelope returned by the API.

A single, predictable error shape across the API supports the API-first principle
(Architecture.md) and gives the frontend a consistent contract to handle failures.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str = Field(..., description="Stable, machine-readable error code.")
    message: str = Field(..., description="Human-readable error message.")
    correlation_id: str = Field(
        default="",
        description="Correlation ID for tracing this request across logs.",
    )


class ErrorResponse(BaseModel):
    error: ErrorDetail
