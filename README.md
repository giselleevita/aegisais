# AegisAIS

**AIS Data Integrity and Anomaly Detection Tool**

AegisAIS is an automated data integrity checker for Automatic Identification System (AIS) maritime data. It ingests AIS position reports, maintains track history per vessel, and automatically detects physically impossible or internally inconsistent data patterns.

## 🚀 Features

- **Real-time Processing**: Process AIS data files with streaming support for large datasets
- **Anomaly Detection**: 7 detection rules covering teleportation, turn rates, position validity, acceleration, and heading/COG consistency
- **Tiered Alert System**: Tier 1 (integrity violations) and Tier 2 (suspicious behavior) alerts with severity scoring
- **Interactive Map**: Visualize vessel positions, alerts, and tracks on an interactive map
- **Track History**: View historical vessel positions and tracks
- **Alert Management**: Update alert status, add notes, filter, and export alerts
- **Onboarding & Demo**: Interactive tour and demo mode for new users

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Installation](#installation)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [Development](#development)
- [Testing](#testing)
- [Deployment](#deployment)

## 🏃 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20.19+
- PostgreSQL (optional, SQLite works for small datasets)

### Local Development

```bash
# 1. Clone the repository
git clone https://github.com/giselleevita/aegisais.git
cd aegisais

# 2. Backend setup
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -U pip
pip install -e .

# 3. Run database migrations
alembic upgrade head

# 4. Start backend
uvicorn app.main:app --reload

# 5. Frontend setup (in new terminal)
cd ../frontend
npm install
npm run dev
```

The application will be available at:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Docker

```bash
docker-compose up --build
```

## 📦 Installation

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .
alembic upgrade head
```

### Frontend

```bash
cd frontend
npm install
```

## 💻 Usage

### 1. Upload AIS Data

Place your AIS data files in `data/raw/` or upload via the web interface.

**Supported formats:**
- `.csv` - Comma-delimited CSV
- `.dat` - Tab or space-delimited
- `.csv.zst` - Compressed CSV
- `.dat.zst` - Compressed DAT

**Required columns:**
- `mmsi` (or `MMSI`)
- `timestamp` (or `base_date_time`, `time`, etc.)
- `lat` (or `latitude`)
- `lon` (or `longitude`)
- Optional: `sog`, `cog`, `heading`

### 2. Process Data

The system automatically starts processing when you upload a file. You can also start manually:

```bash
curl -X POST "http://localhost:8000/v1/replay/start?path=data/raw/file.csv.zst&speedup=100.0"
```

### 3. View Results

- **Dashboard**: See processing progress and statistics
- **Alerts**: Filter and manage detected anomalies
- **Vessels**: Browse tracked vessels
- **Map**: Visualize positions and tracks

## 📚 API Documentation

Comprehensive API documentation is available at:
- **Interactive Docs**: http://localhost:8000/docs (Swagger UI)
- **ReDoc**: http://localhost:8000/redoc
- **API Guide**: See [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)

### Key Endpoints

- `GET /v1/health` - Health check
- `GET /v1/metrics` - System metrics
- `GET /v1/vessels` - List vessels
- `GET /v1/vessels/{mmsi}/track` - Get vessel track
- `GET /v1/alerts` - List alerts (with filtering)
- `PATCH /v1/alerts/{id}/status` - Update alert status
- `GET /v1/alerts/export/csv` - Export alerts as CSV
- `POST /v1/upload` - Upload file
- `POST /v1/replay/start` - Start replay
- `WS /v1/stream` - WebSocket for real-time updates

## 🏗️ Architecture

### Backend

```
backend/app/
├── api/              # FastAPI routes
│   ├── routes_alerts.py
│   ├── routes_vessels.py
│   ├── routes_tracks.py
│   ├── routes_upload.py
│   ├── routes_health.py
│   └── ws.py
├── detection/        # Detection rules
│   ├── rules.py      # 7 detection rules
│   └── scoring.py
├── ingest/           # Data loading
│   ├── loaders.py    # CSV/DAT/ZST loading
│   └── replay.py     # Replay engine
├── services/         # Business logic
│   ├── pipeline.py   # Main processing pipeline
│   └── cleanup.py    # Maintenance tasks
├── tracking/         # Track management
│   ├── track_store.py
│   └── features.py   # Distance, speed calculations
├── models.py         # SQLAlchemy models
├── schemas.py        # Pydantic schemas
└── settings.py       # Configuration
```

### Frontend

```
frontend/src/
├── api/              # API client
├── components/        # React components
│   ├── Dashboard.tsx
│   ├── AlertsPanel.tsx
│   ├── VesselsPanel.tsx
│   ├── MapView.tsx
│   ├── VesselDetails.tsx
│   ├── Onboarding.tsx
│   └── ...
├── hooks/            # Custom hooks
│   └── useWebSocket.ts
├── types/            # TypeScript types
└── config.ts         # Configuration
```

## ⚙️ Configuration

### Environment Variables

**Backend:**
- `DATABASE_URL` - Database connection string (default: `sqlite:///./aegisais.db`)
- `LOG_LEVEL` - Logging level (default: `INFO`)

**Frontend:**
- `VITE_API_BASE_URL` - Backend API URL (default: `http://localhost:8000`)

### Detection Thresholds

Configure detection thresholds in `backend/app/settings.py`:

```python
# Teleport detection
teleport_speed_knots_short = 60.0      # For gaps ≤ 120s
teleport_speed_knots_medium = 100.0   # For gaps 120s-30min

# Turn rate detection
max_turn_rate_deg_per_sec = 3.0
min_speed_for_turn_check_knots = 10.0

# Cooldown
alert_cooldown_sec = 300  # 5 minutes
```

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest tests/ -v

# Frontend linting
cd frontend
npm run lint
```

## 🚢 Deployment

### Production Checklist

- [ ] Use PostgreSQL for database
- [ ] Set up proper logging
- [ ] Configure CORS for production domain
- [ ] Add authentication/authorization
- [ ] Set up monitoring and alerting
- [ ] Configure rate limiting
- [ ] Set up backup strategy
- [ ] Use environment variables for secrets

### Docker Deployment

```bash
docker-compose up -d
```

See [docker-compose.yml](./docker-compose.yml) for configuration.

## 📖 Documentation

- [API Documentation](./API_DOCUMENTATION.md) - Complete API reference
- [Migration Guide](./backend/MIGRATION_GUIDE.md) - Database migrations
- [Large Dataset Guide](./LARGE_DATASET_GUIDE.md) - Performance optimization
- [Code Quality](./CODE_QUALITY.md) - Code standards and best practices
- [Project Structure](./PROJECT_STRUCTURE.md) - File organization

## 🐛 Troubleshooting

### Common Issues

**"File not found" error:**
- Ensure file is in `data/raw/` directory
- Check file path is relative to project root

**"No alerts found":**
- Check detection thresholds in settings
- Verify data has anomalies (test with known bad data)
- Check logs for rule evaluation details

**Database errors:**
- Run migrations: `alembic upgrade head`
- Check database permissions
- Verify `DATABASE_URL` is correct

## 🤝 Contributing

1. Follow code quality standards (see [CODE_QUALITY.md](./CODE_QUALITY.md))
2. Add tests for new features
3. Update documentation
4. Ensure TypeScript/Python types are correct

## 📄 License

[Add your license here]

## 🙏 Acknowledgments

Built for AIS data integrity analysis and anomaly detection.
