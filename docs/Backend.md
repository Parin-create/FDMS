# FDMS — Backend Foundation

| Field | Value |
|---|---|
| **Document** | Backend Foundation (Sprint 1) |
| **Version** | 1.0 |
| **Status** | Implemented |
| **Source of Truth** | [PRD](PRD.md) · [Architecture](Architecture.md) · [ADRs](ADRs.md) · [Sprint Plan](SprintPlan.md) |
| **Last Updated** | 2026-06-23 |
| **Scope** | Backend only. No frontend, no deployment (Azure/CI) code. |

This document describes the FastAPI backend **foundation**: configuration, database, logging, health, Docker, environment, and the dependency-injection pattern. It reflects the `uv`-managed toolchain (`pyproject.toml` + `uv.lock`) and structlog-based logging.

---

## 1. Toolchain & Dependency Management

Dependencies are managed with **[uv](https://docs.astral.sh/uv/)**. The single source of truth is `pyproject.toml` (runtime deps under `[project].dependencies`, tooling under `[dependency-groups].dev`) pinned by `uv.lock`. There is no `requirements.txt` (removed as redundant).

```bash
# Install/refresh the environment from the lockfile
uv sync

# Run any command inside the managed environment
uv run uvicorn app.main:app --reload
uv run alembic upgrade head
uv run ruff check app
uv run mypy app
```

Runtime stack: FastAPI, SQLAlchemy 2.x (async), Alembic, asyncpg, Pydantic Settings, structlog, uvicorn.

---

## 2. Project Layout

```
backend/
├── app/
│   ├── main.py                # App factory, middleware, lifespan
│   ├── api/
│   │   ├── router.py          # Aggregate /api/v1 router
│   │   ├── deps.py            # Dependency-injection foundation (Annotated aliases)
│   │   └── routes/
│   │       ├── health.py      # Liveness + readiness probes
│   │       └── auth.py        # (owned separately) auth endpoints
│   ├── core/
│   │   ├── config.py          # Pydantic Settings (env-driven)
│   │   ├── database.py        # Async engine + session factory + get_db
│   │   ├── logging.py         # structlog configuration + get_logger
│   │   ├── context.py         # Correlation-ID context var
│   │   ├── middleware.py      # Correlation-ID + request-timing middleware
│   │   └── errors.py          # Standard error envelope + handlers
│   ├── models/
│   │   └── base.py            # Declarative Base + UUID/Timestamp mixins
│   └── schemas/               # Pydantic request/response models
├── alembic/                   # Async migration environment
│   ├── env.py
│   └── versions/
├── alembic.ini
├── pyproject.toml + uv.lock   # Dependency source of truth
├── Dockerfile                 # uv-based multi-stage build
├── scripts/entrypoint.sh      # migrate, then serve
└── .env.example
```

---

## 3. Settings Management (`app/core/config.py`)

Type-safe, environment-driven configuration via **Pydantic Settings**, exposed as a cached singleton through `get_settings()`. No secrets are hard-coded; they come from the environment (locally via `.env`, in Azure via Key Vault + managed identity, per ADR-005).

- Application: `app_name`, `environment`, `debug`, `api_v1_prefix`
- Logging: `log_level`, `log_json`
- Database: `postgres_host/port/user/password/db`, pool tuning; exposes `database_url` (asyncpg)
- CORS: `cors_origins` (accepts comma-separated or JSON list)

---

## 4. Database & SQLAlchemy (`app/core/database.py`)

Async SQLAlchemy 2.x engine over **PostgreSQL / asyncpg** (ADR-002, ADR-003):

- `create_async_engine` with connection pooling and `pool_pre_ping=True`
- `async_sessionmaker` (`expire_on_commit=False`)
- `get_db()` — request-scoped session dependency (rolls back on error)
- `dispose_engine()` — pool cleanup on shutdown

**Base model** (`app/models/base.py`): a declarative `Base` with a deterministic constraint **naming convention** (stable Alembic diffs) plus reusable `UUIDPrimaryKeyMixin` and `TimestampMixin` (timezone-aware `created_at`/`updated_at`).

> Row-Level Security session context is **not** wired in the foundation — that is Sprint 2 (ADR-006).

---

## 5. Alembic (`alembic.ini`, `alembic/env.py`)

Async migration environment. The DB URL is injected from `Settings` (single source of truth) and `Base.metadata` is the autogenerate target.

```bash
uv run alembic revision --autogenerate -m "message"
uv run alembic upgrade head
uv run alembic upgrade head --sql      # offline SQL (no DB needed; validates scripts)
```

---

## 6. Structured Logging (`app/core/logging.py`)

**structlog**-based logging configured by `configure_logging(level=, json_logs=)`:

- **JSON** output in production; human-readable **console** output when `LOG_JSON=false`.
- Standard-library logs (uvicorn, SQLAlchemy) are routed through the same pipeline via `ProcessorFormatter`, so all output shares one format.
- Every event carries the request **correlation ID** (from `app/core/context.py`), `level`, `logger`, and an ISO-8601 UTC `timestamp`.
- Use `get_logger(__name__)` and pass structured fields as kwargs:

```python
from app.core.logging import get_logger
logger = get_logger(__name__)
logger.info("request.completed", http_status=200, duration_ms=12.3)
```

The **correlation-ID middleware** (`app/core/middleware.py`) assigns/honours an `X-Correlation-ID` per request, binds it to the logging context, and echoes it on the response. A request-timing middleware logs method/path/status/duration.

---

## 7. Health Endpoints (`app/api/routes/health.py`)

| Endpoint | Purpose | Behaviour |
|---|---|---|
| `GET /api/v1/health/live` | Liveness | `200` while the process serves requests |
| `GET /api/v1/health/ready` | Readiness | Runs `SELECT 1`; `200` when the DB is reachable, `503` (`degraded`) otherwise |

These map directly to container/orchestrator probes.

---

## 8. Dependency-Injection Foundation (`app/api/deps.py`)

Core request-scoped dependencies are exposed as `Annotated` aliases for concise, consistent route signatures:

```python
from app.api.deps import DbSession, SettingsDep

@router.get("/ready")
async def readiness(response: Response, db: DbSession) -> ReadinessResponse: ...
```

- `SettingsDep` → `Annotated[Settings, Depends(get_settings)]`
- `DbSession`  → `Annotated[AsyncSession, Depends(get_db)]`

This is the single import surface for shared dependencies; feature modules add their own and may alias them here as the surface grows.

---

## 9. Error Handling (`app/core/errors.py`)

A single, predictable error envelope across the API:

```json
{ "error": { "code": "http_401", "message": "…", "correlation_id": "…" } }
```

Handlers cover `HTTPException` (preserving response headers such as `WWW-Authenticate`), request validation errors (`422`), and uncaught exceptions (`500`, logged with stack info).

---

## 10. Docker Configuration

Multi-stage `Dockerfile` using **uv**:

1. **Builder** (`python:3.12-slim` + pinned `uv`): `uv sync --frozen --no-dev` installs production deps from the lockfile into `/app/.venv`.
2. **Runtime** (`python:3.12-slim`): copies the prebuilt venv, runs as a non-root user, and starts via `scripts/entrypoint.sh` (which applies migrations then launches uvicorn). `alembic`/`uvicorn` resolve from `/app/.venv/bin` on `PATH`.

```bash
docker build -t fdms-backend ./backend
```

---

## 11. Environment Configuration

See `backend/.env.example`. Copy to `.env` for local non-Docker runs.

| Group | Keys |
|---|---|
| Application | `APP_NAME`, `ENVIRONMENT`, `DEBUG`, `API_V1_PREFIX` |
| Logging | `LOG_LEVEL`, `LOG_JSON` |
| Database | `POSTGRES_HOST/PORT/USER/PASSWORD/DB`, `DB_*` pool tuning |
| CORS | `CORS_ORIGINS` |

---

## 12. Running & Verifying Locally

```bash
cd backend
uv sync
cp .env.example .env            # adjust POSTGRES_* to your database
uv run alembic upgrade head     # apply migrations
uv run uvicorn app.main:app --reload
```

| Check | Expected |
|---|---|
| `GET /api/v1/health/live` | `200` `{"status":"alive",...}` |
| `GET /api/v1/health/ready` | `200` when DB reachable, else `503` |
| Logs | JSON (structlog) with `correlation_id`, `level`, `timestamp` |
| `uv run ruff check app` | foundation modules clean |
| `uv run alembic upgrade head --sql` | emits valid DDL |
