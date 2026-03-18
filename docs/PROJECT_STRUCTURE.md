# AegisAIS Project Structure

> Superseded note
> This document reflects the older `backend` / `frontend` repository layout and is retained as historical reference. For current review use, prefer `SYSTEM_OVERVIEW.md`, `ARCHITECTURE.md`, and the active `apps/api` / `apps/web` tree.

## Root Directory
```text
aegisais/
├── backend/          # Python FastAPI backend
├── frontend/         # React TypeScript frontend
├── data/             # Data files (gitignored, except .gitkeep)
│   ├── raw/          # Input AIS files (.csv, .dat, .zst)
│   └── processed/    # Processed data (future use)
├── docker-compose.yml
├── .gitignore
├── README.md
└── LARGE_DATASET_GUIDE.md
```text

## Backend Structure (`backend/`)

AegisAIS follows a **Modular Monolith** architecture to ensure separation of concerns while keeping deployment simple.

```text
backend/
├── app/                    # Main application package
│   ├── __init__.py
│   ├── main.py             # FastAPI app entry point
│   │
│   ├── api/                # Versioned API routes
│   │   └── v1/             # API Version 1 endpoints
│   │
│   ├── core/               # Global infrastructure
│   │   ├── config.py       # Settings & environment
│   │   ├── database.py     # Database session
│   │   └── logging.py      # Global logger setup
│   │
│   ├── infrastructure/     # Technical services
│   │   ├── ingest/         # AIS Data loaders & replay
│   │   └── ws/             # WebSocket management
│   │
│   ├── modules/            # Domain-specific logic
│   │   ├── alerts/         # Alert rules, schemas
│   │   ├── itdae/          # ITDAE specific algorithms
│   │   └── vessels/        # Vessel tracking, models
│   │
│   ├── utils/              # Shared utilities
│   ├── middleware/         # Custom Middlewares
│   │
│   ├── detection/          # (Legacy) Core detection logic
│   ├── services/           # (Legacy) Cross-domain pipelines
│   └── tracking/           # (Legacy) Core tracking functions
│
├── pyproject.toml          # Python dependencies
├── Dockerfile              # Docker build config
└── aegisais.db             # SQLite database (gitignored)
```text

## Frontend Structure (`frontend/`)

The frontend follows a **Feature-Based** architecture, co-locating components with their respective logic to improve maintainability.

```text
frontend/
├── src/
│   ├── core/               # App-wide configurations
│   │   ├── api-client.ts   # Main API client
│   │   └── config.ts       # Global settings
│   │
│   ├── features/           # Feature domains
│   │   ├── alerts/         # Alerts panel, views
│   │   ├── map/            # Map visualization views
│   │   ├── vessels/        # Vessel details
│   │   └── itdae/          # Specific ITDAE feature sets
│   │
│   ├── layouts/            # Page layouts and wrappers
│   │
│   ├── shared/             # Generic, reusable code
│   │   ├── components/     # UI components (WelcomePage, FileDropZone)
│   │   ├── hooks/          # Shared hooks (useWebSocket)
│   │   └── types/          # Types (common.ts)
│   │
│   ├── App.tsx             # Main application component
│   ├── main.tsx            # React entry point
│   └── index.css           # Global styles
│
├── public/                 # Static assets
├── package.json            # Node dependencies
├── vite.config.ts          # Vite build configuration
└── tsconfig.*.json         # TypeScript configurations
```text

## Data Directory (`data/`)
```text
data/
├── raw/                   # Input AIS files
│   ├── .gitkeep          # Keep directory in git
│   └── *.csv, *.dat, *.zst  # (gitignored)
└── processed/             # Processed outputs (future)
    └── .gitkeep
```text

## Key Files

### Configuration
- `backend/app/settings.py` - Backend configuration (thresholds, DB URL)
- `frontend/src/config.ts` - Frontend API base URL
- `docker-compose.yml` - Docker services (API + PostgreSQL)

### Entry Points
- `backend/app/main.py` - FastAPI application
- `frontend/src/main.tsx` - React application
- `backend/start.sh` - Local backend start script

### Database
- `backend/aegisais.db` - SQLite database (created automatically, gitignored)
- Docker uses PostgreSQL (configured in docker-compose.yml)

## File Organization Principles

1. **Separation of Concerns**
   - Backend: Python/FastAPI in `backend/app/`
   - Frontend: React/TypeScript in `frontend/src/`
   - Data: Input files in `data/raw/`

2. **Modular Structure**
   - API routes grouped by domain (`routes_*.py`)
   - Detection rules separate from pipeline logic
   - Components co-located with CSS

3. **Build Artifacts**
   - All build outputs gitignored (`.egg-info/`, `node_modules/`, `dist/`)
   - Database files gitignored
   - Log files gitignored

4. **Data Files**
   - Raw data in `data/raw/` (gitignored except `.gitkeep`)
   - Processed data in `data/processed/` (future use)
