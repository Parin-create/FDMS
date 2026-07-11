# FDMS — Architecture Decision Records (ADRs)

| Field | Value |
|---|---|
| **Document Title** | FDMS — Architecture Decision Records |
| **Version** | 1.0 |
| **Status** | Draft for Architecture Review |
| **Source of Truth** | [docs/PRD.md](PRD.md) · [docs/Architecture.md](Architecture.md) |
| **Last Updated** | 2026-06-23 |
| **Classification** | Internal — Confidential |

> Each ADR follows: **Context · Decision · Alternatives · Pros · Cons · Consequences.** Status values: Proposed / Accepted / Superseded.

## Index
| ADR | Title | Status |
|---|---|---|
| [ADR-001](#adr-001--multi-tenant-model) | Multi-Tenant Model | Accepted |
| [ADR-002](#adr-002--postgresql-as-the-primary-datastore) | PostgreSQL as Primary Datastore | Accepted |
| [ADR-003](#adr-003--fastapi-as-the-backend-framework) | FastAPI as Backend Framework | Accepted |
| [ADR-004](#adr-004--azure-blob-storage-for-documents) | Azure Blob Storage for Documents | Accepted |
| [ADR-005](#adr-005--microsoft-entra-id-for-identity) | Microsoft Entra ID for Identity | Accepted |
| [ADR-006](#adr-006--rls-enforcement-strategy) | RLS Enforcement Strategy | Accepted |
| [ADR-007](#adr-007--search-strategy) | Search Strategy | Accepted |
| [ADR-008](#adr-008--audit-logging-strategy) | Audit Logging Strategy | Accepted |
| [ADR-009](#adr-009--deployment-platform) | Deployment Platform | Accepted |
| [ADR-010](#adr-010--versioning-strategy) | Versioning Strategy | Accepted |

---

## ADR-001 — Multi-Tenant Model

**Status:** Accepted

### Context
FDMS must serve 500+ tenants and millions of documents with strict per-tenant isolation, rapid onboarding (< 1 business day), and cost-efficient unit economics (PRD §10, §3 BG-4/BG-5). We must choose how tenant data is partitioned in PostgreSQL.

### Decision
Use **Shared Database, Shared Schema** with a mandatory `tenant_id` discriminator on every tenant-scoped table, enforced by **PostgreSQL Row-Level Security (RLS)**. Provide an escape hatch to promote individual high-compliance/large tenants to a dedicated database later without changing the data-access contract.

### Alternatives
- **Shared DB, Multi-Schema** (one schema per tenant).
- **Database per tenant.**

### Pros
- Highest density and lowest cost at 500+ tenants.
- Single schema → simplest migrations and operations.
- Instant onboarding (create a tenant row).
- Database-enforced isolation via RLS, independent of app correctness.
- Straightforward cross-tenant platform analytics.

### Cons
- Isolation correctness depends on RLS being present on every table.
- Shared resources create noisy-neighbor potential.
- A bad migration affects all tenants (large blast radius).

### Consequences
- RLS is **FORCE**d and default-deny on all tenant tables; CI fails if any tenant table lacks a policy (see [ADR-006](#adr-006--rls-enforcement-strategy)).
- Per-tenant quotas and rate limits required to bound noisy neighbors.
- Expand-contract migration discipline and staging rehearsal required.
- Future dedicated-DB promotion is supported by keeping tenant context abstract.

---

## ADR-002 — PostgreSQL as the Primary Datastore

**Status:** Accepted

### Context
We need a transactional system of record for tenants, users, roles, folders, document/version metadata, shares, permissions, and audit — with strong consistency, rich querying, and a native mechanism for tenant isolation (PRD §5, §10, §11).

### Decision
Use **Azure Database for PostgreSQL (Flexible Server)** as the primary metadata/control-plane datastore, leveraging **native RLS** for tenant isolation, plus indexing (B-tree/GIN/trigram/`tsvector`) for MVP metadata search.

### Alternatives
- Azure SQL Database (SQL Server).
- Cosmos DB (NoSQL).
- MySQL / MariaDB.

### Pros
- First-class **RLS** — central to our isolation strategy.
- Mature, standards-based, strong ACID guarantees.
- Powerful indexing/full-text features cover MVP search without extra infrastructure.
- Managed service with PITR, replicas, and pooling on Azure.
- Aligns with the PRD reference stack.

### Cons
- Horizontal write scaling requires deliberate design (partitioning/sharding) at extreme scale.
- RLS adds query-planning considerations and must be tested for performance.
- Cross-schema/extreme multi-tenant tuning needs expertise.

### Consequences
- Read replicas + connection pooling are part of the baseline.
- Largest tables (audit, versions) planned for time/tenant partitioning.
- A dedicated full-text search service is deferred to Phase 2 (see [ADR-007](#adr-007--search-strategy)).

---

## ADR-003 — FastAPI as the Backend Framework

**Status:** Accepted

### Context
The backend must be API-first, high-throughput, container-friendly, and productive for a Python team, exposing a versioned REST API consumed by the React SPA and future clients (PRD §6, Architecture API-first principle).

### Decision
Use **FastAPI** (async Python) for the backend API and worker orchestration, packaged as stateless containers.

### Alternatives
- Django REST Framework.
- Node.js (NestJS/Express).
- Go (Gin/Echo) or .NET (ASP.NET Core).

### Pros
- Native async → high concurrency for I/O-bound document workloads.
- Built-in OpenAPI generation → supports API-first contract.
- Pydantic validation improves input safety (PRD SEC-12).
- Lightweight, container-friendly, fast startup → good for autoscaling.
- Strong Python ecosystem for Azure SDKs, auth, and async workers.

### Cons
- Less "batteries-included" than Django (admin, ORM conventions chosen separately).
- Python CPU-bound throughput lower than Go/.NET (mitigated by offloading heavy work to workers and Blob).
- Team must enforce structure/conventions explicitly.

### Consequences
- Heavy/blocking work (scan, preview, OCR, indexing) runs on **background workers**, not the request path.
- OpenAPI spec is the published contract; semantic versioning applies.
- Stateless design mandated to enable horizontal scaling (see [ADR-009](#adr-009--deployment-platform)).

---

## ADR-004 — Azure Blob Storage for Documents

**Status:** Accepted

### Context
Documents (potentially large, millions of objects) must be stored durably and cost-effectively, with direct client transfer, lifecycle tiering, and immutable versioning (PRD §5.3/5.4, NFR-REL-1, NFR-COST-1).

### Decision
Use **Azure Blob Storage** as the document data plane, with per-tenant prefixes, **short-lived scoped SAS URLs** for direct client I/O, lifecycle tiering (hot/cool/archive), and immutable per-version blobs.

### Alternatives
- Store documents as BLOBs in PostgreSQL.
- AWS S3 / GCS.
- Azure Files (SMB/NFS share).

### Pros
- Practically unlimited, highly durable (≥ 11 nines) object storage.
- Direct-to-Blob transfer offloads bulk I/O from the API tier.
- Native lifecycle tiering for cost optimization.
- SAS tokens enable least-privilege, time-bound access without standing client credentials.
- Geo-redundancy supports DR/RPO.

### Cons
- Eventual-consistency and rehydration latency for archive tier.
- SAS scoping/expiry must be implemented carefully to avoid over-broad access.
- Metadata/state must be coordinated between Postgres and Blob (two stores).

### Consequences
- Blob becomes referenceable only **after malware scan** (PRD SEC-8).
- SAS minting centralized server-side; storage keys live in Key Vault (see [ADR-005](#adr-005--microsoft-entra-id-for-identity) note on managed identity, and Architecture §Security).
- Document metadata (system of record) stays in PostgreSQL; blobs hold content.

---

## ADR-005 — Microsoft Entra ID for Identity

**Status:** Accepted

### Context
Target customers are Microsoft-centric enterprises requiring SSO, MFA, Conditional Access, and lifecycle provisioning, mapped to multi-tenant FDMS (PRD §5.1, A-1).

### Decision
Use **Microsoft Entra ID** as the sole IdP via **OIDC (Authorization Code + PKCE)**, with per-tenant directory federation, **JIT provisioning**, **SCIM** lifecycle, and group→role mapping. Services authenticate to Azure resources via **managed identities**.

### Alternatives
- Auth0 / Okta.
- Custom auth (local accounts + passwords).
- Keycloak (self-hosted).

### Pros
- Native fit for the enterprise target market; frictionless SSO.
- MFA/Conditional Access **delegated** to Entra — no reimplementation (PRD FR-AUTH-4).
- SCIM + JIT automate user lifecycle.
- Managed identities eliminate stored secrets for Azure resource access (PRD SEC-11).

### Cons
- Vendor coupling to the Microsoft identity ecosystem.
- Per-tenant directory configuration variance adds onboarding complexity.
- Non-Entra customers would require future federation work.

### Consequences
- Stateless **JWT validation** at the API boundary; per-tenant issuer/audience checks.
- Onboarding playbooks standardize Entra federation/SCIM setup.
- Tenant→Entra-directory mapping is part of tenant provisioning (see [ADR-001](#adr-001--multi-tenant-model)).

---

## ADR-006 — RLS Enforcement Strategy

**Status:** Accepted

### Context
Tenant isolation is a critical, non-negotiable invariant (PRD MT-2/3/4, SEC-6/7). We must decide how much authorization to push into PostgreSQL RLS versus the application layer.

### Decision
Use a **two-layer model**: RLS enforces **tenant-level isolation** on every tenant-scoped table (forced, default-deny, keyed on a per-connection tenant context), while **fine-grained resource authorization** (folder inheritance, explicit grants, share links/expiry, roles) is computed in the **application/service layer**. Both gates apply to every data operation.

### Alternatives
- **RLS for everything** (encode all resource ACLs in RLS policies).
- **Application-only** authorization (no RLS).
- Database-per-tenant to sidestep RLS (rejected in [ADR-001](#adr-001--multi-tenant-model)).

### Pros
- RLS guarantees no cross-tenant leakage even if application authz has a bug (defense in depth).
- Tenant isolation as a simple, auditable table-level invariant.
- Complex/expressive sharing semantics live where they are easiest to test and evolve.
- Clear separation of concerns between "which tenant" and "which resource."

### Cons
- Two places enforce authorization → must stay coherent.
- Application layer remains responsible for resource-level correctness (must be exhaustively tested).
- RLS adds query-planning overhead requiring performance validation.

### Consequences
- RLS is **FORCE**d on all tenant tables; CI guard fails the build if a tenant table lacks a policy.
- Pooled connections must **reset tenant context** on release to prevent bleed.
- Isolation and privilege-escalation **integration tests** are mandatory in the pipeline; permission intersection enforced before search results are returned (see [ADR-007](#adr-007--search-strategy)).

---

## ADR-007 — Search Strategy

**Status:** Accepted

### Context
MVP requires permission- and tenant-scoped search over file name, metadata, tags, and owner with faceted filtering; full-text content search and OCR are deferred to Phase 2 (PRD §5.7, FR-SRCH-*, Roadmap Phase 2).

### Decision
For **MVP**, implement metadata search **inside PostgreSQL** (B-tree/GIN indexes, trigram/`tsvector` for name search) served from read replicas. For **Phase 2**, introduce a **dedicated, tenant-partitioned search service** (e.g., Azure AI Search / OpenSearch) fed asynchronously for full-text and OCR, with Postgres remaining the system of record.

### Alternatives
- Dedicated search engine from day one.
- External search-as-a-service for MVP.
- Naive `LIKE` queries without proper indexing.

### Pros
- No additional infrastructure for MVP → faster delivery, lower cost.
- Reuses existing transactional store, consistent with metadata.
- Clean upgrade path: search index becomes a rebuildable projection in Phase 2.
- Tenant + permission filtering applied server-side guarantees correct scoping.

### Cons
- Postgres full-text is weaker than a dedicated engine at very large scale (hence Phase-2 split).
- Phase-2 introduces an eventually-consistent derived index to operate and reconcile.

### Consequences
- **Permission intersection enforced before results are returned** in all phases (PRD FR-SRCH-4); RLS guarantees tenant scope (PRD FR-SRCH-5).
- Phase-2 index is partitioned/filtered by `tenant_id`; text extraction/OCR run on async workers.
- Search load moves off the transactional DB in Phase 2 (see Architecture §Search Scaling).

---

## ADR-008 — Audit Logging Strategy

**Status:** Accepted

### Context
All security-relevant actions must be captured in an immutable, tamper-evident, tenant-isolated, exportable trail with configurable retention and SIEM export (PRD §5.11, §8).

### Decision
Emit audit events on the request path and **project them asynchronously** (via a durable queue) into an **append-only, tamper-evident** audit store with **hash-chaining/sequence** integrity, per-tenant retention, and SIEM export/streaming.

### Alternatives
- Synchronous writes to the same OLTP tables on the request path.
- Application logs only (no structured audit store).
- Third-party audit SaaS as the system of record.

### Pros
- Async projection avoids coupling audit durability to request latency (PRD API P95 < 500ms).
- Append-only + hash-chain gives tamper evidence (PRD FR-AUD-2).
- Per-tenant retention and export satisfy varied compliance regimes.
- Decoupled store can be tiered/partitioned independently for cost and scale.

### Cons
- Eventual consistency between action and audit visibility (bounded, monitored).
- Requires at-least-once delivery + reconciliation to guarantee completeness.
- Additional pipeline component to operate and monitor.

### Consequences
- Durable queue with at-least-once delivery and reconciliation checks (TR-5 mitigation).
- Audit records carry actor/action/target/tenant/timestamp/IP/result (PRD FR-AUD-3).
- Audit data is tenant-isolated and access-controlled like all other data; export to SIEM configurable per tenant.

---

## ADR-009 — Deployment Platform

**Status:** Accepted

### Context
We need elastic, container-based hosting with zero-downtime deploys, scale-to-need, and low operational overhead, supporting both API and async worker workloads (PRD §6 NFR-SCAL/AVAIL/MAINT).

### Decision
Deploy on **Azure Container Apps** for both the stateless FastAPI API and background workers, using **KEDA-based autoscaling** (CPU/concurrency/queue depth), with infrastructure defined as code.

### Alternatives
- Azure Kubernetes Service (AKS).
- Azure App Service.
- VM-based / self-managed orchestration.

### Pros
- Serverless containers: autoscaling (incl. scale-to-zero for idle workers) without managing a cluster.
- Native KEDA scaling on queue depth fits the async worker model.
- Lower operational overhead than AKS; supports zero-downtime rolling revisions.
- Aligns with the PRD reference stack.

### Cons
- Less low-level control than AKS for complex networking/operators.
- Platform constraints may require workarounds for unusual workloads.
- Some lock-in to the Azure Container Apps model.

### Consequences
- Backend must remain **stateless** (state in JWT + DB) — reinforces [ADR-003](#adr-003--fastapi-as-the-backend-framework).
- API and worker pools scale independently with separate scaling rules.
- IaC + rolling revisions underpin zero-downtime deploys and DR rebuild (Architecture §DR).

---

## ADR-010 — Versioning Strategy

**Status:** Accepted

### Context
Documents require immutable version history where each upload creates a new version (never an overwrite), with view/restore of prior versions and configurable retention (PRD §5.10, FR-VER-*).

### Decision
Use **copy-on-write, immutable per-version blobs**: each new upload writes a distinct blob; PostgreSQL holds the version chain metadata and an active-version pointer. Restore re-points to a prior version without destroying history. Per-tenant retention prunes old versions where policy allows; older versions tier to cool/archive.

### Alternatives
- Rely solely on Azure Blob native versioning/snapshots.
- Mutable single blob with diff/delta storage.
- Overwrite with backup copies.

### Pros
- True immutability and complete history (PRD FR-VER-1/2).
- Metadata-driven chain enables rich version info, restore, and retention policy in one place.
- Integrity via per-version checksums; supports legal hold/compliance.
- Older versions tier down for cost (NFR-COST-1).

### Cons
- Higher storage footprint than delta-based approaches (mitigated by tiering + retention limits).
- Application owns version-chain consistency between Postgres and Blob.
- Restore semantics and retention pruning must be carefully specified.

### Consequences
- Version metadata (author/timestamp/size/checksum/comment) maintained in Postgres (PRD FR-VER-4).
- Lifecycle policies tier old versions; per-tenant retention limits configurable (FR-VER-5).
- Coordinates with [ADR-004](#adr-004--azure-blob-storage-for-documents) (blob layout) and [ADR-008](#adr-008--audit-logging-strategy) (version events audited).

---

*End of Document — FDMS ADRs v1.0*
