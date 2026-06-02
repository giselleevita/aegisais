# AegisAIS BFF — Geospatial API Gateway

[![CI](https://github.com/giselleevita/aegisais/actions/workflows/ci.yml/badge.svg)](https://github.com/giselleevita/aegisais/actions/workflows/ci.yml)

A contract-first **Backend-for-Frontend** built with [Fastify](https://fastify.dev/) (TypeScript) that sits between the React client and the core Python API. It provides JWT-authenticated, rate-limited, license-gated geospatial endpoints with in-memory response caching.

> Full OpenAPI 3.0 contract: [`openapi.yaml`](./openapi.yaml)

---

## Why a BFF?

- **Decouples** the frontend from the Python API's internal data model
- **License-gates** geospatial features (EEZ layers, bathymetry, weather overlays) per-tenant
- **Rate-limits** at the edge before requests hit the heavier Python pipeline
- **Caches** expensive layer manifests in-process with configurable TTL

---

## Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | — | Liveness probe — returns env and uptime |
| `GET` | `/v1/storage/status` | — | Object storage provider config check |
| `GET` | `/v1/layers/manifest` | JWT + licence | Licence-filtered geodata layer catalogue |
| `WS` | `/v1/stream` | JWT + `ports:read` | Real-time heartbeat stream (ping/pong) |

---

## Design Properties

- **OpenAPI-first** — full contract defined in `openapi.yaml` before implementation
- **Licence-gated** — per-feature licence flags enforced at the route layer (`layers:read`, `ports:read`)
- **Rate limited** — sliding-window per-identity limiter on all authenticated endpoints
- **In-process cache** — configurable TTL cache on layer manifest to reduce upstream load
- **JWT auth** — Bearer token validation on all protected routes

---

## Running Locally

```bash
cd apps/bff
npm install
npm run dev     # http://localhost:8080
```

Or via Docker Compose from the repo root:

```bash
docker compose -f infra/docker/docker-compose.yml up bff
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `PORT` | `8080` | BFF listen port |
| `API_BASE_URL` | `http://api:8000` | Upstream Python API URL |
| `JWT_SECRET` | — | Secret for JWT verification |
| `CACHE_TTL_MS` | `30000` | Layer manifest cache TTL (ms) |
| `RATE_LIMIT_MAX` | `100` | Max requests per window per identity |
| `RATE_LIMIT_WINDOW_MS` | `60000` | Rate limit sliding window (ms) |

---

## Stack

- **Runtime:** Node.js 20+
- **Framework:** Fastify
- **Language:** TypeScript (strict)
- **API contract:** OpenAPI 3.0 ([`openapi.yaml`](./openapi.yaml))
- **Tests:** `apps/bff/tests/`
