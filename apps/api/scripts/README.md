## Utility Scripts

### `smoke_llm.py`

Runs a live smoke test against the configured LLM integration.

It checks:

- direct provider connectivity to the configured OpenAI-compatible endpoint
- in-app analyst provider status via `/v1/analyst/status`
- end-to-end analyst chat via `/v1/analyst/chat`

Usage:

```bash
cd apps/api
make smoke-llm
```

The script reads configuration from the local environment and never prints the API key.

# Scripts Directory

This directory contains utility scripts for AegisAIS.

## generate_demo_data.py

Generates demo AIS data files that showcase all detection rules.

### Usage

```bash
cd backend
python scripts/generate_demo_data.py
```

### What it does

Creates CSV files in `data/raw/` with sample AIS data that triggers:

- **TELEPORT** (Tier 1) - Impossible speed
- **TELEPORT_T2** (Tier 2) - Suspicious speed
- **TURN_RATE** (Tier 1) - Impossible turn rate
- **TURN_RATE_T2** (Tier 2) - Suspicious turn rate
- **POSITION_INVALID** - Invalid coordinates
- **ACCELERATION** - Impossible acceleration
- **HEADING_COG_CONSISTENCY** - Heading/COG mismatch
- **Normal track** - No alerts (baseline)

### Output Files

- `demo_comprehensive.csv` - All alert types in one file
- `demo_teleport_t1.csv` - TELEPORT Tier 1
- `demo_teleport_t2.csv` - TELEPORT Tier 2
- `demo_turn_rate_t1.csv` - TURN_RATE Tier 1
- `demo_turn_rate_t2.csv` - TURN_RATE Tier 2
- `demo_position_invalid.csv` - POSITION_INVALID
- `demo_acceleration.csv` - ACCELERATION
- `demo_heading_cog.csv` - HEADING_COG_CONSISTENCY
- `demo_normal.csv` - Normal track

### Customization

Edit the script to:

- Change vessel MMSIs
- Adjust anomaly severity
- Modify time gaps
- Add more test cases

See [DEMO_GUIDE.md](../../DEMO_GUIDE.md) for usage instructions.
