# GitHub Issue Pack (BL-007 to BL-012)

Use this document to copy-paste the next six implementation issues into GitHub.

## Issue 7

Title: BL-007 Redis degraded-mode policy for cooldown and token checks

Labels:

- type:reliability
- type:security
- priority:P1
- epic:E4-runtime-guardrails

Body:

### Problem

Redis outages can produce alert spam and weaker auth-control behavior in critical paths.

### Scope

- Define explicit fail-safe behavior per operation (cooldown, token revocation, stream reads).
- Add fallback strategy for cooldown and token checks (short TTL SQL table or durable queue-based state).
- Add alerting for degraded-mode activation and recovery.

### Acceptance Criteria

- Cooldown behavior remains bounded during Redis outage simulations.
- Token revocation behavior is explicit, testable, and observable.
- Runbook documents operator actions for degraded mode.

### Dependencies

- None

### File Targets

- apps/api/app/infrastructure/cache/cooldown_store.py
- apps/api/app/modules/auth/service.py
- infra/monitoring/alert_rules.yml

### Definition of Done

- Failure-injection tests pass for Redis-down scenarios.
- Degraded-mode metrics and alerts verified in staging.

---

## Issue 8

Title: BL-008 Distributed rate limiting and license enforcement for BFF

Labels:

- type:reliability
- type:compliance
- priority:P1
- epic:E4-runtime-guardrails

Body:

### Problem

In-memory limiter and stubbed license checks do not hold under horizontal scaling or bypass attempts.

### Scope

- Replace in-memory BFF limiter with shared/distributed enforcement.
- Validate license claims against backend-authoritative policy.
- Add route-level policy tests for restricted data paths.

### Acceptance Criteria

- Rate limits are consistent across multiple BFF replicas.
- Restricted routes enforce license checks during burst and failover scenarios.
- License-check outcomes are observable in logs/metrics.

### Dependencies

- BL-007

### File Targets

- apps/bff/src/services/rateLimiter.ts
- apps/bff/src/middleware/licensing.ts
- apps/bff/src/middleware/auth.ts

### Definition of Done

- Load-test confirms no per-replica bypass.
- Compliance reviewer validates enforcement behavior.

---

## Issue 9

Title: BL-009 Preserve evidence integrity for alert reconstruction

Labels:

- type:product
- type:forensics
- priority:P1
- epic:E5-explainability

Body:

### Problem

Evidence pruning reduces forensic explainability and replayability of alert decisions.

### Scope

- Persist canonical slim evidence plus immutable raw evidence hash/pointer.
- Add replay utility to reconstruct rule decision context.
- Document evidence schema versioning and compatibility expectations.

### Acceptance Criteria

- Analysts can reconstruct alert rationale from persisted artifacts.
- Replay utility reproduces rule outcomes for sampled incidents.
- Evidence schema versioning is documented and backward-compatible.

### Dependencies

- BL-003

### File Targets

- apps/api/app/services/pipeline.py
- apps/api/app/modules/alerts/models.py
- docs/API_DOCUMENTATION.md

### Definition of Done

- At least one end-to-end forensic replay test in CI.
- Analyst sign-off on reconstructed evidence output.

---

## Issue 10

Title: BL-010 Usage ledger and entitlement contract

Labels:

- type:monetization
- type:platform
- priority:P2
- epic:E6-growth

Body:

### Problem

No billing or metering primitives currently exist, limiting monetization and packaging.

### Scope

- Define billable events and units (alerts processed, active vessels, retention, exports).
- Implement append-only usage ledger per organization and billing period.
- Add entitlement checks with clear API error contracts.

### Acceptance Criteria

- Usage can be queried by org and time window.
- Entitlement breaches return deterministic API errors.
- Contract schemas include metering and entitlement payloads.

### Dependencies

- BL-001
- BL-002

### File Targets

- apps/api/app/modules/ (new billing module)
- packages/contracts/schemas/

### Definition of Done

- Pilot org receives usage summary generated from ledger.
- One entitlement policy is enforceable in staging.

---

## Issue 11

Title: BL-011 Competitor import adapter and migration validator

Labels:

- type:migration
- type:integration
- priority:P2
- epic:E6-growth

Body:

### Problem

Switching costs remain high without guided import tooling and validation.

### Scope

- Build import adapters from competitor-style exports to canonical model.
- Generate migration validation reports (counts, drift, invalid records, confidence).
- Add operator docs for repeatable migration execution.

### Acceptance Criteria

- Pilot customer can import historical dataset without manual SQL edits.
- Validation report generated for each import batch and archived.
- Import failures produce actionable error categories.

### Dependencies

- BL-009

### File Targets

- apps/api/app/modules/integrations/
- docs/MIGRATION_GUIDE.md (or dedicated migration doc)

### Definition of Done

- One real or synthetic competitor export migrated in staging.
- Validation output reviewed by solutions engineering.

---

## Issue 12

Title: BL-012 Standalone wedge feature package

Labels:

- type:product
- type:growth
- priority:P2
- epic:E6-growth

Body:

### Problem

Need a low-friction wedge feature to win accounts before full migration.

### Scope

- Deliver explainable alert dossier and migration-overlap support flow.
- Add explicit data portability and export guarantees in docs/UI.
- Package demo path so value is visible in under 30 minutes.

### Acceptance Criteria

- New tenant can onboard wedge feature without full ingestion migration.
- Sales/demo runbook can showcase value in <=30 minutes.
- Portability guarantees documented in user-facing materials.

### Dependencies

- BL-009
- BL-011

### File Targets

- apps/web/src/features/
- docs/DEMO_GUIDE.md
- docs/API_DOCUMENTATION.md

### Definition of Done

- Product and GTM teams approve wedge package positioning.
- Demo script passes with staging environment data.

---

## Suggested Milestone Mapping

- Milestone: Business Logic Hardening Sprint 2-3
- Issues: BL-007 to BL-012
- Target window: Weeks 5 to 12
