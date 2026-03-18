# Large Dataset Guide

This guide explains how to optimize AegisAIS for processing large AIS datasets.

## Quick Start for Large Files

### 1. Use PostgreSQL (Recommended)

For datasets with millions of records, PostgreSQL is much faster than SQLite:

```bash
# Start PostgreSQL with Docker
docker-compose up -d db

# Set database URL
export DATABASE_URL="postgresql+psycopg://aegisais:aegisais@localhost:5432/aegisais"

# Or create a .env file in backend/
echo 'DATABASE_URL=postgresql+psycopg://aegisais:aegisais@localhost:5432/aegisais' > backend/.env
```

### 2. Use Streaming Mode

The system automatically uses streaming mode for files > 50MB. You can also force it:

```bash
curl -X POST "http://localhost:8000/v1/replay/start?path=data/raw/large_file.csv.zst&speedup=100.0&use_streaming=true&batch_size=500"
```

**Parameters:**
- `use_streaming=true`: Process file in chunks (memory-efficient)
- `batch_size=500`: Commit to database every 500 points (adjust based on your needs)

### 3. Optimize Batch Size

**Small files (< 1M points):**
- `batch_size=100` (default)

**Medium files (1M - 10M points):**
- `batch_size=500-1000`

**Large files (> 10M points):**
- `batch_size=1000-5000`
- Consider increasing database connection pool

## Performance Tips

### Database Optimization

1. **Use PostgreSQL** for datasets > 1M records
2. **Create indexes** (automatically created, but verify):
   ```sql
   CREATE INDEX IF NOT EXISTS idx_alerts_mmsi_time ON alerts(mmsi, timestamp);
   CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp);
   CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);
   ```

3. **Tune PostgreSQL** (in `docker-compose.yml` or postgresql.conf):
   ```yaml
   environment:
     POSTGRES_SHARED_BUFFERS: "256MB"
     POSTGRES_EFFECTIVE_CACHE_SIZE: "1GB"
     POSTGRES_MAINTENANCE_WORK_MEM: "128MB"
   ```

### Memory Management

- **Streaming mode** loads only chunks at a time (default for files > 50MB)
- **Batch commits** reduce database overhead
- **Monitor memory** usage during processing

### Speedup Settings

- **Real-time**: `speedup=1.0` (slowest, most accurate)
- **Fast**: `speedup=100.0` (default, good balance)
- **Very Fast**: `speedup=1000.0` (for testing, may miss timing-dependent issues)

## Example: Processing a 10GB File

```bash
# 1. Ensure PostgreSQL is running
docker-compose up -d db

# 2. Set database URL
export DATABASE_URL="postgresql+psycopg://aegisais:aegisais@localhost:5432/aegisais"

# 3. Start backend
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload

# 4. Start replay with optimized settings
curl -X POST "http://localhost:8000/v1/replay/start?path=data/raw/huge_file.csv.zst&speedup=100.0&use_streaming=true&batch_size=1000"

# 5. Monitor progress
curl http://localhost:8000/v1/replay/status
```

## Monitoring Large Dataset Processing

### Check Progress
```bash
curl http://localhost:8000/v1/replay/status
```

### Check Database Size
```sql
-- PostgreSQL
SELECT pg_size_pretty(pg_database_size('aegisais'));

-- Check table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Monitor System Resources
```bash
# Memory usage
top -pid $(pgrep -f uvicorn)

# Disk I/O
iostat -x 1
```

## Troubleshooting

### Out of Memory
- Use streaming mode: `use_streaming=true`
- Reduce batch_size: `batch_size=50`
- Process file in smaller chunks

### Slow Processing
- Increase batch_size: `batch_size=1000-5000`
- Use PostgreSQL instead of SQLite
- Increase speedup: `speedup=500.0`
- Check database indexes are created

### Database Connection Errors
- Increase connection pool size
- Check PostgreSQL max_connections setting
- Reduce batch_size to commit more frequently

## Configuration

Create `backend/.env`:

```env
# Database
DATABASE_URL=postgresql+psycopg://aegisais:aegisais@localhost:5432/aegisais

# Performance tuning
DEFAULT_BATCH_SIZE=500
STREAMING_THRESHOLD_MB=50.0
CHUNK_SIZE=10000
```

## Expected Performance

**SQLite (small datasets < 1M points):**
- ~1,000-5,000 points/second

**PostgreSQL (large datasets):**
- ~10,000-50,000 points/second (depends on hardware and batch_size)

**With streaming (large files):**
- Memory usage: ~100-500MB (instead of GBs)
- Processing speed: Similar to non-streaming

