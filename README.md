# FDMS — File Sharing & Document Management System

Multi-tenant, enterprise document management platform.
**Sprint 0 (project foundation) is implemented** — see [docs/SprintPlan.md](docs/SprintPlan.md). Authentication, tenancy, folders, documents, etc. are delivered in later sprints.

> Source-of-truth documents: [PRD](docs/PRD.md) · [Architecture](docs/Architecture.md) · [ADRs](docs/ADRs.md) · [Sprint Plan](docs/SprintPlan.md)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript (strict), Vite, Tailwind CSS, React Router, TanStack Query |
| Backend | FastAPI, SQLAlchemy 2.x (async), Alembic, Pydantic Settings, structured logging |
| Database | PostgreSQL 16 (asyncpg) |
| Orchestration | Docker, Docker Compose |

---

## Repository Layout

```
FDMS/
├── backend/                 # FastAPI service
│   ├── app/
│   │   ├── api/             # Routers (versioned API) + health endpoints
│   │   ├── core/            # Config, logging, database, middleware, errors
│   │   ├── models/          # SQLAlchemy declarative base + mixins
│   │   ├── schemas/         # Pydantic request/response models
│   │   └── main.py          # Application factory / entrypoint
│   ├── alembic/             # Migration environment (async)
│   ├── alembic.ini
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/                # React + TypeScript SPA
│   ├── src/
│   │   ├── components/      # ErrorBoundary, RouteError
│   │   ├── config/          # Validated runtime env
│   │   ├── layouts/         # App shell
│   │   ├── lib/             # API client, query client, health
│   │   ├── pages/           # Home, NotFound
│   │   ├── routes/          # Router definition
│   │   └── main.tsx
│   ├── Dockerfile + nginx.conf
│   └── .env.example
├── infrastructure/          # docker-compose.yml + env example
└── docs/                    # PRD, Architecture, ADRs, Sprint Plan
```

---

## Quick Start (Docker Compose — recommended)

Requires Docker Desktop. From the repository root:

```bash
# Optional: customise credentials/ports
cp infrastructure/.env.example infrastructure/.env

# Build and start db + backend + frontend
docker compose -f infrastructure/docker-compose.yml up --build
```

Then open:

| Service | URL |
|---|---|
| Frontend (SPA) | http://localhost:8080 |
| Backend API docs | http://localhost:8000/docs |
| Liveness | http://localhost:8000/api/v1/health/live |
| Readiness | http://localhost:8000/api/v1/health/ready |

Stop and remove containers:

```bash
docker compose -f infrastructure/docker-compose.yml down
# add -v to also remove the database volume
```

---

## Local Development (without Docker)

### Backend

Requires Python 3.12+ and a running PostgreSQL (or use the Compose `db` service).

```bash
cd backend
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux:        source .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env        # adjust POSTGRES_* to point at your database

# Apply migrations (no-op until Sprint 2 introduces tables)
alembic upgrade head

# Start the API with autoreload
uvicorn app.main:app --reload
```

API available at http://localhost:8000 (docs at `/docs`).

### Frontend

Requires Node.js 20+.

```bash
cd frontend
npm install
cp .env.example .env        # optional; sensible defaults are built in
npm run dev
```

SPA available at http://localhost:5173 (Vite proxies `/api` to `http://localhost:8000`).

---

## Common Commands

| Task | Command |
|---|---|
| Backend lint | `cd backend && ruff check .` |
| Backend type-check | `cd backend && mypy app` |
| Create migration | `cd backend && alembic revision --autogenerate -m "message"` |
| Apply migrations | `cd backend && alembic upgrade head` |
| Frontend type-check | `cd frontend && npm run typecheck` |
| Frontend lint | `cd frontend && npm run lint` |
| Frontend build | `cd frontend && npm run build` |

---

## Configuration

All configuration is environment-driven (no secrets in code).

- **Backend** — see [backend/.env.example](backend/.env.example) (app, logging, PostgreSQL, CORS).
- **Frontend** — see [frontend/.env.example](frontend/.env.example) (`VITE_`-prefixed only).
- **Compose** — see [infrastructure/.env.example](infrastructure/.env.example).

In Azure, secrets are provided by Key Vault via managed identity (see [ADRs](docs/ADRs.md)).

---

## What Sprint 0 Delivers

- ✅ Backend project structure (FastAPI, layered: api / core / models / schemas)
- ✅ Frontend project structure (Vite + strict TypeScript)
- ✅ Docker setup (multi-stage backend & frontend images)
- ✅ Docker Compose orchestration (db + backend + frontend, healthchecks)
- ✅ Environment configuration (`.env.example` for each component)
- ✅ Configuration management (Pydantic Settings + Zod-validated frontend env)
- ✅ Structured logging framework (JSON logs + correlation IDs)
- ✅ Health endpoints (liveness + DB-backed readiness)
- ✅ Database connection layer (async SQLAlchemy 2.x + pooling)
- ✅ Base models (declarative base, UUID/timestamp mixins, naming convention)
- ✅ Alembic initialization (async migration environment)
- ✅ Frontend shell, routing, layout, and error-handling foundation
- ✅ README setup instructions

**Not in Sprint 0** (later sprints): authentication, tenant management, RLS, folders, uploads, sharing, search, versioning, audit.
