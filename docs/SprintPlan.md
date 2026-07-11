# FDMS — Delivery & Sprint Plan

| Field | Value |
|---|---|
| **Document Title** | FDMS — Sprint / Delivery Plan |
| **Version** | 1.0 |
| **Status** | Draft for Engineering Planning |
| **Source of Truth** | [docs/PRD.md](PRD.md) · [docs/Architecture.md](Architecture.md) · [docs/ADRs.md](ADRs.md) |
| **Last Updated** | 2026-06-23 |
| **Classification** | Internal — Confidential |

> This plan delivers the **MVP scope** defined in [PRD §12](PRD.md). It assumes a cross-functional team (backend, frontend, platform/SRE, security/QA). Sprints are sequential with explicit dependencies; assume ~2-week iterations (adjust to team cadence). Each sprint lists **Goal · Features · Dependencies · Acceptance Criteria · Risks · Deliverables.**

## Sprint Overview
| Sprint | Theme | Primary PRD/Arch Coverage |
|---|---|---|
| [0](#sprint-0--foundation) | Foundation | Cloud baseline, IaC, CI/CD, observability skeleton |
| [1](#sprint-1--authentication) | Authentication | Entra ID / OIDC / JWT (PRD §5.1) |
| [2](#sprint-2--tenant-management) | Tenant Management | Multi-tenancy + RLS (PRD §10, ADR-001/006) |
| [3](#sprint-3--folder-management) | Folder Management | Folders & inheritance (PRD §5.2) |
| [4](#sprint-4--document-upload--storage) | Upload & Storage | Blob, SAS, scan, metadata (PRD §5.3, §5.6) |
| [5](#sprint-5--sharing--permissions) | Sharing & Permissions | RBAC + secure sharing (PRD §5.8, §11) |
| [6](#sprint-6--search) | Search | Metadata search (PRD §5.7, ADR-007) |
| [7](#sprint-7--versioning) | Versioning | Version history & restore (PRD §5.10, ADR-010) |
| [8](#sprint-8--audit-logging) | Audit Logging | Immutable audit (PRD §5.11, ADR-008) |
| [9](#sprint-9--hardening) | Hardening | Security, performance, isolation validation |
| [10](#sprint-10--production-readiness) | Production Readiness | DR, SLOs, admin portal, launch |

---

## Sprint 0 — Foundation

**Goal:** Establish the cloud baseline, delivery pipeline, and observability skeleton so all later work ships safely and is multi-tenant-ready by design.

**Features**
- Azure landing zone: resource groups, networking, Container Apps environment, PostgreSQL Flexible Server, Blob Storage, Key Vault (per ADR-002/004/009).
- Infrastructure-as-Code (IaC) for all environments (dev/staging/prod).
- CI/CD pipeline with build, test, security scan (SAST/dependency), and zero-downtime deploy.
- Observability skeleton: structured logging, metrics, tracing, correlation IDs (Architecture §Observability).
- Repository structure, coding standards, branching/release strategy, secrets via Key Vault + managed identity.

**Dependencies**
- Azure subscription, Entra app registration access, naming/region decisions.

**Acceptance Criteria**
- A "hello" containerized API deploys to staging via CI/CD with zero downtime.
- IaC provisions a full environment reproducibly from scratch.
- Logs/metrics/traces flow to Azure Monitor with correlation IDs.
- No secrets in code; all sourced from Key Vault via managed identity.

**Risks**
- Landing-zone/networking misconfiguration delays everything → mitigate with IaC reviews and a reference architecture.
- Over-engineering the pipeline early → keep it minimal but extensible.

**Deliverables**
- Provisioned dev/staging environments, IaC repo, working CI/CD, observability baseline, engineering runbook v0.

---

## Sprint 1 — Authentication

**Goal:** Authenticate users via Microsoft Entra ID with secure, stateless JWT validation.

**Features**
- OIDC Authorization Code + PKCE flow in the SPA (MSAL) and JWT validation at the API boundary (ADR-005).
- JWKS-based signature/issuer/audience/expiry validation; identity context in requests.
- Session timeouts (idle + absolute), secure token handling, CSRF protection (PRD FR-AUTH-3/7, SEC-18).
- JIT provisioning scaffold on first sign-in (FR-AUTH-5).

**Dependencies**
- Sprint 0 (environments, secrets, API skeleton). Entra app registration.

**Acceptance Criteria**
- A user signs in via Entra and receives a validated session; invalid/expired tokens are rejected.
- MFA/Conditional Access (delegated to Entra) is honored end-to-end.
- Token refresh and forced sign-out (revocation) work.
- No server-side session state (stateless) — confirmed by scaling the API to multiple instances.

**Risks**
- Entra configuration variance/redirect issues → test against a representative directory; document onboarding.
- Token-handling security mistakes → security review of the auth flow.

**Deliverables**
- Working SSO sign-in, JWT validation middleware, auth onboarding doc, auth flow security review.

---

## Sprint 2 — Tenant Management

**Goal:** Implement the multi-tenant core with database-enforced isolation (the platform's foundational invariant).

**Features**
- Tenant entity + lifecycle scaffolding (provision/activate); tenant context middleware deriving `tenant_id` from JWT (Architecture §Tenant Isolation).
- **RLS enabled and FORCEd** on tenant-scoped tables; per-connection tenant context set/reset with pooling (ADR-001/006).
- Tenant↔Entra directory mapping; multi-tenant federation.
- CI guard that fails the build if any tenant-scoped table lacks an RLS policy.
- Isolation integration test suite (cross-tenant access attempts must fail).

**Dependencies**
- Sprint 1 (identity/tenant claims), Sprint 0 (DB).

**Acceptance Criteria**
- A request bound to Tenant A cannot read/write any Tenant B data — verified by automated tests at both app and DB layers.
- Pooled connections reset tenant context (no bleed) — verified under concurrency.
- CI fails when a new tenant table omits RLS.
- A new tenant can be provisioned and bound to an Entra directory.

**Risks**
- Connection-pool tenant bleed (TR-2) → explicit reset + tests.
- Missing RLS policy (TR-1) → CI guard + forced RLS.

**Deliverables**
- Tenant provisioning capability, RLS framework + CI guard, isolation test suite, tenant-context middleware.

---

## Sprint 3 — Folder Management

**Goal:** Provide hierarchical folder organization with permission inheritance and soft-delete.

**Features**
- Create/rename/move/delete folders within permission scope; nested hierarchies (PRD §5.2 FR-FOLD-1/2).
- Permission inheritance from parent with override at any level (FR-FOLD-3).
- Soft-delete (trash) with configurable retention before permanent deletion (FR-FOLD-4).
- Folder-level activity/usage surface (FR-FOLD-5).

**Dependencies**
- Sprint 2 (tenant isolation, RLS), Sprint 1 (identity).

**Acceptance Criteria**
- Users manage folders only within their tenant and permission scope.
- Inheritance flows to children; overrides apply correctly.
- Soft-deleted folders are recoverable within the retention window, then purged.
- All folder operations are tenant-isolated.

**Risks**
- Inheritance/override complexity introduces authz edge cases → model explicitly and unit-test inheritance resolution.
- Deep hierarchies cause performance issues → index path/parent lookups.

**Deliverables**
- Folder management capability, inheritance resolution logic, soft-delete/trash flow, folder activity view.

---

## Sprint 4 — Document Upload & Storage

**Goal:** Enable secure, resumable document upload to Blob Storage with malware scanning and metadata capture.

**Features**
- Single/bulk drag-and-drop upload; resumable/chunked transfer for large files (PRD FR-UP-1/2).
- **Direct-to-Blob** upload via short-lived scoped SAS URLs minted server-side (Architecture §Storage, ADR-004).
- File-type/size policy enforcement per tenant (FR-UP-3); duplicate/checksum capture (FR-UP-5/7).
- **Malware scan via async worker before blob becomes referenceable**; quarantine on failure (FR-UP-4, SEC-8).
- System metadata capture + tagging/classification labels (PRD §5.6 FR-META-1/3); document download via signed URLs (PRD §5.4 FR-DL-1/2).
- Background worker pipeline + queue established (Architecture §Backend).

**Dependencies**
- Sprint 3 (folders to upload into), Sprint 2 (isolation), Sprint 0 (Blob, queue, workers).

**Acceptance Criteria**
- Large files upload resumably; SAS URLs are single-object, least-privilege, short-lived.
- A file is not available/referenceable until it passes malware scan; infected files are quarantined and audited.
- System metadata + tags captured; tenant file-type/size policies enforced.
- Download issues a scoped, expiring SAS URL; storage keys never reach the client.

**Risks**
- Over-broad/long-lived SAS (TR-3) → centralized minting + policy tests.
- Malware bypass (TR-6) → gate referenceability on scan result.
- Large-file upload reliability → chunk/retry/resume tested under failure injection.

**Deliverables**
- Upload/download capability, SAS-minting service, async scan/worker pipeline, metadata & tagging, storage layout per ADR-004.

---

## Sprint 5 — Sharing & Permissions

**Goal:** Deliver RBAC and secure internal/external sharing with full revocation.

**Features**
- RBAC roles + permission catalog (Tenant Admin/Manager/Contributor/Viewer/Guest); role assignment to users and Entra groups (PRD §11, FR-RBAC-1/2).
- Resource-level grants on folders/documents; default-deny; dual-layer enforcement (RBAC-4/8, ADR-006).
- Internal sharing with user/group at view/download/edit levels (PRD §5.8 FR-SHR-1/3).
- **External secure share links** with expiry, optional password, access count; revoke at any time (FR-SHR-2/4).
- Tenant external-sharing policy (allow/deny, domain allowlist); shared-with-me view (FR-SHR-6/7).

**Dependencies**
- Sprint 4 (documents exist), Sprint 3 (folders), Sprint 2 (isolation).

**Acceptance Criteria**
- Effective permission = union of role + resource grants, bounded by tenant policy; default-deny verified.
- External links honor expiry/password/count and can be revoked immediately.
- Guests can access only explicitly shared items; no tenant traversal.
- Privilege-escalation attempts fail (tested).

**Risks**
- Authz model complexity / escalation paths (TR; PRD RBAC-9) → explicit escalation test suite.
- External-link exposure → short TTLs, password option, full audit (carried in Sprint 8).

**Deliverables**
- RBAC engine, resource-grant model, internal + external sharing, sharing policy controls, escalation test suite.

---

## Sprint 6 — Search

**Goal:** Provide fast, permission- and tenant-scoped metadata search with faceted filtering.

**Features**
- Search by name, metadata, tags, owner; faceted filters (type, date, owner, tag, classification, folder) (PRD §5.7 FR-SRCH-1/3).
- PostgreSQL indexing (B-tree/GIN/trigram/`tsvector`) served from read replicas (ADR-007).
- **Permission intersection enforced server-side** before results return; tenant scope via RLS (FR-SRCH-4/5).

**Dependencies**
- Sprints 3–5 (folders, documents/metadata, permissions).

**Acceptance Criteria**
- Search P95 latency < 2 seconds (PRD NFR-PERF-1) at representative data volume.
- Users never see results they cannot access; no cross-tenant results — verified by tests.
- Facets filter correctly and combine.

**Risks**
- Result leakage of unauthorized items (TR-8) → intersection enforced + tested.
- Index performance at scale → load test on read replicas; tune indexes.

**Deliverables**
- Metadata search capability, faceted filtering, search indexes, permission-scoped result enforcement, search load-test results.

---

## Sprint 7 — Versioning

**Goal:** Maintain immutable version history with view, preview, and restore.

**Features**
- Copy-on-write immutable per-version blobs; new upload = new version, never overwrite (PRD §5.10 FR-VER-1/2, ADR-010).
- Version chain metadata (author/timestamp/size/checksum/comment) + active-version pointer (FR-VER-4).
- View/preview/download/restore prior versions per permission (FR-VER-3).
- Configurable per-tenant version retention; old versions tier to cool/archive (FR-VER-5).
- In-browser document preview for common formats via async preview worker (PRD §5.5 FR-PRV-1/2).

**Dependencies**
- Sprint 4 (upload/storage), Sprint 5 (permissions for restore/preview authz).

**Acceptance Criteria**
- Re-uploading creates a new version; full history is preserved and immutable.
- Restore re-points active version without destroying history.
- Prior versions can be previewed/downloaded per permission.
- Preview renders common formats without permanently downloading the original to the client.

**Risks**
- Postgres/Blob version-chain consistency → transactional pointer updates + reconciliation.
- Storage growth from many versions → retention limits + tiering.

**Deliverables**
- Versioning capability, restore flow, version metadata, preview service, retention/tiering policy.

---

## Sprint 8 — Audit Logging

**Goal:** Capture an immutable, tamper-evident, tenant-isolated audit trail with export.

**Features**
- Audit events for auth, access, share, download, preview, admin, delete, permission change (PRD §5.11 FR-AUD-1).
- **Async projection** to an append-only, tamper-evident store (hash-chain/sequence); actor/action/target/tenant/timestamp/IP/result (FR-AUD-2/3, ADR-008).
- Admin search/filter/export scoped to tenant; configurable retention; SIEM export/streaming (FR-AUD-4/5/6).

**Dependencies**
- Sprints 1–7 (events to audit), Sprint 0 (queue).

**Acceptance Criteria**
- All security-relevant actions produce complete audit records; no gaps under load (reconciliation passes).
- Audit records cannot be modified/deleted (tamper-evidence verified).
- Admins can search/filter/export their tenant's audit; SIEM export works.
- Audit is tenant-isolated.

**Risks**
- Audit pipeline loss/gap (TR-5) → durable queue, at-least-once delivery, reconciliation checks.
- Audit volume/retention cost → tiering + partitioning.

**Deliverables**
- Audit pipeline + immutable store, admin audit search/export, SIEM export, completeness/reconciliation tests.

---

## Sprint 9 — Hardening

**Goal:** Validate and strengthen security, performance, and tenant isolation to enterprise standards.

**Features**
- Rate limiting/abuse protection on sensitive endpoints; edge WAF/DDoS (PRD SEC-13).
- Encryption verification (TLS 1.2+, AES-256), key rotation, CMK option validation (SEC-1/2/3).
- Full **threat model review**, SAST/DAST, dependency scanning, and **penetration test** (SEC-14/15).
- Performance/load testing to PRD budgets (search P95 < 2s, API P95 < 500ms, 50k concurrent users); autoscaling validation.
- Accessibility (WCAG 2.1 AA) and responsive UI verification (NFR-USE-1/2).
- Per-tenant quotas/limits to bound noisy neighbors (TR-4).

**Dependencies**
- Sprints 1–8 (full functional surface to test).

**Acceptance Criteria**
- Pen test findings triaged; no open critical/high vulnerabilities at launch.
- Load tests meet latency and concurrency targets with autoscaling.
- Isolation tests pass under load; quotas enforced.
- WCAG 2.1 AA verified on core flows.

**Risks**
- Late-discovered security/perf issues → run security/load testing continuously from earlier sprints, not only here.
- Pen test reveals systemic gaps → buffer time for remediation.

**Deliverables**
- Pen test report + remediation, load-test report, threat model, rate-limiting/quota controls, accessibility report.

---

## Sprint 10 — Production Readiness

**Goal:** Complete the admin portal, prove DR, finalize SLOs, and launch to first production tenant.

**Features**
- **Admin portal**: user/role/group management, tenant policy config, usage dashboards, audit access/export, SSO config (PRD §5.13 FR-ADM-1/2/3/4/6).
- Platform operator tenant lifecycle (provision/suspend/deprovision) and tenant offboarding (export/delete) (FR-ADM-5, MT-6/10).
- **DR validation**: backups, PITR, geo-redundancy, documented restore runbook; prove RTO ≤ 4h / RPO ≤ 15m (PRD NFR-AVAIL-2/3, NFR-REL-2).
- SLO dashboards + alerting for 99.9% availability and latency budgets; on-call runbooks.
- Compliance-readiness review (GDPR/SOC2/HIPAA/ISO posture); go-live checklist.

**Dependencies**
- Sprints 0–9 (all capabilities + hardening).

**Acceptance Criteria**
- A tenant can be provisioned, configured, and offboarded end-to-end by admins/operators.
- DR drill demonstrates restore within RTO/RPO targets.
- SLO dashboards and alerts are live; on-call runbooks validated.
- End-to-end MVP journey passes (sign in → upload → organize → search → preview → share → version → download), fully isolated and audited (PRD §12.3).

**Risks**
- DR targets not met on first drill → schedule drill early enough to remediate.
- Admin portal scope creep → hold to MVP admin features; defer advanced reporting to roadmap.

**Deliverables**
- Admin portal, tenant lifecycle + offboarding, validated DR runbook, SLO dashboards/alerts, compliance-readiness review, production launch.

---

## Cross-Sprint Notes
- **Continuous from Sprint 0:** observability, security scanning, and isolation tests are not deferred to Sprint 9 — they grow with each sprint.
- **Definition of Done (every sprint):** tenant-isolated, permission-checked, audited (once Sprint 8 lands; audit events stubbed earlier), tested (unit + integration), observable, and documented.
- **Out of MVP (see [PRD §12.2](PRD.md) & [§13 Roadmap](PRD.md)):** full-text/OCR search, real-time co-editing, workflow automation, native mobile, AI document intelligence, eDiscovery, integration marketplace.

---

*End of Document — FDMS Sprint Plan v1.0*
