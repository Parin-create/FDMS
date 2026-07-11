# FDMS Frontend — Architecture

| Field | Value |
|---|---|
| **Document** | Frontend architecture & conventions |
| **Scope** | `frontend/` (React + TypeScript SPA) |
| **Status** | Sprint 4.1 — foundation scaffolding in place |
| **Last Updated** | 2026-07-07 |

FDMS is a **multi-tenant healthcare platform**. The frontend is a React + TypeScript SPA that consumes the FastAPI backend and authenticates users via Microsoft Entra ID. This document describes the architecture and the module conventions established in Sprint 4.1. **Sprint 4.1 is scaffolding only — no business features are implemented.**

---

## 1. Tech stack (existing — unchanged)
- **React 18** + **TypeScript** (strict: `verbatimModuleSyntax`, `exactOptionalPropertyTypes`, `noUncheckedIndexedAccess`)
- **Vite 5** build/dev
- **Tailwind CSS** for styling
- **React Router 6** (`createBrowserRouter`)
- **TanStack Query** for server state
- **Zod** for runtime validation of API responses
- **MSAL** (`@azure/msal-browser` + `@azure/msal-react`) for Entra auth
- **ESLint** + strict `tsc` in the build

---

## 2. Directory layout

```
frontend/src/
  auth/                 # EXISTING — the "auth" feature (MSAL, ProtectedRoute, roles, CurrentUserContext)
  config/               # env.ts (validated VITE_* config)
  lib/                  # api.ts (HTTP client), queryClient.ts, currentUser.ts, health.ts
  layouts/              # RootLayout (app shell)
  routes/               # router.tsx (route tree)
  pages/                # top-level route pages (Home, Login, NotFound, AuthNotConfigured)
  components/           # shared components
    ui/                 # NEW — presentational design-system primitives (barrel)
    layout/             # Header, Sidebar, UserMenu (existing)
  features/             # NEW — feature modules (one folder per bounded context)
    dashboard/
    files/
    patients/
    providers/
    appointments/
    medical-records/
    admin/
  hooks/                # NEW — app-wide reusable hooks (barrel)
  types/                # NEW — app-wide shared types (barrel)
  utils/                # NEW — app-wide pure utilities (barrel)
```

> **`auth` stays under `src/auth/`** (not `src/features/auth/`). Moving it would churn imports across the app and violate the "preserve existing code" rule, so it is treated as the auth feature in place.

---

## 3. Feature-module convention

Each `src/features/<module>/` is a self-contained bounded context. As a module is built, it follows this consistent internal structure:

```
features/<module>/
  index.ts        # barrel — the module's public surface (import from "@/features/<module>")
  api/            # typed service functions + zod response schemas
  hooks/          # TanStack Query hooks (queries/mutations) for this module
  components/     # module-specific UI (composes shared ui/ primitives)
  types/          # module types (prefer z.infer from the api schemas)
  queryKeys.ts    # query-key factory for targeted cache invalidation
```

Rules:
- **Feature code imports shared code**, never the reverse (`components/ui`, `hooks`, `utils`, `lib`, `config`).
- **Cross-feature imports go through a feature's `index.ts` barrel**, not into its internals.
- Modules are intended to be **lazy-loaded** at the route level as they ship, to keep the bundle small.

### Module status
| Module | Location | Status |
|---|---|---|
| auth | `src/auth/` | ✅ Implemented (existing) |
| dashboard | `src/features/dashboard/` | 🟡 Scaffolded |
| files | `src/features/files/` | 🟡 Scaffolded (build in Sprint 4.3/4.4) |
| patients | `src/features/patients/` | 🟡 Scaffolded (PHI) |
| providers | `src/features/providers/` | 🟡 Scaffolded |
| appointments | `src/features/appointments/` | 🟡 Scaffolded |
| medical-records | `src/features/medical-records/` | 🟡 Scaffolded (PHI) |
| admin | `src/features/admin/` | 🟡 Scaffolded (TenantAdmin) |

---

## 4. Shared layers
- **`components/ui/`** — business-agnostic, presentational primitives (Button, Modal, Table, Toast, ProgressBar, Spinner, EmptyState, Dropzone base). Feature UI composes these; features never re-invent primitives.
- **`hooks/`** — cross-cutting hooks (e.g. `useDebounce`). Feature-specific hooks live in the feature.
- **`types/`** — cross-cutting types (e.g. pagination envelopes). Prefer `z.infer` where a schema exists.
- **`utils/`** — pure, side-effect-free helpers (e.g. `formatBytes`).
- **`lib/`** — the data-access layer: the HTTP client (`api.ts`), `queryClient`, and existing typed resources (`currentUser`, `health`).

---

## 5. Established conventions (do not diverge)
- **API responses are validated with zod** (see `lib/currentUser.ts`, `lib/health.ts`) — define a schema per response and infer the type.
- **Server state is TanStack Query**; each module owns a `queryKeys` factory and invalidates via those keys.
- **Auth token attachment** flows through the existing token-provider mechanism (`registerTokenProvider` in `lib/api.ts`, wired from MSAL at bootstrap). Features never fetch tokens directly.
- **Errors** normalize to the existing `ApiError` type (status + parsed body).
- **RBAC** is UI gating only via `src/auth/roles.ts` (`roleAtLeast`); the backend is the enforcement point.

### Healthcare (PHI) guardrails
- Never log PHI to the console or telemetry.
- Prefer short-lived signed/SAS URLs for document/media access over proxying bytes.
- Respect least-privilege role gating and session/idle timeout on PHI-bearing modules (`patients`, `medical-records`, clinical `files`).

---

## 6. How to add a new feature (checklist)
1. Create `src/features/<module>/` with `api/`, `hooks/`, `components/`, `types/`, `queryKeys.ts`, and `index.ts`.
2. Add zod schemas + service functions in `api/` (against the agreed backend contract).
3. Add TanStack Query hooks in `hooks/` using the module's `queryKeys`.
4. Build UI in `components/` composing `@/components/ui` primitives.
5. Export the public surface from the module `index.ts`.
6. Register a **lazy** route in `routes/router.tsx` under the protected branch and enable its `Sidebar` entry.
7. Ensure `npm run typecheck`, `npm run lint`, and `npm run build` pass.

---

## 7. Environment configuration
Validated in `src/config/env.ts` (Zod). Current `VITE_*` variables: `VITE_API_BASE_URL`, `VITE_APP_NAME`, `VITE_ENTRA_CLIENT_ID`, `VITE_ENTRA_TENANT_ID`, `VITE_ENTRA_REDIRECT_URI`, `VITE_ENTRA_API_SCOPE`. See `frontend/.env.example`.

---

## 8. Future decisions (planned, NOT applied in Sprint 4.1)
- **HTTP transport (Axios):** as the number of API-heavy modules grows, adopting Axios (interceptors for bearer/error handling, native upload progress + cancellation) is recommended over the current `fetch` wrapper and hand-rolled uploads. This is a **later** decision and is **out of scope for Sprint 4.1** — the existing `lib/api.ts` client is unchanged. When adopted, it will sit behind the existing `apiClient` facade so feature code and conventions do not change.
- **Testing:** Vitest + React Testing Library + MSW (mock API) are planned; no test runner is configured yet.

---

*Sprint 4.1 delivers the module scaffolding and shared-layer folders only. Dashboard and Files feature work begins in later sprints.*
