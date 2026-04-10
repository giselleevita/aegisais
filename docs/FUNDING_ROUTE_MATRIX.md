# Funding Route Matrix

This document operationalizes BL-013 by mapping target NATO-aligned funding routes to concrete submission decisions.

## Current Evidence Posture

- Core code-vs-doc audit baseline exists: `docs/AEGISAIS_AUDIT_2026-04-07.md`
- User and operator flow baseline exists: `docs/USER_FLOW_AUDIT_2026-04-07.md`
- Security evidence pack exists: `docs/SECURITY_EVIDENCE_PACK.md`
- Security and compliance control matrix exists: `docs/security/SECURITY_AND_COMPLIANCE.md`
- Focused collaboration and tenant-boundary validation has been run successfully:
  - `cd apps/api && ./.venv/bin/python -m pytest tests/test_sharing_api.py tests/test_websocket_auth.py tests/test_interoperability.py -q`
  - Latest known result: `18 passed, 1 xfailed`

Open procurement blockers that should still be treated as blockers, not implied as complete:

- External penetration test artifact
- Full incident response runbook
- MFA completion
- Final authoritative entitlement decision plane across API and BFF
- Provider-connected live-feed proof in target environment

## Decision Rules

- Only pursue routes where at least one pilot sponsor can be named.
- No-bid if mandatory compliance evidence cannot be produced by deadline.
- Prioritize routes with mission relevance to maritime domain awareness and dual-use security outcomes.

## Route Matrix

| Route                      | External Window                 | Internal Decision Date | Internal Freeze Date | Eligibility Snapshot                                                    | Required Artifacts                                                | Owner                             | Gate Status             |
| -------------------------- | ------------------------------- | ---------------------- | -------------------- | ----------------------------------------------------------------------- | ----------------------------------------------------------------- | --------------------------------- | ----------------------- |
| DIANA Challenge            | Next applicable challenge cycle | 2026-04-15             | 2026-05-15           | Dual-use defense innovation, allied relevance, technical maturity       | Problem fit brief, technical whitepaper, pilot plan, team profile | Program Management                | Candidate               |
| NATO Innovation Fund (NIF) | Rolling / partner-led           | 2026-04-22             | 2026-05-30           | Venture-scale growth thesis, allied strategic relevance                 | Investment narrative, traction metrics, governance package        | CEO                               | Discovery               |
| NCIA / NATO Tender Path    | Per tender notice               | 2026-04-10             | Tender-specific      | Procurement-compliant delivery capability, security/compliance evidence | Bid package, security evidence pack, interoperability profile     | Program Management + Partnerships | Candidate with blockers |

## Submission Checklist

- Route selected and approved by bid-go meeting
- Named submission owner and backup
- Deadline and internal freeze date recorded
- Required artifact owners assigned
- Submission dependency chain recorded (`security evidence`, `interop profile`, `pilot evidence`, `consortium sign-off`)
- Risk register reviewed and signed
- Current blocker review completed against `SECURITY_EVIDENCE_PACK.md` and `SECURITY_AND_COMPLIANCE.md`
- Messaging reviewed against current audit baseline so older gap-doc claims are not reused in the submission

## Bid-Go Log

| Date       | Route            | Decision | Rationale                                           | Action Owner       |
| ---------- | ---------------- | -------- | --------------------------------------------------- | ------------------ |
| 2026-03-31 | Portfolio review | Pending  | Initial matrix created and awaiting route selection | Program Management |
