# AegisAIS — Reviewer Guide

**Private repository — available on request.** This guide helps recruiters and senior engineers evaluate the platform in about 15 minutes without production credentials.

## What problem it demonstrates

AegisAIS ingests **AIS maritime position data**, maintains per-vessel tracks, and detects **physically impossible or inconsistent patterns** (teleportation, turn-rate violations, heading/COG mismatch, etc.). Alerts are tiered and analyst-ready, with map UI, ITDAE geofence monitoring, and a contract-first BFF gateway.

## Architecture (60 seconds)

- **API:** `apps/api/` — FastAPI pipeline, detection rules, REST + WebSocket, Prometheus metrics
- **BFF:** `apps/bff/` — Fastify geospatial gateway, JWT auth, rate limits, OpenAPI (`openapi.yaml`)
- **Web:** `apps/web/` — React + Vite analyst dashboard (Leaflet map, alerts, tracks)
- **Supply chain:** SBOM + `pip-audit` / `check_frontend_audit.py` gates in CI (`supply-chain` job blocks downstream builds)

See [`docs/architecture/SYSTEM_OVERVIEW.md`](architecture/SYSTEM_OVERVIEW.md) and [`docs/security/SUPPLY_CHAIN_ASSURANCE.md`](security/SUPPLY_CHAIN_ASSURANCE.md).

## Fastest local path

```bash
bash scripts/start_full_stack.sh
# Frontend http://localhost:5173 | API docs http://localhost:8000/docs | BFF http://localhost:8080
```

For code-only review (no Docker): skim `apps/api/app/` detection modules and `apps/web/src/` map flows; run unit tests in `apps/api` with `pip-sync requirements-dev.lock && pytest`.

## 15-minute review checklist

| Step | Where to look | What to verify |
|------|---------------|----------------|
| 1 | `README.md` | Detection rules, tiered alerts, monorepo layout |
| 2 | `apps/api/` | Ingestion + anomaly detection logic |
| 3 | `apps/bff/openapi.yaml` | Contract-first BFF surface |
| 4 | `apps/web/src/` | Map, alert management, analyst workflows |
| 5 | `.github/workflows/ci.yml` | `supply-chain` → backend/frontend gate |
| 6 | `docs/security/SUPPLY_CHAIN_ASSURANCE.md` | SBOM, vulnerability policy, accepted exceptions |

**Tests to skim:** `cd apps/api && pytest -q` (after `pip-sync requirements-dev.lock`)

## What this is / is not

- **Is:** Maritime AIS integrity platform with map UI, BFF, and documented supply-chain controls
- **Is not:** Certified for regulated maritime operations without further validation and deployment hardening

## Request access

Contact via GitHub profile or portfolio site. Reviewers typically receive read access plus this guide and the main README.
