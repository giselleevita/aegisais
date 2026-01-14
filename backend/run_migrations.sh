#!/bin/bash
# Script to run database migrations

set -e

echo "Running database migrations..."

# Check if alembic is installed
if ! python3 -c "import alembic" 2>/dev/null; then
    echo "Installing alembic..."
    pip install alembic
fi

# Run migrations
cd "$(dirname "$0")"
alembic upgrade head

echo "Migrations completed successfully!"
