# Business Logic Implementation Backlog

This backlog converts the recent business-logic and competitive-decoupling audit into executable work items.

## Prioritization Model

- `P0`: Must complete before enterprise-scale rollout or regulated customer onboarding.
- `P1`: Should complete in current quarter to improve reliability, trust, and conversion.
- `P2`: Strategic growth items for competitive displacement and monetization.

Scoring legend:

- Impact: `1` (low) to `5` (very high)
- Effort: `1` (low) to `5` (very high)
- Priority Score: `impact * 2 - effort`

## Epic E1: Tenant Isolation Hardening (P0)

### BL-001 Add organisation_id to vessel latest and vessel position

- Priority: `P0`
- Impact: `5`
- Effort: `4`
- Priority Score: `6`
- Owner: Data Platform + Backend
- Problem: Vessel records are not tenant-scoped, creating cross-tenant exposure risk.
- Scope:
  - Add `organisation_id` to vessel tables and related ORM models.
  - Backfill existing rows by trusted mapping strategy.
  - Add indexes for `(organisation_id, mmsi)` and query hot paths.
- Acceptance Criteria:
  - Vessel read endpoints return only tenant-scoped data for non-super-admin users.
  - Tenant isolation tests cover list/detail/track endpoints.
  - Migration includes deterministic backfill and rollback path.
- Dependencies: None
- File Targets:
  - `apps/api/app/modules/vessels/models.py`
  - `apps/api/alembic/versions/*`
  - `apps/api/app/api/v1/vessels.py`

### BL-002 Enforce org filtering in all vessel query paths

- Priority: `P0`
- Impact: `5`
- Effort: `3`
- Priority Score: `7`
- Owner: Backend API
- Problem: Some query paths rely on non-tenant-scoped entities.
- Scope:
  - Reuse org-scope helpers for all vessel/position read and write paths.
  - Add explicit super-admin bypass tests.
- Acceptance Criteria:
  - No vessel query for viewer/analyst/admin can return another org's records.
  - Security regression tests pass for each role.
- Dependencies: `BL-001`
- File Targets:
  - `apps/api/app/modules/auth/org_scope.py`
  - `apps/api/app/api/v1/vessels.py`

## Epic E2: Idempotent Alert and Incident Lifecycle (P0)

### BL-003 Add idempotency key for alert persistence

- Priority: `P0`
- Impact: `5`
- Effort: `3`
- Priority Score: `7`
- Owner: Detection Pipeline + Backend
- Problem: Worker retries can create duplicate alert/incident records.
- Scope:
  - Define deterministic idempotency key using canonical event identity (org, source event id when present, mmsi, rule type, normalized event time bucket, evidence hash).
  - Normalize timestamp precision/timezone before key derivation and persist canonical key material for debugging.
  - Add database uniqueness guard and upsert behavior.
- Acceptance Criteria:
  - Replaying identical worker payloads does not create duplicate alerts.
  - Semantically equivalent payloads with different timestamp formatting/precision still map to one alert record.
  - Duplicate prevention covered by integration tests with forced retry.
- Dependencies: `BL-001`
- File Targets:
  - `apps/api/app/modules/alerts/models.py`
  - `apps/api/app/services/workers/alert_worker.py`
  - `apps/api/alembic/versions/*`

### BL-004 Prevent duplicate incident creation per alert idempotency group

- Priority: `P0`
- Impact: `4`
- Effort: `2`
- Priority Score: `6`
- Owner: Backend API
- Problem: Auto-incident path can duplicate after partial failures.
- Scope:
  - Make incident creation conditional/idempotent with explicit conflict handling.
  - Add worker transaction boundary checks.
- Acceptance Criteria:
  - Exactly one incident exists for equivalent alert events under retry storms.
  - No orphan incidents without corresponding alert record.
- Dependencies: `BL-003`
- File Targets:
  - `apps/api/app/modules/incidents/service.py`
  - `apps/api/app/services/workers/alert_worker.py`

## Epic E3: Compliance-Grade Auditability (P0)

### BL-005 Add audit events for system-created incidents

- Priority: `P0`
- Impact: `5`
- Effort: `2`
- Priority Score: `8`
- Owner: Security + Backend
- Problem: System-generated incident creation lacks complete audit trail.
- Scope:
  - Emit immutable audit records for all incident lifecycle paths (API and worker).
  - Include correlation id and provenance in details payload.
- Acceptance Criteria:
  - Every incident create/update/delete path has a corresponding audit event.
  - Audit export includes worker/system actor context.
- Dependencies: `BL-004`
- File Targets:
  - `apps/api/app/modules/audit/services.py`
  - `apps/api/app/services/workers/alert_worker.py`
  - `apps/api/app/modules/incidents/service.py`
  - `apps/api/app/api/v1/incidents.py`

### BL-006 Define mandatory audit coverage matrix and tests

- Priority: `P0`
- Impact: `4`
- Effort: `2`
- Priority Score: `6`
- Owner: Security Engineering
- Problem: Audit coverage is partial and can regress silently.
- Scope:
  - Create machine-checkable matrix mapping endpoints/actions -> audit required.
  - Add tests that fail on missing required audit entries.
- Acceptance Criteria:
  - Coverage matrix stored in repo and enforced in CI.
  - High-risk operations cannot merge without audit assertions.
- Dependencies: `BL-005`
- File Targets:
  - `apps/api/tests/*audit*`
  - `.github/workflows/ci.yml`
  - `docs/AUDIT_COVERAGE_MATRIX.md`
  - `docs/security/SECURITY_AND_COMPLIANCE.md`

## Epic E4: Runtime Guardrails and Degraded Modes (P1)

### BL-007 Redis degraded-mode policy for cooldown and token checks

- Priority: `P1`
- Impact: `4`
- Effort: `3`
- Priority Score: `5`
- Owner: Platform Reliability
- Problem: Redis outage can produce alert spam and weak auth control behavior.
- Scope:
  - Introduce explicit fail-safe policy by operation type.
  - Add optional fallback store for cooldown/tokens (short TTL SQL table or durable queue).
- Acceptance Criteria:
  - Cooldown behavior remains bounded during Redis outage.
  - Token revocation enforcement behavior is explicit and alerting-backed.
- Dependencies: None
- File Targets:
  - `apps/api/app/infrastructure/cache/cooldown_store.py`
  - `apps/api/app/modules/auth/service.py`
  - `infra/monitoring/alert_rules.yml`

### BL-008 Distributed rate limiting and license enforcement for BFF

- Priority: `P1`
- Impact: `4`
- Effort: `3`
- Priority Score: `5`
- Owner: BFF Team
- Problem: In-memory limits and stubbed license gates break under scale and bypass scenarios.
- Scope:
  - Replace in-memory limiter with Redis/shared enforcement.
  - Validate license claims against backend-authoritative policy.
- Acceptance Criteria:
  - Rate limits are stable across horizontal replicas.
  - Restricted data routes enforce licenses even during burst traffic.
- Dependencies: `BL-007`
- File Targets:
  - `apps/bff/src/services/rateLimiter.ts`
  - `apps/bff/src/middleware/licensing.ts`
  - `apps/bff/src/middleware/auth.ts`

## Epic E5: Explainability and Reproducibility (P1)

### BL-009 Preserve evidence integrity for alert reconstruction

- Priority: `P1`
- Impact: `4`
- Effort: `3`
- Priority Score: `5`
- Owner: Detection Team
- Problem: Evidence pruning reduces forensic explainability.
- Scope:
  - Store canonical slim payload plus immutable raw evidence hash/pointer.
  - Add replay utility that reconstructs rule decision context.
- Acceptance Criteria:
  - Analysts can reproduce alert rationale from persisted evidence.
  - Evidence schema versioning is documented and backward-compatible.
- Dependencies: `BL-003`
- Scheduled: Week 9 (start after BL-003 lands; unblocks INT-003, BL-011, BL-012)
- File Targets:
  - `apps/api/app/services/pipeline.py`
  - `apps/api/app/modules/alerts/models.py`
  - `docs/API_DOCUMENTATION.md`

## Epic E6: Monetization and Migration Wedge (P2)

### BL-010 Usage ledger and entitlement contract

- Priority: `P2`
- Impact: `5`
- Effort: `4`
- Priority Score: `6`
- Owner: Product Platform
- Problem: No billing or metering model currently exists.
- Scope:
  - Define billable events (alerts processed, active vessels, data retention, exports).
  - Implement append-only usage ledger and entitlement checks.
- Acceptance Criteria:
  - Usage metrics are queryable by org and period.
  - Entitlement violations are enforced with clear API error contracts.
- Dependencies: `BL-001`, `BL-002`
- File Targets:
  - `apps/api/app/modules/*` (new billing module)
  - `packages/contracts/schemas/*`

### BL-011 Competitor import adapter and migration validator

- Priority: `P2`
- Impact: `5`
- Effort: `3`
- Priority Score: `7`
- Owner: Integrations + Solutions Engineering
- Problem: Switching cost remains high without guided import tooling.
- Scope:
  - Build import adapters for competitor-style exports to canonical model.
  - Produce migration validation report (counts, drift, failed records, confidence).
- Acceptance Criteria:
  - Pilot customer can import historical dataset without manual SQL changes.
  - Validation report generated for each import batch.
- Dependencies: `BL-009`
- File Targets:
  - `apps/api/app/modules/integrations/*`
  - `apps/api/MIGRATION_GUIDE.md` or new migration docs

### BL-012 Standalone wedge feature package

- Priority: `P2`
- Impact: `4`
- Effort: `3`
- Priority Score: `5`
- Owner: Product + Frontend
- Problem: Need low-friction “foot in the door” offering to win accounts pre-migration.
- Scope:
  - Deliver explainable alert dossier + migration overlap support flow.
  - Add export portability guarantees in UI/API docs.
- Acceptance Criteria:
  - New tenant can onboard wedge feature without full ingestion migration.
  - Sales can demo value in under 30 minutes using sample data.
- Dependencies: `BL-009`, `BL-011`
- File Targets:
  - `apps/web/src/features/*`
  - `docs/DEMO_GUIDE.md`
  - `docs/API_DOCUMENTATION.md`

## Epic E7: NATO Funding Readiness and Bid Execution (P0/P1)

### BL-013 Funding route matrix and bid calendar

- Priority: `P0`
- Impact: `5`
- Effort: `2`
- Priority Score: `8`
- Owner: CEO + Program Management
- Problem: Product backlog exists, but there is no mapped path to specific NATO-aligned funding instruments.
- Scope:
  - Build target-program matrix for DIANA, NIF, and NCIA-style tenders with eligibility, deadlines, and decision gates.
  - Define no-bid rules and bid-go criteria.
- Acceptance Criteria:
  - One canonical matrix exists with owners, due dates, and submission dependencies.
  - At least one submission path is approved for execution in current quarter.
- Dependencies: None
- File Targets:
  - `docs/FUNDING_ROUTE_MATRIX.md` (new)
  - `docs/BUSINESS_LOGIC_IMPLEMENTATION_BACKLOG.md`

### BL-014 Compliance evidence pack and accreditation roadmap

- Priority: `P0`
- Impact: `5`
- Effort: `4`
- Priority Score: `6`
- Owner: Security Engineering + Platform
- Problem: Security intent is present, but evidence artifacts required by defense evaluators are incomplete.
- Scope:
  - Deliver control matrix mapped to ISO 27001, NIST CSF, and SOC 2 controls.
  - Add threat model, data classification model, and accreditation milestone plan.
  - Add incident response, key management, and data retention policy references.
- Acceptance Criteria:
  - Evidence pack is versioned in repo and reviewable end-to-end.
  - Each critical control has evidence pointer and accountable owner.
- Dependencies: `BL-005`, `BL-006`
- File Targets:
  - `docs/security/SECURITY_AND_COMPLIANCE.md`
  - `docs/SECURITY_EVIDENCE_PACK.md` (new)
  - `docs/ARCHITECTURE.md`

### BL-015 Interoperability profile and standards mapping

- Priority: `P0`
- Impact: `4`
- Effort: `3`
- Priority Score: `5`
- Owner: Integrations + API Platform
- Problem: Interoperability claims are not yet documented in a defense-procurement-friendly format.
- Scope:
  - Define interoperability profile mapping canonical APIs/schemas to target maritime and C2 integration requirements.
  - Add compatibility and conformance checklist with known gaps.
- Acceptance Criteria:
  - Interoperability profile is documented with explicit supported/unsupported capabilities.
  - Demo script validates one end-to-end import and one export against documented profile.
- Dependencies: `BL-009`, `BL-011`
- File Targets:
  - `docs/API_DOCUMENTATION.md`
  - `packages/contracts/schemas/*`
  - `docs/INTEROPERABILITY_PROFILE.md` (new)

### BL-016 Sovereign deployment and supply-chain assurance

- Priority: `P1`
- Impact: `4`
- Effort: `3`
- Priority Score: `5`
- Owner: Platform + DevSecOps
- Problem: Funding panels often require deployment sovereignty and software supply-chain guarantees.
- Scope:
  - Define deployment options for data residency and tenant segregation.
  - Generate SBOM in CI, enforce vulnerability SLA policy, and document artifact signing/attestation approach.
- Acceptance Criteria:
  - CI publishes SBOM and fails on policy-violating critical vulnerabilities.
  - Sovereign deployment reference architecture is documented and reviewable.
- Dependencies: `BL-007`
- File Targets:
  - `.github/workflows/ci.yml`
  - `infra/k8s/README.md`
  - `docs/SUPPLY_CHAIN_ASSURANCE.md` (new)

### BL-017 Mission KPI baseline and pilot evidence package

- Priority: `P1`
- Impact: `5`
- Effort: `2`
- Priority Score: `8`
- Owner: Solutions Engineering + Product
- Problem: Engineering KPIs exist, but mission and procurement outcomes are not baseline-tracked for evaluators.
- Scope:
  - Define baseline and target for mission KPIs (detection lead-time, false alert reduction, analyst hours saved).
  - Create pilot evidence template including validation reports, operator feedback, and ROI summary.
- Acceptance Criteria:
  - KPI baseline and target values are documented for at least one pilot scenario.
  - Pilot evidence template is reusable for every bid submission.
- Dependencies: `BL-011`, `BL-012`
- File Targets:
  - `docs/DEMO_GUIDE.md`
  - `docs/FUNDING_PILOT_EVIDENCE_TEMPLATE.md` (new)
  - `docs/BUSINESS_LOGIC_IMPLEMENTATION_BACKLOG.md`

### BL-018 Consortium and partner execution model

- Priority: `P1`
- Impact: `4`
- Effort: `2`
- Priority Score: `6`
- Owner: CEO + Partnerships
- Problem: Many defense funding routes are consortium-biased; partner roles and governance are not formalized.
- Scope:
  - Define partner role matrix (prime, integrator, field operator, compliance support).
  - Define bid governance, RACI, and escalation path.
- Acceptance Criteria:
  - Consortium structure and governance model are documented.
  - At least two partner categories have identified candidates and outreach owner.
- Dependencies: `BL-013`
- File Targets:
  - `docs/CONSORTIUM_EXECUTION_MODEL.md` (new)
  - `docs/BUSINESS_LOGIC_IMPLEMENTATION_BACKLOG.md`

## 90-Day Delivery Plan

### Weeks 1-4 (Risk Containment)

- Execute `BL-001` to `BL-006`.
- Exit Criteria:
  - No cross-tenant vessel leakage in tests.
  - No duplicate alert/incident under synthetic retry tests.
  - Full incident lifecycle audit coverage in CI.

### Weeks 5-8 (Reliability and Trust)

- Execute `BL-007` to `BL-009`.
- Exit Criteria:
  - Defined and tested degraded-mode behavior during Redis outages.
  - Distributed BFF controls in place for rate/entitlements.
  - Reproducible alert evidence in analyst workflow.

### Weeks 9-12 (Growth and Displacement)

- Execute `BL-010` to `BL-012`.
- Run funding-readiness stream in parallel: `BL-013` to `BL-018`, with `BL-014` and `BL-016` starting no later than week 9 and `BL-018` starting no later than week 10.
- Exit Criteria:
  - Metering ledger and entitlement checks live for pilot accounts.
  - Competitor import adapter and migration validator usable in pilot.
  - Wedge package demo-ready with migration overlap playbook.
  - Bid package has named route, mission KPI baseline, interoperability profile, compliance evidence pack, and consortium execution model.

## Parallel Workstream Model

- Stream A: Platform and Product Delivery (`BL-001` to `BL-012`) led by Engineering.
- Stream B: Funding and Procurement Readiness (`BL-013` to `BL-018`) led by Program, Security, and Partnerships.
- Weekly integration checkpoint required:
  - Confirm Stream A evidence feeds Stream B bid package.
  - Confirm Stream B requirements feed back into Stream A backlog priorities.

## Program KPIs

- Security KPI: `0` confirmed cross-tenant data leakage incidents.
- Reliability KPI: `<1%` duplicate alert/incident rate during replay and worker retries.
- Compliance KPI: `100%` required actions generate audit events.
- Growth KPI: first migration pilot completed with zero-downtime cutover.
- Commercial KPI: at least one billable entitlement policy enforced in production.
- Funding KPI: one qualified NATO-aligned route submitted with complete evidence pack and named pilot sponsor.

### KPI Operationalization

- Security KPI: owner `Security Engineering`, source `security regression test suite + incident register`, cadence `weekly`.
- Reliability KPI: owner `Detection Pipeline`, source `retry-replay integration tests + alert dedupe dashboard`, cadence `weekly`.
- Compliance KPI: owner `Security Engineering`, source `audit coverage matrix CI gate`, cadence `per PR + weekly summary`.
- Growth KPI: owner `Solutions Engineering`, source `migration validator reports`, cadence `per pilot batch`.
- Commercial KPI: owner `Product Platform`, source `entitlement enforcement logs + usage ledger`, cadence `weekly`.
- Funding KPI: owner `Program Management`, source `funding route matrix + submission checklist + pilot evidence package`, cadence `weekly`.

## Notes

- This backlog is intentionally outcome-first and owner-mapped for sprint planning.
- Ticket IDs (`BL-###`) can be mirrored directly into your issue tracker.
