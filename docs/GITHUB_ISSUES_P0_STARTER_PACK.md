# GitHub Issue Starter Pack (First 6)

Use this document to copy-paste the first six high-priority issues into GitHub.

## Issue 1

Title: BL-001 Add organisation_id to vessel latest and vessel position

Labels:

- type:security
- type:data-model
- priority:P0
- epic:E1-tenant-isolation

Body:

### Problem

Vessel records are not tenant-scoped, creating cross-tenant exposure risk and blocking regulated customer onboarding.

### Scope

- Add organisation_id to vessel latest and vessel position tables.
- Update ORM models and query paths.
- Backfill existing rows with deterministic mapping strategy.
- Add indexes for organisation_id + mmsi hot paths.

### Acceptance Criteria

- Non-super-admin vessel endpoints return only tenant-scoped records.
- Tenant isolation tests cover list, detail, and track endpoints.
- Migration includes rollback plan and successful backfill validation.

### Dependencies

- None

### File Targets

- apps/api/app/modules/vessels/models.py
- apps/api/alembic/versions/
- apps/api/app/api/v1/vessels.py

### Definition of Done

- Schema migration merged and applied in staging.
- Automated tests enforce tenant isolation.
- Security sign-off from backend owner.

---

## Issue 2

Title: BL-002 Enforce org filtering in all vessel query paths

Labels:

- type:security
- type:api
- priority:P0
- epic:E1-tenant-isolation

Body:

### Problem

Some vessel and position query paths may bypass organization-level filtering.

### Scope

- Reuse org-scope helpers for all vessel/position read and write paths.
- Add explicit super-admin bypass tests.
- Remove any legacy direct query paths without org guard.

### Acceptance Criteria

- Viewer, analyst, and admin roles cannot read another org data.
- Super-admin behavior remains intentional and tested.
- Security regression suite passes in CI.

### Dependencies

- BL-001

### File Targets

- apps/api/app/modules/auth/org_scope.py
- apps/api/app/api/v1/vessels.py

### Definition of Done

- All vessel routes consistently call org filtering.
- Test matrix covers role and org boundary cases.

---

## Issue 3

Title: BL-003 Add idempotency key for alert persistence

Labels:

- type:reliability
- type:pipeline
- priority:P0
- epic:E2-idempotency

Body:

### Problem

Worker retries can create duplicate alerts and downstream duplicate incidents.

### Scope

- Define deterministic idempotency key: organisation_id + mmsi + rule_type + event_timestamp + evidence_hash.
- Add uniqueness protection in persistence layer.
- Update worker persist logic to handle conflict/upsert safely.

### Acceptance Criteria

- Reprocessing identical payloads does not create duplicate alerts.
- Integration test simulating retry storms passes.
- Metrics show duplicate prevention count.

### Dependencies

- BL-001

### File Targets

- apps/api/app/modules/alerts/models.py
- apps/api/app/services/workers/alert_worker.py
- apps/api/alembic/versions/

### Definition of Done

- Duplicate alerts under retry are zero in test harness.
- Migration and conflict behavior documented.

---

## Issue 4

Title: BL-004 Prevent duplicate incident creation per alert idempotency group

Labels:

- type:reliability
- type:incidents
- priority:P0
- epic:E2-idempotency

Body:

### Problem

Auto-incident creation can duplicate if alert persistence partially fails and retries.

### Scope

- Make incident creation idempotent and conflict-aware.
- Ensure transaction boundaries avoid orphan records.
- Add defensive checks in worker flow.

### Acceptance Criteria

- Exactly one incident for equivalent alert events under retries.
- No incident exists without corresponding alert.
- End-to-end replay tests validate behavior.

### Dependencies

- BL-003

### File Targets

- apps/api/app/modules/incidents/service.py
- apps/api/app/services/workers/alert_worker.py

### Definition of Done

- Duplicate incident rate in replay tests is zero.
- Data integrity checks pass in staging.

---

## Issue 5

Title: BL-005 Add audit events for system-created incidents

Labels:

- type:compliance
- type:audit
- priority:P0
- epic:E3-auditability

Body:

### Problem

System-generated incident creation does not always emit complete audit records.

### Scope

- Emit immutable audit events for worker-generated incident create/update actions.
- Include correlation id, provenance, and actor context as system/worker.
- Ensure events are exportable in audit endpoints.

### Acceptance Criteria

- Every incident create/update/delete has an audit trail entry.
- Audit export includes worker/system actor metadata.
- Negative tests fail when required audit events are missing.

### Dependencies

- BL-004

### File Targets

- apps/api/app/modules/audit/services.py
- apps/api/app/services/workers/alert_worker.py

### Definition of Done

- Audit coverage report shows 100 percent for incident lifecycle actions.
- Compliance reviewer sign-off complete.

---

## Issue 6

Title: BL-006 Define mandatory audit coverage matrix and tests

Labels:

- type:compliance
- type:test
- priority:P0
- epic:E3-auditability

Body:

### Problem

Audit coverage is partial and can regress silently without policy-as-code checks.

### Scope

- Create machine-checkable matrix mapping high-risk operations to mandatory audit events.
- Add CI tests that fail when required audit events are absent.
- Document matrix ownership and update policy.

### Acceptance Criteria

- Matrix committed and referenced by tests.
- CI blocks changes that violate required audit coverage.
- Security docs updated with required event map.

### Dependencies

- BL-005

### File Targets

- apps/api/tests/
- docs/security/SECURITY_AND_COMPLIANCE.md

### Definition of Done

- CI policy tests merged and active on pull requests.
- Engineering and security owners agree on matrix governance.

---

## Suggested Milestone Mapping

- Milestone: Business Logic Hardening Sprint 1
- Issues: BL-001 to BL-006
- Target window: Weeks 1 to 4
