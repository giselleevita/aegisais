# AegisAIS

[![CI](https://github.com/giselleevita/aegisais/actions/workflows/ci.yml/badge.svg)](https://github.com/giselleevita/aegisais/actions/workflows/ci.yml)
[![Images](https://github.com/giselleevita/aegisais/actions/workflows/images.yml/badge.svg)](https://github.com/giselleevita/aegisais/actions/workflows/images.yml)
[![codecov](https://codecov.io/gh/giselleevita/aegisais/branch/main/graph/badge.svg)](https://codecov.io/gh/giselleevita/aegisais)

**AIS Data Integrity and Anomaly Detection — Maritime Intelligence Platform**

AegisAIS is an automated data integrity and anomaly detection platform for Automatic Identification System (AIS) maritime data. It ingests AIS position reports, maintains per-vessel track history, and automatically detects physically impossible or internally inconsistent data patterns — surfacing them as prioritised, analyst-ready alerts.

> See [`docs/security/SECURITY.md`](./docs/security/SECURITY.md) for scope, limitations, and responsible use guidelines.

**Private repository — reviewers:** see [docs/REVIEWER_GUIDE.md](docs/REVIEWER_GUIDE.md) for a 15-minute evaluation path.

---

## Quick Start (Docker)

```bash
git clone https://github.com/giselleevita/aegisais.git && cd aegisais
bash scripts/start_full_stack.sh
```

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| API + Swagger | http://localhost:8000/docs |
| BFF Geospatial API | http://localhost:8080 |
| Prometheus metrics | http://localhost:8000/metrics |

---

## Features

- **Real-time Processing** — Stream large AIS data files with batch ingestion and live WebSocket updates
- **Anomaly Detection** — 7 detection rules covering teleportation, turn rates, position validity, acceleration, and heading/COG consistency
- **Tiered Alert System** — Tier 1 (integrity violations) and Tier 2 (suspicious behaviour) with 0–100 severity scoring
- **ITDAE Module** — Dedicated Infrastructure Threat Detection and Analysis Engine, including Baltic cable geofence monitoring
- **Interactive Map** — Visualise vessel positions, alert locations, and historical tracks via Leaflet
- **Track History** — Replay and inspect per-vessel position history over any time window
- **Alert Management** — Update status, add analyst notes, filter by type/severity, and export as CSV or JSON
- **Prometheus Metrics** — Built-in instrumentation at `/metrics` for observability integration
- **BFF Geospatial Gateway** — Contract-first Fastify BFF with JWT auth, licence gating, rate limiting, and OpenAPI 3.0 spec ([`apps/bff/openapi.yaml`](./apps/bff/openapi.yaml))
- **Demo & Onboarding** — Interactive guided tour and pre-built demo datasets covering every alert type

---

## Table of Contents

- [Monorepo Layout](#monorepo-layout)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [Detection Rules](#detection-rules)
- [Development](#development)
- [Testing](#testing)
- [Deployment](#deployment)
- [Documentation](#documentation)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## Monorepo Layout

AegisAIS is a [Turborepo](https://turbo.build/) monorepo managed with npm workspaces:

```text
aegisais/
├── apps/
│   ├── api/          # FastAPI backend (Python) — core AIS pipeline, detection engine, REST API
│   ├── bff/          # Fastify BFF (TypeScript) — contract-first geospatial API gateway
│   └── web/          # React + Vite frontend (TypeScript) — analyst dashboard and map UI
├── packages/         # Shared packages (reserved for future use)
├── data/
│   ├── raw/          # Uploaded / source AIS data files
│   └── processed/    # Processed output (gitignored)
├── docs/             # Project-level documentation
├── infra/            # Infrastructure configuration
├── turbo.json        # Turborepo task pipeline
└── package.json      # Root workspace manifest
```

---

## Installation

### Prerequisites

| Tool | Version |
| --- | --- |
| Python | 3.11+ |
| Node.js | 20.19+ |
| npm | 10.8+ |
| PostgreSQL | 14+ _(optional — SQLite works for development)_ |

### Local Development

```bash
# 1. Clone the repository
git clone https://github.com/giselleevita/aegisais.git
cd aegisais

# 2. Backend — create virtualenv and install dependencies
cd apps/api
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -U pip
pip install -e .

# 3. Run database migrations
alembic upgrade head

# 4. Start the API server
uvicorn app.main:app --reload    # http://localhost:8000

# 5. Frontend — open a new terminal
cd ../../apps/web
npm install
npm run dev                      # http://localhost:5173
```

Or start both apps in parallel from the repo root using Turborepo:

```bash
npm install   # install root devDependencies (turbo)
npm run dev   # starts api + web concurrently
```

### Docker

```bash
bash scripts/start_full_stack.sh
```

The helper script starts the core Docker services in parallel, auto-selects non-conflicting host ports when common defaults are already occupied, auto-generates a self-signed local TLS certificate for nginx when `infra/docker/nginx/certs/` is empty, and prints the chosen URLs at the end.

If you want to invoke Docker Compose manually instead, the core processing stack needs more than the API alone:

```bash
docker compose -f infra/docker/docker-compose.yml up -d \
	db redis api processing-worker persistence-worker alert-worker bff web nginx
```

Host-port overrides supported by the compose file:

- `POSTGRES_HOST_PORT`
- `REDIS_HOST_PORT`
- `BFF_HOST_PORT`
- `WEB_HOST_PORT`
- `NGINX_HTTP_HOST_PORT`
- `NGINX_HTTPS_HOST_PORT`
- `PROMETHEUS_HOST_PORT`
- `GRAFANA_HOST_PORT`

---

## Usage

### 1. Provide AIS Data

Place AIS data files in `data/raw/` or upload them via the web interface.

**Supported formats:**

| Format | Description |
| --- | --- |
| `.csv` | Comma-delimited CSV |
| `.dat` | Tab- or space-delimited |
| `.csv.zst` | Zstandard-compressed CSV |
| `.dat.zst` | Zstandard-compressed DAT |

**Required columns** (flexible name matching):

| Field | Accepted column names |
| --- | --- |
| MMSI | `mmsi`, `MMSI` |
| Timestamp | `timestamp`, `base_date_time`, `time` |
| Latitude | `lat`, `latitude` |
| Longitude | `lon`, `longitude` |
| SOG _(optional)_ | `sog` |
| COG _(optional)_ | `cog` |
| Heading _(optional)_ | `heading` |

### 2. Process Data

Processing begins automatically after upload. To start or control replay manually:

```bash
# Start replay at 100× speed
curl -X POST "http://localhost:8000/v1/replay/start?path=data/raw/file.csv.zst&speedup=100.0"

# Check replay status
curl "http://localhost:8000/v1/replay/status"

# Stop replay
curl -X POST "http://localhost:8000/v1/replay/stop"
```

### 3. View Results

| View | Description |
| --- | --- |
| **Dashboard** | Processing progress and system metrics |
| **Alerts** | Filter, annotate, and export detected anomalies |
| **Vessels** | Browse tracked vessels and their latest positions |
| **Map** | Interactive Leaflet map with vessel tracks and alert markers |

---

## API Documentation

Full reference: [`docs/product/API_DOCUMENTATION.md`](./docs/product/API_DOCUMENTATION.md)

Interactive docs are served by the running API:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **BFF OpenAPI spec**: [`apps/bff/openapi.yaml`](./apps/bff/openapi.yaml)

### Key Endpoints

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/v1/health` | Basic health check |
| `GET` | `/v1/health/detailed` | Health check including database connectivity |
| `GET` | `/v1/metrics` | System metrics (vessel and alert counts) |
| `GET` | `/v1/vessels` | List vessels (filterable by min severity) |
| `GET` | `/v1/vessels/{mmsi}` | Get vessel by MMSI |
| `GET` | `/v1/vessels/{mmsi}/track` | Get historical track positions |
| `GET` | `/v1/alerts` | List alerts (filterable by type, status, severity, time) |
| `PATCH` | `/v1/alerts/{id}/status` | Update alert status and/or analyst notes |
| `GET` | `/v1/alerts/stats/summary` | Alert statistics summary |
| `GET` | `/v1/alerts/export/csv` | Export alerts as CSV |
| `GET` | `/v1/alerts/export/json` | Export alerts as JSON |
| `POST` | `/v1/upload` | Upload AIS data file (max 5 GB) |
| `GET` | `/v1/upload/list` | List uploaded files |
| `POST` | `/v1/replay/start` | Start data replay |
| `POST` | `/v1/replay/stop` | Stop current replay |
| `GET` | `/v1/replay/status` | Get replay progress |
| `WS` | `/v1/stream` | WebSocket stream for real-time alerts and progress ticks |
| `GET` | `/metrics` | Prometheus metrics endpoint |

---

## Architecture

### Backend — Modular Monolith (`apps/api`)

```text
apps/api/app/
├── api/
│   └── v1/               # Versioned REST endpoints (vessels, alerts, tracks, upload, health)
├── core/                 # Database engine, config, logging, and startup events
├── infrastructure/
│   ├── cache/            # Redis-backed track store and cooldown store
│   ├── ingest/           # AIS file loaders, schema normalisation, and replay engine
│   ├── messaging/        # Internal pub/sub publisher and consumer
│   └── ws/               # WebSocket connection manager
├── modules/              # Domain feature modules
│   ├── alerts/           # Alert models, schemas, and services
│   ├── audit/            # Audit trail models and services
│   ├── auth/             # Authentication models, dependencies, and routes
│   ├── fusion/           # Data fusion models
│   ├── itdae/            # Infrastructure Threat Detection & Analysis Engine
│   │   ├── api/          # ITDAE routes (/api/v1/itdae/*)
│   │   ├── detection/    # ITDAE detection rules and severity scoring
│   │   ├── geofences/    # Geofence zones (e.g. Baltic cable regions)
│   │   ├── ingestion/    # ITDAE decoder and stream ingestion
│   │   ├── services/     # ITDAE pipeline service
│   │   └── tracking/     # ITDAE track store and feature extraction
│   └── vessels/          # Vessel models, schemas, and services
├── services/
│   ├── pipeline.py       # Main AIS processing pipeline
│   ├── cleanup.py        # Data cleanup service
│   └── workers/          # Background workers (alert, processing, persistence)
├── detection/            # Core detection rules and severity scoring
├── tracking/             # Core track store and feature extraction
├── middleware/           # Rate limiting middleware
├── utils/                # Shared utility functions and error types
└── main.py               # FastAPI application entry point
```

### BFF — Geospatial API Gateway (`apps/bff`)

A contract-first [Fastify](https://fastify.dev/) Backend-for-Frontend designed via OpenAPI 3.0. See [`apps/bff/README.md`](./apps/bff/README.md) and [`apps/bff/openapi.yaml`](./apps/bff/openapi.yaml).

| Endpoint | Auth | Description |
| --- | --- | --- |
| `GET /health` | — | Liveness probe |
| `GET /v1/storage/status` | — | Object storage provider check |
| `GET /v1/layers/manifest` | JWT + licence | License-filtered layer catalogue; Redis-backed cache |
| `WS /v1/stream` | JWT + `ports:read` licence | Real-time heartbeat stream |

### Frontend — Feature-Based (`apps/web`)

```text
apps/web/src/
├── core/                 # API client config, global constants, ErrorBoundary
├── features/
│   ├── alerts/           # Alerts panel and alert management UI
│   ├── geodata/          # EEZ boundaries and environmental overlays
│   ├── itdae/            # ITDAE-specific map layers and components
│   ├── map/              # Leaflet map view and vessel track visualisation
│   └── vessels/          # Vessel details panel and vessel list
├── shared/
│   ├── components/       # FileDropZone, Dashboard, DemoMode, WelcomePage, Onboarding, ReplayControls
│   ├── hooks/            # useWebSocket and other shared hooks
│   └── types/            # Shared TypeScript types (common.ts)
├── App.tsx               # Root application component
└── main.tsx              # React entry point
```

---

## Configuration

### Environment Variables

**Backend (`apps/api`)**

| Variable | Default | Description |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./aegisais.db` | SQLAlchemy database connection string |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

**Frontend (`apps/web`)**

| Variable | Default | Description |
| --- | --- | --- |
| `VITE_API_BASE_URL` | `http://localhost:8000` | Backend API base URL |

Create a `.env` file in `apps/web/` to override:

```env
VITE_API_BASE_URL=http://localhost:8000
```

---

## Detection Rules

### Tier 1 — Integrity Violations

| Alert Type | Trigger |
| --- | --- |
| `TELEPORT` | Implied speed between consecutive positions exceeds the physical speed limit for the time gap |
| `TURN_RATE` | Heading change rate exceeds the maximum physically possible for the reported speed |

### Tier 2 — Suspicious Behaviour

| Alert Type | Trigger |
| --- | --- |
| `TELEPORT_T2` | Implied speed is high but not outright impossible — warrants review |
| `TURN_RATE_T2` | Turn rate is elevated but below the hard physical threshold |
| `POSITION_INVALID` | Coordinates fall outside valid geographic range |
| `ACCELERATION` | Speed change between positions exceeds physical limits |
| `HEADING_COG_CONSISTENCY` | Heading and COG diverge significantly at a reportable speed |

Thresholds are defined in `apps/api/app/modules/itdae/settings.py`.

---

## Development

### Database Migrations

```bash
cd apps/api
alembic upgrade head          # Apply all pending migrations
alembic current               # Check current state
alembic revision --autogenerate -m "describe your change"
alembic downgrade -1          # Roll back one step
```

### Demo Data

```bash
cd apps/api
python scripts/generate_demo_data.py
```

---

## Testing

```bash
# Backend unit and integration tests
cd apps/api && pytest tests/ -v

# Frontend linting
cd apps/web && npm run lint
```

---

## Deployment

### Production Checklist

- [ ] Use PostgreSQL — set `DATABASE_URL` to a Postgres connection string
- [ ] Run `alembic upgrade head` before starting the API
- [ ] Restrict CORS origins to your production domain
- [ ] Configure rate limiting for public-facing deployments
- [ ] Set up Prometheus scraping against `/metrics`
- [ ] Store all secrets in environment variables — never commit `.env` files

### Kubernetes

```bash
kubectl apply -k infra/k8s/overlays/staging
kubectl apply -k infra/k8s/overlays/production
```

---

## Documentation

| Domain | Key Documents |
| --- | --- |
| **Architecture** | [`ARCHITECTURE.md`](./docs/architecture/ARCHITECTURE.md), [`INFRA_BASELINE_KUBERNETES.md`](./docs/architecture/INFRA_BASELINE_KUBERNETES.md) |
| **Operations** | [`DEMO_GUIDE.md`](./docs/operations/DEMO_GUIDE.md), [`DB_MIGRATION_SETUP.md`](./docs/operations/DB_MIGRATION_SETUP.md) |
| **Product** | [`API_DOCUMENTATION.md`](./docs/product/API_DOCUMENTATION.md), [`FEATURES_IMPLEMENTED.md`](./docs/product/FEATURES_IMPLEMENTED.md) |
| **Security** | [`SECURITY.md`](./docs/security/SECURITY.md), [`INCIDENT_RESPONSE_RUNBOOK.md`](./docs/security/INCIDENT_RESPONSE_RUNBOOK.md) |
| **BFF** | [`apps/bff/README.md`](./apps/bff/README.md), [`apps/bff/openapi.yaml`](./apps/bff/openapi.yaml) |

---

## Troubleshooting

| Symptom | Resolution |
| --- | --- |
| `"File not found"` during replay | Ensure the file is in `data/raw/` and the path is relative to the project root |
| No alerts generated | Check thresholds in `settings.py`; verify the data contains anomalies |
| Alerts not appearing in UI | Refresh the page; clear active filters; confirm WebSocket shows "Connected" |
| Database errors on startup | Run `alembic upgrade head`; verify `DATABASE_URL` |
| `Multiple head revisions` from Alembic | Pull latest migrations, then `alembic upgrade head` |
| `"Vite requires Node.js 20.19+"` | Run `nvm use` inside `apps/web/` |

---

## Contributing

1. Branch from `main` and use conventional commit messages
2. Add tests for any new detection rules or API endpoints
3. Update the relevant documentation in `docs/`
4. Open a pull request using the provided [PR template](./.github/PULL_REQUEST_TEMPLATE.md)

---

## License

[MIT](./LICENSE)
