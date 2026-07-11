#!/usr/bin/env sh
# Container entrypoint for the FDMS backend.
#
# Migrations are OPT-IN via RUN_MIGRATIONS=true. On Azure Container Apps, replicas
# scale horizontally, so running "alembic upgrade head" in every replica would race.
# Recommended: run migrations once as a dedicated ACA Job / pre-deploy step
# (RUN_MIGRATIONS=true) and keep serving replicas with RUN_MIGRATIONS unset.
# Locally (docker-compose) it is set to true so the schema is applied on startup.
#
# uvicorn is exec'd so it becomes PID 1 and receives SIGTERM directly for a
# graceful shutdown. alembic/uvicorn resolve from the uv venv on PATH.
set -eu

PORT="${PORT:-8000}"

if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
    echo "[entrypoint] Applying database migrations (alembic upgrade head)..."
    alembic upgrade head
fi

echo "[entrypoint] Starting FDMS API on 0.0.0.0:${PORT}..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT}" \
    --proxy-headers \
    --forwarded-allow-ips="*"
