# Untracked Files Inventory

This document classifies all untracked files resulting from the recent repository canonicalization and new feature development, with explicit keep/delete disposition and rationale.

**Status**: Baseline inventory captured on 2026-04-10. Use this document to make informed decisions about which files to commit or exclude.

---

## Summary

| Category                | Count | Disposition | Action         |
| ----------------------- | ----- | ----------- | -------------- |
| **New Feature Modules** | 5     | ✅ KEEP     | Commit to repo |
| **New Migrations**      | 3     | ✅ KEEP     | Commit to repo |
| **New Tests**           | 5     | ✅ KEEP     | Commit to repo |
| **Canonical Docs**      | 8     | ✅ KEEP     | Commit to repo |
| **Operational Scripts** | 7     | ✅ KEEP     | Commit to repo |
| **Contract Schemas**    | 9     | ✅ KEEP     | Commit to repo |
| **Frontend Features**   | 2     | ✅ KEEP     | Commit to repo |
| **GitHub Config**       | 1     | ⚠️ REVIEW   | Verify intent  |
| **Total**               | 40    | —           | —              |

---

## Detailed Classification

### 1. New Feature Modules (KEEP) — Core Business Logic

These are active development branches for new capabilities integrated into the main platform.

| File                                   | Type    | Purpose                                          | Keep  | Rationale                                            |
| -------------------------------------- | ------- | ------------------------------------------------ | ----- | ---------------------------------------------------- |
| `apps/api/app/modules/assets/`         | Module  | Subsea assets tracking and management            | ✅    | New domain module for maritime infrastructure assets |
| `apps/api/app/modules/iot/`            | Module  | IoT sensor data ingestion and processing         | ✅    | New domain module for edge IoT network integration   |
| `apps/api/app/infrastructure/iot/`     | Module  | IoT transport layer and stream handlers          | ✅    | Infrastructure support for IoT connectivity layer    |
| `apps/api/app/detection/iot_fusion.py` | Service | Multi-source data fusion for IoT-AIS correlation | ✅    | Core detection logic extending anomaly rule set      |
| **Subtotal**                           | —       | —                                                | **4** | —                                                    |

---

### 2. Database Migrations (KEEP) — Data Model Evolution

Alembic migration files for new features and schema changes.

| File                                                           | Type      | Purpose                                   | Keep  | Rationale                                      |
| -------------------------------------------------------------- | --------- | ----------------------------------------- | ----- | ---------------------------------------------- |
| `apps/api/alembic/versions/014_add_user_mfa_columns.py`        | Migration | Multi-factor authentication schema        | ✅    | Extends auth module with MFA support           |
| `apps/api/alembic/versions/015_subsea_assets_and_iot_core.py`  | Migration | Assets and IoT core tables                | ✅    | Schema for new assets and iot modules          |
| `apps/api/alembic/versions/016_iot_telemetry_and_edge_sync.py` | Migration | Telemetry and edge synchronization tables | ✅    | Schema for platform expansion (edge computing) |
| **Subtotal**                                                   | —         | —                                         | **3** | —                                              |

---

### 3. Test Suite (KEEP) — Quality Assurance

New unit and integration tests validating feature coverage and NATO compliance requirements.

| File                                                  | Type | Purpose                                            | Keep  | Rationale                                                |
| ----------------------------------------------------- | ---- | -------------------------------------------------- | ----- | -------------------------------------------------------- |
| `apps/api/tests/test_assets_iot_api.py`               | Test | API endpoints for assets and IoT modules           | ✅    | Unit tests for new REST routes                           |
| `apps/api/tests/test_iot_audit.py`                    | Test | Audit trail and compliance logging for IoT paths   | ✅    | NATO D-07 compliance: audit trail for all IoT operations |
| `apps/api/tests/test_auth_mfa.py`                     | Test | MFA authentication flows                           | ✅    | Security: validates MFA implementation                   |
| `apps/api/tests/test_sanctions_api.py`                | Test | Sanctions screening integration                    | ✅    | Compliance: OFAC/sanctions list matching                 |
| `apps/api/tests/test_interoperability_conformance.py` | Test | NATO STANAG compliance (SAIS provider conformance) | ✅    | NATO D-04: validates provider contract conformance       |
| **Subtotal**                                          | —    | —                                                  | **5** | —                                                        |

---

### 4. Canonical Documentation (KEEP) — Source of Truth

Domain-scoped documentation files from the recent reorganization (replacing legacy root-level stubs).

| File                                              | Type     | Purpose                                    | Keep   | Rationale                                                        |
| ------------------------------------------------- | -------- | ------------------------------------------ | ------ | ---------------------------------------------------------------- |
| `docs/README.md`                                  | Index    | Documentation navigation guide             | ✅     | Entrypoint for all docs; just created during canonicalization    |
| `docs/architecture/ARCHITECTURE.md`               | Ref      | System architecture and component overview | ✅     | Canonical source; replaces legacy root stub                      |
| `docs/architecture/CONSORTIUM_EXECUTION_MODEL.md` | Ref      | NATO consortium deployment model           | ✅     | Canonical source; replaces legacy root stub                      |
| `docs/architecture/INFRA_BASELINE_KUBERNETES.md`  | Ref      | Kubernetes infrastructure topology         | ✅     | Canonical source; replaces legacy root stub                      |
| `docs/architecture/PROJECT_STRUCTURE.md`          | Ref      | Monorepo layout and module organization    | ✅     | Canonical source; replaces legacy root stub (already modernized) |
| `docs/architecture/SCALE_AND_INFRA.md`            | Ref      | Scaling strategy and infrastructure sizing | ✅     | Canonical source; replaces legacy root stub                      |
| `docs/architecture/SYSTEM_OVERVIEW.md`            | Ref      | High-level system overview                 | ✅     | Canonical source; replaces legacy root stub                      |
| `docs/security/SECURITY.md`                       | Policy   | Security scope, threat model, compliance   | ✅     | Canonical source; replaces legacy root stub                      |
| `docs/security/SECURITY_EVIDENCE_PACK.md`         | Evidence | Compliance artifacts and attestations      | ✅     | Canonical source; replaces legacy root stub                      |
| `docs/security/SUPPLY_CHAIN_ASSURANCE.md`         | Policy   | Supply chain security controls             | ✅     | Canonical source; replaces legacy root stub                      |
| **Subtotal**                                      | —        | —                                          | **10** | —                                                                |

---

### 5. Operational Scripts (KEEP) — Runtime & CI/CD

Helper scripts for demo capture, evidence finalization, and full-stack orchestration.

| File                                                  | Type          | Purpose                                             | Keep   | Rationale                                                 |
| ----------------------------------------------------- | ------------- | --------------------------------------------------- | ------ | --------------------------------------------------------- |
| `scripts/start_full_stack.sh`                         | Orchestration | Starts all Docker services with auto-port detection | ✅     | Root entry point for one-command deployment               |
| `scripts/setup_d01_ingest.sh`                         | Setup         | Configures D-01 ingest pipeline for demo            | ✅     | Operational: used by demo and NATO evidence capture       |
| `scripts/capture_d01_evidence.sh`                     | Evidence      | Captures evidence for D-01 (live ingest) work item  | ✅     | NATO: required for fundability evidence trail             |
| `scripts/finalize_d01_evidence.sh`                    | Evidence      | Finalizes and packages D-01 evidence artifacts      | ✅     | NATO: evidence packaging (repeatable audit trail)         |
| `scripts/finalize_d04_evidence.sh`                    | Evidence      | Finalizes D-04 (STANAG conformance) evidence        | ✅     | NATO: STANAG compliance evidence collection               |
| `scripts/finalize_airgap_evidence.sh`                 | Evidence      | Finalizes evidence for air-gap deployment scenario  | ✅     | NATO: edge deployment evidence (D-07)                     |
| `scripts/operations/`                                 | Directory     | Implementations for root script wrappers            | ✅     | Core scripts with corrected repo-root paths (`../../../`) |
| `apps/api/scripts/generate_d04_interop_samples.py`    | Utility       | Generates SAIS provider conformance samples         | ✅     | NATO: generates sample data for interop validation        |
| `apps/api/scripts/generate_d04_receiver_rehearsal.py` | Utility       | Generates D-04 receiver rehearsal scenarios         | ✅     | NATO: rehearsal data for provider testing                 |
| `apps/api/scripts/smoke_llm.py`                       | Utility       | LLM-based smoke tests for behavioral validation     | ✅     | QA: validates system behavior via LLM assertions          |
| **Subtotal**                                          | —             | —                                                   | **10** | —                                                         |

---

### 6. Contract Schemas (KEEP) — Type-Safe Integrations

TypeScript schema definitions and bindings for contract-first API design.

| File                                                       | Type      | Purpose                                      | Keep  | Rationale                                                |
| ---------------------------------------------------------- | --------- | -------------------------------------------- | ----- | -------------------------------------------------------- |
| `packages/contracts/schemas/Asset.schema.json`             | Schema    | JSON Schema for Asset domain model           | ✅    | Contract definition: enables IDE autocomplete in clients |
| `packages/contracts/schemas/Device.schema.json`            | Schema    | JSON Schema for IoT Device model             | ✅    | Contract definition: device registration schema          |
| `packages/contracts/schemas/DeviceHeartbeat.schema.json`   | Schema    | JSON Schema for device keep-alive signals    | ✅    | Contract definition: health check schema                 |
| `packages/contracts/schemas/SensorNode.schema.json`        | Schema    | JSON Schema for edge sensor network nodes    | ✅    | Contract definition: edge network topology               |
| `packages/contracts/schemas/SensorReading.schema.json`     | Schema    | JSON Schema for raw sensor measurements      | ✅    | Contract definition: telemetry payload                   |
| `packages/contracts/schemas/TelemetryEnvelope.schema.json` | Schema    | JSON Schema for aggregated telemetry batches | ✅    | Contract definition: batch transport format              |
| `packages/contracts/src/`                                  | Directory | TypeScript bindings generated from schemas   | ✅    | Type definitions: auto-generated, used by BFF and tests  |
| **Subtotal**                                               | —         | —                                            | **7** | —                                                        |

---

### 7. Frontend Features (KEEP) — UI Extensions

New React/TypeScript components for globe visualization.

| File                                                  | Type      | Purpose                                            | Keep  | Rationale                                         |
| ----------------------------------------------------- | --------- | -------------------------------------------------- | ----- | ------------------------------------------------- |
| `apps/web/src/aml/pages/GlobeViewerRuntime.tsx`       | Component | 3D globe viewer for geospatial asset visualization | ✅    | UI: interactive globe for maritime infrastructure |
| `apps/web/src/features/globe/globeWorkbenchConfig.ts` | Config    | Globe workbench tool configuration and layout      | ✅    | Config: globe viewer settings and layer stack     |
| **Subtotal**                                          | —         | —                                                  | **2** | —                                                 |

---

### 8. Domain Directories (KEEP) — Canonical Doc Folders

New canonical documentation domain folders that replace legacy root-level stubs.

| File               | Type      | Purpose                                   | Keep  | Rationale                                    |
| ------------------ | --------- | ----------------------------------------- | ----- | -------------------------------------------- |
| `docs/funding/`    | Directory | Funding, business case, and evidence docs | ✅    | Canonical domain: replaces legacy root stubs |
| `docs/governance/` | Directory | Backlog, audit matrices, issue packs      | ✅    | Canonical domain: replaces legacy root stubs |
| `docs/operations/` | Directory | Operational guides, migrations, demos     | ✅    | Canonical domain: replaces legacy root stubs |
| `docs/product/`    | Directory | API spec, features, standards alignment   | ✅    | Canonical domain: replaces legacy root stubs |
| `docs/security/`   | Directory | Security policies, compliance, evidence   | ✅    | Canonical domain: replaces legacy root stubs |
| `apps/api/docs/`   | Directory | API implementation documentation          | ✅    | Dev docs: used during API development        |
| **Subtotal**       | —         | —                                         | **6** | —                                            |

---

### 9. GitHub Configuration (REVIEW) — Automation

GitHub-specific configuration files that may or may not be committed based on team policy.

| File                     | Type   | Purpose                                   | Keep?     | Rationale                                                                                                                                                                                   |
| ------------------------ | ------ | ----------------------------------------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `.github/dependabot.yml` | Config | Automated dependency update configuration | ⚠️ REVIEW | **Action**: Decide based on team policy. If dependency automation is desired, commit it. If not, add `.github/` to `.gitignore`. Suggested: KEEP if automated security updates are desired. |
| **Subtotal**             | —      | —                                         | **1**     | —                                                                                                                                                                                           |

---

## Recommendation Summary

### ✅ Immediate Commit (40 files & directories)

All files classified as KEEP should be committed to the repository:

```bash
# Stage all KEEP category files
git add apps/api/app/modules/ \
        apps/api/app/infrastructure/iot/ \
        apps/api/app/detection/iot_fusion.py \
        apps/api/alembic/versions/01{4,5,6}_*.py \
        apps/api/tests/test_{assets_iot,iot_audit,auth_mfa,sanctions,interoperability}_*.py \
        apps/api/scripts/ \
        apps/api/docs/ \
        apps/web/src/aml/ \
        apps/web/src/features/globe/ \
        packages/contracts/schemas/ \
        packages/contracts/src/ \
        scripts/ \
        docs/

# Review and commit
git commit -m "chore: add new feature modules (assets, iot), tests, migrations, scripts, and canonical docs

- Add subsea assets and IoT sensor modules (apps/api/app/modules/)
- Add IoT infrastructure and fusion detection logic
- Add 3 new migrations (MFA, assets, telemetry)
- Add 5 new test suites (assets, IoT, auth, sanctions, conformance)
- Add 10 operational & evidence capture scripts
- Add TypeScript contract schemas for type-safe integrations
- Add globe viewer UI components for geospatial visualization
- Reorganize docs into canonical domain folders (architecture, operations, product, security, governance, funding)
- Update PROJECT_STRUCTURE.md with apps/api, apps/web, apps/bff layout
"
```

### ⚠️ Conditional Commit (1 file)

`.github/dependabot.yml` — Decide on team policy:

- **KEEP**: If automated security updates are desired in CI/CD
- **DELETE**: If manual dependency updates are preferred; add `.github/` to `.gitignore`

### Verification After Commit

Once committed, validate the commit:

```bash
# Check commit contents
git show --name-status

# Run test suite to ensure no regressions
npm run test
.venv/bin/python -m pytest apps/api/tests/

# Verify documentation build
docs/README.md references all domain folders
```

---

## References

- **Original canonicalization**: Converted root-level doc stubs to domain-scoped folders
- **Recent development**: Added IoT, assets, MFA, and telemetry features
- **NATO compliance**: Operational scripts capture evidence for D-01, D-04, D-07 work items
- **Type safety**: Contract schemas enable IDE autocomplete across monorepo
