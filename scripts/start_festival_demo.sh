#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

scripts/festival_preflight.sh
docker compose -f infra/docker/docker-compose.yml up --build -d \
  db redis api processing-worker persistence-worker observation-worker alert-worker bff web nginx
docker compose -f infra/docker/docker-compose.yml ps

echo "AegisAIS festival stack is starting. Open http://localhost:5174 after services become healthy."
