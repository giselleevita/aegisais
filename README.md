# AegisAIS

AIS Spoofing & Anomaly Detection (rules-first) with FastAPI.

## Setup

### Place Data Files

Place your AIS data files (`.csv`, `.dat`, or `.zst` compressed) in the `data/raw/` directory:

```bash
# Examples
cp your_data.csv.zst data/raw/
cp your_data.dat.zst data/raw/
cp your_data.csv data/raw/
cp your_data.dat data/raw/
```

**Supported formats:**
- `.csv` - Comma-delimited CSV files
- `.dat` - Tab or space-delimited data files
- `.csv.zst` - Compressed CSV files
- `.dat.zst` - Compressed DAT files

### Run (local, SQLite)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -U pip
pip install -e .
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

### Run with Docker

```bash
docker-compose up --build
```

## Usage

### Replay AIS Data

Start replaying a data file:

```bash
# Using curl
curl -X POST "http://localhost:8000/v1/replay/start?path=data/raw/your_file.dat.zst&speedup=100.0"

# Check status
curl http://localhost:8000/v1/replay/status

# Stop replay
curl -X POST http://localhost:8000/v1/replay/stop
```

**Note**: The `path` parameter should be relative to the application working directory. When running locally, use paths like `data/raw/filename.dat.zst` or `data/raw/filename.csv.zst`. When running in Docker, the `data/` directory is mounted, so use the same path format.

### Query Vessels

```bash
# List all vessels
curl http://localhost:8000/v1/vessels

# List vessels with alerts (severity >= 50)
curl "http://localhost:8000/v1/vessels?min_severity=50"
```

### Query Alerts

```bash
# List all alerts
curl http://localhost:8000/v1/alerts

# Filter alerts by MMSI
curl "http://localhost:8000/v1/alerts?mmsi=123456789"

# Filter by alert type
curl "http://localhost:8000/v1/alerts?alert_type=TELEPORT"

# Get alert statistics
curl http://localhost:8000/v1/alerts/stats/summary
```

### WebSocket Stream

Connect to the WebSocket endpoint for real-time updates:

```javascript
const ws = new WebSocket('ws://localhost:8000/v1/stream');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data);
};
```
