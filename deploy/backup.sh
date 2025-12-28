#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
TS="$(date +%Y%m%d_%H%M%S)"

DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-acrdb}"
DB_USER="${DB_USER:-acruser}"

mkdir -p "$BACKUP_DIR"

PGPASSWORD="${DB_PASSWORD:-}" pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
  > "${BACKUP_DIR}/backup_${TS}.sql"

if [[ -n "${BACKUP_RETENTION_DAYS:-}" ]]; then
  find "$BACKUP_DIR" -type f -name "backup_*.sql" -mtime +"$BACKUP_RETENTION_DAYS" -delete
fi

echo "Backup criado em ${BACKUP_DIR}/backup_${TS}.sql"
