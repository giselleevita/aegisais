# Demo Files Guide

This guide explains how to use the demo files to showcase all AegisAIS functionalities.

## 📁 Demo Files

The demo files are located in `data/raw/` and demonstrate different alert types:

### Comprehensive Demo

- **`demo_comprehensive.csv`** - Contains all alert types in one file
  - Best for: Quick demonstration of all features
  - Expected alerts: 7+ alerts (one of each type)

### Individual Alert Type Demos

#### Tier 1 (Integrity Violations)

1. **`demo_teleport_t1.csv`** - TELEPORT Tier 1
   - **What it demonstrates**: Vessel appears to move impossibly fast
   - **Expected alert**: `TELEPORT` (severity: 85-95)
   - **Scenario**: Vessel moves 157 km in 60 seconds (implied speed ~200 knots)
   - **MMSI**: 200000001

2. **`demo_turn_rate_t1.csv`** - TURN_RATE Tier 1
   - **What it demonstrates**: Impossible turn rate at high speed
   - **Expected alert**: `TURN_RATE` (severity: 80-90)
   - **Scenario**: Vessel turns 60° in 10 seconds at 25 knots (6°/s)
   - **MMSI**: 300000001

#### Tier 2 (Suspicious Behavior)

3. **`demo_teleport_t2.csv`** - TELEPORT Tier 2
   - **What it demonstrates**: Suspicious but not impossible movement
   - **Expected alert**: `TELEPORT_T2` (severity: 50-70)
   - **Scenario**: Vessel moves 41 km in 300 seconds (implied speed ~50 knots)
   - **MMSI**: 200000002

4. **`demo_turn_rate_t2.csv`** - TURN_RATE Tier 2
   - **What it demonstrates**: Suspicious turn rate
   - **Expected alert**: `TURN_RATE_T2` (severity: 40-60)
   - **Scenario**: Vessel turns 30° in 20 seconds at 15 knots (1.5°/s)
   - **MMSI**: 300000002

#### Data Quality Issues

5. **`demo_position_invalid.csv`** - POSITION_INVALID
   - **What it demonstrates**: Invalid coordinate values
   - **Expected alert**: `POSITION_INVALID` (severity: 70-80)
   - **Scenario**: Latitude > 90° (invalid)
   - **MMSI**: 400000001

6. **`demo_acceleration.csv`** - ACCELERATION
   - **What it demonstrates**: Impossible acceleration
   - **Expected alert**: `ACCELERATION` (severity: 75-85)
   - **Scenario**: Speed increases from 5 to 50 knots in 10 seconds
   - **MMSI**: 500000001

7. **`demo_heading_cog.csv`** - HEADING_COG_CONSISTENCY
   - **What it demonstrates**: Heading and COG inconsistency
   - **Expected alert**: `HEADING_COG_CONSISTENCY` (severity: 70-80)
   - **Scenario**: Heading (180°) and COG (0°) differ by 180° at high speed
   - **MMSI**: 600000001

#### Normal Track

8. **`demo_normal.csv`** - Normal Vessel Track
   - **What it demonstrates**: Normal vessel behavior (no alerts)
   - **Expected alerts**: None
   - **Scenario**: Vessel moves normally at 12 knots
   - **MMSI**: 100000001

## 🚀 How to Use

### Option 1: Web Interface (Recommended)

1. **Start the application:**

   ```bash
   # Backend
   cd apps/api
   source .venv/bin/activate
   uvicorn app.main:app --reload

   # Frontend (new terminal)
   cd apps/web
   npm run dev
   ```

2. **Upload a demo file:**
   - Go to http://localhost:5173
   - Click "Upload File" or drag & drop
   - Select one of the demo files from `data/raw/`
   - The replay will start automatically

3. **View results:**
   - **Dashboard**: See processing progress
   - **Alerts**: View detected anomalies
   - **Vessels**: Browse tracked vessels
   - **Map**: Visualize positions and tracks

### Option 2: API (Command Line)

```bash
# 1. Upload file
curl -X POST "http://localhost:8000/v1/upload" \
  -F "file=@data/raw/demo_comprehensive.csv"

# 2. Start replay (if not automatic)
curl -X POST "http://localhost:8000/v1/replay/start?path=data/raw/demo_comprehensive.csv&speedup=100.0"

# 3. Check status
curl "http://localhost:8000/v1/replay/status"

# 4. View alerts
curl "http://localhost:8000/v1/alerts?limit=20"

# 5. Get alert statistics
curl "http://localhost:8000/v1/alerts/stats/summary"
```

### Option 3: Demo Mode

1. Go to the **Home** page
2. Click **"Start Demo Mode"**
3. Select a demo file from the list
4. Click **"Start Replay"**

## 📊 Expected Results

### demo_comprehensive.csv

After processing, you should see:

- **7+ alerts** of different types
- **8 vessels** tracked
- **Alert types**:
  - `TELEPORT` (Tier 1)
  - `TELEPORT_T2` (Tier 2)
  - `TURN_RATE` (Tier 1)
  - `TURN_RATE_T2` (Tier 2)
  - `POSITION_INVALID`
  - `ACCELERATION`
  - `HEADING_COG_CONSISTENCY`

### Individual Demo Files

Each file should produce **1 alert** of the corresponding type.

## 🔍 Verifying Results

### Check Alerts by Type

```bash
# TELEPORT alerts
curl "http://localhost:8000/v1/alerts?alert_type=TELEPORT"

# TURN_RATE alerts
curl "http://localhost:8000/v1/alerts?alert_type=TURN_RATE"

# All Tier 2 alerts
curl "http://localhost:8000/v1/alerts?alert_type=TELEPORT_T2"
curl "http://localhost:8000/v1/alerts?alert_type=TURN_RATE_T2"
```

### View Alert Details

```bash
# Get specific alert
curl "http://localhost:8000/v1/alerts/1"

# Export alerts
curl "http://localhost:8000/v1/alerts/export/csv" -o alerts.csv
```

### View Vessel Tracks

```bash
# Get track for a vessel
curl "http://localhost:8000/v1/vessels/200000001/track"
```

## 🎯 Demo Scenarios

### Scenario 1: Quick Overview

1. Upload `demo_comprehensive.csv`
2. Wait for processing
3. View Dashboard for statistics
4. Check Alerts page
5. View Map to see positions

### Scenario 2: Alert Type Deep Dive

1. Upload `demo_teleport_t1.csv`
2. View the TELEPORT alert
3. Check evidence (distance, speed, time gap)
4. Upload `demo_teleport_t2.csv`
5. Compare Tier 1 vs Tier 2 alerts

### Scenario 3: Alert Management

1. Upload `demo_comprehensive.csv`
2. Filter alerts by type
3. Update alert status (reviewed, resolved, false_positive)
4. Add notes to alerts
5. Export alerts as CSV/JSON

### Scenario 4: Vessel Tracking

1. Upload `demo_comprehensive.csv`
2. Click on a vessel in Vessels panel
3. View vessel details
4. See vessel track on map
5. View vessel's alerts

## 📝 Regenerating Demo Files

If you need to regenerate the demo files:

```bash
cd apps/api
python scripts/generate_demo_data.py
```

This will create all demo files in `data/raw/`.

## 🐛 Troubleshooting

### No Alerts Generated

- **Check thresholds**: Review `backend/app/settings.py` for detection thresholds
- **Check logs**: Look for rule evaluation details in backend logs
- **Verify data**: Ensure demo files are in `data/raw/` directory

### Alerts Not Showing in UI

- **Refresh page**: Alerts may take a moment to appear
- **Check filters**: Ensure no filters are applied
- **Check WebSocket**: Verify connection status (should show "Connected")

### Processing Too Slow

- **Increase speedup**: Use higher `speedup` parameter (e.g., 1000.0)
- **Use streaming**: Ensure `use_streaming=true` for large files

## 📚 Related Documentation

- [API Documentation](./API_DOCUMENTATION.md) - Complete API reference
- [README](./README.md) - Setup and usage guide
- [Large Dataset Guide](./LARGE_DATASET_GUIDE.md) - Performance tips

## 🎓 Learning Objectives

After using the demo files, you should understand:

1. **Alert Types**: All 7 detection rules and their triggers
2. **Tier System**: Difference between Tier 1 (integrity) and Tier 2 (suspicious)
3. **Severity Scoring**: How alerts are scored (0-100)
4. **Evidence**: What data is captured for each alert type
5. **Track History**: How vessel positions are stored and visualized
6. **Alert Management**: How to review, resolve, and export alerts

## 💡 Tips

- Start with `demo_comprehensive.csv` for a quick overview
- Use individual files to understand specific alert types
- Compare Tier 1 vs Tier 2 alerts to understand severity differences
- Use the Map view to visualize vessel movements
- Export alerts to analyze patterns in spreadsheet tools

---

## 🪝 Wedge Feature: Low-Friction Onboarding (BL-012)

The wedge feature lets a new customer get value from AegisAIS without a full
AIS-feed migration. Sales teams can demo the core value proposition — explainable
anomaly alerts with full evidence dossiers — in under 30 minutes using a
competitor export file.

### Onboarding Flow (< 30 minutes)

| Step | Action                                                                                                     | Time     |
| ---- | ---------------------------------------------------------------------------------------------------------- | -------- |
| 1    | Export historical track CSV from current tool (MarineTraffic, VesselFinder, FleetMon, or generic NMEA CSV) | 2 min    |
| 2    | Upload via **Import → Competitor Import** in the UI (or `POST /v1/import/competitor`)                      | 1 min    |
| 3    | Review the migration validation report: confidence score, row counts, drift summary                        | 2 min    |
| 4    | The pipeline re-runs detection rules over imported data; alerts appear in the Alerts panel                 | 5–15 min |
| 5    | Analyst reviews explainable alert dossiers with evidence hashes                                            | ongoing  |

### Import API (BL-011)

```bash
# Import a MarineTraffic CSV export
curl -X POST "http://localhost:8000/v1/import/competitor" \
  -F "file=@vessel_history.csv" \
  -F "format=marine_traffic"

# Response: migration validation report
# {
#   "format": "marine_traffic",
#   "total_rows": 5000,
#   "imported_rows": 4890,
#   "failed_rows": 110,
#   "confidence_score": 0.978,
#   "missing_position": 12,
#   "missing_timestamp": 45,
#   "duplicate_track_keys": 53,
#   "invalid_mmsi": 0
# }
```

Supported `format` values: `marine_traffic`, `vessel_finder`, `fleet_mon`, `generic_nmea`.

### Explainable Alert Dossier

Every alert surfaces a machine-verifiable **evidence hash** (SHA-256 of the slim
evidence payload). Analysts can reproduce the detection decision from the
persisted evidence without re-running the pipeline:

```bash
# Retrieve an alert with its evidence dossier
curl "http://localhost:8000/v1/alerts/42"
# {
#   "id": 42,
#   "type": "TELEPORT",
#   "severity": 90,
#   "evidence": { "dt_sec": 45, "distance_m": 95000, "implied_speed_kn": 1226 },
#   "evidence_hash": "5a3f...c4b1",  ← immutable SHA-256 fingerprint (BL-009)
#   "idempotency_key": "e7d9...a1f2" ← replay-safe dedup key (BL-003)
# }
```

### Export Portability Guarantees

AegisAIS data is never locked in. All exports are in open formats:

| Endpoint                       | Format       | Notes                                    |
| ------------------------------ | ------------ | ---------------------------------------- |
| `GET /v1/alerts/export/csv`    | RFC 4180 CSV | All alert fields including evidence_hash |
| `GET /v1/alerts/export/json`   | JSON Lines   | One object per line; stream-safe         |
| `GET /v1/incidents/export/csv` | RFC 4180 CSV | Incident + linked alert reference        |

Evidence hashes enable customers to verify that exported records match what the
system persisted — no vendor lock-in and full forensic traceability.

### Migration Overlap Support

Customers can run AegisAIS **alongside** their existing system during an
evaluation period:

1. Feed AIS data to both systems simultaneously.
2. Use `GET /v1/alerts?start_time=T1&end_time=T2` to compare alert coverage.
3. Use the competitor import adapter to re-process historical data through
   AegisAIS detection rules for a retrospective quality comparison.
4. When confidence is high, point-in-time cutover with zero data loss.

---

## 📊 Mission KPI Measurement (BL-017)

Use the following queries to measure mission KPIs over a pilot window. All queries assume the API is running and the test database is populated.

### Detection Lead-Time

```bash
# Retrieve alerts from the last 30 days with creation timestamps
curl "http://localhost:8000/v1/alerts?limit=500" | \
  python3 -c "
import json, sys
alerts = json.load(sys.stdin)
deltas = []
for a in alerts:
    if a.get('created_at') and a.get('evidence', {}).get('event_time'):
        from datetime import datetime
        created = datetime.fromisoformat(a['created_at'].replace('Z', '+00:00'))
        event = datetime.fromisoformat(a['evidence']['event_time'].replace('Z', '+00:00'))
        deltas.append((created - event).total_seconds() / 60)
if deltas:
    deltas.sort()
    median = deltas[len(deltas)//2]
    print(f'Median detection lead-time: {median:.1f} min (n={len(deltas)})')
    print(f'Target: < 2 min | Baseline: ~22 min')
"
```

### False Alert Precision

```bash
# Count alerts by status to compute precision
curl "http://localhost:8000/v1/alerts/stats/summary" | \
  python3 -c "
import json, sys
stats = json.load(sys.stdin)
total = stats.get('total', 0)
false_pos = stats.get('by_status', {}).get('false_positive', 0)
if total > 0:
    precision = 1 - (false_pos / total)
    print(f'False alert precision: {precision:.2f} ({false_pos} of {total} marked non-actionable)')
    print(f'Target: >= 0.85 | Baseline: ~0.55')
"
```

### Data Migration Confidence

```bash
# Import a sample competitor CSV and check the validation report
curl -s -X POST "http://localhost:8000/v1/import/competitor" \
  -F "file=@data/raw/demo_comprehensive.csv" \
  -F "format=generic_nmea" | \
  python3 -c "
import json, sys
report = json.load(sys.stdin)
print(f'Confidence score: {report.get(\"confidence_score\", 0):.3f}')
print(f'Imported: {report.get(\"imported_rows\", 0)} / {report.get(\"total_rows\", 0)} rows')
print(f'Target: >= 0.90')
"
```

### KPI Baseline Reference

| KPI                       | Baseline | Target   | Measurement                                    |
| ------------------------- | -------- | -------- | ---------------------------------------------- |
| Detection lead-time       | ~22 min  | < 2 min  | `created_at` − `event_time` (median)           |
| False alert precision     | ~0.55    | ≥ 0.85   | 1 − (false_positive / total alerts reviewed)   |
| Analyst time per incident | ~3 h     | ≤ 45 min | `resolved_at` − `created_at` (median, sampled) |
| Migration confidence      | N/A      | ≥ 0.90   | `CompetitorMigrationReport.confidence_score`   |
| System availability       | N/A      | ≥ 99.5%  | Prometheus `up{job="api"}` (30-day window)     |

Full pilot evidence template and baseline rationale: `docs/funding/FUNDING_PILOT_EVIDENCE_TEMPLATE.md`
