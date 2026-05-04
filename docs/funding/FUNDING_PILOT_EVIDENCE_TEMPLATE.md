# Funding Pilot Evidence Template

**Version:** 1.2 | **Date:** 2026-04-07

This template operationalizes BL-017 and standardizes proof artifacts for funding submissions and procurement evaluations.

---

## Pilot Metadata

- Pilot name:
- Sponsor organization:
- Start date:
- End date:
- Technical owner:
- Program owner:
- Reference bid / programme:

---

## Mission KPI Baseline and Target

The following KPI definitions and baseline/target values are frozen at pilot kickoff. Changes require documented approval with a revision note.

| KPI                       | Definition                                                                                                                | Measurement Window                          | Data Source                                                                                                 | Baseline                                                                            | Target                                                     | Actual | Status             |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------- | ----------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- | ---------------------------------------------------------- | ------ | ------------------ |
| Detection lead-time       | Median time from eligible AIS event ingestion to alert creation, measured at alert `created_at` minus event `occurred_at` | 30-day pilot window                         | Pipeline timestamps + alert records (`alerts` table)                                                        | ~22 min (industry reference for manual maritime analyst triage workflows)           | < 2 min (automated detection)                              | TBD    | Pending pilot data |
| False alert precision     | 1 − (non-actionable alerts / total reviewed alerts) across operator-reviewed samples                                      | Per review cycle (weekly) + pilot aggregate | Analyst review outcomes in incident records                                                                 | ~0.55 (industry reference: 30–60% false alert rate for legacy rule-based AIS tools) | ≥ 0.85 (≤ 15% false alert rate)                            | TBD    | Pending pilot data |
| Analyst time per incident | Median operator time from alert assignment to incident resolution, including evidence review                              | Sampled weekly + pilot aggregate            | Incident `acknowledged_at` and `resolved_at` minus alert `created_at`; cross-checked with operator time log | ~3 h (manual correlation + narrative write-up)                                      | ≤ 45 min (automated evidence dossier + pre-filled context) | TBD    | Pending pilot data |
| Data migration confidence | Percentage of competitor track rows imported with confidence score ≥ 0.90                                                 | Single import batch                         | `CompetitorMigrationReport.confidence_score`                                                                | N/A (new capability)                                                                | ≥ 0.90                                                     | TBD    | Ready to measure   |
| System availability       | API uptime during pilot window                                                                                            | 30-day pilot window                         | Prometheus `up` metric + synthetic health check                                                             | N/A (pre-pilot)                                                                     | ≥ 99.5%                                                    | TBD    | Ready to measure   |

### KPI Baseline Rationale

- **Detection lead-time baseline (22 min):** Representative of analyst-in-loop workflows where AIS alerts require manual queue review before action. Source: published maritime security workflow studies (2023–2024).
- **False alert precision baseline (0.55):** Legacy rule-based AIS anomaly tools typically show 30–60% false alert rates before operator tuning. AegisAIS tiered rule engine and confidence scoring targets suppression of low-signal events.
- **Analyst time baseline (3 h):** Includes alert triage (~30 min), open-source vessel lookup (~60 min), incident narrative (~60 min), escalation decision (~30 min). Automated evidence dossier (BL-009, BL-012) targets ≤ 45 min total.

---

## Measurement Protocol

1. Record baseline for a comparable workflow **before** pilot start date. Freeze baseline values in this document.
2. Use the same tenant, alert classes, and review criteria throughout baseline and pilot periods.
3. Freeze KPI definitions at pilot kickoff; changes require documented approval and a revision note.
4. Store all query logic and calculation notes alongside evidence outputs (path referenced below).
5. Run a mid-pilot checkpoint at day 15 to assess trajectory and surface data quality issues early.
6. Final evidence bundle assembled at pilot close + 5 business days.

---

## Evidence Bundle

Complete the paths below as evidence is generated:

- Validation report (migration): _path TBD_
- Interoperability conformance test results: _path TBD_
  - Run: `python -m pytest apps/api/tests/test_competitor_import.py apps/api/tests/test_alert_evidence_hash.py -v && python3 scripts/check_contract_samples.py`
- Security evidence references: `docs/SECURITY_EVIDENCE_PACK.md`, `docs/security/SECURITY_AND_COMPLIANCE.md`
- Collaboration and tenant-boundary validation:
  - Run: `cd apps/api && ./.venv/bin/python -m pytest tests/test_sharing_api.py tests/test_websocket_auth.py tests/test_interoperability.py -q`
  - Latest known result: `18 passed, 1 xfailed`
- KPI calculation query / notebook: _path TBD_
- Operator feedback summary: _path TBD_
- ROI summary: _path TBD_
- SBOM artifacts: `backend-sbom.cdx.json`, `frontend-sbom.cdx.json` (CI artifacts)
- Interoperability profile: `docs/INTEROPERABILITY_PROFILE.md`
- Supply chain assurance: `docs/SUPPLY_CHAIN_ASSURANCE.md`
- Current platform audit baseline: `docs/AEGISAIS_AUDIT_2026-04-07.md`
- Current user-flow baseline: `docs/USER_FLOW_AUDIT_2026-04-07.md`

---

## ROI Reference Model

| Outcome                              | Conservative Estimate                             | Source                             |
| ------------------------------------ | ------------------------------------------------- | ---------------------------------- |
| Analyst hours saved per incident     | 2.25 h/incident (75% of 3 h baseline)             | KPI target: 45 min vs 3 h baseline |
| Annual savings at 200 incidents/year | 450 analyst-hours/year                            |                                    |
| Analyst day-rate equivalent (EUR)    | ~€800–€1,200/day (defence contractor market rate) |                                    |
| Annual ROI (analyst hours, mid-rate) | ~€50,000–€75,000/year per operating org           |                                    |
| Detection lead-time reduction        | ~20 min/incident                                  | 22 min → < 2 min                   |
| Cost of 20-min threat response delay | Organisation-specific; use threat cost model      |                                    |

---

## Risks and Mitigations

| Risk                                         | Impact | Mitigation                                                                                    | Owner                 |
| -------------------------------------------- | ------ | --------------------------------------------------------------------------------------------- | --------------------- |
| Data quality drift between ingestion sources | High   | Validation gates + retry-safe import adapter (BL-011); `confidence_score` threshold enforced  | Integrations          |
| Operational adoption lag                     | Medium | Guided onboarding (BL-012); < 30-min setup; sample data included                              | Solutions Engineering |
| Compliance evidence delay                    | High   | Weekly evidence checkpoint; Security Engineering owns `SECURITY_EVIDENCE_PACK.md`             | Security Engineering  |
| KPI measurement tool unavailability          | Medium | Fallback to manual count from DB queries; queries documented in evidence bundle               | Technical Owner       |
| Pilot scope creep                            | Medium | Freeze KPI definitions and pilot scope at kickoff; formal change request required             | Program Owner         |
| Environment-dependent live feed readiness    | High   | Record provider-connected vs stub-backed mode explicitly in pilot evidence and KPI notes      | Technical Owner       |
| Procurement overclaim vs current control set | High   | Use current trust kit and audit baselines; do not claim completed IR runbook / pen test / MFA | Program Owner         |

---

## Sign-off

| Role                    | Name | Date | Signature |
| ----------------------- | ---- | ---- | --------- |
| Technical sign-off      |      |      |           |
| Program sign-off        |      |      |           |
| Sponsor acknowledgement |      |      |           |
| Security Engineering    |      |      |           |
