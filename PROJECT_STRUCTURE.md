# AegisAIS Project Structure

## Root Directory
```
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
```

## Backend Structure (`backend/`)
```
backend/
├── app/                    # Main application package
│   ├── __init__.py
│   ├── main.py            # FastAPI app entry point
│   ├── settings.py        # Configuration
│   ├── db.py              # Database setup
│   ├── models.py          # SQLAlchemy models
│   ├── schemas.py         # Pydantic schemas
│   ├── logging_config.py  # Logging setup
│   │
│   ├── api/               # API routes
│   │   ├── routes_alerts.py
│   │   ├── routes_tracks.py
│   │   ├── routes_upload.py
│   │   ├── routes_vessels.py
│   │   └── ws.py          # WebSocket handler
│   │
│   ├── detection/         # Alert detection rules
│   │   ├── rules.py       # Detection rules (Tier 1 & 2)
│   │   └── scoring.py     # (Future: scoring logic)
│   │
│   ├── ingest/            # Data ingestion
│   │   ├── loaders.py     # CSV/AIS point loaders
│   │   └── replay.py      # Replay engine
│   │
│   ├── services/          # Business logic
│   │   └── pipeline.py    # Point processing pipeline
│   │
│   └── tracking/          # Track management
│       ├── features.py    # Distance/speed calculations
│       └── track_store.py # Per-vessel track windows
│
├── pyproject.toml         # Python dependencies
├── Dockerfile             # Docker build config
├── start.sh              # Local dev start script
└── aegisais.db           # SQLite database (gitignored)
```

## Frontend Structure (`frontend/`)
```
frontend/
├── src/
│   ├── api/
│   │   └── client.ts      # API client
│   │
│   ├── components/        # React components
│   │   ├── AboutAegisAIS.tsx/css
│   │   ├── AlertsPanel.tsx/css
│   │   ├── Dashboard.tsx/css
│   │   ├── FileDropZone.tsx/css
│   │   ├── ReplayControls.tsx/css
│   │   └── VesselsPanel.tsx/css
│   │
│   ├── hooks/
│   │   └── useWebSocket.ts
│   │
│   ├── App.tsx/css        # Main app component
│   ├── main.tsx           # Entry point
│   ├── config.ts          # Configuration
│   └── index.css          # Global styles
│
├── public/
├── package.json
├── vite.config.ts
└── tsconfig.*.json
```

## Data Directory (`data/`)
```
data/
├── raw/                   # Input AIS files
│   ├── .gitkeep          # Keep directory in git
│   └── *.csv, *.dat, *.zst  # (gitignored)
└── processed/             # Processed outputs (future)
    └── .gitkeep
```

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
