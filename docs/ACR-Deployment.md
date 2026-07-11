# FDMS Backend — Azure Container Registry (ACR) Deployment

| Field | Value |
|---|---|
| **Document** | ACR image build, tagging & push (Sprint 4 Phase 2) |
| **Scope** | Backend container image only. No app logic / frontend changes. |
| **Image** | `fdms-backend` (FastAPI, `linux/amd64`) |
| **Last Updated** | 2026-07-07 |

This describes how to build a reproducible, OCI-labelled backend image and publish it to Azure Container Registry for consumption by Azure Container Apps (deployment to ACA is the next phase).

---

## 1. Prerequisites
- **Azure CLI** (`az`) logged in: `az login`.
- An **ACR** already provisioned; you need its name (e.g. `fdmsacr`, login server `fdmsacr.azurecr.io`).
- Push rights: role **AcrPush** (or Owner/Contributor) on the registry.
- Docker with BuildKit (local builds), **or** use server-side `az acr build` (no local Docker needed).

---

## 2. Image versioning & tagging strategy

**Source of truth for the version** is `backend/pyproject.toml` → `version` (currently `0.1.0`). Bump it there for each release (SemVer `MAJOR.MINOR.PATCH`).

Each build produces this tag set (see `scripts/build-and-push.sh`):

| Tag | Example | Use |
|---|---|---|
| `:<version>` | `0.1.0` | **Immutable release — deploy from this.** |
| `:<major.minor>` | `0.1` | Latest patch of a minor line (convenience). |
| `:<major>` | `0` | Latest minor of a major line (convenience). |
| `:sha-<ref>` | `sha-9f2c1ab` | Immutable build-provenance tag (traceable to a commit). |
| `:latest` | `latest` | Convenience only — **never deploy `:latest` to production.** |

**Best practices**
- **Deploy by immutable digest or `:<version>`/`:sha-<ref>`**, not `:latest` — guarantees the running revision is exactly what you tested.
- Enable **[ACR image locking / immutable tags](https://learn.microsoft.com/azure/container-registry/container-registry-image-lock)** on release tags so they can't be overwritten.
- Configure a **retention/purge policy** for untagged manifests to control cost (`az acr config retention`).
- Enable **Microsoft Defender for Containers** for vulnerability scanning on push.

---

## 3. OCI labels (provenance)

The image carries standard `org.opencontainers.image.*` labels: `title`, `description`, `version`, `revision` (VCS ref), `created` (build date), `vendor`, `licenses`, `source`, `documentation`, and `base.name`. `version`/`revision`/`created` are injected at build time via `--build-arg`. Update the `IMAGE_SOURCE` / `IMAGE_DOCS` build-args (or the Dockerfile defaults) to your real repo/wiki URLs.

Inspect them after a build:
```bash
docker image inspect fdms-backend:0.1.0 --format '{{json .Config.Labels}}'
```

---

## 4. Reproducible builds
- **Base image pinned by digest** in the `Dockerfile` (`ARG PYTHON_IMAGE=python:3.12-slim@sha256:...`). Refresh with `docker buildx imagetools inspect python:3.12-slim` and bump the ARG when you intend to update.
- **Python deps pinned** via `uv.lock` + `uv sync --frozen --no-dev` (no floating versions).
- **uv itself pinned** (`ghcr.io/astral-sh/uv:0.11.9`).
- Build is `--platform linux/amd64` (ACA runs amd64).
- Optional: add SBOM/provenance attestations — `docker buildx build --provenance=true --sbom=true ...`.

---

## 5. Build & push

### Option A — helper script (local Docker)
From `backend/`:
```bash
# build only (dry run)
ACR_NAME=fdmsacr ./scripts/build-and-push.sh

# build + push all tags
ACR_NAME=fdmsacr ./scripts/build-and-push.sh --push
```

### Option B — manual (local Docker)
From `backend/`:
```bash
VERSION=0.1.0
REGISTRY=fdmsacr.azurecr.io
VCS_REF=$(git rev-parse --short HEAD 2>/dev/null || echo unknown)
BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)

docker build --platform linux/amd64 \
  --build-arg VERSION=$VERSION \
  --build-arg VCS_REF=$VCS_REF \
  --build-arg BUILD_DATE=$BUILD_DATE \
  -t $REGISTRY/fdms-backend:$VERSION \
  -t $REGISTRY/fdms-backend:sha-$VCS_REF \
  -t $REGISTRY/fdms-backend:latest .

az acr login --name fdmsacr
docker push $REGISTRY/fdms-backend:$VERSION
docker push $REGISTRY/fdms-backend:sha-$VCS_REF
docker push $REGISTRY/fdms-backend:latest
```

### Option C — server-side build (no local Docker; most reproducible for CI)
Runs the build inside ACR from the `backend/` context:
```bash
az acr build \
  --registry fdmsacr \
  --image fdms-backend:0.1.0 \
  --image fdms-backend:latest \
  --platform linux/amd64 \
  --build-arg VERSION=0.1.0 \
  --build-arg BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
  ./backend
```

### PowerShell note (Windows)
`$(...)` command substitution works in PowerShell too; or precompute:
```powershell
$Date = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
az acr build --registry fdmsacr --image fdms-backend:0.1.0 --build-arg BUILD_DATE=$Date ./backend
```

---

## 6. Verify in the registry
```bash
az acr repository show-tags --name fdmsacr --repository fdms-backend --output table
az acr manifest list-metadata --registry fdmsacr --name fdms-backend --output table
# resolve the immutable digest for a tag (use this in deployments):
az acr repository show --name fdmsacr --image fdms-backend:0.1.0 --query "digest" -o tsv
```

Pull test:
```bash
az acr login --name fdmsacr
docker pull fdmsacr.azurecr.io/fdms-backend:0.1.0
```

---

## 7. Consuming from Azure Container Apps (next phase — reference)
- Grant the Container App's **managed identity** the **AcrPull** role on the registry (no admin credentials).
- Reference the image by **digest** for immutability:
  `fdmsacr.azurecr.io/fdms-backend@sha256:<digest>`.
- Run migrations once as an **ACA Job** using the same image (`RUN_MIGRATIONS=true` / `alembic upgrade head`); keep serving replicas with migrations off (see `scripts/entrypoint.sh`).
- Set ingress `targetPort` = `8000`; configure probes to `/api/v1/health/live` and `/api/v1/health/ready`.

---

## 8. ACR readiness checklist
- [x] Image is OCI-compliant `linux/amd64`, multi-stage, non-root.
- [x] Reproducible: digest-pinned base, frozen deps, pinned uv.
- [x] Versioned tag set + `sha-<ref>` provenance tag.
- [x] Full OCI labels (build-arg-injected version/revision/created).
- [x] Build/push script + `az acr build` path documented.
- [ ] (Ops) Enable image lock, retention policy, Defender scanning, AcrPull for ACA identity.
