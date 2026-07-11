"""Aggregate API router for the versioned API surface."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import auth, debug, files, health

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(files.router)
# TEMPORARY: deployment-debug endpoint — remove after diagnosing DB auth.
api_router.include_router(debug.router)
