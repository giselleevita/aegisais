#!/usr/bin/env bash
# PostgreSQL logical backup to compressed SQL (Sprint 2 — IMPLEMENTATION_PLAN Task 2.4)
set -euo pipefail

RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"
OUT="/backups/aegisais_backup_$(date +%Y%m%d_%H%M%S).sql.gz"

export PGPASSWORD="${PGPASSWORD:?PGPASSWORD must be set}"

pg_dump -h "${PGHOST:-db}" -U "${PGUSER:-aegisais}" -d "${PGDATABASE:-aegisais}" | gzip -9 >"$OUT"

find /backups -type f -name 'aegisais_backup_*.sql.gz' -mtime "+${RETENTION_DAYS}" -delete

echo "Backup written: $OUT"
