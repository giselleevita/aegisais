# Interoperability Profile

**Version:** 1.0 | **Date:** 2026-03-31 | **Status:** Active

This document operationalizes BL-015 and provides the defense-procurement-friendly interoperability profile for AegisAIS, covering supported integration capabilities, standards conformance, known gaps, and evidence pointers.

---

## 1 Scope

This profile covers:

- Maritime AIS data ingestion and anomaly detection
- API-level integration for import, export, alerting, and incident reporting
- Schema-level interoperability using versioned JSON contracts (`packages/contracts/schemas/`)
- C2/command system integration readiness
- Migration adapter coverage for named competitor platforms

---

## 2 Standards and Specifications Mapping

| Standard / Specification | Description                     | AegisAIS Coverage                                    | Gap / Notes                                                   |
| ------------------------ | ------------------------------- | ---------------------------------------------------- | ------------------------------------------------------------- |
| ITU-R M.1371-5           | AIS Class A/B message format    | ✅ MMSI, position, heading, COG, SOG fields ingested | AIS binary payload not directly decoded; CSV/API adapter used |
| NMEA 0183 v4.10          | NMEA sentence format (VDM/VDO)  | ✅ Generic NMEA CSV adapter (BL-011)                 | Streaming NMEA via TCP not yet supported                      |
| S-57 / S-111 / S-124     | IHO S-100 data model family     | ⚠️ Track and entity models aligned conceptually      | Formal S-100 schema compliance not yet certified              |
| STANAG 5527 / NFFI       | NATO Friendly Force Information | ⚠️ Entity and Track schemas aligned to intent        | No NFFI XML serialiser; JSON contract available               |
| STANAG 4586              | UAV Ground Control interop      | ❌ Not in scope for current release                  | Sensor feed adapter planned for future increment              |
| APP-6D                   | NATO Military Symbology         | ❌ Not in scope for current release                  | UI symbology extension planned                                |
| Cursor on Target (CoT)   | CoT event schema (MITRE/TAK)    | ⚠️ Event schema aligns conceptually                  | No native CoT XML output; JSON mapping available              |
| JSON Schema 2020-12      | Schema validation standard      | ✅ All contract schemas use 2020-12                  | Validated in CI via `check_contract_samples.py`               |
| ISO 8601                 | Date/time encoding              | ✅ All timestamps in UTC ISO 8601                    |                                                               |
| RFC 4122                 | UUID format                     | ✅ All record IDs use UUID v4                        |                                                               |
| RFC 4180                 | CSV format for exports          | ✅ Alert and incident CSV export                     | Header row required; UTF-8 encoding                           |

---

## 3 Capability Matrix

| Capability                                       | Delivery Status                 | Interface                                            | Schema                               | Notes                                                   |
| ------------------------------------------------ | ------------------------------- | ---------------------------------------------------- | ------------------------------------ | ------------------------------------------------------- |
| Historical dataset import — MarineTraffic format | ✅ Implemented (BL-011)         | `POST /v1/import/competitor?format=marine_traffic`   | `ImportBundle.schema.json`           | Row-level validation report included                    |
| Historical dataset import — VesselFinder format  | ✅ Implemented (BL-011)         | `POST /v1/import/competitor?format=vessel_finder`    | `ImportBundle.schema.json`           |                                                         |
| Historical dataset import — FleetMon format      | ✅ Implemented (BL-011)         | `POST /v1/import/competitor?format=fleet_mon`        | `ImportBundle.schema.json`           |                                                         |
| Historical dataset import — Generic NMEA CSV     | ✅ Implemented (BL-011)         | `POST /v1/import/competitor?format=generic_nmea`     | `ImportBundle.schema.json`           | Field name variants normalised                          |
| Alert export (JSON)                              | ✅ Available                    | `GET /v1/alerts/{id}` / `GET /v1/alerts/export/json` | `Alert.schema.json`                  | Includes `evidence_hash` and `idempotency_key`          |
| Alert export (CSV)                               | ✅ Available                    | `GET /v1/alerts/export/csv`                          | RFC 4180                             | All alert fields including `evidence_hash`              |
| Track export                                     | ✅ Available                    | `GET /v1/tracks/{id}`                                | `Track.schema.json`                  |                                                         |
| Incident export                                  | ✅ Available                    | `GET /v1/incidents/export/csv`                       | RFC 4180                             |                                                         |
| Evidence reconstruction                          | ✅ Implemented (BL-009)         | `GET /v1/alerts/{id}`                                | `Alert.schema.json` (extended)       | SHA-256 of slim evidence payload; deterministic replay  |
| Alert idempotency / dedup                        | ✅ Implemented (BL-003)         | Alert writer / worker                                | Internal                             | Replay-safe; savepoint + IntegrityError recovery        |
| Tenant isolation                                 | ✅ Implemented (BL-001, BL-002) | All vessel/alert/incident routes                     | `_common.json#/$defs/AccessMetadata` | Org-scoped queries; role-based access enforced          |
| License-aware route control                      | ✅ Implemented (BL-008)         | BFF middleware                                       | N/A                                  | `KNOWN_FEATURES` allowlist; Redis-backed rate limiting  |
| Usage metering                                   | ✅ Implemented (BL-010)         | Internal ledger                                      | `UsageLedgerEntry` model             | Event types: alert.processed, export.csv, vessel.active |
| Native AIS stream ingestion                      | ✅ Available                    | OpenSky + internal ingestion                         | AIS feed adapter                     | Real-time; duplicate guard via quota manager            |
| CoT XML export                                   | ❌ Not available                | N/A                                                  | —                                    | Planned; JSON mapping available as workaround           |
| STANAG 5527 / NFFI XML                           | ❌ Not available                | N/A                                                  | —                                    | JSON equivalent available via Track + Event schemas     |
| Link 16 / JREAP-C                                | ❌ Not in scope                 | N/A                                                  | —                                    | Out of scope for this programme increment               |
| S-100 formal certification                       | ❌ Not available                | N/A                                                  | —                                    | Schema alignment complete; certification not started    |

---

## 4 Schema Version History

| Schema                     | Current Version | Breaking Changes                                                 | Backward Compatibility                              |
| -------------------------- | --------------- | ---------------------------------------------------------------- | --------------------------------------------------- |
| `Alert.schema.json`        | 1.2             | Added `evidence_hash`, `idempotency_key` fields (BL-009, BL-003) | Fields are additive; nullable; consumers can ignore |
| `Track.schema.json`        | 1.0             | None                                                             | Stable                                              |
| `Event.schema.json`        | 1.0             | None                                                             | Stable                                              |
| `Entity.schema.json`       | 1.0             | None                                                             | Stable                                              |
| `Incident.schema.json`     | 1.0             | None                                                             | Stable                                              |
| `ImportBundle.schema.json` | 1.0.0           | New schema (BL-015)                                              | N/A (new)                                           |
| `_common.json`             | 1.1             | `AccessMetadata.ownerOrgId` added                                | Additive; optional                                  |

All schemas use JSON Schema 2020-12. Schema `$id` URIs are stable and used as canonical references.

---

## 5 Conformance Test Plan

| Test ID | Scenario                                                    | Expected Result                                                   | Coverage                      | Owner          |
| ------- | ----------------------------------------------------------- | ----------------------------------------------------------------- | ----------------------------- | -------------- |
| INT-001 | Import sample MarineTraffic track CSV (500 rows)            | Records ingest; validation report generated; confidence ≥ 0.90    | `test_competitor_import.py`   | Integrations   |
| INT-002 | Import sample VesselFinder, FleetMon, generic NMEA CSVs     | Each format normalised to `CanonicalTrackPoint`; no schema errors | `test_competitor_import.py`   | Integrations   |
| INT-003 | Reconstruct alert rationale from stored evidence            | `evidence_hash` matches SHA-256 of `slim_evidence` payload        | `test_alert_evidence_hash.py` | Detection Team |
| INT-004 | Export alerts as JSON; validate against `Alert.schema.json` | All required fields present; `additionalProperties: false` passes | `check_contract_samples.py`   | API Platform   |
| INT-005 | Replay identical worker payload twice                       | Single alert record created; duplicate rejected                   | `test_alert_idempotency.py`   | Detection Team |
| INT-006 | Tenant isolation: org A cannot read org B vessel records    | Zero rows returned across list/detail/track endpoints             | `test_org_scope.py`           | Security       |
| INT-007 | Rate limiter stable across two BFF replica requests         | Limit enforced; count accumulated in Redis                        | Manual / integration          | BFF Team       |

### Demo Conformance Script

```bash
# From repo root, with venv activated:
cd apps/api

# INT-001 to INT-005: automated test groups
python -m pytest tests/test_competitor_import.py tests/test_alert_evidence_hash.py \
  tests/test_alert_idempotency.py tests/test_org_scope.py -v

# INT-004: contract samples validation
python ../../scripts/check_contract_samples.py
```

Expected result: **all tests pass, contract samples validated**.

---

## 6 Known Gaps and Migration Workarounds

| Gap                         | Impact                                     | Workaround                                               | Roadmap                          |
| --------------------------- | ------------------------------------------ | -------------------------------------------------------- | -------------------------------- |
| No CoT XML serialiser       | Medium — TAK/ATAK integration blocked      | Use JSON Alert export + custom CoT adapter at receiver   | Planned                          |
| No STANAG 5527 / NFFI XML   | Medium — NATO C2 XML integration blocked   | Use Track/Event JSON schemas with agreed field mapping   | Pending demand signal            |
| No streaming NMEA TCP input | Low — batch import only                    | Export to CSV from NMEA source; use generic_nmea adapter | Planned                          |
| S-100 formal certification  | Medium — some procurement forms require it | Self-assessment alignment doc available on request       | To be initiated after pilot      |
| Link 16 / JREAP-C           | High for some use cases                    | Out of scope; third-party gateway required               | Not planned in current increment |

---

## 7 Evidence Pointers

| Artefact                      | Location                                                               |
| ----------------------------- | ---------------------------------------------------------------------- |
| API contracts                 | `docs/API_DOCUMENTATION.md`                                            |
| JSON schemas                  | `packages/contracts/schemas/`                                          |
| Import bundle schema          | `packages/contracts/schemas/ImportBundle.schema.json`                  |
| Contract sample validation    | `scripts/check_contract_samples.py`                                    |
| Competitor import tests       | `apps/api/tests/test_competitor_import.py`                             |
| Evidence hash tests           | `apps/api/tests/test_alert_evidence_hash.py`                           |
| Idempotency tests             | `apps/api/tests/test_alert_idempotency.py`                             |
| Org-scope isolation tests     | `apps/api/tests/test_org_scope.py`                                     |
| Sovereign deployment profiles | `infra/k8s/profiles/sovereign-eu/`, `infra/k8s/profiles/sovereign-uk/` |
| Migration guide               | `apps/api/MIGRATION_GUIDE.md`                                          |
| Competitor import adapter     | `apps/api/app/modules/integrations/adapters_competitor.py`             |
