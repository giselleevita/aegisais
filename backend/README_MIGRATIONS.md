# Quick Start: Database Migrations

## First Time Setup

1. **Install dependencies:**
   ```bash
   cd backend
   pip install -e .
   ```

2. **Run migrations:**
   ```bash
   alembic upgrade head
   ```

3. **Start the server:**
   ```bash
   ./start.sh  # Development
   # or
   ./start_with_migrations.sh  # Production (runs migrations first)
   ```

## Common Commands

```bash
# Check current migration status
alembic current

# View migration history
alembic history

# Create a new migration (after modifying models)
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

## Docker

The Dockerfile automatically runs migrations on container startup.

For manual migration in Docker:
```bash
docker-compose exec api alembic upgrade head
```

## See Also

- `MIGRATION_GUIDE.md` - Detailed migration documentation
- `alembic/versions/` - Migration files
