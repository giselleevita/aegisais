#!/bin/bash

# D-01 AISStream Configuration and Ingest Run Setup (UPDATED)
# Usage: bash setup_d01_ingest.sh <your_aisstream_api_key> [optional_bbox]
# This version properly integrates with Docker Compose environment

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/infra/docker/docker-compose.yml"

if [[ $# -lt 1 ]]; then
  echo "❌ Usage: bash setup_d01_ingest.sh <aisstream_api_key> [bbox]"
  echo ""
  echo "Example:"
  echo "  bash setup_d01_ingest.sh 'sk_live_your_key_here' '50.5,10.0,65.0,30.0'"
  exit 1
fi

AISSTREAM_KEY="$1"
AISSTREAM_BBOX="${2:-50.5,10.0,65.0,30.0}"

echo "🔧 D-01 AIS Ingest Setup"
echo "========================"
echo ""
echo "Configuration:"
echo "  Region: $AISSTREAM_BBOX"
echo "  API Key: ${AISSTREAM_KEY:0:20}***"
echo ""

# Step 1: Save .env.local for reference
echo "📝 Step 1: Saving configuration..."
mkdir -p "$REPO_ROOT/apps/api"
cat > "$REPO_ROOT/apps/api/.env.local" << EOF
# D-01 Live AIS Ingest Configuration (Generated: $(date))
AISSTREAM_API_KEY=$AISSTREAM_KEY
AISSTREAM_BBOX=$AISSTREAM_BBOX
EOF

echo "   ✅ Configuration saved"
echo ""

# Step 2: Stop any existing stack
echo "🐳 Step 2: Preparing Docker stack..."
cd "$REPO_ROOT"
docker compose -f "$COMPOSE_FILE" down 2>/dev/null || true
sleep 2

# Step 3: Start Docker stack with environment variables
echo "   Starting services..."

export AISSTREAM_API_KEY="$AISSTREAM_KEY"
export AISSTREAM_BBOX="$AISSTREAM_BBOX"

docker compose -f "$COMPOSE_FILE" up -d
sleep 10

echo "   ✅ Docker stack started"
echo ""

# Step 4: Verify containers are running
echo "🏥 Step 3: Verifying services..."
docker compose -f "$COMPOSE_FILE" ps

echo ""
echo "✅ Setup complete!"
echo ""
echo "📊 Next: Start monitoring in a separate terminal"
echo "   bash scripts/capture_d01_evidence.sh &"
echo ""
echo "🔗 Dashboards:"
echo "   - Grafana: http://localhost:3000 (admin/admin)"
echo "   - Prometheus: http://localhost:9090"
echo "   - API: https://localhost:443/docs"
echo ""
