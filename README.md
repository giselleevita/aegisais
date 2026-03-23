# AegisAIS

[![CI](https://github.com/giselleevita/aegisais/actions/workflows/ci.yml/badge.svg)](https://github.com/giselleevita/aegisais/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/giselleevita/aegisais/branch/main/graph/badge.svg)](https://codecov.io/gh/giselleevita/aegisais)

**AIS Data Integrity and Anomaly Detection — Maritime Intelligence Platform**

AegisAIS is an automated data integrity and anomaly detection platform for Automatic Identification System (AIS) maritime data. It ingests AIS position reports, maintains per-vessel track history, and automatically detects physically impossible or internally inconsistent data patterns — surfacing them as prioritised, analyst-ready alerts.

> See [`docs/SECURITY.md`](./docs/SECURITY.md) for scope, limitations, and responsible use guidelines.

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

## Quick Start

### Prerequisites

| Tool | Version |
|---|---|
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

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| Prometheus metrics | http://localhost:8000/metrics |
| BFF Geospatial API | http://localhost:8080 |

### Docker

```bash
docker-compose up --build
```

---

## Installation

### Backend (`apps/api`)

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -e .
alembic upgrade head
```

### Frontend (`apps/web`)

```bash
cd apps/web
nvm use          # uses .nvmrc — Node 20.19.0
npm install
```

---

## Usage

### 1. Provide AIS Data

Place AIS data files in `data/raw/` or upload them via the web interface.

**Supported formats:**

| Format | Description |
|---|---|
| `.csv` | Comma-delimited CSV |
| `.dat` | Tab- or space-delimited |
| `.csv.zst` | Zstandard-compressed CSV |
| `.dat.zst` | Zstandard-compressed DAT |

**Required columns** (flexible name matching):

| Field | Accepted column names |
|---|---|
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
|---|---|
| **Dashboard** | Processing progress and system metrics |
| **Alerts** | Filter, annotate, and export detected anomalies |
| **Vessels** | Browse tracked vessels and their latest positions |
| **Map** | Interactive Leaflet map with vessel tracks and alert markers |

---

## API Documentation

Full reference: [`docs/API_DOCUMENTATION.md`](./docs/API_DOCUMENTATION.md)

Interactive docs are served by the running API:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

| Method | Path | Description |
|---|---|---|
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

A contract-first [Fastify](https://fastify.dev/) Backend-for-Frontend, designed via OpenAPI 3.0, that sits between the React client and the core Python API. It provides JWT-authenticated, rate-limited, license-gated geospatial endpoints with in-memory response caching.

| Endpoint | Auth | Description |
|---|---|---|
| `GET /health` | — | Liveness probe — returns env and status |
| `GET /v1/storage/status` | — | Object storage provider configuration check |
| `GET /v1/layers/manifest` | JWT + licence | License-filtered layer catalogue; Redis-backed cache |
| `WS /v1/stream` | JWT + `ports:read` licence | Real-time heartbeat stream with ping/pong protocol |

**Key design properties:**
- **OpenAPI-first** — full contract in `openapi.yaml` before any implementation
- **License-gated** — per-feature licence flags enforced at the route layer
- **Rate limited** — sliding-window per-identity limiter on all read endpoints
- **In-process cache** — configurable TTL cache on the layer manifest to reduce upstream load

### Frontend — Feature-Based (`apps/web`)

```text
apps/web/src/
├── core/                 # API client config and global constants
├── features/
│   ├── alerts/           # Alerts panel and alert management UI
│   ├── itdae/            # ITDAE-specific map layers and components
│   ├── map/              # Leaflet map view and vessel track visualisation
│   └── vessels/          # Vessel details panel and vessel list
├── layouts/              # Application-wide layout wrappers
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
|---|---|---|
| `DATABASE_URL` | `sqlite:///./aegisais.db` | SQLAlchemy database connection string |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

**Frontend (`apps/web`)**

| Variable | Default | Description |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000` | Backend API base URL |

Create a `.env` file in `apps/web/` to override:

```env
VITE_API_BASE_URL=http://localhost:8000
```

---

## Detection Rules

AegisAIS applies two tiers of detection rules to every incoming AIS position update.

### Tier 1 — Integrity Violations

| Alert Type | Trigger |
|---|---|
| `TELEPORT` | Implied speed between consecutive positions exceeds the physical speed limit for the time gap |
| `TURN_RATE` | Heading change rate exceeds the maximum physically possible for the reported speed |

### Tier 2 — Suspicious Behaviour

| Alert Type | Trigger |
|---|---|
| `TELEPORT_T2` | Implied speed is high but not outright impossible — warrants review |
| `TURN_RATE_T2` | Turn rate is elevated but below the hard physical threshold |
| `POSITION_INVALID` | Coordinates fall outside valid geographic range (lat > ±90°, lon > ±180°) |
| `ACCELERATION` | Speed change between positions exceeds physical limits |
| `HEADING_COG_CONSISTENCY` | Heading and COG diverge significantly at a reportable speed |

All alerts carry a **severity score (0–100)** and structured **evidence fields** (implied speed, distance, time delta, tier, etc.).

### Configuring Thresholds

Thresholds are defined in `apps/api/app/modules/itdae/settings.py`:

```python
teleport_speed_knots_short   = 60.0    # Threshold for time gaps ≤ 120 s
teleport_speed_knots_medium  = 100.0   # Threshold for time gaps 120 s–30 min
max_turn_rate_deg_per_sec    = 3.0
min_speed_for_turn_check_kn  = 10.0
alert_cooldown_sec           = 300     # 5-minute cooldown per vessel per rule
```

---

## Development

### Database Migrations

AegisAIS uses [Alembic](https://alembic.sqlalchemy.org/) for schema version control.

```bash
cd apps/api

# Apply all pending migrations
alembic upgrade head

# Check current migration state
alembic current

# Auto-generate a migration after changing models
alembic revision --autogenerate -m "describe your change"

# Roll back one step
alembic downgrade -1

# If you see "Multiple head revisions", the repo includes a merge revision — upgrade to the single head:
alembic heads   # should show one head after pulling latest
alembic upgrade head
```

**SQLite (default local dev):** The full migration chain runs on SQLite. Organisation **foreign keys** are skipped on SQLite only (Alembic cannot `ALTER ADD CONSTRAINT`); the app still enforces tenancy in code. Use **PostgreSQL** for database-level FK parity.

See [`apps/api/MIGRATION_GUIDE.md`](./apps/api/MIGRATION_GUIDE.md) and [`docs/DB_MIGRATION_SETUP.md`](./docs/DB_MIGRATION_SETUP.md) for full details.

### Demo Data

Pre-built demo files covering every alert type live in `data/raw/`. To regenerate:

```bash
cd apps/api
python scripts/generate_demo_data.py
```

See [`docs/DEMO_GUIDE.md`](./docs/DEMO_GUIDE.md) for demo scenarios and expected results.

---

## Testing

```bash
# Backend unit and integration tests
cd apps/api
pytest tests/ -v

# Frontend linting
cd apps/web
npm run lint
```

---

## Deployment

### Production Checklist

- [ ] Use PostgreSQL — set `DATABASE_URL` to a Postgres connection string
- [ ] Run `alembic upgrade head` before starting the API
- [ ] Configure authentication — the `auth` module is included; enable and secure it appropriately
- [ ] Restrict CORS origins to your production domain in `apps/api/app/main.py`
- [ ] Configure rate limiting for public-facing deployments
- [ ] Set up Prometheus scraping against `/metrics`
- [ ] Enable structured logging and forward to your observability stack
- [ ] Store all secrets in environment variables — never commit `.env` files
- [ ] Implement a database backup and recovery strategy

### Docker

```bash
docker-compose up -d
```

The API Dockerfile automatically runs `alembic upgrade head` on container startup before launching the server. See [`apps/api/start_with_migrations.sh`](./apps/api/start_with_migrations.sh) for manual control.

---

## Documentation

| Document | Description |
|---|---|
| [`docs/API_DOCUMENTATION.md`](./docs/API_DOCUMENTATION.md) | Complete REST and WebSocket API reference |
| [`docs/DEMO_GUIDE.md`](./docs/DEMO_GUIDE.md) | Demo datasets, scenarios, and expected results |
| [`docs/DB_MIGRATION_SETUP.md`](./docs/DB_MIGRATION_SETUP.md) | Database migration system overview |
| [`docs/LARGE_DATASET_GUIDE.md`](./docs/LARGE_DATASET_GUIDE.md) | Performance tuning for large AIS datasets |
| [`docs/SECURITY.md`](./docs/SECURITY.md) | Security scope, limitations, and responsible use |
| [`apps/api/MIGRATION_GUIDE.md`](./apps/api/MIGRATION_GUIDE.md) | Alembic migration developer guide |

---

## Troubleshooting

| Symptom | Resolution |
|---|---|
| `"File not found"` during replay | Ensure the file is in `data/raw/` and the path is relative to the project root |
| No alerts generated | Check thresholds in `settings.py`; verify the data contains anomalies; inspect API logs |
| Alerts not appearing in UI | Refresh the page; clear active filters; confirm WebSocket shows "Connected" |
| Database errors on startup | Run `alembic upgrade head`; verify `DATABASE_URL`; check database permissions |
| `Multiple head revisions` from Alembic | Pull latest migrations, then `alembic upgrade head` (merge revisions unify branches) |
| ITDAE geofence seed / missing `itdae_geofence_zones` | Apply migrations; until then the API skips seed cleanly when the table is absent |
| `"Vite requires Node.js 20.19+"` | Run `nvm use` inside `apps/web/` or install Node.js 20.19+ |
| Processing too slow on large files | Increase the `speedup` parameter; ensure `use_streaming=true` |

---

## Contributing

1. Branch from `main` and use conventional commit messages
2. Add tests for any new detection rules or API endpoints
3. Update the relevant documentation in `docs/`
4. Ensure TypeScript strict types pass (`npm run lint`) and Python type hints are present
5. Open a pull request using the provided [PR template](./.github/PULL_REQUEST_TEMPLATE.md)

---

## License

[MIT](./LICENSE)
