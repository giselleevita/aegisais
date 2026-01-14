#!/bin/bash
# Development start script
# For production with migrations, use start_with_migrations.sh

cd "$(dirname "$0")"
source .venv/bin/activate

# Optional: Run migrations before starting (uncomment if needed)
# echo "Running migrations..."
# alembic upgrade head

uvicorn app.main:app --reload
