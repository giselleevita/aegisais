# Repository Audit

## Scope

This audit covers the current monorepo shape, runtime topology, data model, ingestion/alert logic, frontend state, and deployment pathways.

## Current Architecture Snapshot

- Monorepo with npm workspaces and Turbo.
- Backend in `apps/api` (FastAPI + SQLAlchemy + Alembic + Redis Streams workers).
- Frontend in `apps/web` (React + Vite + TypeScript).
- New BFF slice in `apps/bff` (Fastify + WebSocket) introduced for layer-manifest/query orchestration.
- Containerized platform in `infra/docker/docker-compose.yml` with Postgres/Redis/API/workers/monitoring.

## Dependency Graph (Logical)

```text
web (React AML workbench + legacy)
  -> API (/v1/*)
  -> BFF (/v1/layers, /v1/query, /v1/stream)

API (FastAPI)
  -> Postgres (state: vessels, alerts, incidents, watchlist, auth, audit, ITDAE)
  -> Redis (streams + cache + cooldown)
  -> worker processes (processing/persistence/alert/itdae ingestion)

BFF (Fastify)
  -> layer registry config + license gates
  -> cache + rate limiter
  -> WS stream fanout
  -> PostGIS canonical tables (vertical slice schema)
```

## Reusable Components

- Existing auth, audit, websocket hooks, and API client patterns are reusable.
- Existing AML shell/routing is reusable for new analyst workbench sections.
- Existing replay pipeline and rule engine can host simulation fixtures for detection demos.

## Technical Debt / Risks

- Parallel UI modes (legacy + AML) increase QA matrix and route parity complexity.
- Mixed pipeline styles (core workers vs module-specific paths) risk inconsistent behavior.
- Contract drift risk between API/BFF/frontend unless schemas are centrally enforced.
- External dataset licensing constraints must be encoded in runtime gates, not docs only.

## Recommended Migration Sequence

1. Keep existing API functional; add BFF as additive orchestration layer.
2. Move new geospatial features behind AML routes and feature flags.
3. Standardize contracts under `packages/contracts/schemas` and generate TS types.
4. Add licensed layer gates (non-commercial/restricted) in BFF manifest and UI badges.
5. Add ingestion adapters/importers incrementally (OpenSky + Ports first).
6. Expand incidents and explainable fused detections with provenance-first evidence.
