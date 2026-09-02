# AegisAIS — Reviewer Guide

This guide helps engineers evaluate the platform in about 15 minutes without production credentials.

## What problem it demonstrates

AegisAIS ingests **AIS maritime position data**, maintains per-vessel tracks, and detects **physically impossible or inconsistent patterns** (teleportation, turn-rate violations, heading/COG mismatch, etc.). Alerts are tiered and analyst-ready, with map UI, ITDAE geofence monitoring, and a contract-first BFF gateway.

## Architecture (60 seconds)

- **API:** `apps/api/` — FastAPI pipeline, detection rules, REST + WebSocket, Prometheus metrics
- **BFF:** `apps/bff/` — Fastify geospatial gateway, JWT auth, rate limits, OpenAPI (`openapi.yaml`)
- **Web:** `apps/web/` — React + Vite analyst dashboard (Leaflet map, alerts, tracks)
- **Supply chain:** SBOM + `pip-audit` / `check_frontend_audit.py` gates in CI (`supply-chain` job blocks downstream builds)

See [`docs/architecture/SYSTEM_OVERVIEW.md`](architecture/SYSTEM_OVERVIEW.md) and [`docs/security/SUPPLY_CHAIN_ASSURANCE.md`](security/SUPPLY_CHAIN_ASSURANCE.md).

## Run a small detection example without services

Use Python 3.11 or 3.12 on Linux or WSL, matching backend CI. The lockfile includes
`uvloop`, which cannot install on native Windows. Initial dependency downloads may
take several minutes. From a fresh checkout, in Bash:

```bash
git clone https://github.com/giselleevita/aegisais.git
cd aegisais/apps/api
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.lock
python -m pip install --no-deps -e .
python -m scripts.detection_walkthrough
```

No API keys, database, Redis, or Docker services are needed for this rule example.
Dependencies still need to be installed. On Windows, run this locked environment
inside WSL; changing only the virtual-environment activation command is not enough.

The [walkthrough source](../apps/api/scripts/detection_walkthrough.py) uses
synthetic points, starting at latitude 40.0 / longitude -74.0:

| Input relative to the first point | Rule | Expected result |
|---|---|---|
| Latitude 40.001, 60 seconds later | Teleport | `NO_ALERT` |
| Latitude 41.0, 60 seconds later | Teleport | `TELEPORT` |
| Latitude 200.0, 60 seconds later | Position validity | `POSITION_INVALID` |
| Latitude 41.0, 60 seconds earlier | Teleport | `NO_ALERT` |

With the default thresholds, the command prints:

```text
normal movement: NO_ALERT
impossible jump: TELEPORT
invalid latitude: POSITION_INVALID
out-of-order timestamp: NO_ALERT
```

`NO_ALERT` in the last case means the pair is skipped because elapsed time is
non-positive. It does **not** mean the input was validated as a safe vessel track.
The command exits nonzero if a result differs; custom environment thresholds can
change the expected results. This example exercises individual rules, not stream
delivery, database persistence, authentication, or UI updates.

Run the existing detection regression tests in the same environment:

```bash
export SECRET_KEY=local-review-only-not-a-production-secret-2026
python -m pytest tests/test_detection_rules.py -v --no-cov
```

The shared test fixtures set `APP_ENV=test`, which requires an explicit secret.
Test databases use in-memory SQLite.

## Full application path

```bash
bash scripts/start_full_stack.sh
```

Run this from the repository root with Docker running and Bash available. Use
the URLs printed by the launcher: it can choose alternative host ports when
defaults are occupied. Follow the [demo guide](operations/DEMO_GUIDE.md) for the
application workflow. Starting only FastAPI and Vite does not start the Redis
stream workers needed for end-to-end replay.

## 15-minute review checklist

| Step | Where to look | What to verify |
|------|---------------|----------------|
| 1 | `README.md` | Detection rules, tiered alerts, monorepo layout |
| 2 | `apps/api/` | Ingestion + anomaly detection logic |
| 3 | `apps/bff/openapi.yaml` | Contract-first BFF surface |
| 4 | `apps/web/src/` | Map, alert management, analyst workflows |
| 5 | `.github/workflows/ci.yml` | `supply-chain` → backend/frontend gate |
| 6 | `docs/security/SUPPLY_CHAIN_ASSURANCE.md` | SBOM, vulnerability policy, accepted exceptions |

## Engineering decisions to inspect

| Question | Code / evidence | Tradeoff |
|---|---|---|
| How does a position pair become an alert? | [Rules](../apps/api/app/detection/rules.py), [tests](../apps/api/tests/test_detection_rules.py) | Gap-aware thresholds are explainable but require domain calibration. |
| What happens on worker failures and retries? | [Worker boundaries](../apps/api/tests/test_worker_runtime_boundaries.py), [alert idempotency](../apps/api/tests/test_alert_idempotency.py) | Separate workers decouple processing and persistence; retries and duplicate delivery need explicit handling. |
| How are tenant boundaries checked? | [Organisation scope](../apps/api/tests/test_org_scope.py), [sensitive routes](../apps/api/tests/test_sensitive_route_auth.py) | Route authorization and tenant filtering need verification beyond a detector demo. |

An anomaly is a data-quality signal for analyst review, not proof of spoofing or
malicious intent. The small example is not a precision/recall benchmark and makes
no throughput claim. See [security scope](security/SECURITY.md) for further limits.

## What this is / is not

- **Is:** Maritime AIS integrity platform with map UI, BFF, and documented supply-chain controls
- **Is not:** Certified for regulated maritime operations without further validation and deployment hardening
