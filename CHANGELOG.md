# Changelog

All notable changes to AegisAIS are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

- `scripts/start_full_stack.sh` to start the core Docker processing stack with automatic host-port selection when common ports are already occupied
- `docs/RUNTIME_AND_TRAINING_IMPLEMENTATION_PLAN.md` documenting the runtime remediation and the remaining work needed for a real training pipeline
- `docs/NATO_FUNDABILITY_8_WEEK_EXECUTION_BOARD.md` with route-gated delivery milestones for DIANA/NIF/NCIA readiness
- `docs/NATO_SPOOFING_MODEL_DESIGN.md` freezing the D-03 spoofing and dark-vessel MVP design
- `docs/NATO_PARTNER_OUTREACH_TARGET_LIST.md` capturing the D-06 pilot, integrator, and compliance outreach list
- `docs/D-01_LIVE_INGEST_EVIDENCE_CAPTURE.md` — runbook for executing 72-hour monitored live AIS stream ingest with quantified evidence targets
- `scripts/capture_d01_evidence.sh` — background metric-collection script that logs ingest rate, processing latency, queue depth, and error events every 5 minutes
- `scripts/finalize_d01_evidence.sh` — end-of-run script that generates `D-01_INGEST_EVIDENCE_PACKAGE_FINAL.md` with submission-ready metrics, uptime calculation, and artifact manifest
- `docs/NATO_EXECUTION_BOARD_STATUS.md` — current implementation status, roadmap summary, and next-action checklist for all Week 1-2 deliverables
- `docs/D-04_COT_STANAG_RECEIVER_CONFORMANCE.md` — runbook for D-04 CoT/STANAG receiver validation (schema conformance, sample payloads, TAK Server integration)
- `docs/D-02_SAIS_PROVIDER_INTEGRATION.md` — D-02 provider selection guide and integration template for Spire Global or alternative S-AIS providers
- `docs/D-07_LIVE_STREAM_HARDENING.md` — D-07 hardening framework for Weeks 3-4: circuit breaker pattern, exponential backoff, backpressure handling, SLO monitoring
- `docs/NATO_BOARD_IMPLEMENTATION_SUMMARY.md` — Current implementation status, file inventory, action items, and submission readiness assessment
- `apps/api/scripts/generate_d04_interop_samples.py` — generates sample CoT and STANAG XML payloads for receiver testing
- `apps/api/tests/test_interoperability_conformance.py` — automated conformance test suite validating CoT and STANAG XML generators
- `scripts/finalize_d04_evidence.sh` — D-04 evidence packaging script; generates conformance summary and receiver integration status
- `CONTRIBUTING.md` and `MIT LICENSE` for open-source best practices
- SBOM generation (`anchore/sbom-action`) for backend and frontend on every CI run
- Sigstore build-provenance attestation for SBOM artifacts and all three Docker images (API, BFF, Web)
- `docs/governance/AUDIT_COVERAGE_MATRIX.md` — machine-checkable audit event matrix, enforced in CI
- `scripts/check_audit_coverage.py` — CI gate that fails when audit-sensitive files change without audit evidence updates
- `scripts/check_contract_samples.py` — CI gate validating Alert/Incident/Track sample payloads against JSON schemas
- `apps/api/app/modules/integrations/contracts_validator.py` — lightweight stdlib-only JSON Schema validator
- `apps/api/app/modules/integrations/migration_validator.py` — `PortSeedRow` batch import validator with structured `MigrationValidationReport`
- `apps/api/app/services/pilot_metrics.py` — pilot KPI calculation scaffold (detection lead-time, false alert rate, analyst time saved)
- `apps/api/app/api/v1/pilot.py` — `GET /v1/pilot/kpi-summary` endpoint backed by live alert data
- Interoperability conformance test harness (`test_interoperability.py`) covering INT-001 and INT-002
- Sovereign Kubernetes deployment profiles for EU (`infra/k8s/profiles/sovereign-eu`) and UK (`infra/k8s/profiles/sovereign-uk`)
- `securityContext` hardening on all Kubernetes pod specs: `runAsNonRoot`, `allowPrivilegeEscalation: false`, `capabilities.drop: ALL`, `seccompProfile: RuntimeDefault`
- `cryptography>=46.0.6` and `ecdsa>=0.19.2` explicit pins to close CVE-2026-34073 and CVE-2026-33936

### Changed

- Docker Compose nginx, Prometheus, and Grafana host ports are now configurable via environment variables
- Local full-stack startup now auto-generates self-signed nginx development certificates when `infra/docker/nginx/certs` is empty
- Backend runtime lockfiles now pin `greenlet` explicitly so Docker `--require-hashes` installs succeed on supported Linux architectures
- `httpx` moved into backend runtime dependencies and the Docker web command now targets `apps/web` directly so the API worker path and Vite container start correctly
- Backend runtime now declares `websockets` explicitly so live aisstream ingestion can run outside stub mode
- Docker local services now receive a valid development `SECRET_KEY`, and the processing worker tolerates missing optional numeric AIS fields during replay
- The incidents Alembic migration now branches from the organisation-aware revision so fresh PostgreSQL bootstraps no longer fail on a missing `organisations` table
- CI frontend vulnerability gate raised from `--audit-level=critical` to `--audit-level=high`
- API `PodDisruptionBudget` raised from `minAvailable: 1` to `minAvailable: 2` to prevent single-pod SPOF under node drain
- BL-009 (evidence integrity) scheduled to Week 9, unblocking INT-003, BL-011, BL-012
- Sovereign profile READMEs now include `kubectl diff` step before apply
- `CHANGELOG.md` to track releases
- BFF (`apps/bff`) geospatial API gateway: JWT-authenticated layer manifest, license-gated WebSocket stream, object storage status endpoint
- Codecov integration for test coverage reporting
- Web workspace dev dependencies aligned on patched `vite` 7.3.2 to clear the Vite security advisory without duplicate-install type conflicts

### Fixed

- Cleared current React hook dependency warnings across the web app by stabilizing async loaders with `useCallback`
- File upload drop-zone handlers now correctly support async `onFileDrop` implementations
- Replaced the vulnerable contracts type generator dependency with a Node 20 compatible `json-schema-to-ts` based generator

### Changed

- `SECRET_KEY` default removed from source — empty string forces explicit env-var configuration; validator rejects weak keys in all non-development environments
- All internal `TODO` comments replaced with tracked GitHub issue links ([#2](https://github.com/giselleevita/aegisais/issues/2), [#3](https://github.com/giselleevita/aegisais/issues/3))
- README BFF architecture section updated to reflect real implemented routes and design properties

### Removed

- 14 internal working documents (implementation plans, audit reports, risk registers, conflict matrices, validation reports, wireframes, vision docs) not suitable for a public repository

---

## [0.5.0] — 2026-03-21

### Added

- **Globe / 3D workbench** — auto camera toggle and camera telemetry (`feat(globe)`)
- **AML UI/UX hardening** — operational demo-ready anti-money-laundering analyst workbench
- **Incidents detail flow** — full incident lifecycle with activity timeline
- **AML audit workbench** — expanded audit filtering and structured audit trail
- **Modular GEOINT vertical slice** — 3D workbench with multi-layer geospatial intelligence overlay
- **BFF service** (`apps/bff`) — Fastify gateway with OpenAPI contract, JWT middleware, rate limiter, in-memory cache, and license-gating

### Changed

- Turborepo monorepo restructure — `apps/api`, `apps/bff`, `apps/web` workspace layout
- Docker Compose host ports made configurable via environment variables

### Fixed

- Restored default e2e port compatibility after Playwright environment drift
- Stabilised lockfile and e2e checks across macOS and Linux CI environments
- Cleared mypy backlog; restored strict CI type gate
- Cleared ruff lint violations blocking CI matrix
- Scoped lockfile check to py311; unblocked known audit CVE
- Included Linux `greenlet` hash pins in runtime lockfile

---

## [0.4.0] — 2026-02-14

### Added

- **Enterprise hardening** — Sprint 2–4 features: multi-tenancy stub, satellite AIS (S-AIS) provider config, OpenSky integration, structured audit logging
- **Prometheus & Grafana** observability stack in Docker Compose
- **Redis-backed rate limiting** — sliding-window per-identity limiter shared across workers
- **Security headers middleware** — HSTS, X-Frame-Options, CSP
- **Password reset via SMTP** — configurable email delivery with fallback dev logging
- **WebSocket authentication** — JWT token required for `/v1/stream` in all non-development environments
- **Production config validation** — hard startup failure for weak `SECRET_KEY`, SQLite in production, and disabled WebSocket auth
- **Alembic migration history** — full schema versioning from initial schema

### Changed

- CI matrix expanded to Python 3.11 and 3.12
- `pip-audit` security check added to CI pipeline
- Playwright E2E smoke-check optimised for CI speed

---

## [0.3.0] — 2025-12-01

### Added

- **ITDAE module** — Infrastructure Threat Detection and Analysis Engine with Baltic Sea cable geofence monitoring
- **Detection rule engine** — 7 rules: `TELEPORT`, `TURN_RATE`, `ACCELERATION`, `POSITION_INVALID`, `HEADING_COG_INCONSISTENT`, `SIGNAL_LOSS`, `CABLE_PROXIMITY`
- **Tiered alert severity** — Tier 1 (integrity violation) and Tier 2 (suspicious behaviour), 0–100 scoring
- **Track history replay** — configurable speed multiplier, start/stop control via REST
- **Alert management API** — status updates, analyst notes, CSV/JSON export
- **Interactive Leaflet map** — vessel positions, alert markers, track overlays

### Changed

- FastAPI app restructured into domain modules (`vessels`, `alerts`, `incidents`, `audit`, `fusion`, `itdae`)

---

## [0.2.0] — 2025-10-15

### Added

- **Batch AIS ingestion** — `.csv`, `.dat`, `.csv.zst`, `.dat.zst` upload pipeline with streaming decompression
- **Upload security** — filename sanitisation, path-traversal prevention, decompressed-size bounds, header validation
- **Background workers** — alert worker, processing worker, persistence worker with Redis Streams coordination
- **Demo datasets** — pre-built AIS files covering all 7 detection rule types
- **Onboarding tour** — interactive guided walkthrough for first-time users

---

## [0.1.0] — 2025-09-01

### Added

- Initial AIS ingestion pipeline (CSV/DAT parsing, MMSI validation, track store)
- FastAPI REST API with Swagger UI and ReDoc
- React + Vite frontend with feature-based directory structure
- SQLite development database with SQLAlchemy ORM
- GitHub Actions CI with lint, type-check, and test stages
- Docker Compose for local full-stack development

[Unreleased]: https://github.com/giselleevita/aegisais/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/giselleevita/aegisais/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/giselleevita/aegisais/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/giselleevita/aegisais/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/giselleevita/aegisais/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/giselleevita/aegisais/releases/tag/v0.1.0
