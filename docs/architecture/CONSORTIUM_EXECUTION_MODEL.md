# Consortium Execution Model

**Version:** 1.1 | **Date:** 2026-03-31

This document operationalizes BL-018 and formalizes partner roles, bid governance, RACI, and execution calendar for consortium-based defense funding submissions.

---

## 1 Partner Role Matrix

| Role                                   | Core Responsibility                                                                     | Selection Criteria                                                                                                                                        | Headcount | Owner                 |
| -------------------------------------- | --------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- | --------------------- |
| **Prime / Lead**                       | Submission ownership; contractual and financial lead; programme delivery responsibility | Proven procurement capacity; delivery track record in defense programmes; legal entity eligible to contract with target programme (DIANA, NCIA, national) | 1 org     | CEO                   |
| **Integrator**                         | Technical integration and platform deployment at partner / customer site                | Deep API and Kubernetes platform competence; experience with maritime or C2 system integration; prior work in allied force or coast guard context         | 1–2 orgs  | Partnerships          |
| **Field Operator**                     | Operational validation; pilot usage; mission domain credibility                         | Active maritime or naval domain presence; operational staff available for pilot; recognised by evaluator community                                        | 1–2 orgs  | Solutions Engineering |
| **Compliance / Accreditation Support** | Defence security review support; evidence pack co-authorship; audit support             | Demonstrated ISO 27001 / DIATF / JSP 440 experience; cleared / security-vetted staff available                                                            | 1 org     | Security Engineering  |

### Identified Candidates (status as of Q1 2026)

| Role               | Category                           | Status   | Next Step                                         | Owner                 |
| ------------------ | ---------------------------------- | -------- | ------------------------------------------------- | --------------------- |
| Prime / Lead       | AegisAIS Ltd                       | Active   | Confirm prime eligibility for DIANA Challenge 3   | CEO                   |
| Integrator         | TBD — Maritime Systems Integrator  | Identify | Shortlist from DIGEST / NATO TIDE participants    | Partnerships          |
| Field Operator     | TBD — Coast Guard / Naval Unit     | Identify | Pilot scoping call via DIANA introduction channel | Solutions Engineering |
| Compliance Support | TBD — Specialist ITSEC consultancy | Identify | Issue RFQ and qualification review                | Security Engineering  |

---

## 2 Bid Governance

### 2.1 Decision Quorum

All bid-go / no-bid decisions require agreement from:

1. CEO (strategic and financial authority)
2. Program Management (delivery feasibility)
3. Security Engineering (compliance readiness)

A no-bid decision by any quorum member triggers a 5-business-day escalation window for further review before the decision is finalised.

### 2.2 Weekly Bid Readiness Review

| Item                              | Frequency | Chair                | Attendees                        | Output                         |
| --------------------------------- | --------- | -------------------- | -------------------------------- | ------------------------------ |
| Route status review (active bids) | Weekly    | Program Management   | CEO, Engineering, Partnerships   | Decision log update            |
| Evidence pack checkpoint          | Weekly    | Security Engineering | Program Management, Integrations | Evidence readiness score (1–5) |
| Partner pipeline review           | Bi-weekly | Partnerships         | CEO, Solutions Engineering       | Candidate status update        |
| No-bid review                     | Ad-hoc    | CEO                  | All quorum members               | No-bid record with rationale   |

### 2.3 Escalation Path

```
Issue identified by owner
  → Owner raises in weekly review
    → Program Management tracks and assigns resolution deadline
      → Unresolved after 5 business days: escalates to CEO decision
        → CEO decision documented in bid log (FUNDING_ROUTE_MATRIX.md)
```

---

## 3 RACI Matrix

| Workstream                         | Responsible                     | Accountable        | Consulted                          | Informed              |
| ---------------------------------- | ------------------------------- | ------------------ | ---------------------------------- | --------------------- |
| Funding route selection            | Program Management              | CEO                | Partnerships, Security Engineering | Engineering           |
| Technical delivery (BL-001–BL-018) | Engineering                     | CTO                | Program Management                 | CEO                   |
| Security evidence pack             | Security Engineering            | Program Management | Platform, CEO                      | Engineering           |
| Interoperability evidence          | Integrations + API Platform     | Program Management | Solutions Engineering              | CEO                   |
| Pilot evidence package             | Solutions Engineering + Product | Program Management | Security Engineering, Integrations | CEO                   |
| Partner identification / outreach  | Partnerships                    | CEO                | Program Management                 | Solutions Engineering |
| Compliance support sourcing        | Security Engineering            | CEO                | Partnerships                       | Program Management    |
| Bid submission                     | Program Management              | CEO                | All quorum                         | Partners              |
| Post-award programme management    | Program Management              | CEO                | Engineering, Partners              | All                   |

---

## 4 Bid Calendar (90-Day Horizon)

| Milestone                                         | Target    | Owner                       | Dependencies               | Status      |
| ------------------------------------------------- | --------- | --------------------------- | -------------------------- | ----------- |
| Prime eligibility confirmed for DIANA Challenge 3 | Week 1    | CEO                         | Legal entity review        | Not started |
| Integrator shortlist (≥ 3 candidates)             | Week 2    | Partnerships                | TIDE / DIGEST contacts     | Not started |
| Field operator scoping call                       | Week 3    | Solutions Engineering       | DIANA introduction channel | Not started |
| Compliance support RFQ issued                     | Week 2    | Security Engineering        | —                          | Not started |
| BL-015 interoperability profile                   | ✅ Week 1 | Integrations + API Platform | BL-011, BL-009             | Done        |
| BL-016 supply chain assurance                     | ✅ Week 1 | DevSecOps                   | —                          | Done        |
| BL-017 pilot evidence template                    | ✅ Week 1 | Solutions Engineering       | BL-011, BL-012             | Done        |
| BL-018 consortium model                           | ✅ Week 1 | CEO + Partnerships          | BL-013                     | Done        |
| Consortium MoU / LOI signed                       | Week 5    | CEO                         | Partner identification     | Not started |
| Full bid package assembled                        | Week 8    | Program Management          | All BL-01x complete        | Not started |
| Internal bid review (full quorum)                 | Week 9    | CEO                         | Bid package ready          | Not started |
| Submission (target: DIANA Challenge 3)            | Week 12   | Program Management          | Internal review passed     | Not started |

---

## 5 Communication Cadence

| Audience                     | Channel                             | Frequency                       | Owner              |
| ---------------------------- | ----------------------------------- | ------------------------------- | ------------------ |
| Internal bid team            | Bid readiness review (async + sync) | Weekly                          | Program Management |
| Partners                     | Partner status call                 | Bi-weekly                       | Partnerships       |
| Evaluator / programme office | Formal correspondence only          | As required                     | CEO                |
| Engineering                  | Backlog sync                        | Weekly (existing sprint review) | CTO                |
| Board / investors            | Programme status report             | Monthly                         | CEO                |

---

## 6 Governance Artefacts

| Artefact                  | Location                                            | Owner                 | Update Frequency      |
| ------------------------- | --------------------------------------------------- | --------------------- | --------------------- |
| Funding route matrix      | `docs/funding/FUNDING_ROUTE_MATRIX.md`              | Program Management    | Weekly                |
| Bid decision log          | `docs/funding/FUNDING_ROUTE_MATRIX.md` (Bid-Go Log section) | CEO             | Per decision          |
| Evidence pack             | `docs/security/SECURITY_EVIDENCE_PACK.md`           | Security Engineering  | Per compliance change |
| Compliance control matrix | `docs/security/SECURITY_AND_COMPLIANCE.md`          | Security Engineering  | Monthly               |
| KPI baseline              | `docs/funding/FUNDING_PILOT_EVIDENCE_TEMPLATE.md`   | Solutions Engineering | Per pilot             |
| This document             | `docs/architecture/CONSORTIUM_EXECUTION_MODEL.md`   | CEO + Partnerships    | Quarterly             |
