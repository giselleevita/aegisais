# Audit Coverage Matrix

This document operationalizes BL-006 and provides a machine-checkable source of truth for audit-required operations.

## Required Audit Events

| Domain        | Operation                      | Actor Type | Audit Required | Minimum Event Fields                                                                                      | Enforcement Source                  | Owner                |
| ------------- | ------------------------------ | ---------- | -------------- | --------------------------------------------------------------------------------------------------------- | ----------------------------------- | -------------------- |
| Incidents     | create                         | human      | Yes            | actor, actor_type=human, organisation_id, incident_id, correlation_id, provenance                         | API tests + CI gate                 | Security Engineering |
| Incidents     | update                         | human      | Yes            | actor, actor_type=human, organisation_id, incident_id, changed_fields, correlation_id                     | API tests + CI gate                 | Security Engineering |
| Incidents     | delete                         | human      | Yes            | actor, actor_type=human, organisation_id, incident_id, correlation_id, provenance                         | API tests + CI gate                 | Security Engineering |
| Incidents     | create (system — alert worker) | system     | Yes            | actor=system:alert_worker, actor_type=system, organisation_id, alert_id, mmsi, alert_type, correlation_id | Worker integration tests + CI gate  | Detection Pipeline   |
| Alerts        | create (system)                | system     | Yes            | actor_type=system, organisation_id, alert_id, rule_type, evidence_hash, correlation_id                    | Worker integration tests + CI gate  | Detection Pipeline   |
| Auth          | token revoke                   | human      | Yes            | actor, organisation_id, subject_id, correlation_id                                                        | Auth tests + CI gate                | Security Engineering |
| Vessel access | cross-tenant denied access     | human      | Yes            | actor, organisation_id, target_org_id, route, correlation_id                                              | Security regression tests + CI gate | Backend API          |

## System-Actor Event Details

System-generated audit events (actor_type=system) are distinguished from human-driven events by:

- `user_id` field set to a stable service-identity string (e.g. `system:alert_worker`).
- `correlation_id` set to the Redis Stream message ID, providing end-to-end traceability from ingestion to incident.
- Events are emitted **within the same database transaction** as the resource mutation, so an audit row is either committed with the resource or rolled back together.

### `incident.create.system` — Alert Worker

Emitted by `apps/api/app/services/workers/alert_worker.py::handle_alert` whenever the alert persistence worker auto-creates an incident from an alert. Required fields:

| Field                | Value                    | Notes                                             |
| -------------------- | ------------------------ | ------------------------------------------------- |
| `action`             | `incident.create.system` | Fixed string; searchable in audit log             |
| `user_id`            | `system:alert_worker`    | Never a real user ID                              |
| `resource_type`      | `incident`               |                                                   |
| `resource_id`        | `str(alert.id)`          | Alert ID — incident ID not yet known at emit time |
| `organisation_id`    | alert.organisation_id    |                                                   |
| `correlation_id`     | Redis Stream message ID  | Enables trace from stream entry to DB row         |
| `details.alert_id`   | alert.id                 |                                                   |
| `details.mmsi`       | alert.mmsi               |                                                   |
| `details.alert_type` | alert.type               |                                                   |

## CI Enforcement Contract

- Changes to audit-required operations must include test coverage proving event emission.
- CI must fail if a required operation is modified without corresponding audit assertions.
- System-actor operations are subject to the same enforcement as human-actor operations.
- This matrix is the reference artifact for BL-006 and downstream compliance evidence.
- Worker audit tests must live in `apps/api/tests/test_alert_worker_audit.py` and assert on `AuditLog` rows in the test database.
