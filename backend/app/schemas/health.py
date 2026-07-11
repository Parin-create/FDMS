"""Schemas for the health/readiness endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class LivenessResponse(BaseModel):
    """Process is up and serving."""

    status: Literal["alive"] = "alive"
    service: str = Field(..., description="Service name.")
    version: str = Field(..., description="Service version.")
    environment: str = Field(..., description="Deployment environment.")


class ReadinessResponse(BaseModel):
    """Process is up AND its dependencies are reachable."""

    status: Literal["ready", "degraded"] = Field(..., description="Overall readiness.")
    database: Literal["ok", "error"] = Field(..., description="Database connectivity.")
