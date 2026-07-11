# FDMS — Enterprise Architecture

| Field | Value |
|---|---|
| **Document Title** | FDMS — System Architecture |
| **Version** | 1.0 |
| **Status** | Draft for CTO / Architecture Review |
| **Source of Truth** | [docs/PRD.md](PRD.md) |
| **Audience** | CTO, Principal/Staff Engineers, Cloud & Security Architects, SRE |
| **Last Updated** | 2026-06-23 |
| **Classification** | Internal — Confidential |

> Scope note: This document is architecture and planning only. It contains **no code, no database schema/DDL, no API implementations, and no UI screens.** Technology choices follow the PRD reference stack (React/TS, FastAPI, PostgreSQL, Azure Blob, Entra ID, Azure Container Apps).

---

## Table of Contents
1. [Executive Architecture Summary](#executive-architecture-summary)
2. [Architecture Principles](#architecture-principles)
3. [System Context](#system-context)
4. [High-Level Architecture](#high-level-architecture)
5. [Multi-Tenant Strategy](#multi-tenant-strategy)
6. [Tenant Isolation Strategy](#tenant-isolation-strategy)
7. [Authentication Architecture](#authentication-architecture)
8. [Authorization Architecture](#authorization-architecture)
9. [Storage Architecture](#storage-architecture)
10. [Search Architecture](#search-architecture)
11. [Audit Architecture](#audit-architecture)
12. [Security Architecture](#security-architecture)
13. [Compliance Architecture](#compliance-architecture)
14. [Observability](#observability)
15. [Scalability Strategy](#scalability-strategy)
16. [Disaster Recovery](#disaster-recovery)
17. [Cost Optimization](#cost-optimization)
18. [Technical Risks](#technical-risks)

---

## Executive Architecture Summary

FDMS is a **cloud-native, multi-tenant SaaS** for enterprise document management, designed to serve **50,000+ concurrent users, 500+ tenants, and millions of documents** at a **99.9% availability SLA** (RTO ≤ 4h, RPO ≤ 15m per PRD §6).

The architecture is a **stateless containerized API tier** (FastAPI on Azure Container Apps) fronting a **PostgreSQL** metadata/control plane and **Azure Blob Storage** data plane, with **Microsoft Entra ID** as the identity provider. The defining design decision is **defense-in-depth tenant isolation**: tenant context is established at authentication, propagated through every request, enforced in application code, and enforced *again* at the database via **PostgreSQL Row-Level Security (RLS)** — so a logic bug in the app cannot, by itself, leak data across tenants.

Key architectural commitments:

- **Tenancy model:** Shared database, shared schema with a mandatory `tenant_id` discriminator on every row, protected by RLS. (See [Multi-Tenant Strategy](#multi-tenant-strategy) and [ADR-001](ADRs.md).)
- **Data/control plane split:** Blobs never transit the API for bulk transfer — clients upload/download directly to Blob Storage via **short-lived, scoped SAS URLs**. The API holds metadata, policy, and authorization.
- **Stateless compute:** All session/identity state lives in JWTs and the database, enabling horizontal autoscaling with no sticky sessions.
- **Async by design:** Virus scanning, preview generation, text extraction, and audit fan-out run on background workers off a queue, keeping the synchronous request path fast.
- **API-first:** Every capability is exposed through a versioned REST API; the React SPA is just the first consumer. This enables future mobile/integration clients without rework.
- **Immutable audit:** Every security-relevant action writes to an append-only, tamper-evident audit store with configurable retention and SIEM export.

The platform is deliberately built **multi-tenant-ready from day one** even though the MVP may deploy a single anchor tenant — the isolation primitives (RLS, tenant-scoped storage, tenant context) are foundational, not retrofitted.

---

## Architecture Principles

| Principle | What it means for FDMS | How it is realized |
|---|---|---|
| **Security First** | Default-deny; least privilege; encrypt everywhere | RBAC + RLS dual enforcement, TLS 1.2+, AES-256 at rest, signed URLs, malware scan before availability |
| **Multi-Tenant First** | Tenant is a first-class concept on every record and request | Mandatory `tenant_id`, RLS policies, tenant-scoped storage prefixes, tenant context middleware |
| **Cloud Native** | Containerized, elastic, managed services over self-managed | Azure Container Apps, managed PostgreSQL, Blob Storage, Key Vault, managed identities |
| **API First** | Versioned API is the contract; UI is a client | OpenAPI-described REST, semantic versioning, backward-compatible evolution |
| **Observability First** | You cannot operate what you cannot see; everything tenant-tagged | Structured logs, metrics, distributed tracing, tenant-aware dashboards & alerts |
| **Cost Efficient** | Pay for what is used; tier cold data | Storage lifecycle tiering (hot/cool/archive), autoscaling, per-tenant quotas |
| **Compliance Ready** | Controls present by design, certifiable later | Immutable audit, retention/legal hold, residency pinning, erasure/export capability |

---

## System Context

### Actors
| Actor | Description | Primary Interactions |
|---|---|---|
| **End User (Knowledge Worker)** | Authenticated tenant member | Upload, search, preview, share, download, version |
| **Manager / Folder Owner** | Owns folders, delegates access | Folder structure, grant/revoke, activity review |
| **Tenant Administrator** | Manages a single tenant | Users, roles, policy, audit, usage |
| **Platform Operator** | Provider-side SRE/admin | Tenant lifecycle, platform config, cross-tenant observability (no document content access by default) |
| **CISO / Compliance Officer** | Governance role within a tenant | Audit review, access reports, legal hold, export |
| **External Guest** | Recipient of a secure share link | Time-bound view/download of specific items |

### External Systems
| System | Role | Integration |
|---|---|---|
| **Microsoft Entra ID** | Identity provider (SSO, MFA, Conditional Access) | OIDC / OAuth 2.0; SCIM for provisioning |
| **Azure Blob Storage** | Document/blob data plane | SAS-tokenized direct client I/O; lifecycle tiering |
| **Azure Key Vault** | Secrets & encryption-key custody | Managed identity access; key rotation |
| **Malware Scanning Service** | Pre-availability file scanning | Async worker invocation on upload |
| **SIEM (tenant-side)** | Security monitoring | Audit log export / streaming |
| **Email / Notification Service** | Share notifications, alerts | Outbound transactional messaging |
| **Azure Monitor / Log Analytics** | Telemetry sink | Logs, metrics, traces, alerts |

### Trust Boundaries
1. **Public Internet ↔ Edge** — WAF / Azure Front Door / API Gateway terminates TLS, applies rate limiting and DDoS protection.
2. **Edge ↔ Application Tier** — Only authenticated, tenant-bound requests pass; JWT validated at the boundary.
3. **Application Tier ↔ Data Tier** — App connects to PostgreSQL with per-request tenant context; RLS enforces row visibility. No direct client-to-DB access.
4. **Application Tier ↔ Blob Storage** — Clients receive only short-lived scoped SAS URLs; no standing credentials on the client. Storage keys never leave the backend/Key Vault.
5. **Tenant ↔ Tenant** — Hard logical boundary; no path (API, search, share, or query) crosses it.
6. **Provider ↔ Tenant data** — Operators manage infrastructure and lifecycle but are isolated from document contents except via explicitly authorized, audited support access.

```
[Browser SPA] --TLS--> [Front Door/WAF + API Gateway] --TLS--> [FastAPI on Container Apps]
                                                                    |          |
                                          (metadata, authz, RLS)    |          | (async)
                                                                    v          v
                                                          [PostgreSQL]   [Queue -> Workers]
                                                                              |  (scan, preview, index, audit fan-out)
[Browser] <--scoped SAS URL-- [FastAPI] -- generates --> [Azure Blob Storage] <---'
[Entra ID] <--OIDC--> [SPA + FastAPI]      [Key Vault]      [Azure Monitor / Log Analytics]
```

---

## High-Level Architecture

### Frontend
- **React + TypeScript + Tailwind CSS** SPA, served as static assets via CDN (Azure Front Door / Static hosting).
- Authenticates via **MSAL** (Entra ID), holds short-lived access tokens in memory, refresh handled by the identity flow.
- Talks only to the versioned REST API; performs **direct-to-Blob** upload/download using SAS URLs issued by the API.
- Responsibilities: presentation, optimistic UX, upload chunking/resume orchestration, client-side validation (never authoritative).

### Backend
- **FastAPI** application, **stateless**, packaged as containers on **Azure Container Apps** with horizontal autoscaling (KEDA-driven on CPU/concurrency/queue depth).
- Layers: API/routing → request middleware (auth, tenant context, rate limit, correlation ID) → service/domain layer → data-access layer (sets RLS session context) → integrations (Blob, Key Vault, queue).
- **Background workers** (separate Container Apps revision/scale rule) consume a queue for: malware scanning, preview/thumbnail generation, text extraction for search, audit projection, lifecycle and notification tasks.

### Database
- **Azure Database for PostgreSQL (Flexible Server)** — the metadata and control plane: tenants, users, roles, folders, document/version metadata, shares, permissions, audit.
- **RLS enabled on all tenant-scoped tables**; application sets a per-connection tenant context.
- Read replicas for read-heavy workloads (search-by-metadata, listing); primary for writes. Connection pooling (PgBouncer / built-in pooler).

### Storage
- **Azure Blob Storage** is the document data plane. Tenant-segregated namespaces; versions stored as discrete immutable blobs.
- Lifecycle management tiers blobs hot → cool → archive based on access age and policy.

### Identity
- **Microsoft Entra ID** for authentication (OIDC), MFA/Conditional Access (delegated), SCIM provisioning, and group→role mapping.
- Per-tenant federation mapping (Entra tenant → FDMS tenant).

### Observability
- **Azure Monitor + Log Analytics + Application Insights**: structured logs, RED/USE metrics, distributed tracing, and alerting. All telemetry carries `tenant_id`, `correlation_id`, and actor identifiers (PRD §6 NFR-MAINT-2).

---

## Multi-Tenant Strategy

The PRD (§10) mandates logical multi-tenancy with strict per-tenant isolation, enforced at the database via RLS, scaling to 500+ tenants and millions of documents. Three canonical models were evaluated.

### 1. Shared DB, Shared Schema (single schema, `tenant_id` discriminator + RLS)
- **Advantages:** Lowest operational overhead; one schema to migrate; best density and cost efficiency at 500+ tenants; trivial cross-tenant platform analytics; fast tenant onboarding (insert a row).
- **Disadvantages:** Isolation depends on correct discriminator + RLS on *every* table; "noisy neighbor" risk on shared resources; blast radius of a bad migration spans all tenants.
- **Risks:** A missing RLS policy or unfiltered query leaks data; requires rigorous, automated guardrails.

### 2. Shared DB, Multi-Schema (one schema per tenant)
- **Advantages:** Stronger logical separation; per-tenant schema customization possible; isolation more intuitive.
- **Disadvantages:** Migrations must fan out across N schemas (operationally painful at 500+); catalog bloat and connection/planning overhead; weaker cross-tenant analytics.
- **Risks:** Schema-count scaling limits; migration drift between tenants; PostgreSQL performance degradation with thousands of schemas.

### 3. Database Per Tenant
- **Advantages:** Strongest isolation; per-tenant backup/restore, residency, and scaling; smallest blast radius.
- **Disadvantages:** Highest cost and ops complexity; provisioning latency; fleet-wide migration orchestration required; poor density for 500+ tenants.
- **Risks:** Cost explosion; operational toil; connection sprawl.

### Decision
**Adopt Model 1 — Shared DB, Shared Schema with a mandatory `tenant_id` on every tenant-scoped table, protected by PostgreSQL RLS.** This best fits the PRD's scale targets (500+ tenants, millions of docs), cost goals, and rapid-onboarding requirement (< 1 business day), while RLS provides database-enforced isolation that does not depend solely on application correctness.

**Guardrails (mandatory):** RLS forced on every tenant table (including for the table owner); a default-deny posture; automated CI checks that fail the build if any tenant-scoped table lacks an RLS policy; isolation integration tests in the pipeline; reserved capacity / quotas to bound noisy neighbors.

**Escape hatch:** The architecture supports promoting a high-compliance or very large tenant to a **dedicated database** later without changing the application's data-access contract (the tenant-context mechanism is identical). This is a future option (PRD residency, MT-8), not MVP scope. See [ADR-001](ADRs.md) and [ADR-006](ADRs.md).

---

## Tenant Isolation Strategy

Isolation is enforced at three layers — defense in depth (PRD SEC-6, SEC-7, MT-2/3/4).

### Application Layer
- **Tenant context middleware** resolves `tenant_id` from the validated JWT claims on every request and binds it to the request scope.
- All service and data-access calls require this context; there is no "ambient/global" data access path.
- Cross-tenant operations are reserved to Platform Operator flows and are explicit, separately authorized, and audited.
- The client is never trusted to assert its tenant; tenant is derived server-side from identity.

### Database Layer
- **RLS policies** on every tenant-scoped table filter rows by a session variable (e.g., a per-connection `app.tenant_id`) set by the data-access layer at the start of each unit of work.
- RLS is **FORCE**d so even table owners are constrained; policies are default-deny.
- Connections are returned to the pool only after the tenant context is reset, preventing context bleed across pooled connections.
- Platform/migration roles that must bypass RLS are tightly scoped and never used by request-serving code paths.

### Storage Layer
- Blobs are organized under a **per-tenant prefix/namespace** (logical container partitioning) so a tenant's objects share a path root.
- **SAS URLs are scoped to a single blob (or tenant prefix), least-privilege (read or write), and short-lived** — they cannot enumerate or reach another tenant's objects.
- Storage account keys never leave the backend; only the API mints SAS tokens (keys sourced from Key Vault).
- Optional future hardening: per-tenant container or storage account for tenants requiring physical separation/residency.

---

## Authentication Architecture

### Entra ID
- Microsoft Entra ID is the sole IdP for interactive users (PRD FR-AUTH-1/2). MFA and Conditional Access are **delegated to Entra** — FDMS honors but does not reimplement them (FR-AUTH-4).
- Each tenant's Entra directory is federated and mapped to an FDMS `tenant_id`. Multi-tenant app registration supports many customer directories.
- **JIT provisioning** on first sign-in (FR-AUTH-5) and **SCIM** for lifecycle provisioning/deprovisioning (FR-AUTH-6).

### OIDC
- **Authorization Code flow with PKCE** for the SPA (no implicit flow).
- Standard scopes/claims; group and role claims consumed for authorization mapping.
- Per-tenant issuer/authority validation ensures tokens are accepted only from the federated directory mapped to that tenant.

### JWT
- Access tokens are **JWTs validated on every request** at the API boundary: signature (JWKS), issuer, audience, expiry, and tenant claim.
- Validated claims populate the request's identity + tenant context. No server-side session store — **stateless** (enables horizontal scale).

### Token Lifecycle
- Short-lived access tokens; refresh handled via the OIDC refresh flow (FR-AUTH-7).
- **Revocation/rotation:** refresh-token revocation honored; token-version/`sid` checks support forced sign-out; JWKS rotation supported.
- Configurable idle and absolute session timeouts (FR-AUTH-3); secure token handling on the client (in-memory access token, HttpOnly where cookies are used, CSRF protection — PRD SEC-18).

---

## Authorization Architecture

### RBAC Model
Authorization is **default-deny** (PRD FR-RBAC-4, SEC-5) and enforced **server-side at both application and database layers** (FR-RBAC-8). Effective permission = union of role grants + resource-level grants, bounded by tenant policy (RBAC-1).

### Permission Hierarchy
| Role | Scope | Representative Capabilities |
|---|---|---|
| **Tenant Administrator** | Entire tenant | Manage users/roles/groups, tenant policy, all folders/documents, audit access/export |
| **Manager / Folder Owner** | Owned folders & descendants | Manage structure, grant/revoke access in scope, manage versions, view activity |
| **Contributor** | Granted resources | Upload, edit, create versions, preview, download, share (per policy) |
| **Viewer / Reader** | Granted resources | Preview and download (per policy); no edit/share |
| **Guest / External** | Specific shared items | Time-bound view/download of explicitly shared items only |

- Roles assignable to **individual users and to Entra ID groups** (FR-RBAC-2, RBAC-3).
- **Resource-level grants** on folders/documents; **folder inheritance** flows to children unless overridden (RBAC-4/5).
- **Custom roles** definable by Tenant Admins from a permission catalog (FR-RBAC-5, RBAC-6).
- Platform Operator is a **cross-tenant control-plane** role, deliberately excluded from document content by default.

### RLS Enforcement Strategy
RLS is the **second, independent gate** behind application authorization:
- Layer 1 (tenant): RLS filters every row by `tenant_id` (see [Tenant Isolation](#tenant-isolation-strategy)) — guarantees no cross-tenant leakage even if app authz is wrong.
- Layer 2 (resource): Effective permissions for a user on folders/documents are computed in the application/service layer (inheritance + explicit grants + role) and used to authorize the operation; the database additionally constrains visibility to the tenant.
- Rationale: tenant isolation is a hard, table-level invariant ideally suited to RLS; fine-grained per-resource ACL evaluation (inheritance, share links, expiry) is richer than RLS expresses cleanly and lives in the service layer, which is exhaustively tested and audited. This split keeps RLS simple/auditable while supporting complex sharing semantics. See [ADR-006](ADRs.md).

---

## Storage Architecture

### Blob Container Strategy
- Single logical storage strategy with **per-tenant prefixes** (`<tenant_id>/<folder-path-or-id>/<document_id>/<version_id>`), with the option to promote large/regulated tenants to dedicated containers/accounts.
- All access mediated by **short-lived, single-object, least-privilege SAS URLs** (PRD SEC-9, FR-DL-2). Clients never hold storage credentials.
- Uploads use **resumable/chunked** transfer (block blobs) for large files (FR-UP-2); the blob becomes referenceable in metadata only **after malware scan passes** (FR-UP-4).

### Document Lifecycle (Hot / Cool / Archive)
| Tier | When | Characteristics |
|---|---|---|
| **Hot** | Recently created/accessed, active versions | Low latency, higher storage cost — default for new and frequently accessed blobs |
| **Cool** | Infrequently accessed (e.g., 30+ days idle) | Lower storage cost, higher access cost — older versions, dormant documents |
| **Archive** | Rarely accessed, retained for compliance | Lowest cost, rehydration latency — long-tail retention, legal-hold cold copies |

- Azure Blob **lifecycle management policies** automate tier transitions by last-access/age; tenant policy and classification can pin or accelerate tiering.
- Archive rehydration is surfaced to users as an asynchronous "retrieval in progress" state.

### Version Storage Strategy
- **Immutable, copy-on-write versions** (PRD FR-VER-1/2): each upload of an existing document writes a **new blob**; prior versions are never overwritten.
- Metadata records the version chain (author, timestamp, size, checksum, optional comment); restore points an active pointer at a prior version without destroying history (FR-VER-3/4).
- Configurable per-tenant version retention limits prune old versions where policy allows (FR-VER-5), with older versions naturally tiered to cool/archive. See [ADR-010](ADRs.md).
- Content **checksums** enable integrity verification and optional dedup (FR-UP-5/7).

---

## Search Architecture

### Metadata Search (MVP)
- MVP search covers **file name, metadata, tags, owner, classification**, with **faceted filtering** (PRD §5.7, FR-SRCH-1/3).
- Backed by **PostgreSQL** indexing (B-tree/GIN on metadata, tags, and trigram/`tsvector` for name search), served from read replicas.
- **Permission- and tenant-scoped results**: RLS guarantees tenant scoping; the service layer intersects results with the user's effective resource permissions so users see only what they may access (FR-SRCH-4/5). This is non-negotiable and applied before results leave the API.

### Future Full-Text Search
- Content full-text search (PRD FR-SRCH-2, Phase 2) introduced via a **dedicated search service** (e.g., Azure AI Search / OpenSearch) fed asynchronously by workers that extract text on upload.
- The index is **partitioned/filtered by `tenant_id`**; queries always carry tenant + permission filters. Postgres remains the system of record; the search index is a derived, rebuildable projection.

### Future OCR
- For scanned/image documents (Phase 2), an **OCR worker** extracts text asynchronously and feeds the full-text index.
- OCR and extraction are decoupled from the upload path and never block availability; failures degrade gracefully (metadata-only searchability).

---

## Audit Architecture

### Immutable Events
- Every security-relevant action (auth, access, share, download, preview, admin, delete, permission change) emits an audit event (PRD §5.11, FR-AUD-1).
- Records are **append-only and tamper-evident** (FR-AUD-2): no updates/deletes; integrity protected via hash-chaining/sequence and write-once storage semantics.
- Each record captures **actor, action, target, tenant, timestamp, source IP, and result** (FR-AUD-3). Audit writes are produced on the request path and **projected asynchronously** to durable storage to avoid latency coupling, while guaranteeing eventual completeness.

### Retention
- **Configurable per-tenant retention** aligned to compliance (FR-AUD-5; e.g., 7 years for regulated tenants). Older audit data tiers to cheaper storage but remains queryable/exportable.

### Export
- Admins/CISOs can **search, filter, and export** audit logs scoped to their tenant (FR-AUD-4), and configure **streaming/export to an external SIEM** (FR-AUD-6).

### Compliance Support
- The immutable, exportable trail provides the evidentiary record for SOC 2, GDPR, HIPAA, and ISO 27001 (PRD §8). Audit is tenant-isolated like all other data.

---

## Security Architecture

### Encryption
- **In transit:** TLS 1.2+ (1.3 preferred) everywhere, including internal service hops (PRD SEC-1).
- **At rest:** AES-256 for blobs and database (SEC-2); platform-managed plus option for customer-managed keys (CMK) for regulated tenants.

### Secrets Management
- All secrets and encryption keys in **Azure Key Vault**; services authenticate via **managed identity** — no secrets in code, images, or config (SEC-3, SEC-11). Key rotation supported.

### Signed URLs
- All direct blob access via **short-lived, single-object, least-privilege SAS tokens** minted server-side (SEC-9). No standing client credentials; expiry bounds exposure.

### Malware Scanning
- Every upload is **scanned by an async worker before the blob is made referenceable/available** (SEC-8, FR-UP-4). Infected files are quarantined and the event audited.

### Rate Limiting
- Throttling at the edge/gateway and on sensitive endpoints (auth, share, download), with anomaly detection and abuse protection (SEC-13). Per-tenant and per-principal limits prevent resource monopolization.

### Threat Model Summary (STRIDE-oriented)
| Threat | Example | Primary Mitigation |
|---|---|---|
| **Spoofing** | Forged identity/token | Entra OIDC, JWT signature/issuer/audience validation, MFA (delegated) |
| **Tampering** | Altered documents/audit | Immutable versions, checksums, tamper-evident append-only audit |
| **Repudiation** | "I didn't do it" | Comprehensive immutable audit with actor/IP/result |
| **Information Disclosure** | Cross-tenant leak | RLS + app tenant context + scoped SAS + tenant-partitioned search |
| **Denial of Service** | Endpoint flooding | Edge WAF/DDoS, rate limiting, autoscaling, quotas |
| **Elevation of Privilege** | Role/permission abuse | Default-deny RBAC, server-side authz, dual-layer enforcement, escalation tests |
| **Malware propagation** | Infected upload shared out | Pre-availability scanning, quarantine |
| **Insider misuse** | Over-broad access | Least privilege, access reviews, anomaly detection, operator/content separation |

Secure SDLC (SEC-15): threat modeling, code review, SAST/DAST, dependency scanning, and security gates in CI/CD; periodic penetration testing (SEC-14).

---

## Compliance Architecture

| Framework | Architectural support |
|---|---|
| **GDPR** | Data-subject access/erasure flows, per-tenant residency pinning, processing records via audit, consent-aware sharing, export/portability (PRD CMP-2, CMP-7) |
| **SOC 2 (Type II)** | Access controls (RBAC/RLS), immutable audit, change management via CI/CD, monitoring/alerting, operational evidence (CMP-1) |
| **HIPAA Ready** | Encryption in transit/at rest, strict access control, full audit trail, BAA-ready operational posture for healthcare tenants (CMP-3) |
| **ISO 27001 Ready** | ISMS-aligned controls, documented risk management, secure SDLC, asset/access governance (CMP-4) |
| **Cross-cutting** | Region-pinned deployment (CMP-5), configurable retention & **legal hold** (CMP-6), tenant-isolated immutable audit (CMP-8) |

Certifications are post-launch organizational milestones; the architecture ensures the platform is **capable** of meeting them (PRD §8 note).

---

## Observability

Telemetry is **tenant-aware**: every log line, metric, and trace span carries `tenant_id`, `correlation_id`, principal, and route (PRD NFR-MAINT-2).

- **Logging:** Structured (JSON) application and audit-adjacent operational logs to Log Analytics; PII minimized and never logging document contents.
- **Metrics:** RED (Rate/Errors/Duration) for APIs and USE (Utilization/Saturation/Errors) for resources; business metrics (uploads, searches, shares) tagged per tenant; SLO dashboards for the 99.9% target and PRD latency budgets (search P95 < 2s, API P95 < 500ms).
- **Tracing:** Distributed tracing (OpenTelemetry → Application Insights) spanning SPA → API → DB → workers → Blob.
- **Alerting:** SLO-burn alerts, error-rate and saturation alerts, security alerts (auth anomalies, failed-authz spikes, isolation-test failures), and per-tenant capacity alerts. Paging via on-call rotation.
- **Tenant-aware monitoring:** Operators can slice all signals per tenant to detect noisy neighbors, isolate incidents, and report per-tenant SLAs without exposing document content.

---

## Scalability Strategy

Targets: 50,000+ concurrent users, 500+ tenants, millions of documents, 99.9% SLA (PRD §6).

### Horizontal Scaling
- **Stateless FastAPI** on Azure Container Apps autoscales on CPU, concurrency, and **queue depth** (KEDA). No sticky sessions (state is in JWT + DB). Independent scaling of API vs. worker pools.

### Database Scaling
- Vertical scale of the PostgreSQL Flexible Server primary; **read replicas** offload listing/metadata-search reads; **connection pooling** (PgBouncer) to handle high connection counts.
- Future-proofing: table partitioning for the largest tables (audit, document versions) by time/tenant; the architecture preserves the option to shard the largest tenants to dedicated databases via the unchanged tenant-context contract.

### Storage Scaling
- Azure Blob Storage scales effectively without capacity planning; **direct client I/O** keeps bulk transfer off the API tier entirely, so storage throughput does not bottleneck compute.

### Search Scaling
- MVP metadata search scales via Postgres indexes + read replicas. Phase-2 full-text search moves to a horizontally scalable, tenant-partitioned search service, decoupling search load from the transactional database.

---

## Disaster Recovery

Targets: **RTO ≤ 4 hours, RPO ≤ 15 minutes** (PRD NFR-AVAIL-2/3); durability ≥ 11 nines (NFR-REL-1).

- **Backup:** Automated PostgreSQL backups with **point-in-time restore** (PITR) and transaction-log shipping to meet the 15-minute RPO; **geo-redundant storage (GRS/RA-GRS)** for blobs; Key Vault soft-delete + purge protection; infrastructure-as-code for reproducible environment rebuild.
- **Restore:** Documented, automated restore runbooks; environment reconstructed from IaC + DB PITR + replicated blobs.
- **RPO ≤ 15m:** Continuous log archiving and geo-replication bound data loss to ≤ 15 minutes.
- **RTO ≤ 4h:** Standby region / rapid redeploy from IaC; failover runbook targeting < 4 hours to restore service.
- **Validation:** **Quarterly restore tests** and periodic DR game-days (PRD NFR-REL-2).

---

## Cost Optimization

| Lever | Approach |
|---|---|
| **Storage tiering** | Lifecycle policies move idle/older blobs hot → cool → archive; classification can pin tiers (PRD NFR-COST-1) |
| **Autoscaling** | Scale-to-need (and scale-to-zero for idle worker pools) on Container Apps; avoid over-provisioning |
| **Resource limits** | Per-tenant quotas (storage, request, upload size) bound noisy neighbors and cost; alerting on outliers |
| **Right-sizing** | Read replicas only where read load justifies; reserved capacity for predictable baseline; spot/consumption for bursty async work |
| **Data-plane offload** | Direct-to-Blob transfer avoids paying for compute to proxy large files |

---

## Technical Risks

| # | Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|---|
| TR-1 | **Missing/incorrect RLS policy** leaks cross-tenant data | Critical | Low–Med | Force RLS on all tenant tables; CI guard fails build if policy absent; isolation integration tests; pen test |
| TR-2 | **Pooled-connection tenant context bleed** | Critical | Low | Reset tenant context on connection release; tests asserting isolation under pooling |
| TR-3 | **SAS URL scope too broad / long-lived** | High | Low–Med | Single-object, least-privilege, short-TTL tokens; centralized minting; automated policy tests |
| TR-4 | **Noisy neighbor** degrades shared DB/compute | High | Medium | Per-tenant quotas, rate limits, autoscaling, read replicas, capacity alerts |
| TR-5 | **Audit pipeline loss/gap** undermines compliance | High | Low | Durable queue with at-least-once delivery, tamper-evident chain, reconciliation checks |
| TR-6 | **Malware bypass** (file available before scan) | High | Low | Block referenceability until scan passes; quarantine; scan-failure alerts |
| TR-7 | **Shared-schema migration error** hits all tenants | High | Medium | Backward-compatible/expand-contract migrations, staging rehearsal, automated rollback |
| TR-8 | **Search results leak unauthorized items** | High | Low–Med | Permission intersection enforced server-side before return; tests; tenant-partitioned index |
| TR-9 | **Entra integration variance** across tenant directories | Medium | Medium | Standardize OIDC/SCIM; per-tenant issuer validation; tested onboarding playbooks |
| TR-10 | **Cost overrun** at scale (storage/egress/compute) | Medium | Medium | Tiering, quotas, autoscaling, cost dashboards & budget alerts |

> Cross-reference: these technical risks complement the product/business risks in [PRD §14](PRD.md). Decisions underpinning these mitigations are recorded in [ADRs.md](ADRs.md) and sequenced in [SprintPlan.md](SprintPlan.md).

---

*End of Document — FDMS Architecture v1.0*
