# NATO Submission Close-Out Checklist

**Version:** 1.0 | **Date:** 2026-04-10 | **Status:** Active

This document converts the current repo-backed readiness posture into a concrete close-out sequence for NATO-aligned submissions. It is the canonical execution list for the remaining work that cannot be closed purely by internal code changes.

---

## 1 Current Position

The following internal readiness items are already in place and validated in-repo:

- Security evidence pack, incident runbook, MFA, sanctions controls, and CI audit gates are implemented.
- CoT and STANAG 5527 / NFFI XML export paths are implemented.
- D-04 lab receiver rehearsal evidence is generated and archived.
- Repo-backed air-gapped rehearsal evidence is generated and archived.
- Live-source integration scaffolding exists for aisstream.io, OpenSky, and Spire S-AIS.
- Statistical anomaly scoring and spoofing-detection logic are implemented in code.

The remaining blockers are therefore external-assurance, field-validation, and partner-traction items.

---

## 2 Exit Criteria

Submission readiness is achieved only when all of the following are true:

| Track                          | Exit Condition                                                        | Evidence Required                                                       | Owner                             |
| ------------------------------ | --------------------------------------------------------------------- | ----------------------------------------------------------------------- | --------------------------------- |
| External interoperability      | TAK Server or NATO-owned receiver confirms ingest of CoT/NFFI outputs | Receiver logs, screenshots, signed test note, archived payload set      | Integrations + Program Management |
| Classified deployment evidence | Customer-side or partner-side air-gapped rehearsal completed          | Operator run log, deployment checklist, classification-marking evidence | DevSecOps + Security Engineering  |
| External security assurance    | Independent pen test and ISO 27001 gap analysis completed             | Pen test report, remediation summary, ISO gap report                    | Security Engineering              |
| Pilot evidence                 | 30-day pilot or equivalent operational evaluation completed           | KPI pack, operator feedback, ROI summary, uptime evidence               | Solutions Engineering             |
| Consortium maturity            | Named integrator, field operator, and compliance partner secured      | LOIs, MoU, outreach log, bid ownership confirmation                     | CEO + Partnerships                |

---

## 3 Ordered Close-Out Sequence

### Phase 1: Freeze Internal Baseline

| Step | Action                                                         | Output                                                 | Owner              | Target    |
| ---- | -------------------------------------------------------------- | ------------------------------------------------------ | ------------------ | --------- |
| 1.1  | Freeze the evidence baseline for security and interoperability | Final reference set of repo-backed evidence artifacts  | Program Management | Immediate |
| 1.2  | Record the current passing validation commands in the bid file | Validation appendix with exact commands and pass dates | Platform           | Immediate |
| 1.3  | Open a named bid record for the target route                   | Route owner, freeze date, decision log                 | Program Management | Immediate |

### Phase 2: Close External Technical Evidence

| Step | Action                                                      | Output                                                    | Owner                  | Depends On |
| ---- | ----------------------------------------------------------- | --------------------------------------------------------- | ---------------------- | ---------- |
| 2.1  | Run external TAK Server validation using the D-04 package   | Ingest logs, receiver screenshots, signed validation note | Integrations           | 1.1        |
| 2.2  | Run external NATO-owned or partner NFFI receiver validation | Field conformance record and payload archive              | Integrations + Partner | 2.1        |
| 2.3  | Execute customer-side or partner-side air-gapped rehearsal  | Classified deployment evidence annex                      | DevSecOps              | 1.1        |

### Phase 3: Close External Assurance

| Step | Action                                          | Output                                    | Owner                           | Depends On |
| ---- | ----------------------------------------------- | ----------------------------------------- | ------------------------------- | ---------- |
| 3.1  | Commission external penetration test            | Signed scope and booked assessment window | Security Engineering            | 1.3        |
| 3.2  | Complete ISO 27001 gap analysis                 | External gap report with remediation map  | Security Engineering            | 3.1        |
| 3.3  | Attach remediation status for material findings | Bid-ready security annex                  | Security Engineering + Platform | 3.2        |

### Phase 4: Close Operational Proof

| Step | Action                                                    | Output                        | Owner                 | Depends On |
| ---- | --------------------------------------------------------- | ----------------------------- | --------------------- | ---------- |
| 4.1  | Launch a 30-day pilot or sponsor-backed evaluation window | Named pilot record and scope  | Solutions Engineering | 1.3        |
| 4.2  | Capture KPI evidence using the pilot template             | Completed KPI evidence pack   | Solutions Engineering | 4.1        |
| 4.3  | Capture operator and mission feedback                     | Sponsor-safe feedback summary | Solutions Engineering | 4.1        |

### Phase 5: Close Partner and Bid Maturity

| Step | Action                                            | Output                                  | Owner                       | Depends On |
| ---- | ------------------------------------------------- | --------------------------------------- | --------------------------- | ---------- |
| 5.1  | Shortlist integrator candidates and open outreach | Outreach tracker and shortlist          | Partnerships                | 1.3        |
| 5.2  | Secure field operator participation               | Named operator LOI or pilot sponsorship | CEO + Solutions Engineering | 5.1        |
| 5.3  | Secure compliance support partner                 | RFQ result and named support partner    | Security Engineering        | 5.1        |
| 5.4  | Sign consortium MoU / LOIs                        | Bid-ready consortium package            | CEO                         | 5.2        |

---

## 4 Immediate Priority List

These are the next actions with the highest impact on submission viability:

1. Schedule the external TAK / NFFI receiver validation against the existing D-04 evidence package.
2. Commission the pen test and lock the external assurance dates.
3. Identify and contact the first three integrator and field-operator candidates.
4. Open the pilot record and attach the KPI template to a named sponsor conversation.
5. Run the customer-side or partner-side classified rehearsal and archive the operator evidence.

---

## 5 Evidence Assembly Map

| Package Area             | Canonical Source                                                     |
| ------------------------ | -------------------------------------------------------------------- |
| Security baseline        | `docs/security/SECURITY_EVIDENCE_PACK.md`                            |
| Interoperability profile | `docs/product/INTEROPERABILITY_PROFILE.md`                           |
| Pilot KPI template       | `docs/funding/FUNDING_PILOT_EVIDENCE_TEMPLATE.md`                    |
| Consortium model         | `docs/architecture/CONSORTIUM_EXECUTION_MODEL.md`                    |
| D-04 evidence            | `apps/api/docs/evidence/D-04_RECEIVER_CONFORMANCE_EVIDENCE_FINAL.md` |
| Air-gap evidence         | `docs/evidence/AIR_GAPPED_REHEARSAL_EVIDENCE_FINAL.md`               |
| Route decisions          | `docs/funding/FUNDING_ROUTE_MATRIX.md`                               |

---

## 6 Rule For Bid-Go

No route should move from candidate to committed unless:

- at least one named operator or sponsor exists,
- the external receiver-validation path has a booked execution date,
- the external security-assurance path has a booked execution date,
- and the accountable owner can point to the exact evidence files listed above.
