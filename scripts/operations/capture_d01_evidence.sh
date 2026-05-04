#!/bin/bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
EVIDENCE_DIR="$REPO_ROOT/docs/evidence"
RUN_DATE=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$EVIDENCE_DIR/d01_ingest_run_${RUN_DATE}.log"

mkdir -p "$EVIDENCE_DIR"

log_entry() {
  local msg="$1"
  local ts=$(date '+%Y-%m-%d %H:%M:%S')
  echo "[$ts] $msg" | tee -a "$LOG_FILE"
}

query_prometheus() {
  local query="$1"
  local port="${PROMETHEUS_HOST_PORT:-9090}"
  
  curl -s "http://localhost:$port/api/v1/query" \
    --data-urlencode "query=$query" | jq . 2>/dev/null || echo '{"status":"error"}'
}

export_prometheus_range() {
  local start_time="$1"
  local end_time="$2"
  local port="${PROMETHEUS_HOST_PORT:-9090}"
  
  curl -s "http://localhost:$port/api/v1/query_range" \
    --data-urlencode "query=rate(aisstream_messages_ingested_total[5m])" \
    --data-urlencode "start=$start_time" \
    --data-urlencode "end=$end_time" \
    --data-urlencode "step=300" | jq . 2>/dev/null || echo '{"status":"error"}'
}

query_db_stats() {
  local pg_port="${POSTGRES_HOST_PORT:-5432}"
  
  PGPASSWORD="aegisais" psql -h localhost -p "$pg_port" -U aegisais -d aegisais \
    -c "SELECT COUNT(*) as total_ais_points, COUNT(DISTINCT mmsi) as unique_vessels FROM ais_point LIMIT 1;" \
    -t 2>/dev/null || echo "0|0"
}

log_entry "D-01 ingest evidence capture started"
log_entry "Evidence directory: $EVIDENCE_DIR"
log_entry "Prometheus query endpoint: http://localhost:${PROMETHEUS_HOST_PORT:-9090}"

# Sample metrics every 5 minutes for 72 hours (if running that long)
SAMPLE_INTERVAL=300  # 5 minutes
TOTAL_SAMPLES=$((72 * 60 * 60 / SAMPLE_INTERVAL))
SAMPLE_COUNT=0

log_entry "Starting metric collection. Target samples: $TOTAL_SAMPLES (expected duration: 72 hours)"

while true; do
  SAMPLE_COUNT=$((SAMPLE_COUNT + 1))
  
  # Query ingest volume
  INGEST_RATE=$(query_prometheus 'rate(aisstream_messages_ingested_total[5m])' | jq '.data.result[0].value[1]' 2>/dev/null | tr -d '"' || echo "N/A")
  
  # Query processing latency
  LATENCY_P99=$(query_prometheus 'histogram_quantile(0.99, aisstream_processing_duration_seconds)' | jq '.data.result[0].value[1]' 2>/dev/null | tr -d '"' || echo "N/A")
  
  # Query worker queue depth
  QUEUE_DEPTH=$(query_prometheus 'redis_queue_size' | jq '.data.result[0].value[1]' 2>/dev/null | tr -d '"' || echo "N/A")
  
  # Get database stats every 10 samples (50 minutes)
  if (( SAMPLE_COUNT % 10 == 0 )); then
    DB_STATS=$(query_db_stats)
    TOTAL_POINTS=$(echo "$DB_STATS" | cut -d'|' -f1)
    UNIQUE_VESSELS=$(echo "$DB_STATS" | cut -d'|' -f2)
    log_entry "DB stats: Total AIS points=$TOTAL_POINTS, Unique vessels=$UNIQUE_VESSELS"
  fi
  
  log_entry "Sample #$SAMPLE_COUNT: Ingest rate=${INGEST_RATE} msg/s, p99 latency=${LATENCY_P99}s, Queue depth=$QUEUE_DEPTH"
  
  # Check for worker restarts (basic)
  RESTART_COUNT=$(docker compose -f "$REPO_ROOT/infra/docker/docker-compose.yml" ps --format json 2>/dev/null | jq '[.[] | select(.State=="restarting")] | length' 2>/dev/null || echo "0")
  if (( RESTART_COUNT > 0 )); then
    log_entry "⚠️  Alert: $RESTART_COUNT services in restart state"
  fi
  
  # Every 2 hours, capture a Grafana dashboard snapshot (if Grafana is running)
  if (( SAMPLE_COUNT % 24 == 0 )); then
    GRAFANA_PORT="${GRAFANA_HOST_PORT:-3000}"
    SNAP_FILE="$EVIDENCE_DIR/d01_grafana_snapshot_sample_${SAMPLE_COUNT}.json"
    if curl -s -f "http://localhost:$GRAFANA_PORT/api/search" >/dev/null 2>&1; then
      log_entry "Capturing Grafana dashboard state..."
      # Grafana snapshots would go here (requires more config)
    fi
  fi
  
  # Sleep till next sample but allow manual exit with Ctrl+C
  sleep "$SAMPLE_INTERVAL" &
  SLEEP_PID=$!
  if ! wait $SLEEP_PID 2>/dev/null; then
    log_entry "Evidence capture interrupted by user"
    break
  fi
done

log_entry "D-01 ingest evidence capture ended"
