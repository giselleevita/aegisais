# AegisAIS API Documentation

## Base URL

```
http://localhost:8000
```

## Authentication

Currently, the API does not require authentication. For production deployments, consider adding API key authentication or OAuth2.

## Endpoints

### Health & Status

#### `GET /v1/health`
Basic health check.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-27T12:00:00.000000",
  "service": "AegisAIS"
}
```

#### `GET /v1/health/detailed`
Detailed health check including database connectivity.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-27T12:00:00.000000",
  "service": "AegisAIS",
  "database": {
    "connected": true,
    "error": null
  }
}
```

#### `GET /v1/metrics`
Get system metrics and statistics.

**Response:**
```json
{
  "timestamp": "2025-01-27T12:00:00.000000",
  "vessels": {
    "total": 150
  },
  "alerts": {
    "total": 1250,
    "by_status": {
      "new": 800,
      "reviewed": 300,
      "resolved": 100,
      "false_positive": 50
    }
  },
  "positions": {
    "total": 50000
  }
}
```

### Vessels

#### `GET /v1/vessels`
List all vessels with optional filtering.

**Query Parameters:**
- `min_severity` (int, optional): Minimum alert severity (0-100). Default: 0
- `limit` (int, optional): Maximum number of results (1-5000). Default: 500

**Response:**
```json
[
  {
    "mmsi": "123456789",
    "timestamp": "2025-01-27T12:00:00",
    "lat": 40.7128,
    "lon": -74.0060,
    "sog": 12.5,
    "cog": 45.0,
    "heading": 45.0,
    "last_alert_severity": 75
  }
]
```

#### `GET /v1/vessels/{mmsi}`
Get a specific vessel by MMSI.

**Path Parameters:**
- `mmsi` (string, required): Vessel MMSI (9 digits)

**Response:**
```json
{
  "mmsi": "123456789",
  "timestamp": "2025-01-27T12:00:00",
  "lat": 40.7128,
  "lon": -74.0060,
  "sog": 12.5,
  "cog": 45.0,
  "heading": 45.0,
  "last_alert_severity": 75
}
```

#### `GET /v1/vessels/{mmsi}/track`
Get historical track positions for a vessel.

**Path Parameters:**
- `mmsi` (string, required): Vessel MMSI (9 digits)

**Query Parameters:**
- `start_time` (datetime, optional): Start timestamp filter (ISO format)
- `end_time` (datetime, optional): End timestamp filter (ISO format)
- `limit` (int, optional): Maximum number of positions (1-10000). Default: 1000

**Response:**
```json
[
  {
    "id": 1,
    "mmsi": "123456789",
    "timestamp": "2025-01-27T12:00:00",
    "lat": 40.7128,
    "lon": -74.0060,
    "sog": 12.5,
    "cog": 45.0,
    "heading": 45.0
  }
]
```

### Alerts

#### `GET /v1/alerts`
List alerts with optional filtering.

**Query Parameters:**
- `mmsi` (string, optional): Filter by MMSI (9 digits)
- `alert_type` (string, optional): Filter by alert type (TELEPORT, TURN_RATE, etc.)
- `status` (string, optional): Filter by status (new, reviewed, resolved, false_positive)
- `min_severity` (int, optional): Minimum severity (0-100). Default: 0
- `max_severity` (int, optional): Maximum severity (0-100). Default: 100
- `start_time` (datetime, optional): Start timestamp filter (ISO format)
- `end_time` (datetime, optional): End timestamp filter (ISO format)
- `limit` (int, optional): Maximum number of results (1-1000). Default: 100
- `offset` (int, optional): Pagination offset. Default: 0

**Response:**
```json
[
  {
    "id": 1,
    "timestamp": "2025-01-27T12:00:00",
    "mmsi": "123456789",
    "type": "TELEPORT",
    "severity": 85,
    "summary": "Implied speed 120.5 kn exceeds threshold (short gap)",
    "evidence": {
      "dt_sec": 60,
      "distance_m": 1852,
      "implied_speed_kn": 120.5,
      "tier": "short"
    },
    "status": "new",
    "notes": null
  }
]
```

#### `GET /v1/alerts/{alert_id}`
Get a specific alert by ID.

**Path Parameters:**
- `alert_id` (int, required): Alert ID

**Response:**
```json
{
  "id": 1,
  "timestamp": "2025-01-27T12:00:00",
  "mmsi": "123456789",
  "type": "TELEPORT",
  "severity": 85,
  "summary": "Implied speed 120.5 kn exceeds threshold (short gap)",
  "evidence": {...},
  "status": "new",
  "notes": null
}
```

#### `PATCH /v1/alerts/{alert_id}/status`
Update alert status and/or notes.

**Path Parameters:**
- `alert_id` (int, required): Alert ID

**Request Body:**
```json
{
  "status": "reviewed",
  "notes": "Investigated - confirmed data error"
}
```

**Response:**
Updated alert object.

#### `GET /v1/alerts/stats/summary`
Get alert statistics.

**Query Parameters:**
- `start_time` (datetime, optional): Start timestamp filter (ISO format)
- `end_time` (datetime, optional): End timestamp filter (ISO format)

**Response:**
```json
{
  "total": 1250,
  "by_type": {
    "TELEPORT": 500,
    "TURN_RATE": 300,
    "POSITION_INVALID": 200,
    "ACCELERATION": 150,
    "HEADING_COG_CONSISTENCY": 100
  },
  "average_severity": 65.5,
  "by_severity_range": {
    "high": 400,
    "medium": 500,
    "low": 350
  }
}
```

#### `GET /v1/alerts/export/csv`
Export alerts as CSV.

**Query Parameters:** Same as `GET /v1/alerts`

**Response:** CSV file download

#### `GET /v1/alerts/export/json`
Export alerts as JSON.

**Query Parameters:** Same as `GET /v1/alerts`

**Response:** JSON file download

### Replay Control

#### `POST /v1/replay/start`
Start replaying AIS data from a file.

**Query Parameters:**
- `path` (string, required): Server-side path to data file
- `speedup` (float, optional): Replay speed multiplier (≥0.1). Default: 100.0
- `use_streaming` (bool, optional): Use streaming mode. Default: true
- `batch_size` (int, optional): Batch size for commits (1-10000). Default: 100

**Response:**
```json
{
  "status": "started",
  "path": "data/raw/file.csv.zst",
  "speedup": 100.0,
  "streaming": true,
  "batch_size": 100
}
```

#### `POST /v1/replay/stop`
Stop the current replay.

**Response:**
```json
{
  "status": "stopping"
}
```

#### `GET /v1/replay/status`
Get current replay status.

**Response:**
```json
{
  "running": true,
  "processed": 50000,
  "last_timestamp": "2025-01-27T12:00:00",
  "stop_requested": false
}
```

### File Upload

#### `POST /v1/upload`
Upload a file to the data/raw directory.

**Request:** Multipart form data with `file` field

**Supported formats:**
- `.csv` - Comma-delimited CSV
- `.dat` - Tab or space-delimited
- `.csv.zst` - Compressed CSV
- `.dat.zst` - Compressed DAT

**File size limit:** 5GB

**Response:**
```json
{
  "status": "success",
  "filename": "data.csv.zst",
  "path": "data/raw/data.csv.zst",
  "size_bytes": 1048576,
  "size_mb": 1.0
}
```

#### `GET /v1/upload/list`
List all uploaded files.

**Response:**
```json
{
  "files": [
    {
      "filename": "data.csv.zst",
      "path": "data/raw/data.csv.zst",
      "size_bytes": 1048576,
      "size_mb": 1.0
    }
  ]
}
```

### WebSocket Stream

#### `WS /v1/stream`
WebSocket endpoint for real-time updates.

**Message Types:**

1. **Alert:**
```json
{
  "kind": "alert",
  "data": {
    "id": 1,
    "timestamp": "2025-01-27T12:00:00",
    "mmsi": "123456789",
    "type": "TELEPORT",
    "severity": 85,
    "summary": "...",
    "evidence": {...}
  }
}
```

2. **Progress Tick:**
```json
{
  "kind": "tick",
  "processed": 50000
}
```

3. **Error:**
```json
{
  "kind": "error",
  "message": "Error description"
}
```

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request
```json
{
  "detail": "Error description"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 429 Too Many Requests
```json
{
  "detail": "Rate limit exceeded: 100 requests per 60 seconds"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

## Rate Limiting

API endpoints are rate-limited to prevent abuse:
- Default: 100 requests per 60 seconds per IP address
- Rate limit headers are included in responses

## Data Formats

### Timestamps
All timestamps are in ISO 8601 format: `YYYY-MM-DDTHH:MM:SS[.ffffff]`

### Coordinates
- Latitude: -90 to 90 degrees
- Longitude: -180 to 180 degrees

### MMSI
- Format: Exactly 9 digits
- Example: `123456789`

### Alert Types
- `TELEPORT` - Tier 1 teleportation detection
- `TELEPORT_T2` - Tier 2 suspicious teleportation
- `TURN_RATE` - Tier 1 turn rate violation
- `TURN_RATE_T2` - Tier 2 suspicious turn rate
- `POSITION_INVALID` - Invalid position
- `ACCELERATION` - Acceleration/SOG mismatch
- `HEADING_COG_CONSISTENCY` - Heading/COG inconsistency

### Alert Status
- `new` - New, unprocessed alert
- `reviewed` - Alert has been reviewed
- `resolved` - Alert has been resolved
- `false_positive` - Alert marked as false positive

## OpenAPI Documentation

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Examples

### Upload and Process File

```bash
# 1. Upload file
curl -X POST "http://localhost:8000/v1/upload" \
  -F "file=@data.csv.zst"

# 2. Start replay
curl -X POST "http://localhost:8000/v1/replay/start?path=data/raw/data.csv.zst&speedup=100.0"

# 3. Check status
curl "http://localhost:8000/v1/replay/status"

# 4. Get alerts
curl "http://localhost:8000/v1/alerts?limit=10"
```

### Filter and Export Alerts

```bash
# Get high-severity alerts from last 24 hours
curl "http://localhost:8000/v1/alerts?min_severity=70&start_time=2025-01-26T12:00:00"

# Export as CSV
curl "http://localhost:8000/v1/alerts/export/csv?min_severity=70" -o alerts.csv

# Export as JSON
curl "http://localhost:8000/v1/alerts/export/json?alert_type=TELEPORT" -o alerts.json
```

### Get Vessel Track

```bash
# Get track for specific vessel
curl "http://localhost:8000/v1/vessels/123456789/track?limit=1000"

# Get track for time range
curl "http://localhost:8000/v1/vessels/123456789/track?start_time=2025-01-27T00:00:00&end_time=2025-01-27T23:59:59"
```
