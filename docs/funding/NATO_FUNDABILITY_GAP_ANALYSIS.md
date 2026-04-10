# NATO Fundability Gap Analysis

**Version:** 1.0 | **Date:** 2026-03-31 | **Classification:** INTERNAL — Strategic Planning

---

## Executive Summary

1. **Biggest risk:** AegisAIS positions itself as a "data quality tool for AIS anomalies" but NATO funds **AI-driven maritime domain awareness platforms**. The absence of any ML/AI capability, live data ingestion, and NATO interoperability standards (STANAG 5527, CoT) makes the product structurally unfundable at DIANA or NIF without major feature investment.

2. **Biggest opportunity:** The ITDAE critical infrastructure protection module (Baltic cables) is directly aligned with NATO's #1 maritime priority post-Nord Stream. Expanding this from 4 hardcoded corridors to a full critical submarine infrastructure monitoring capability — with live AIS feeds, dark vessel detection, and spoofing identification — creates a unique wedge into DIANA Challenge 3.

3. **Top action:** Wire live AIS ingestion, implement AIS spoofing detection, and build a STANAG 5527/CoT export layer within the next 8 weeks. Without these three, no NATO submission is credible.

---

## Part 1 — What You Have (Honest Assessment)

| Capability                                 | Depth                                                                                                    | NATO Relevance                                                 |
| ------------------------------------------ | -------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| 7 heuristic AIS detection rules            | ✅ Production-quality                                                                                    | Medium — necessary but not differentiating                     |
| Analyst UI (map, alerts, tracks)           | ✅ Functional                                                                                            | Medium — standard capability                                   |
| ITDAE geofence + behavioral rules          | ✅ Detection logic solid                                                                                 | **HIGH** — directly aligned with NATO CIP priorities           |
| ITDAE risk scoring (multi-signal weighted) | ✅ Well-designed                                                                                         | **HIGH** — explainable AI narrative                            |
| Alert idempotency + evidence integrity     | ✅ SHA-256 hashes                                                                                        | High — forensic chain-of-custody for intelligence products     |
| Competitor import adapters                 | ✅ Working                                                                                               | Low — procurement differentiator, not mission-relevant         |
| Security evidence pack                     | ⚠️ Partial (IR runbook, MFA, and CI scanning implemented; pen test still open)                           | **BLOCKER** for NCIA tender                                    |
| Interop profile                            | ⚠️ CoT/NFFI XML implemented; lab receiver rehearsal automated, external receiver confirmation still open | **BLOCKER** until partner or field conformance evidence exists |
| Sovereign deployment profiles              | ✅ EU/UK overlays                                                                                        | High — data residency for allied nations                       |
| S-AIS integration                          | 🔴 Stub (returns empty)                                                                                  | **BLOCKER** — multi-sensor is mandatory                        |
| ML/AI scoring                              | ⚠️ Statistical ensemble baseline implemented; no trained model or eval corpus                            | **BLOCKER** for DIANA-grade deep-tech narrative                |
| Live AIS stream                            | ⚠️ aisstream.io client implemented; no sustained pilot evidence                                          | **BLOCKER** until TRL-5 evidence exists                        |
| Vessel identity fusion                     | 🔴 Stub (schema only)                                                                                    | **BLOCKER** — multi-INT is core NATO MDA requirement           |
| Consortium partners                        | 🔴 All TBD except self                                                                                   | **BLOCKER** — DIANA requires named consortium                  |

**Honest TRL assessment:** TRL 4 (validated in lab). Not TRL 5 (not validated in relevant environment) because no live data feed has ever been connected.

---

## Part 2 — What NATO Actually Funds (and Why You Don't Match Yet)

### DIANA Challenge Programme

**What they want:**

- Dual-use deep technology solving an **allied defense problem**
- Clear AI/ML component (DIANA was created specifically for emerging tech — AI, quantum, biotech, space)
- Problem-solution fit with a named operational user
- TRL 4→6 progression plan with pilot evidence
- Consortium with integrator + field operator + compliance partner

**Where AegisAIS falls short:**

- Rule-based heuristics are 1990s technology — not "deep tech"
- Current ML layer is still a statistical baseline rather than a trained model with evaluation evidence.
- No named operational user or letter of intent
- Live ingest exists in code, but there is still no accepted TRL-5 pilot evidence package.
- Consortium is all "TBD"

### NATO Innovation Fund (NIF)

**What they want:**

- Venture-scale growth thesis (€100M+ addressable market)
- Strategic relevance to allied security
- Strong governance and IP strategy
- Traction metrics (users, revenue, partnerships)

**Where AegisAIS falls short:**

- No traction metrics (zero users, zero revenue)
- No commercial customers to cite
- Growth thesis is theoretical — no market validation
- IP strategy not documented

### NCIA Tender

**What they want:**

- Procurement-compliant delivery (NATO security clearances, TEMPEST, classified envs)
- Full security evidence pack (pen test, IR runbook, ISO 27001)
- STANAG interoperability (5527/NFFI, CoT, OTH-GOLD)
- Proven operational deployment

**Where AegisAIS falls short:**

- Security evidence incomplete (no pen test, no external assurance artefacts)
- STANAG serializers and repo-backed receiver rehearsal exist, but external operational receiver validation remains incomplete
- Classified environment deployment story exists in docs, and repo-backed rehearsal evidence now exists, but customer-side execution is still outstanding
- No operational deployment evidence

---

## Part 3 — The 12 Critical Gaps (Ranked by Impact on Fundability)

### GAP-01: No AI/ML Capability 🔴 CRITICAL

**Current state:** `scoring.py` contains `# Placeholder for ML / advanced scoring later`

**Why it kills funding:** DIANA was created to fund AI, quantum, and emerging tech. A rule-based anomaly detector is mature technology requiring no innovation funding. NIF invests in venture-scale tech companies — heuristic tools don't scale to €100M markets.

**What to build:**

- **Trajectory prediction model** — LSTM/Transformer trained on historical AIS to predict next position; flag deviations as anomalies
- **Behavioral profiling** — Unsupervised clustering (DBSCAN/HDBSCAN) to build vessel "pattern of life"; detect out-of-character behavior
- **AIS spoofing detection** — ML classifier for GPS manipulation signatures (impossible position sequences, clock drift patterns, RF fingerprint inconsistencies)
- **Ensemble scoring** — Combine heuristic rules + ML models into weighted confidence score with explainability (SHAP/LIME)

**Effort:** 8-12 weeks for trajectory prediction + spoofing detection MVP. Behavioral profiling can follow.

**NATO narrative:** "Explainable AI for maritime anomaly detection — heuristic rules provide baseline transparency; ML models detect novel threats human analysts would miss."

---

### GAP-02: No Live Data Ingestion 🔴 CRITICAL

**Current state:** `ITDAEStreamManager.start()` logs a message and does nothing. S-AIS client returns empty list.

**Why it kills funding:** A maritime surveillance tool that cannot ingest live AIS data is a demo, not a product. NATO evaluators will ask "show me live vessels in the Baltic" — you can't.

**What to build:**

- **aisstream.io WebSocket client** — Free tier available, covers global AIS. Wire to existing pipeline's `enqueue_point()`
- **AISHub UDP/TCP receiver** — Standard community AIS sharing network
- **Spire Maritime API client** — S-AIS provider, commercial but has NATO partnerships
- **NMEA TCP stream decoder** — Direct connection to AIS base stations

**Effort:** 2-4 weeks for aisstream.io + one S-AIS provider (Spire has the simplest REST API).

**NATO narrative:** "Multi-source AIS fusion — terrestrial AIS, satellite AIS, and community networks aggregated in real-time."

---

### GAP-03: No AIS Spoofing / Manipulation Detection 🔴 CRITICAL

**Current state:** Not implemented. Not even mentioned in backlog.

**Why it kills funding:** AIS spoofing is THE #1 maritime security concern for NATO post-Ukraine. Russia, Iran, and China actively spoof AIS to mask naval movements, sanctions evasion, and submarine cable operations. This is what NATO is desperately trying to solve.

**What to build:**

- **GPS manipulation detection** — Flag impossible position jumps that differ from spoofing (spoofing creates plausible-but-false tracks; teleport detection catches implausible ones)
- **Identity spoofing** — Multiple vessels broadcasting same MMSI simultaneously; MMSI format violations; flag-state inconsistencies
- **Dark-to-light transition analysis** — Vessel goes dark, reappears with different identity or trajectory (sanctions evasion pattern)
- **RF fingerprint correlation** (future) — Cross-reference AIS message RF characteristics with known transmitter profiles

**Effort:** 4-6 weeks for GPS manipulation + identity spoofing MVP. Dark-to-light requires live data (GAP-02 prerequisite).

**NATO narrative:** "Counter-spoofing capability addressing the most critical gap in allied maritime domain awareness."

---

### GAP-04: No STANAG / NATO Interoperability 🔴 HIGH

**Current state:** JSON schemas only. Interop profile admits: "No CoT XML serializer", "No STANAG 5527/NFFI XML".

**Why it kills funding:** NATO C2 systems (ICC, TRITON, MSSIS) speak STANAG 5527 (NFFI), Cursor-on-Target (CoT), and OTH-GOLD. A product that can't feed these systems is isolated from the NATO kill chain.

**What to build:**

- **STANAG 5527 / NFFI XML serializer** — Map Alert/Entity/Track schemas to NATO Force-Finding Information Format
- **Cursor-on-Target (CoT) XML output** — Standard for real-time tactical feeds (used by ATAK, TAK Server, NATO C2)
- **OTH-GOLD message formatter** — Over-the-Horizon Gold standard for maritime surveillance
- **NMEA AIS sentence generator** — Re-encode processed/fused data back to NMEA for downstream AIS displays

**Effort:** 3-5 weeks for CoT + STANAG 5527 serializers. OTH-GOLD can follow.

**NATO narrative:** "Native NATO interoperability — alerts and tracks flow directly into allied C2 systems without manual re-entry."

---

### GAP-05: No Dark Vessel Detection 🔴 HIGH

**Current state:** ITDAE has `AIS_DARK_IN_ZONE` (detects silence in cable zones) but no general dark vessel capability.

**Why it kills funding:** Dark vessel detection — finding ships with AIS off — is the core use case for satellite AIS. It's what navies pay for. Without it, the S-AIS integration (when built) has no purpose.

**What to build:**

- **Expected transmission model** — ML model predicts when a vessel "should" transmit based on historical pattern
- **Dark period detection** — Flag when expected transmission doesn't arrive (system-wide, not just cable zones)
- **SAR/optical satellite correlation** (future) — Cross-reference dark AIS periods with satellite imagery showing vessel still present
- **Fleet-wide darkness scoring** — Dashboard showing vessels ranked by cumulative dark time / suspicious patterns

**Effort:** 3-4 weeks for expected transmission model + dark period detection (requires GAP-02 as prerequisite for meaningful data).

**NATO narrative:** "Persistent surveillance — vessels that turn off AIS to avoid detection are identified and tracked through behavioral modeling and satellite correlation."

---

### GAP-06: Consortium is Entirely TBD 🔴 HIGH

**Current state:** Partner matrix shows: Integrator = "TBD", Field Operator = "TBD", Compliance Support = "TBD".

**Why it kills funding:** DIANA requires a consortium. NIF expects partnership evidence. NCIA tenders require delivery partners. You cannot submit a credible bid as a solo entity with no named partners.

**What to do:**

- **Integrator candidates:** SYSTEMATIC (France), Thales Maritime, Kongsberg Discovery, Saab Maritime — approach via NATO TIDE community or Digital Ocean programme
- **Field operator candidates:** Norwegian Coastal Administration, Finnish Border Guard, UK Maritime & Coastguard Agency, NATO MARCOM — approach via DIANA introduction channels
- **Compliance support:** PA Consulting (UK defence ITSEC), NCC Group, Nixu (Nordic cybersecurity) — issue RFQ immediately
- **Academic partner:** Consider a university partner (Plymouth, KTH, NTNU) for ML credibility and TRL evidence

**Effort:** Ongoing — 4-8 weeks to secure LOIs. This is the hardest gap to close because it requires relationship building, not code.

---

### GAP-07: No Classified Environment Story 🟡 HIGH

**Current state:** Sovereign deployment profiles exist (EU/UK Kubernetes overlays) but no classification discussion.

**Why it kills funding:** Defence data is classified. NATO procurement requires products to operate at NATO RESTRICTED minimum. Without an air-gapped deployment story and data classification marking, the product is limited to UNCLASSIFIED usage only.

**What to build/document:**

- **Air-gapped deployment guide** — Document offline installation, offline SBOM verification, offline update mechanism
- **Data classification marking** — Add NATO classification marking to all data objects (UNCLASSIFIED, RESTRICTED, CONFIDENTIAL, SECRET) per STANAG 4774
- **Cross-domain connectivity model** — Document how data flows between classification levels (e.g., AIS from UNCLASSIFIED → analysis at RESTRICTED → products at CONFIDENTIAL)
- **Security accreditation pathway** — Map to DIATF (UK), BSI (Germany), ANSSI (France) frameworks for MoD customer approval

**Effort:** 2-3 weeks for documentation + classification marking implementation; air-gapped guide requires deployment testing.

---

### GAP-08: Critical Infrastructure Protection is Too Narrow 🟡 MEDIUM-HIGH

**Current state:** 4 hardcoded Baltic cable corridors. No admin interface for geofence management.

**Why it kills funding:** NATO's critical submarine infrastructure concern extends to ALL subsea cables, pipelines, offshore wind farms, and ports across the Atlantic and Mediterranean. 4 hardcoded corridors is a demo, not a product.

**What to build:**

- **Dynamic geofence CRUD** — Admin UI/API to create, edit, and delete geofence zones (the ITDAE router already has some endpoints; expand them)
- **Pre-loaded infrastructure database** — Subsea cable routes from TeleGeography, pipeline routes from open data, offshore wind farm locations from 4C Offshore
- **Zone templates** — Pre-configured monitoring profiles (cable crossing, pipeline proximity, port approach, anchorage, offshore energy)
- **Multi-region expansion** — Mediterranean, North Atlantic, Arctic, Indo-Pacific cable corridors
- **Temporal geofences** — Zones that activate during exercises, events, or threat escalation

**Effort:** 3-4 weeks for dynamic geofence UI + pre-loaded infrastructure database.

**NATO narrative:** "Comprehensive critical submarine infrastructure monitoring — covering allied cable, pipeline, and energy assets across the Euro-Atlantic area."

---

### GAP-09: No Sanctions Evasion / Illicit Activity Detection 🟡 MEDIUM-HIGH

**Current state:** Partial. OFAC/EU/UN-backed watchlist matching, sovereign watchlist import, STS transfer detection, flag-hopping analysis, and dark-port sanctions correlation are implemented in the platform. Remaining work is operational rollout evidence and broader port-pattern analytics.

**Why it kills funding:** Sanctions enforcement is a top priority for NATO-aligned nations (Russian oil sanctions, North Korean shipping, Iranian proliferation). Coast guards and navies fund tools that help enforce sanctions.

**What to build:**

- **MMSI/IMO/flag-state watchlist matching** — Cross-reference vessel identifiers against OFAC SDN, EU consolidated sanctions list, UN Panel of Experts lists
- **Ship-to-ship transfer detection** — Identify vessels rendezvousing at sea (proximity + speed-matching algorithm)
- **Flag hopping detection** — Vessel changes flag state, MMSI, or name to evade sanctions
- **Dark activity + sanctions correlation** — Vessels that go dark in sanctioned ports or near sanctioned entities
- **Port call pattern analysis** — Flag vessels with unusual port rotation (visiting sanctioned + non-sanctioned ports alternately)

**Effort:** 1-2 weeks for operator evidence, historical data tuning, and broader port-pattern analytics.

**NATO narrative:** "Maritime sanctions enforcement support — automated detection of evasion patterns enabling faster CFSP/OFAC compliance action."

---

### GAP-10: Security Evidence Incomplete 🟡 MEDIUM

**Current state:** No pen test yet; incident response runbook, TOTP MFA, and container image scanning are now implemented.

**Why it kills funding:** NCIA tenders require completed security evidence. DIANA evaluators review security maturity as a TRL indicator.

**What to build:**

- **Incident response runbook (IR-01)** — Rehearse and archive evidence
- **MFA implementation** — TOTP (RFC 6238) on auth module is implemented; retain rollout evidence and endpoint coverage
- **Container image scanning** — Trivy/Grype in CI pipeline
- **Commission pen test NOW** — Don't wait until June; NCIA submission target is April 10

**Effort:** 1-2 weeks for rollout evidence and remaining security hardening; pen test is still an external dependency.

---

### GAP-11: No Intelligence Product Generation 🟡 MEDIUM

**Current state:** PDF report generation exists but limited to alert listings.

**Why it kills funding:** NATO analysts produce INTSUM (Intelligence Summaries), MPRAs (Maritime Patrol & Reconnaissance Area briefs), and SURFPIC (Surface Picture) products. A tool that doesn't generate recognizable intelligence products is harder to sell to operational users.

**What to build:**

- **Automated INTSUM generation** — Daily/weekly summary of anomalous vessel activity, top threats, trend analysis
- **Vessel dossier** — Complete profile (identity, track history, alert history, behavioral pattern, sanctions matches, risk score) exportable as briefing aid
- **Area situation report** — Geographic area summary (Baltic, Med, etc.) with threat heatmap data
- **TLP (Traffic Light Protocol) marking** — All products marked with sharing classification (TLP:WHITE through TLP:RED)
- **STIX/TAXII export** (future) — For threat intelligence sharing platforms

**Effort:** 3-4 weeks for INTSUM template + vessel dossier + TLP marking.

---

### GAP-12: No Multi-National Collaboration Features 🟡 MEDIUM

**Current state:** Org/tenant isolation exists but no cross-org sharing.

**Why it kills funding:** NATO is an ALLIANCE. The value proposition must include allied information sharing. Single-org tools are less compelling than platforms that enable multi-national collaboration.

**What to build:**

- **Alert sharing between orgs** — Share specific alerts/incidents with partner tenants (with TLP marking)
- **Shared watchlists** — Collaborate on vessels of interest across allied organisations
- **Federated deployment model** — Each nation runs sovereign instance; selective data sharing via API
- **Common operational picture (COP) feed** — Configurable feed of fused vessel data + alerts for shared displays
- **Need-to-know access controls** — Beyond RBAC: compartmented access based on nationality and clearance

**Effort:** 4-6 weeks for alert sharing + shared watchlists + TLP integration.

---

## Part 4 — Prioritized Roadmap for NATO Fundability

### Phase 1: "Make It Real" (Weeks 1-4) — CRITICAL PATH

| ID      | Feature                                                         | Depends On | Effort  | NATO Impact          |
| ------- | --------------------------------------------------------------- | ---------- | ------- | -------------------- |
| GAP-02  | Live AIS ingestion (aisstream.io + Spire)                       | —          | 2-3 wks | Unblocks everything  |
| GAP-03a | AIS identity spoofing detection (multi-MMSI, format violations) | GAP-02     | 2 wks   | DIANA differentiator |
| GAP-10a | Incident response runbook (IR-01)                               | —          | 1 wk    | NCIA blocker removal |
| GAP-10b | MFA implementation (TOTP)                                       | —          | 1 wk    | NCIA blocker removal |
| GAP-10c | Container image scanning (Trivy in CI)                          | —          | 2 days  | NCIA blocker removal |

### Phase 2: "Make It Smart" (Weeks 3-8) — DIANA DIFFERENTIATOR

| ID      | Feature                                                | Depends On             | Effort  | NATO Impact                      |
| ------- | ------------------------------------------------------ | ---------------------- | ------- | -------------------------------- |
| GAP-01a | Trajectory prediction model (LSTM/Transformer)         | GAP-02 (training data) | 4-6 wks | DIANA "deep tech" requirement    |
| GAP-01b | Ensemble scoring (rules + ML with SHAP explainability) | GAP-01a                | 2 wks   | DIANA "trustworthy AI" narrative |
| GAP-03b | GPS manipulation detection (ML classifier)             | GAP-02, GAP-01a        | 3 wks   | #1 naval priority                |
| GAP-05  | Dark vessel detection (expected transmission model)    | GAP-02                 | 3 wks   | Core MDA capability              |
| GAP-04a | Cursor-on-Target XML serializer                        | —                      | 2 wks   | NATO C2 integration              |
| GAP-04b | STANAG 5527/NFFI XML serializer                        | —                      | 2 wks   | NATO C2 integration              |

### Phase 3: "Make It NATO" (Weeks 5-12) — SUBMISSION READINESS

| ID      | Feature                                                    | Depends On       | Effort  | NATO Impact              |
| ------- | ---------------------------------------------------------- | ---------------- | ------- | ------------------------ |
| GAP-08  | Dynamic geofence expansion (UI + infrastructure DB)        | —                | 3 wks   | CIP coverage             |
| GAP-09a | Sanctions watchlist matching (OFAC/EU/UN)                  | GAP-02           | 3 wks   | Law enforcement use case |
| GAP-09b | Ship-to-ship transfer detection                            | GAP-02           | 2 wks   | Sanctions enforcement    |
| GAP-07  | Classified environment documentation + STANAG 4774 marking | —                | 2 wks   | Procurement readiness    |
| GAP-11  | INTSUM + vessel dossier + TLP marking                      | GAP-05, GAP-09   | 3 wks   | Operational user value   |
| GAP-12  | Allied sharing (cross-org alerts, shared watchlists)       | —                | 4 wks   | NATO alliance value prop |
| GAP-06  | Consortium LOIs signed                                     | — (relationship) | Ongoing | DIANA requirement        |

---

## Part 5 — Repositioned Product Narrative

### Current positioning (weak):

> "Automated data integrity and anomaly detection platform for AIS maritime data"

This says: **data quality tool**. NATO doesn't fund data quality tools.

### Recommended repositioning (strong):

> "AI-powered Maritime Domain Awareness platform for allied critical infrastructure protection, counter-spoofing, and sanctions enforcement — with sovereign deployment, NATO C2 interoperability, and explainable threat intelligence"

This says: **defense AI platform** solving NATO's top 3 maritime priorities.

### Reframed Feature Narrative for DIANA Challenge 3

| Feature Category     | Current Framing                        | NATO Framing                                                                                           |
| -------------------- | -------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Detection rules      | "AIS anomaly detection"                | "Explainable AI baseline for trustworthy maritime threat assessment"                                   |
| ITDAE module         | "Baltic cable monitoring"              | "Critical submarine infrastructure protection platform (CSIP)"                                         |
| Competitor import    | "MarineTraffic/VesselFinder migration" | "Multi-source intelligence fusion and data sovereignty"                                                |
| Evidence integrity   | "SHA-256 alert hashes"                 | "Forensic-grade evidence chain for intelligence products and legal proceedings"                        |
| Sovereign deployment | "EU/UK Kubernetes overlays"            | "Data residency and national sovereignty by design — deployable within allied nation's infrastructure" |
| Org isolation        | "Multi-tenant"                         | "Need-to-know information compartmentation for multi-national operations"                              |

---

## Part 6 — Competitor Landscape (NATO Maritime AI)

| Competitor                          | Strengths                                                     | Weakness You Can Exploit                                                   |
| ----------------------------------- | ------------------------------------------------------------- | -------------------------------------------------------------------------- |
| **Windward** (Israel)               | ML fleet analytics, sanctions screening, massive AIS database | Non-NATO nation origin; proprietary cloud-only; no sovereign deployment    |
| **MarineTraffic**                   | Largest AIS network, brand recognition                        | Data provider, not defense platform; no detection/alerting depth           |
| **Pole Star / LRIT**                | LRIT authority status, government relationships               | Legacy tech; slow innovation; expensive per-vessel licensing               |
| **Gatehouse Maritime** (Systematic) | NATO contracts, C2 integration, SitaWare integration          | Danish incumbent; expensive; slow to adopt AI/ML                           |
| **exactEarth** (Spire)              | S-AIS data; government contracts                              | Data provider, not analysis platform; acquired by Spire (commercial focus) |
| **Preligens/Safran** (France)       | Satellite imagery AI, French defence contracts                | Not maritime-specialist; image-focused, not AIS-focused                    |

### Your Asymmetric Advantages (if gaps are closed):

1. **Open architecture + sovereign deployment** — Competitors are cloud-SaaS locked. You deploy on-prem in classified environments. This is a structural advantage for NCIA procurement.

2. **Explainable AI** — Heuristic rules provide transparent baseline; ML adds capability but rules remain auditable. NATO procurement REQUIRES explainability for AI systems (NATO AI Strategy 2021).

3. **Critical infrastructure specialization** — Windward and MarineTraffic do fleet analytics. You do subsea cable protection. Post-Nord Stream, this is NATO's #1 maritime priority.

4. **Cost structure** — Open source core + sovereign deployment = 10x cheaper than Gatehouse SitaWare or Windward enterprise. For NATO innovation programmes, cost matters.

5. **Speed of deployment** — Docker Compose → production in hours, not months of professional services. DIANA evaluators value this.

---

## Part 7 — 90-Day Action Plan for NATO Submission Readiness

Use `docs/funding/NATO_SUBMISSION_CLOSEOUT_CHECKLIST.md` as the canonical execution sequence for the remaining external blockers. This gap analysis explains why those blockers matter; the close-out checklist defines the accountable order for finishing them.

### Weeks 1-4: Foundation

- [ ] Wire aisstream.io WebSocket → pipeline (GAP-02). Prove live Baltic AIS feed working.
- [ ] Implement MMSI spoofing detection — simultaneous MMSI broadcasts, format violations (GAP-03a)
- [x] Write IR runbook (GAP-10a), implement TOTP MFA (GAP-10b), add Trivy to CI (GAP-10c)
- [ ] Approach 3 integrator candidates (Kongsberg, Saab, Systematic) via TIDE community (GAP-06)
- [ ] Approach 1 academic partner (Plymouth, NTNU) for ML collaboration + TRL evidence (GAP-06)
- [ ] Commission pen test — do NOT wait until June (GAP-10)

### Weeks 5-8: AI & Interoperability

- [ ] Train trajectory prediction model on historical AIS data (openly available via MarineCadastre/Danish Maritime Authority) (GAP-01a)
- [ ] Implement ensemble scoring with SHAP explainability (GAP-01b)
- [ ] Build CoT XML serializer (GAP-04a) and validate with TAK Server
- [ ] Build STANAG 5527 serializer (GAP-04b) and validate against NFFI schema
- [ ] Implement dark vessel detection (GAP-05)
- [ ] Secure LOIs from at least 1 field operator (coast guard or naval unit) (GAP-06)

### Weeks 9-12: Submission

- [ ] Expand geofence database — full Euro-Atlantic cable network from TeleGeography (GAP-08)
- [ ] Archive operator evidence for UN-backed sanctions sync, flag-hopping review, and dark-port workflows (GAP-09a)
- [ ] Write classified environment deployment guide + STANAG 4774 marking (GAP-07)
- [ ] Generate INTSUM template + vessel dossier (GAP-11)
- [ ] Assemble DIANA Challenge 3 bid package:
  - Problem fit brief: "AI-Driven Critical Submarine Infrastructure Protection"
  - Technical whitepaper: Architecture + ML approach + explainability
  - Pilot plan: 30-day Baltic CIP demonstration with named coast guard partner
  - Team profile: Engineering + consortium partners
  - Security evidence pack: Complete
  - Interoperability profile: CoT + STANAG 5527 validated

---

## Part 8 — Feature Priority Matrix (Effort vs. NATO Impact)

```
                        HIGH NATO IMPACT
                              │
         GAP-03 Spoofing      │  GAP-02 Live Data ⭐
         GAP-01 ML/AI         │  GAP-04 STANAG/CoT
         GAP-05 Dark Vessels  │  GAP-06 Consortium
                              │
  HIGH ───────────────────────┼─────────────────────── LOW
  EFFORT                      │                       EFFORT
                              │
         GAP-12 Collaboration │  GAP-10 Security Fix
         GAP-09 Sanctions     │  GAP-07 Classified Docs
         GAP-08 CIP Expansion │  GAP-11 Intel Products
                              │
                        LOW NATO IMPACT
```

**Start bottom-right (quick wins), then top-right (high impact, low effort), then top-left (high effort, high impact).**

Priority order: GAP-02 → GAP-10 → GAP-03 → GAP-04 → GAP-06 → GAP-01 → GAP-05 → GAP-07 → GAP-08 → GAP-09 → GAP-11 → GAP-12

---

## Part 9 — What "NATO-Fundable" Actually Means

A NATO-fundable product must demonstrate ALL of:

| Criterion                                       | Current State                                                 | Required State                                                    |
| ----------------------------------------------- | ------------------------------------------------------------- | ----------------------------------------------------------------- |
| Solves an allied defense problem                | ⚠️ Solves AIS data quality; doesn't address spoofing/darkness | ✅ Addresses CIP, counter-spoofing, sanctions enforcement         |
| Uses emerging technology (AI/ML)                | 🔴 Rule-based only                                            | ✅ ML trajectory prediction + ensemble scoring + explainability   |
| Interoperates with NATO C2                      | 🔴 JSON only                                                  | ✅ STANAG 5527 + CoT + OTH-GOLD                                   |
| Deployable in sovereign/classified environments | ⚠️ Kubernetes overlays exist                                  | ✅ Air-gapped guide + classification marking + accreditation path |
| Consortium with operational user                | 🔴 All partners TBD                                           | ✅ Named integrator + coast guard/navy field operator             |
| Security evidence complete                      | ⚠️ Missing pen test and external assurance artefacts          | ✅ Full evidence pack with pen test report                        |
| Pilot evidence with KPIs                        | 🔴 All KPIs "TBD / Pending"                                   | ✅ 30-day pilot with measured outcomes                            |
| Commercially viable                             | 🔴 Zero users, zero revenue                                   | ✅ At least 1 paying pilot or LOI from government user            |

**Bottom line: 3 of 8 criteria are partially met. 0 of 8 are fully met. This is not yet NATO-fundable.**

---

## Appendix: Quick Reference — NATO Maritime Programmes to Target

| Programme                                      | Focus                            | Why AegisAIS Fits                    |
| ---------------------------------------------- | -------------------------------- | ------------------------------------ |
| **DIANA Challenge 3** (if maritime/CIP themed) | Emerging tech for allied defense | CIP + AI + sovereign deployment      |
| **NATO Digital Ocean**                         | Maritime surveillance innovation | Multi-sensor MDA platform            |
| **Project Portunus** (NATO CMRE)               | Subsea infrastructure protection | ITDAE module directly aligned        |
| **EDF (European Defence Fund)**                | EU defence capability gaps       | Maritime CIP + sanctions enforcement |
| **PESCO (Maritime Surveillance)**              | EU collaborative defence         | Multi-national MDA sharing           |
| **UK DASA** (Defence & Security Accelerator)   | UK-specific defence innovation   | Sovereign UK deployment profile      |
| **Norwegian FFI**                              | Arctic/Nordic maritime security  | Baltic + Arctic cable protection     |

**Recommendation:** Don't fixate on DIANA alone. The EDF and national programmes (UK DASA, Norwegian FFI) have lower barrier to entry and can provide the pilot evidence needed for later DIANA/NIF submissions.
