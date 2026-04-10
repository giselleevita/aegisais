# AegisAIS Procurement Evidence Snapshot - 2026-04-07

## Executive Summary

- Current state: AegisAIS has materially stronger control evidence and operational hardening than older strategy and gap docs implied.
- Ready-to-use evidence exists for tenant isolation, authenticated interop and collaboration paths, auditability, bounded exports, BFF JWT normalization, and classification/releasability gates.
- Procurement caution: external assurance and some control-plane maturity items are still open and must not be presented as complete.

## Current Verified Evidence

### Platform audit baseline

- Core code-vs-doc audit: `docs/AEGISAIS_AUDIT_2026-04-07.md`
- User and operator flow audit: `docs/USER_FLOW_AUDIT_2026-04-07.md`
- Security evidence pack: `docs/SECURITY_EVIDENCE_PACK.md`
- Security and compliance control matrix: `docs/security/SECURITY_AND_COMPLIANCE.md`
- Interoperability profile: `docs/INTEROPERABILITY_PROFILE.md`
- Trust-facing summary: `docs/TRUST_KIT.md`

### Focused API validation

Command:

```bash
cd apps/api && ./.venv/bin/python -m pytest tests/test_sharing_api.py tests/test_websocket_auth.py tests/test_interoperability.py -q
```

Latest known result:

- `18 passed, 1 xfailed`

Validated areas:

- Sharing routes require authenticated user context
- Sharing derives `source_org_id` from caller org instead of hardcoded tenant
- COP feed requires authenticated viewer access
- Alert export is bounded
- Org-scoped alert-status WebSocket broadcasts stay within tenant boundary
- Interop export uses persisted scoped entities

### BFF validation

Commands:

```bash
cd apps/bff && npm run lint && npm test
```

Latest known result:

- TypeScript typecheck passed
- `6/6` BFF auth-policy tests passed

Validated areas:

- Missing/invalid bearer token rejection
- Classification gate rejection on insufficient clearance
- Releasability gate rejection on missing NATO tag
- Normalized auth context returned from `/v1/auth/context`

### Web validation

Command:

```bash
cd apps/web && npm run lint
```

Latest known result:

- ESLint passed

## Control State Snapshot

### Strongly evidenced now

- Org-scoped tenant filtering on primary API entity paths
- Fail-closed org-scope behavior for unscoped models
- Authenticated interop export against persisted entities
- Authenticated sharing and COP routes
- Org-aware routing for alert-status WebSocket payloads
- BFF JWT claim normalization for role, clearances, releasability, and licenses
- BFF classification and releasability policy middleware
- Audit matrix and audit plumbing for major operator/governance flows
- Bounded alert export behavior

### Evidenced but still partial

- Entitlement enforcement exists, but a single authoritative cross-surface entitlement decision plane is still being consolidated
- Live feed capability exists, but production-grade readiness still depends on provider-connected environments and evidence capture
- Collaboration flow is authenticated and tenant-derived, but still payload-backed rather than persisted as first-class collaboration records

## Open Blockers

These should remain explicit blockers in funding and procurement material:

- External penetration test artifact
- Full incident response runbook sign-off and operationalization
- MFA completion
- Final authoritative entitlement decision plane across API and BFF
- Provider-connected live-feed proof in the target environment
- Persisted collaboration records and provenance beyond payload-backed sharing

## Safe External Claims

These claims are supportable from current repo evidence:

- AegisAIS enforces tenant-aware access patterns and audited operator workflows on core alert and incident surfaces
- AegisAIS supports authenticated NATO-oriented export and collaboration pathways with current regression coverage
- AegisAIS includes claim-normalized BFF auth context and policy gates for classification and releasability-sensitive routes
- AegisAIS provides explainable rule-based anomaly detection with supporting audit and evidence lineage

## Claims To Avoid

Do not currently claim:

- Completed MFA rollout
- Completed external penetration testing
- Completed full incident response program maturity
- Guaranteed provider-connected live-feed readiness in all target environments
- Fully unified entitlement policy across all surfaces
- Fully persisted collaboration provenance for all sharing actions

## Suggested Submission Bundle

Minimum evidence bundle for current procurement or funding use:

1. `docs/PROCUREMENT_EVIDENCE_SNAPSHOT_2026-04-07.md`
2. `docs/AEGISAIS_AUDIT_2026-04-07.md`
3. `docs/USER_FLOW_AUDIT_2026-04-07.md`
4. `docs/SECURITY_EVIDENCE_PACK.md`
5. `docs/security/SECURITY_AND_COMPLIANCE.md`
6. `docs/INTEROPERABILITY_PROFILE.md`
7. `docs/TRUST_KIT.md`
8. `docs/FUNDING_PILOT_EVIDENCE_TEMPLATE.md`
9. `docs/FUNDING_ROUTE_MATRIX.md`

## Procurement Readout

AegisAIS is now in a state where procurement-facing materials can credibly reference concrete security and interoperability evidence, but only if they stay tightly aligned to the current audited baseline. The primary risk is no longer “missing platform,” but “overstating unresolved assurance items.”
