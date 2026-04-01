# Security Evidence Pack

**Version:** 1.1  
**Owner:** Security Engineering + Platform  
**Classification:** Restricted — Accreditation and Procurement Use  
**Last Updated:** 2026-04-01

This document operationalizes BL-014 and provides machine-reviewable evidence pointers
required for defense evaluator, NCIA tender, and ISO 27001/SOC 2 accreditation reviews.
Each critical control maps to a verifiable evidence pointer (file path, test command,
or CI gate).

---

## Control Mapping Coverage

- ISO 27001: Organizational and technical controls mapping (Annex A)
- NIST CSF: Govern, Identify, Protect, Detect, Respond, Recover mapping
- SOC 2: Security and availability control evidence mapping (Trust Services Criteria)

---

## Evidence Index

| Control Area              | ISO 27001 Reference | NIST CSF Reference | SOC 2 Reference | Evidence Artifact                          | Source Path                                                        | Owner                | Review Cadence |
| ------------------------- | ------------------- | ------------------ | --------------- | ------------------------------------------ | ------------------------------------------------------------------ | -------------------- | -------------- |
| Access control (RBAC)     | A.5.15, A.8.2       | PR.AA-4            | CC6.3           | RBAC tests + org_scope enforcement         | `app/modules/auth/org_scope.py`                                    | Security Engineering | Monthly        |
| Tenant isolation          | A.5.15, A.9.4       | PR.AC-3            | CC6.3           | BL-001/BL-002 org-scoped queries           | `alembic/versions/010_vessel_org_scope.py`                         | Backend              | Per PR         |
| Auditability              | A.8.15, A.8.16      | DE.AE, DE.CM       | CC7.2           | Audit coverage matrix + CI gate            | `docs/AUDIT_COVERAGE_MATRIX.md`, `scripts/check_audit_coverage.py` | Security Engineering | Per PR         |
| Immutable audit records   | A.8.15              | PR.PT-1            | CC7.2           | AuditLog — no update/delete path           | `app/modules/audit/`                                               | Security Engineering | Monthly        |
| System-actor audit events | A.8.15              | DE.CM-3            | CC7.2           | `incident.create.system` in worker         | `app/services/workers/alert_worker.py`                             | Security             | Per PR         |
| Alert idempotency         | A.12.1              | PR.IP-1            | CC8.1           | SHA-256 idempotency key + DB constraint    | `alembic/versions/011_alert_idempotency_key.py`                    | Detection            | Per PR         |
| Evidence integrity        | A.12.1              | PR.DS-6            | CC9.2           | SHA-256 evidence hash on Alert row         | `alembic/versions/012_alert_evidence_hash.py`                      | Detection            | Per PR         |
| Rate limiting (BFF)       | A.12.6              | PR.AC-5            | CC6.6           | Redis-backed rate limiter                  | `apps/bff/src/services/rateLimiter.ts`                             | BFF                  | Monthly        |
| License enforcement       | A.9.1               | PR.AC-4            | CC6.3           | KNOWN_FEATURES allowlist                   | `apps/bff/src/middleware/licensing.ts`                             | BFF                  | Monthly        |
| Secrets management        | A.10.1              | PR.DS-1            | CC6.1           | Env vars only; no hardcoded secrets        | `app/core/config.py`                                               | Platform             | Quarterly      |
| JWT key length validation | A.10.1              | PR.DS-5            | CC6.1           | `check_secret_key` validator               | `app/core/config.py`                                               | Platform             | Per PR         |
| Session token revocation  | A.9.4               | PR.AC-7            | CC6.6           | Redis blocklist + Prometheus counters      | `app/modules/auth/service.py`                                      | Backend              | Monthly        |
| Redis degraded mode       | A.17.2              | RS.MI-3            | CC7.5           | In-process fallback + alert rules          | `app/infrastructure/cache/cooldown_store.py`                       | Platform             | Monthly        |
| Usage metering            | A.5.33              | PR.DS              | CC8.1           | Append-only usage ledger                   | `app/modules/billing/models.py`                                    | Platform             | Quarterly      |
| Entitlement enforcement   | A.9.1               | PR.AC-4            | CC6.3           | `check_entitlement()` service              | `app/modules/billing/service.py`                                   | Platform             | Monthly        |
| Competitor migration      | A.14.2              | PR.IP-6            | CC9.2           | Adapter + validation report                | `app/modules/integrations/adapters_competitor.py`                  | Integrations         | As needed      |
| Input validation          | A.14.2              | PR.DS-5            | CC6.6           | Pydantic v2 on all API schemas             | `app/modules/*/schemas.py`                                         | Backend              | Per PR         |
| SQL injection prevention  | A.14.2              | PR.DS-5            | CC6.6           | SQLAlchemy parameterised queries           | All ORM models                                                     | Backend              | Per PR         |
| CORS enforcement          | A.13.1              | PR.AC-5            | CC6.6           | `CORSMiddleware` in main.py                | `app/main.py`                                                      | Backend              | Per PR         |
| Data retention policy     | A.5.33              | PR.DS              | CC9.2           | Usage ledger records retention events      | `app/modules/billing/models.py`                                    | Platform             | Quarterly      |
| Export portability        | A.18.1              | PR.IP-6            | CC9.2           | RFC 4180 CSV + JSON Lines export           | Alert/Incident export endpoints                                    | Platform             | Monthly        |
| Incident response         | A.5.24–A.5.27       | RS.RP, RS.AN       | CC7.3           | Interim runbook in SECURITY_AND_COMPLIANCE | `docs/security/SECURITY_AND_COMPLIANCE.md`                         | Security Engineering | Quarterly      |
| Key management            | A.8.24              | PR.DS              | CC6.1           | Key rotation policy documented             | `docs/security/SECURITY_AND_COMPLIANCE.md`                         | Platform             | Quarterly      |
| Contract validation CI    | A.12.1              | PR.IP-1            | CC8.1           | JSON Schema sample validator               | `scripts/check_contract_samples.py`                                | Platform             | Per PR         |

---

## Threat Model Summary

See full threat model in [SECURITY_AND_COMPLIANCE.md](security/SECURITY_AND_COMPLIANCE.md#threat-model-summary).

| Threat                    | Mitigating Controls                                       | Current Risk |
| ------------------------- | --------------------------------------------------------- | ------------ |
| Cross-tenant data leakage | Tenant isolation (org_scope), RBAC                        | Low          |
| Alert spam / DoS          | Rate limit (AC-05), Idempotency (IM-01), Redis guardrails | Low          |
| JWT theft and replay      | Key length validation, revocation, TLS (partial)          | Medium       |
| Evidence tampering        | SHA-256 evidence hash, immutable audit                    | Low          |
| Privilege escalation      | KNOWN_FEATURES allowlist, org scope                       | Low          |
| Duplicate incident storm  | Savepoint idempotency (BL-004)                            | Low          |

---

## Accreditation Roadmap

| Milestone                              | Target Date | Exit Evidence                                       | Owner                |
| -------------------------------------- | ----------- | --------------------------------------------------- | -------------------- |
| Threat model complete                  | 2026-04-30  | Approved document                                   | Security Engineering |
| Data classification complete           | 2026-04-30  | Classification matrix in S&C doc                    | Security Engineering |
| Control evidence baseline complete     | 2026-04-10  | This document fully populated                       | Security Engineering |
| NCIA tender security pack submission   | 2026-04-10  | Bid package (this doc + SECURITY_AND_COMPLIANCE.md) | Program Management   |
| External penetration test commissioned | 2026-06-01  | Scoping statement signed                            | Security Engineering |
| ISO 27001 gap analysis                 | 2026-06-15  | Gap report with remediation plan                    | Security Engineering |
| SOC 2 Type I scope defined             | 2026-07-01  | Scope definition approved                           | CEO + Legal          |
| MFA implementation                     | 2026-07-01  | Sprint 8 delivery                                   | Platform             |
| Dependabot + container scanning in CI  | 2026-05-15  | Pipeline config PR merged                           | DevSecOps            |

---

## Continuous Verification Commands

```bash
# Full test suite (all acceptance criteria covered)
cd apps/api && python -m pytest tests/ -q --tb=short

# Audit coverage CI gate
python3 scripts/check_audit_coverage.py

# Contract validation CI gate
python3 scripts/check_contract_samples.py

# Alembic migration chain (confirms all control migrations applied)
cd apps/api && python -m alembic history

# BFF TypeScript type check (confirms license gate compiles)
cd apps/bff && npm run lint
```

---

## Open Gaps

- Validate final clause/control references against the selected submission framework before external submission.
- Add external assurance artifacts (pen test report, ISO gap analysis) as they become available.
- MFA (AC-03) implementation not yet started — target Sprint 8.
- Container image scanning (trivy) not yet integrated into CI — target next DevSecOps sprint.
- Full incident response runbook (IR-01) pending — required before NCIA tender submission.
- Automated upstream license attestation at ingest time is partially implemented.
