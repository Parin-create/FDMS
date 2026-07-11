# syntax=docker/dockerfile:1
# Production image for the FDMS FastAPI backend (Azure Container Apps / ACR).
# Multi-stage build with uv: dependencies are resolved into a venv in the builder
# stage; the runtime stage ships only the venv + app (no uv, no build tooling).

# Base image pinned by digest for REPRODUCIBLE builds (python:3.12-slim).
# Override with --build-arg PYTHON_IMAGE=... to bump; refresh the digest via:
#   docker buildx imagetools inspect python:3.12-slim
ARG PYTHON_IMAGE=python:3.12-slim@sha256:423ed6ab25b1921a477529254bfeeabf5855151dc2c3141699a1bfc852199fbf

# --- Builder: resolve and install production dependencies -------------------
FROM ${PYTHON_IMAGE} AS builder

# Pinned uv from its official image (kept out of the runtime image).
COPY --from=ghcr.io/astral-sh/uv:0.11.9 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Install dependencies first (cached layer) from the lockfile — production only.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Add the application and finalize the sync.
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# --- Runtime: minimal image with only what is needed to run -----------------
FROM ${PYTHON_IMAGE} AS runtime

# OCI image metadata. VERSION/VCS_REF/BUILD_DATE are injected at build time
# (see scripts/build-and-push.sh); the rest are static provenance labels.
ARG VERSION=0.0.0-dev
ARG VCS_REF=unknown
ARG BUILD_DATE=1970-01-01T00:00:00Z
ARG IMAGE_SOURCE=https://dev.azure.com/your-org/FDMS
ARG IMAGE_DOCS=https://dev.azure.com/your-org/FDMS/_wiki

LABEL org.opencontainers.image.title="fdms-backend" \
      org.opencontainers.image.description="FDMS backend API (FastAPI) for Azure Container Apps" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.vendor="FDMS" \
      org.opencontainers.image.licenses="Proprietary" \
      org.opencontainers.image.source="${IMAGE_SOURCE}" \
      org.opencontainers.image.documentation="${IMAGE_DOCS}" \
      org.opencontainers.image.base.name="docker.io/library/python:3.12-slim"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1 \
    # Production defaults (overridable by the platform environment).
    ENVIRONMENT=production \
    LOG_LEVEL=INFO \
    LOG_JSON=true \
    PORT=8000 \
    PATH="/app/.venv/bin:$PATH"

# CA certificates for outbound TLS (PostgreSQL verify-full, and any TLS not
# covered by certifi). Apt lists are removed to keep the image small.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Non-root, no-login system user (least privilege — recommended for ACA).
RUN useradd --create-home --uid 1000 --shell /usr/sbin/nologin appuser

WORKDIR /app

# Copy only the runtime artifacts (venv + app + migrations); no build manifests.
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appuser /app/app /app/app
COPY --from=builder --chown=appuser:appuser /app/alembic /app/alembic
COPY --from=builder --chown=appuser:appuser /app/alembic.ini /app/alembic.ini
COPY --chown=appuser:appuser scripts /app/scripts
RUN chmod +x /app/scripts/entrypoint.sh

USER appuser

# Documents the listening port; ACA ingress targetPort should match PORT.
EXPOSE 8000

# Container-level liveness (ACA also runs its own probes against /health/*).
HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
    CMD ["python", "-c", "import os,sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8000')+'/api/v1/health/live', timeout=3).status==200 else 1)"]

# ACA sends SIGTERM on scale-in/deploy; uvicorn (exec'd as PID 1) handles it for
# graceful shutdown (lifespan flushes telemetry, closes storage + DB engine).
STOPSIGNAL SIGTERM

ENTRYPOINT ["sh", "/app/scripts/entrypoint.sh"]
