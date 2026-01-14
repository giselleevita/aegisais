# Database Migration Guide

AegisAIS uses Alembic for database migrations. This guide explains how to set up and run migrations.

## Setup

### 1. Install Dependencies

```bash
cd backend
pip install -e .  # This will install alembic from pyproject.toml
```

Or install alembic directly:
```bash
pip install alembic
```

### 2. Configure Database URL

The migration system uses the same database URL from `app/settings.py`. Make sure your `DATABASE_URL` environment variable is set, or create a `.env` file:

```bash
# For SQLite (default)
DATABASE_URL=sqlite:///./aegisais.db

# For PostgreSQL
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/aegisais
```

## Running Migrations

### Initial Setup (First Time)

If you're setting up a new database, run:

```bash
cd backend
alembic upgrade head
```

This will create all tables:
- `vessels_latest` - Latest position for each vessel
- `alerts` - Alert records
- `alert_cooldowns` - Cooldown tracking for alerts

### Check Migration Status

```bash
alembic current
```

### View Migration History

```bash
alembic history
```

### Rollback (if needed)

```bash
# Rollback one migration
alembic downgrade -1

# Rollback to a specific revision
alembic downgrade <revision_id>

# Rollback all migrations
alembic downgrade base
```

## Creating New Migrations

When you modify models in `app/models.py`, create a new migration:

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "description of changes"

# Or create an empty migration
alembic revision -m "description of changes"
```

Then edit the generated file in `alembic/versions/` to ensure it's correct.

### Example: Adding a New Column

1. Modify the model in `app/models.py`
2. Generate migration: `alembic revision --autogenerate -m "add new column"`
3. Review the generated migration file
4. Apply: `alembic upgrade head`

## Migration Files

- `alembic.ini` - Alembic configuration
- `alembic/env.py` - Migration environment setup
- `alembic/versions/` - Migration scripts (versioned)

## Integration with Application

The application no longer uses `Base.metadata.create_all()` in production. Instead:

1. **Development**: You can still use `create_all()` for quick testing, but migrations are preferred
2. **Production**: Always use migrations (`alembic upgrade head`)

### Docker/Deployment

Add migration step to your deployment:

```dockerfile
# In Dockerfile or docker-compose.yml
RUN alembic upgrade head
```

Or in a startup script:

```bash
#!/bin/bash
# Start script
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Troubleshooting

### Migration conflicts

If you have conflicts (e.g., multiple developers):
1. Check current revision: `alembic current`
2. Pull latest migrations
3. Run: `alembic upgrade head`

### Database out of sync

If your database is out of sync with models:
1. Check current state: `alembic current`
2. Compare with models
3. Create a migration to sync: `alembic revision --autogenerate -m "sync schema"`

### SQLite vs PostgreSQL

Migrations work with both, but some differences:
- SQLite doesn't support some operations (ALTER COLUMN, etc.)
- PostgreSQL is recommended for production
- Test migrations on both if supporting both

## Current Schema

The initial migration (`001_initial_schema.py`) creates:

1. **vessels_latest**
   - Primary key: `mmsi`
   - Indexes: `timestamp`, `last_alert_severity`

2. **alerts**
   - Primary key: `id` (auto-increment)
   - Indexes: `mmsi`, `timestamp`, `type`, `severity`
   - Composite indexes: `(mmsi, timestamp)`, `(type, timestamp)`, `(severity, timestamp)`

3. **alert_cooldowns**
   - Primary key: `(mmsi, rule_type)`
   - Indexes: `last_alert_timestamp`
   - Composite index: `(mmsi, rule_type)`
