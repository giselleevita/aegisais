#!/bin/bash
# Start script that runs migrations before starting the server

set -e

cd "$(dirname "$0")"

echo "Running database migrations..."
alembic upgrade head

echo "Starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
