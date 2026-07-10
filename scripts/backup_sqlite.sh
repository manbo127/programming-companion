#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/srv/codemate}"
DB_PATH="${DB_PATH:-${APP_DIR}/instance/companion.db}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/codemate}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"

if [[ ! -f "$DB_PATH" ]]; then
    echo "Database does not exist: $DB_PATH" >&2
    exit 1
fi

if ! command -v sqlite3 >/dev/null 2>&1; then
    echo "sqlite3 is required to create a consistent online backup." >&2
    exit 1
fi

mkdir -p "$BACKUP_DIR"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_path="${BACKUP_DIR}/companion-${timestamp}.db"

# SQLite's online backup command safely includes committed WAL data.
sqlite3 "$DB_PATH" ".timeout 5000" ".backup '$backup_path'"
gzip -f "$backup_path"

find "$BACKUP_DIR" -maxdepth 1 -type f -name 'companion-*.db.gz' \
    -mtime "+${RETENTION_DAYS}" -delete

echo "Backup created: ${backup_path}.gz"
