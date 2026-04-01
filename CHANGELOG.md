# Changelog

All notable changes to AegisAIS are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- `CONTRIBUTING.md` and `MIT LICENSE` for open-source best practices
- SBOM generation (`anchore/sbom-action`) for backend and frontend on every CI run
- Sigstore build-provenance attestation for SBOM artifacts and all three Docker images (API, BFF, Web)
- `docs/AUDIT_COVERAGE_MATRIX.md` — machine-checkable audit event matrix, enforced in CI
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
- CI frontend vulnerability gate raised from `--audit-level=critical` to `--audit-level=high`
- API `PodDisruptionBudget` raised from `minAvailable: 1` to `minAvailable: 2` to prevent single-pod SPOF under node drain
- BL-009 (evidence integrity) scheduled to Week 9, unblocking INT-003, BL-011, BL-012
- Sovereign profile READMEs now include `kubectl diff` step before apply
- `CHANGELOG.md` to track releases
- BFF (`apps/bff`) geospatial API gateway: JWT-authenticated layer manifest, license-gated WebSocket stream, object storage status endpoint
- Codecov integration for test coverage reporting

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
