# IDEA AGENT V2 TASK

═══════════════════════════════════════════════════════

# PROJECT OVERVIEW

────────────────

Project Name    : File Sharing & Document Management System (FDMS)
Domain          : General Enterprise (adaptable to Legal, Finance, Healthcare, Government, Education)
Company Profile : Mid-to-Large Enterprise (500–10,000 employees), multi-department, multi-region
Build Type      : Greenfield SaaS Product
Monetization    : B2B SaaS — Per-Tenant Seat-Based Pricing
Primary Audience: Product Team, CTO, CIO, Enterprise Architects, Investors

# OBJECTIVE

─────────

Design and validate a product discovery document for an enterprise-grade, multi-tenant File Sharing & Document Management System (FDMS) that enables organizations to securely upload, store, organize, search, share, govern, and version documents using Azure cloud services.

The output must be executive-ready, enterprise-focused, data-informed, and grounded in real business pain points. Avoid generic content, placeholders, or implementation details.

═══════════════════════════════════════════════════════
SECTION REQUIREMENTS
═══════════════════════════════════════════════════════

## 1. EXECUTIVE SUMMARY

Provide:

* Business overview
* Problem overview
* Proposed solution
* Target market
* Key differentiators
* Expected business impact

Audience:

* CTO
* CIO
* Product Leadership
* Investors

Length:
~ Half Page

---

## 2. PRODUCT VISION

Provide:

### Vision Statement

* 2–3 concise sentences

### Product Tagline

* One-line positioning statement

### North Star Goal

* 3-year vision

### Mission Statement

* Why the product exists

### Strategic Objectives

* Top 3 strategic objectives

---

## 3. TARGET USERS & USER PERSONAS

Define exactly 4 personas.

For each persona provide:

### Persona Information

* Name
* Role
* Department
* Seniority
* Tech Literacy Level

### Goals

* 2–3 goals

### Pain Points

* 2–3 frustrations

### Daily Activities

* Document-related activities

### Success Criteria

* What success looks like

Mandatory Personas:

1. IT Administrator / System Administrator
2. Department Head / Business Manager
3. End User / Knowledge Worker
4. Compliance & Audit Officer

---

## 4. PROBLEM STATEMENT

Use the structure:

"Today, [user] struggles with [problem] when [context], which causes [impact]. There is no solution that [gap]. FDMS solves this by [approach]."

Include:

### Quantified Pain Points

* 3–5 pain points
* Use industry benchmarks if required
* Clearly label estimates

### Root Causes

* Organizational causes
* Process causes
* Technology causes

### Hair-On-Fire Problem

Identify the #1 problem the MVP must solve.

---

## 5. BUSINESS VALUE

Analyze value across:

### Cost Savings

### Productivity Gains

### Risk Reduction

### Operational Efficiency

### Compliance Improvements

For each:

* Description
* Business impact
* Expected outcome

Include:

### Build vs Buy Rationale

Explain:

* Why an organization would build FDMS
* Why existing tools may not fully satisfy requirements

Do NOT perform detailed competitor comparisons.
That belongs to Feasibility Analysis.

---

## 6. MVP SCOPE

Classify features as:

### P0 — Launch Critical

### P1 — Important

### P2 — Nice To Have

For each P0 feature:

Provide:

* Feature Name
* Description
* User Story
* Acceptance Criteria

Minimum P0 features:

* Authentication
* Folder Management
* Document Upload
* Document Download
* Metadata Management
* Search
* Sharing
* Permissions
* Audit Logging
* Version Management

---

## 7. MVP USER JOURNEYS

Create detailed journeys for:

### A. Document Upload & Storage

### B. Document Search & Retrieval

### C. Secure Sharing & Permission Management

### D. Version Control & Audit Trail

For each journey provide:

* Trigger
* Steps (3–5)
* Outcome
* User Emotional State

---

## 8. OUT-OF-SCOPE FOR MVP

List at least 10 items.

For each:

* Feature
* Reason Deferred

Examples:

* AI Summaries
* OCR
* Workflow Automation
* E-Signatures
* Enterprise Content Management
* Offline Sync

---

## 9. MULTI-TENANCY DEFINITION

Define:

### Tenant Definition

What constitutes a tenant?

### Tenant Lifecycle

* Onboarding
* Active Usage
* Offboarding
* Data Export

### Data Isolation Requirements

### Permission Boundaries

* Platform Admin
* Tenant Admin
* Manager
* Contributor
* Viewer

---

## 10. NON-FUNCTIONAL EXPECTATIONS

Define business expectations only.

Do NOT design solutions.

Include:

### Performance Expectations

* Upload latency
* Download latency
* Search response time

### Scalability Expectations

* Concurrent users
* Tenant growth

### Availability Expectations

* Uptime goals

### Reliability Expectations

* Backup expectations
* Recovery expectations

### Storage Expectations

* File sizes
* Upload volume
* Storage growth

---

## 11. COMPLIANCE & GOVERNANCE

Define expectations for:

### Audit Trails

### Document Retention

### Legal Hold

### Access Reviews

### Data Residency

### Regulatory Requirements

Consider:

* GDPR
* SOC 2
* HIPAA (future)
* ISO 27001

Separate:

* MVP Requirements
* Future Requirements

---

## 12. SEARCH & DISCOVERY EXPECTATIONS

Define:

### Search Experience

### Metadata Search

### Full-Text Search Expectations

### Search Accuracy

### Search Performance

### User Discoverability Requirements

No implementation details.

---

## 13. STORAGE ASSUMPTIONS

Estimate:

### Average Tenant Storage

### Large Tenant Storage

### Monthly Growth

### Archival Needs

### Hot vs Cold Access Patterns

### Retention Assumptions

Clearly mark all assumptions.

---

## 14. SUCCESS METRICS

Organize into:

### Business KPIs

Examples:

* MRR
* Tenant Retention
* Churn

### Product KPIs

Examples:

* Upload Volume
* Search Success Rate
* Active Users

### User Satisfaction KPIs

Examples:

* NPS
* Support Tickets
* Onboarding Completion

For each metric provide:

* Name
* Target
* Measurement Method
* Timeframe (30/60/90 Days)

---

## 15. RISKS & ASSUMPTIONS

Organize into:

### Business Risks

### Technical Risks

### Compliance Risks

### Operational Risks

### Assumption Risks

For each:

* Risk
* Likelihood (H/M/L)
* Impact (H/M/L)
* Mitigation Strategy

---

## 16. CHANGE MANAGEMENT RISKS

Identify:

* User Adoption Risks
* Training Challenges
* Migration Resistance
* Shadow IT Risks
* Existing Tool Replacement Risks

Provide mitigation recommendations.

---

## 17. FUTURE ROADMAP

Create:

### Phase 2 (3–6 Months)

### Phase 3 (6–12 Months)

### Phase 4 (12–18 Months)

Each phase:

* 3–5 features
* Business rationale
* Customer value

Highlight features requiring:

* Microsoft Entra ID Advanced Features
* Azure AI Search
* Azure Purview
* Azure Cognitive Services

---

## 18. QUESTIONS FOR FEASIBILITY AGENT

Generate:

### Top 10 Business Validation Questions

### Top 10 Technical Unknowns

### Top 10 Product Assumptions

These become direct inputs for the Feasibility Agent.

═══════════════════════════════════════════════════════
TECHNOLOGY CONTEXT
(REFERENCE ONLY — DO NOT DESIGN IMPLEMENTATION)
═══════════════════════════════════════════════════════

Backend:

* FastAPI
* PostgreSQL
* SQLAlchemy
* Alembic

Frontend:

* React
* TypeScript
* Tailwind CSS

Cloud:

* Azure Blob Storage
* Microsoft Entra ID

Security:

* RBAC
* PostgreSQL Row-Level Security (RLS)
* Multi-Tenant Architecture

Compliance:

* GDPR
* SOC 2
* Audit Logging

═══════════════════════════════════════════════════════
OUTPUT FORMAT
═══════════════════════════════════════════════════════

Format:

* Markdown
* Professional Tables
* H2/H3 Headers

Tone:

* Executive-Friendly
* Enterprise-Focused
* Product Strategy Oriented

Avoid:

* Generic Content
* Placeholder Text
* Database Schemas
* API Specifications
* Architecture Diagrams
* Technology Design
* Code

Deliverables:

1. Executive Summary
2. Product Vision & Mission
3. User Personas
4. Problem Statement
5. Business Value
6. MVP Scope
7. User Journeys
8. Out-of-Scope Items
9. Multi-Tenancy Definition
10. Non-Functional Expectations
11. Compliance & Governance
12. Search Expectations
13. Storage Assumptions
14. Future Roadmap
15. Risks & Assumptions
16. Success Metrics
17. Questions For Feasibility Agent

STRICT CONSTRAINT:
This is a Product Discovery and Business Validation document only.
Do NOT generate architecture, database design, API contracts, deployment plans, infrastructure design, or implementation details.
