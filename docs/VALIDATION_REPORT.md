# Validation Report

## Scope

This validation pass checked:

- active repository structure and entry points
- backend runtime viability
- backend test execution
- frontend build and lint execution
- Docker API image build path
- alignment between the new audit package and the current codebase
- conflicts between the new audit package and older documentation

This report is evidence-based. Anything not directly checked is called out as not verified.

## Repository Baseline

The active repository layout is:

- `apps/api`
- `apps/web`
- `infra/docker/docker-compose.yml`
- `docs/*`

The repo is clearly in a migration state from the older `backend` / `frontend` structure to the current `apps/api` / `apps/web` monorepo layout. This is the primary source of documentation drift.

## Commands Run

```bash
find docs -maxdepth 1 -type f | sort
find apps -maxdepth 2 -type f | sort
sed -n '1,260p' apps/api/pyproject.toml
sed -n '1,260p' apps/web/package.json
sed -n '1,260p' infra/docker/docker-compose.yml
sed -n '1,240p' apps/api/start.sh
sed -n '1,240p' apps/api/start_with_migrations.sh
sed -n '1,240p' apps/web/start.sh
find apps/api/app -maxdepth 3 -type f | sort
find apps/web/src -maxdepth 4 -type f | sort
python3.11 -m venv /tmp/aegisais-api-validate
/tmp/aegisais-api-validate/bin/pip install -r apps/api/requirements-dev.lock
/tmp/aegisais-api-validate/bin/pip install --no-deps -e apps/api
cd apps/api && /tmp/aegisais-api-validate/bin/pytest -q
cd apps/api && DATABASE_URL=sqlite:///./aegisais.db /tmp/aegisais-api-validate/bin/uvicorn app.main:app --host 127.0.0.1 --port 8010
curl -sS http://127.0.0.1:8010/v1/health
curl -sS http://127.0.0.1:8010/
cd apps/web && npm run build
cd apps/web && npm run lint
docker compose -f infra/docker/docker-compose.yml build api
rg -n 'require_role|require_admin|get_current_user' apps/api/app
find apps/api/tests -type f | sort
find apps/web -type f | rg 'test|spec|playwright|cypress'
```

## Practical Validation Results

## Passed

| Check | Result | Evidence |
| --- | --- | --- |
| Backend dependency install in isolated Python 3.11 environment | Passed | `requirements-dev.lock` installed successfully into a fresh venv |
| Backend test suite | Passed | `38 passed in 12.11s` |
| Backend local runtime startup | Passed | Uvicorn started successfully on `127.0.0.1:8010` |
| Backend health endpoint | Passed | `GET /v1/health` returned `{"status":"healthy",...}` |
| Backend root endpoint | Passed | `GET /` returned API metadata |
| Frontend production build | Passed | `vite build` completed successfully |
| Frontend lint execution | Passed with warnings | ESLint ran to completion with warnings only |

## Failed

| Check | Result | Failure Detail | Risk |
| --- | --- | --- | --- |
| Docker API image build | Failed | `pip install --require-hashes -r requirements.lock` fails because transitive requirement `greenlet>=1` is not pinned under hash mode | High |

## Passed with Qualification

| Check | Qualification |
| --- | --- |
| Frontend lint | No blocking errors, but 16 warnings remain, including missing React hook dependencies and unused ESLint disable directives |
| Authentication model | Auth exists in code and protects multiple routes, but production hardening is incomplete |

## Not Verified

- Full `docker compose up` stack startup
- Worker service behavior in Docker
- Frontend dev server runtime behavior in a browser
- Realtime websocket behavior end to end
- PostgreSQL-backed local runtime
- Redis-backed local runtime
- CI workflow execution in GitHub Actions
- Restore procedure for backups
- Scheduled cleanup behavior in a real deployed environment

## Stack Reality Summary

## Backend

Confirmed:

- FastAPI application starts locally
- health endpoints respond
- JWT/OAuth2-style authentication routes and dependencies exist
- multiple API routes require authenticated or admin users
- tests exist and pass locally

Partially supported:

- production-hardening claims around security remain incomplete
- Redis and worker-oriented infrastructure exist in code and compose config, but were not executed in this pass

## Frontend

Confirmed:

- React/Vite frontend exists under `apps/web`
- production build succeeds
- feature structure matches alert, vessel, map, and ITDAE domains

Partially supported:

- lint is non-blocking but not clean
- no project-owned frontend test suite was found

## Docker and Deployment

Confirmed:

- active Docker setup lives in `infra/docker/docker-compose.yml`
- compose defines `db`, `redis`, `api`, and dedicated worker/ingestion services

Contradicted by runtime validation:

- the current hardened API Docker install path does not build successfully because the lockfile is not valid for `--require-hashes`

## Audit Document Alignment

| Audit Doc | Statement Area | Status | Notes |
| --- | --- | --- | --- |
| `SYSTEM_OVERVIEW.md` | AIS integrity/anomaly-detection scope | Confirmed | Matches README, security scope, API behavior, and code layout |
| `SYSTEM_OVERVIEW.md` | Not production-complete platform | Confirmed | Supported by security policy, missing ops controls, and validation results |
| `ARCHITECTURE.md` | Modular monolith backend and feature-based frontend | Confirmed | Matches current `apps/api` and `apps/web` layout |
| `ARCHITECTURE.md` | Auth present but not fully production-hardened | Confirmed | Supported by auth routes, dependencies, and config defaults |
| `ARCHITECTURE.md` | Deployment shape | Partially supported | Compose includes API, Postgres, Redis, and worker services; full runtime was not executed |
| `RISK_REGISTER.md` | SQLite scale limits | Confirmed | Matches config defaults, docs, and deployment guidance |
| `RISK_REGISTER.md` | No integration/performance testing | Confirmed | Backend has tests; no integration or performance suite was found |
| `RISK_REGISTER.md` | Export governance and audit controls incomplete | Partially supported | Export endpoints exist; stronger governance controls were not verified |
| `SCALE_AND_INFRA.md` | PostgreSQL and streaming improve scale posture | Confirmed | Supported by code and docs |
| `SCALE_AND_INFRA.md` | Monitoring, recovery, and retention are incomplete | Confirmed | Supported by docs and lack of verified ops controls |
| `ACTION_PLAN.md` | Hardening and testing priority | Confirmed | Matches practical validation findings |

## Key Mismatches Between Audit Docs and Repo Reality

| Mismatch | Repo Reality | Risk Level |
| --- | --- | --- |
| Older gap analysis says auth is missing | Auth routes and role dependencies exist in code | High |
| Older docs describe `backend` / `frontend` layout as current | Active repo uses `apps/api` / `apps/web` | High |
| Older docs describe `docker-compose.yml` at repo root | Active compose file is `infra/docker/docker-compose.yml` | High |
| New audit docs originally understated deployment topology | Current compose includes API, Postgres, Redis, and worker services | Medium |
| Hardened dependency/Docker path implies reproducible container build | Current Docker build fails under hash enforcement | High |
| README and multiple docs link to root-level files that no longer exist | Active docs live under `docs/` | High |

## Documentation Conflict Summary

Primary conflict patterns:

- path drift from `backend` / `frontend` to `apps/api` / `apps/web`
- historical gap analysis conflicting with later implementation summaries
- broken or stale links in the root README
- older operational guidance pointing to obsolete compose and setup paths

These conflicts are material for due diligence because they can make the system appear either more complete or less complete than it actually is.

## Safe Cleanup Applied

The following conservative documentation cleanups were made:

- added a layout-migration note to `README.md`
- fixed the README security link to `docs/SECURITY.md`
- added historical or superseded notes to:
  - `docs/PROJECT_STRUCTURE.md`
  - `docs/MISSING_FEATURES.md`
  - `docs/FEATURES_IMPLEMENTED.md`
  - `docs/CODE_QUALITY.md`
  - `docs/FIXES_SUMMARY.md`
- corrected the new audit package to reflect that auth exists in code but is not yet production-hardened

## Overall Validation Assessment

The repository is reviewable and materially more trustworthy after this pass, but it is not fully validated end to end.

Current confidence level by area:

- backend local runtime: high
- backend unit-level test baseline: high
- frontend buildability: high
- frontend quality baseline: medium
- Docker production path: low until the hash-locked build is fixed
- deployment/documentation consistency: medium after cleanup, with remaining legacy drift still present

## Recommended Next Action

Fix the Docker dependency installation path first. It is the clearest repo-to-documentation trust break because the current production-oriented build flow does not complete successfully.
