#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

python3 -m json.tool data/demo/festival_cable_multisensor.json >/dev/null
python3 -m json.tool packages/contracts/schemas/Observation.schema.json >/dev/null
python3 -m json.tool apps/web/public/maps/baltic-land.geojson >/dev/null
test -f apps/web/public/maps/ATTRIBUTION.md
test "$(wc -c < apps/web/public/maps/baltic-land.geojson)" -lt 5242880

docker compose -f infra/docker/docker-compose.yml config --quiet

for service in api processing-worker persistence-worker observation-worker alert-worker db redis web; do
  docker compose -f infra/docker/docker-compose.yml config --services | rg -qx "$service"
done

if [[ -f data/models/isolation_forest.joblib && -f data/models/isolation_forest.manifest.json ]]; then
  python3 - <<'PY'
import hashlib, json
from pathlib import Path
manifest = json.loads(Path("data/models/isolation_forest.manifest.json").read_text())
actual = hashlib.sha256(Path("data/models/isolation_forest.joblib").read_bytes()).hexdigest()
if actual != manifest.get("artifact_sha256"):
    raise SystemExit("model artifact hash mismatch")
expected = [
    "speed_knots", "speed_std", "acceleration_knots_per_sec",
    "turn_rate_deg_per_sec", "course_entropy", "displacement_m",
    "loiter_ratio", "update_gap_sec", "prediction_residual_m",
    "distance_to_cable_m",
]
if manifest.get("feature_schema") != expected:
    raise SystemExit("model feature schema mismatch")
print(f"model: {manifest['model_version']} ({manifest['metrics'].get('validation')})")
PY
else
  echo "model: missing (rule fallback will work, but festival readiness fails)" >&2
  exit 1
fi

if docker compose -f infra/docker/docker-compose.yml ps --status running --services 2>/dev/null | grep -qx api; then
  docker compose -f infra/docker/docker-compose.yml exec -T api python - <<'PY'
import json, urllib.request
for endpoint in ("/v1/health", "/v1/health/ready"):
    with urllib.request.urlopen(f"http://127.0.0.1:8000{endpoint}", timeout=5) as response:
        payload = json.load(response)
        if payload.get("status") not in {"healthy", "ready"}:
            raise SystemExit(f"{endpoint}: {payload}")
print("api: healthy")
PY
fi

echo "Festival preflight passed."
