# Security and Compliance

**Version:** 1.2  
**Owner:** Security Engineering  
**Last Updated:** 2026-04-01  
**Classification:** Internal — Shareable with Accreditation Reviewers

---

## Enforced Controls

- Provider secrets are server-side only:
  - API/BFF read tokens from environment variables.
  - Browser payloads never include provider keys or credentials.
- Licensing gates are applied in manifest/orchestration paths:
  - restricted/non-commercial datasets are default-off and entitlement-gated.
- Evidence bundles include `schema_version` and `provenance_version`.
- Incident evidence records legal posture metadata:
  - `subsurface_tracking: not_performed`
  - explicit licensing notes for source usage constraints.
- Alert-to-incident lineage is preserved for auditability and explainability.

---

## Access and Tenant Boundaries

- RBAC stubs exist in API and BFF slices and are wired to authenticated roles.
- Tenant-aware access policy is represented in contracts (`access level` and scoping metadata).
- UI displays access/licence context in layer inspector and catalog.

---

## Audit Logging Requirements

- Audit events are required for:
  - exports/downloads
  - incident edits and status transitions
  - privileged layer access actions
- Existing audit plumbing is present; export/edit coverage is partially stubbed and called out below.

---

## UI Compliance Signals

- Restricted and non-commercial badges are rendered in the workbench for gated layers.
- Provenance text and confidence class/score are visible in inspector context.

---

## Control Matrix (ISO 27001 / NIST CSF / SOC 2 Alignment)

> Legend: ✅ Implemented · ⚠️ Partial · ❌ Not yet implemented · N/A Not applicable

| Control ID | Control Description                         | ISO 27001 Ref | NIST CSF | SOC 2 CC | Status | Evidence Pointer                                                                         | Owner     |
| ---------- | ------------------------------------------- | ------------- | -------- | -------- | ------ | ---------------------------------------------------------------------------------------- | --------- |
| AC-01      | Role-based access control (RBAC)            | A.9.2         | PR.AC-4  | CC6.3    | ✅     | `app/modules/auth/`                                                                      | Platform  |
| AC-02      | Tenant isolation — org-scoped queries       | A.9.4         | PR.AC-3  | CC6.3    | ✅     | `BL-001`, `BL-002`, `app/modules/auth/org_scope.py`                                      | Backend   |
| AC-03      | Multi-factor authentication                 | A.9.4         | PR.AC-7  | CC6.7    | ❌     | Planned — Sprint 8                                                                       | Platform  |
| AC-04      | Session token expiry and revocation         | A.9.4         | PR.AC-7  | CC6.6    | ✅     | `app/modules/auth/service.py`, `BL-007`                                                  | Backend   |
| AC-05      | Rate limiting — BFF layer                   | A.12.6        | PR.AC-5  | CC6.6    | ✅     | `BL-008`, `apps/bff/src/services/rateLimiter.ts`                                         | BFF       |
| AC-06      | License gate enforcement                    | A.9.1         | PR.AC-4  | CC6.3    | ✅     | `BL-008`, `apps/bff/src/middleware/licensing.ts`                                         | BFF       |
| AU-01      | Audit log for all privileged actions        | A.12.4        | DE.CM-3  | CC7.2    | ✅     | `BL-005`, `BL-006`, `app/modules/audit/`                                                 | Security  |
| AU-02      | Audit coverage matrix enforced in CI        | A.12.4        | DE.CM-3  | CC7.2    | ✅     | `docs/AUDIT_COVERAGE_MATRIX.md`, `scripts/check_audit_coverage.py`                       | Security  |
| AU-03      | Immutable audit records (no update/delete)  | A.12.4        | PR.PT-1  | CC7.2    | ✅     | `AuditLog` ORM — no update path exposed                                                  | Security  |
| AU-04      | System-actor audit events (worker/pipeline) | A.12.4        | DE.CM-3  | CC7.2    | ✅     | `BL-005`, `test_alert_worker_audit.py`                                                   | Security  |
| CR-01      | Secrets management — env vars only          | A.10.1        | PR.DS-1  | CC6.1    | ✅     | `app/core/config.py`                                                                     | Platform  |
| CR-02      | JWT signing key — length validation         | A.10.1        | PR.DS-5  | CC6.1    | ✅     | `config.py` field_validator                                                              | Platform  |
| CR-03      | TLS enforced in production                  | A.10.1        | PR.DS-2  | CC6.7    | ⚠️     | nginx config in `infra/docker/nginx/`; mutual TLS not yet enforced                       | DevSecOps |
| CR-04      | Data at rest encryption                     | A.10.1        | PR.DS-1  | CC6.1    | ⚠️     | PostgreSQL disk encryption via infra layer; application-level encryption not implemented | Platform  |
| CR-05      | Evidence hash for alert integrity           | A.12.1        | PR.DS-6  | CC9.2    | ✅     | `BL-009`, `Alert.evidence_hash`, `derive_evidence_hash()`                                | Detection |
| DP-01      | Data retention policy defined               | A.18.1        | PR.IP-6  | CC9.2    | ⚠️     | Usage ledger captures retention events (BL-010); purge schedule not yet automated        | Platform  |
| DP-02      | PII minimisation in AIS data                | A.13.2        | PR.DS-5  | CC6.1    | ✅     | MMSI-only; no vessel owner PII ingested by default                                       | Legal     |
| DP-03      | Export portability guarantees               | A.18.1        | PR.IP-6  | CC9.2    | ✅     | `BL-012`, RFC 4180 CSV + JSON Lines export endpoints                                     | Platform  |
| IM-01      | Idempotent alert creation                   | A.12.1        | PR.IP-1  | CC8.1    | ✅     | `BL-003`, `Alert.idempotency_key`, savepoint pattern                                     | Detection |
| IM-02      | Idempotent incident creation                | A.12.1        | PR.IP-1  | CC8.1    | ✅     | `BL-004`, `create_incident_from_alert_with_flag`                                         | Backend   |
| IM-03      | Redis degraded-mode guardrails              | A.17.2        | RS.MI-3  | CC7.5    | ✅     | `BL-007`, `cooldown_store.py`, Prometheus alert rules                                    | Platform  |
| IR-01      | Incident response runbook                   | A.16.1        | RS.RP-1  | CC7.3    | ❌     | Planned — needed for NCIA tender                                                         | Security  |
| IR-02      | Security alerting (Prometheus)              | A.16.1        | DE.AE-5  | CC7.4    | ✅     | `infra/monitoring/alert_rules.yml`                                                       | Platform  |
| SC-01      | CORS policy enforced                        | A.13.1        | PR.AC-5  | CC6.6    | ✅     | `app/main.py` CORS middleware                                                            | Backend   |
| SC-02      | SQL injection prevention (ORM)              | A.14.2        | PR.DS-5  | CC6.6    | ✅     | SQLAlchemy parameterised queries throughout                                              | Backend   |
| SC-03      | Input validation at boundaries              | A.14.2        | PR.DS-5  | CC6.6    | ✅     | Pydantic v2 validation on all API schemas                                                | Backend   |
| SC-04      | Dependency vulnerability scanning           | A.12.6        | ID.RA-1  | CC7.1    | ⚠️     | `codecov.yml` present; Dependabot not yet configured                                     | DevSecOps |
| SC-05      | Container image scanning                    | A.12.6        | ID.RA-1  | CC7.1    | ❌     | Planned — trivy scan in CI                                                               | DevSecOps |

---

## Threat Model (Summary)

| Threat                                  | Attack Vector              | Mitigating Controls                                               | Residual Risk  |
| --------------------------------------- | -------------------------- | ----------------------------------------------------------------- | -------------- |
| Cross-tenant data leakage               | Authenticated API call     | AC-02 (org_scope), AC-01 (RBAC)                                   | Low            |
| Alert spam / DoS via AIS injection      | Unauthenticated AIS ingest | AC-05 (rate limit), IM-01 (idempotency), IM-03 (Redis guardrails) | Low            |
| Duplicate incident creation             | Worker retry storm         | IM-02 (savepoint), IM-01                                          | Low            |
| JWT token theft and replay              | Token interception         | CR-02 (signing key length), AC-04 (revocation), CR-03 (TLS)       | Medium-TLS gap |
| Evidence tampering post-persist         | DB access                  | CR-05 (evidence_hash), AU-03 (immutable audit)                    | Low            |
| Secret exfiltration via BFF             | XSS / SSRF                 | CR-01 (env vars), SC-01 (CORS)                                    | Low            |
| Privilege escalation via forged license | Bearer token               | AC-06 (KNOWN_FEATURES allowlist)                                  | Low            |

---

## Data Classification

| Class        | Examples                         | Storage                       | Access                 |
| ------------ | -------------------------------- | ----------------------------- | ---------------------- |
| Public       | Port reference data, MMSI ranges | PostgreSQL                    | Any authenticated role |
| Restricted   | AIS tracks, alerts, incidents    | PostgreSQL (org-scoped)       | Tenant roles only      |
| Confidential | JWT signing keys, API secrets    | Environment / secrets manager | Platform SRE only      |
| Regulated    | PII (if any)                     | Not currently ingested        | N/A                    |

---

## Accreditation Milestone Plan

| Milestone                                | Target Date | Dependency                  | Owner        |
| ---------------------------------------- | ----------- | --------------------------- | ------------ |
| Internal security review complete        | 2026-05-01  | BL-014 doc                  | Security Eng |
| Penetration test (external) commissioned | 2026-06-01  | IR-01 runbook               | Security Eng |
| ISO 27001 gap analysis                   | 2026-06-15  | Control matrix              | Security Eng |
| SOC 2 Type I scope defined               | 2026-07-01  | Gap analysis                | CEO + Legal  |
| NCIA tender security evidence pack       | 2026-04-10  | `SECURITY_EVIDENCE_PACK.md` | Program Mgmt |
| MFA implementation                       | 2026-07-01  | Sprint 8                    | Platform     |
| Dependabot + container scanning in CI    | 2026-05-15  | DevSecOps sprint            | DevSecOps    |

---

## Key Management Policy

- JWT signing keys are generated per deployment, minimum 32 bytes, set via `SECRET_KEY` env var.
- Key rotation: planned quarterly; rotation requires coordinated token revocation via Redis.
- Provider API keys are injected at runtime only; never committed to version control.
- No application-level encryption keys currently in scope (disk encryption deferred to infra layer).

---

## Incident Response (Summary)

> Full runbook: pending (IR-01). Interim process below.

1. Detection: Prometheus alert fires → wakes on-call engineer.
2. Triage: Check `infra/monitoring/alert_rules.yml` for rule context.
3. Containment: Disable compromised org via admin API; revoke tokens via Redis.
4. Evidence preservation: Export audit logs (`GET /v1/audit?limit=10000`) before any DB change.
5. Notification: Notify affected tenants per contractual SLA.
6. Post-incident: Write incident report; update threat model.

---

## Stubbed / Pending

- Centralized legal-policy engine is not implemented yet (policy is currently rule + metadata driven).
- Automated upstream license attestation at ingest time is not fully implemented.
- Complete export/incident-edit audit event coverage is partially implemented and needs endpoint-level completion.
- MFA (AC-03) planned Sprint 8.
- Container image scanning (SC-05) planned next DevSecOps sprint.

---

## Blocked

- Jurisdiction-specific legal controls for seabed/subsurface operations require formal legal counsel sign-off.
- Partner feed contracts (e.g., commercial subsea and non-commercial fishing constraints) need machine-readable entitlement sources.

---

## Legal Constraints

- This implementation does **not** perform direct live subsurface/submarine tracking.
- Subsurface capability is limited to inferred zones, integration stubs, and simulation/replay workflows.
- Fused detection currently uses surface-activity + cable proximity only.
