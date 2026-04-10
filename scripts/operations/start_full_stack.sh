#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/infra/docker/docker-compose.yml"
NGINX_CERT_DIR="$ROOT_DIR/infra/docker/nginx/certs"

pick_port() {
  local var_name="$1"
  shift

  if [[ -n "${!var_name:-}" ]]; then
    export "$var_name=${!var_name}"
    return 0
  fi

  local candidate
  for candidate in "$@"; do
    if ! lsof -nP -iTCP:"$candidate" -sTCP:LISTEN >/dev/null 2>&1; then
      export "$var_name=$candidate"
      return 0
    fi
  done

  echo "Unable to find an available port for $var_name" >&2
  return 1
}

ensure_dev_tls_certs() {
  local cert_file="$NGINX_CERT_DIR/cert.pem"
  local key_file="$NGINX_CERT_DIR/key.pem"

  if [[ -f "$cert_file" && -f "$key_file" ]]; then
    return 0
  fi

  if ! command -v openssl >/dev/null 2>&1; then
    echo "openssl is required to generate local TLS certificates for nginx" >&2
    return 1
  fi

  mkdir -p "$NGINX_CERT_DIR"
  echo "Generating self-signed development TLS certificate for nginx..."
  openssl req -x509 -nodes -newkey rsa:4096 \
    -keyout "$key_file" \
    -out "$cert_file" \
    -days 365 \
    -subj "/CN=localhost" >/dev/null 2>&1
}

pick_port POSTGRES_HOST_PORT 5432 5433 55432
pick_port REDIS_HOST_PORT 6379 6380 56379
pick_port BFF_HOST_PORT 8081 18081 28081
pick_port WEB_HOST_PORT 5174 4174 35174
pick_port NGINX_HTTP_HOST_PORT 80 8088 18080
pick_port NGINX_HTTPS_HOST_PORT 443 8443 18443
pick_port PROMETHEUS_HOST_PORT 9090 19090 29090
pick_port GRAFANA_HOST_PORT 3000 13000 23000

export GF_SECURITY_ADMIN_PASSWORD="${GF_SECURITY_ADMIN_PASSWORD:-admin}"

ensure_dev_tls_certs

echo "Starting AegisAIS core stack with the following host ports:"
echo "  PostgreSQL: $POSTGRES_HOST_PORT"
echo "  Redis:      $REDIS_HOST_PORT"
echo "  BFF:        $BFF_HOST_PORT"
echo "  Web:        $WEB_HOST_PORT"
echo "  HTTP:       $NGINX_HTTP_HOST_PORT"
echo "  HTTPS:      $NGINX_HTTPS_HOST_PORT"
echo "  Prometheus: $PROMETHEUS_HOST_PORT"
echo "  Grafana:    $GRAFANA_HOST_PORT"

docker compose -f "$COMPOSE_FILE" up -d \
  db redis api processing-worker persistence-worker alert-worker bff web nginx

echo
echo "Core stack start requested. Current service state:"
docker compose -f "$COMPOSE_FILE" ps

echo
echo "Expected entry points:"
echo "  API docs:   http://localhost:$NGINX_HTTP_HOST_PORT/docs"
echo "  API docs:   https://localhost:$NGINX_HTTPS_HOST_PORT/docs"
echo "  BFF health: http://localhost:$BFF_HOST_PORT/health"
echo "  Web dev UI: http://localhost:$WEB_HOST_PORT"