#!/bin/bash
# =============================================================================
# Nova VTU - PostgreSQL Database Backup Script
#
# Usage:
#   ./backup.sh                    # Create backup with default settings
#   ./backup.sh --upload           # Create backup and upload to S3
#   ./backup.sh --retention 30     # Keep backups for 30 days
#
# Environment Variables:
#   POSTGRES_HOST      - Database host (default: db)
#   POSTGRES_PORT      - Database port (default: 5432)
#   POSTGRES_DB        - Database name (default: nova_vtu)
#   POSTGRES_USER      - Database user (default: nova_vtu)
#   POSTGRES_PASSWORD  - Database password (required)
#   BACKUP_DIR         - Local backup directory (default: /backups)
#   RETENTION_DAYS     - Days to keep backups (default: 7)
#
# S3 Upload (optional):
#   S3_BUCKET          - S3 bucket name
#   AWS_ACCESS_KEY_ID  - AWS access key
#   AWS_SECRET_ACCESS_KEY - AWS secret key
#   AWS_REGION         - AWS region (default: us-east-1)
# =============================================================================

set -euo pipefail

# Configuration with defaults
POSTGRES_HOST="${POSTGRES_HOST:-db}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_DB="${POSTGRES_DB:-nova_vtu}"
POSTGRES_USER="${POSTGRES_USER:-nova_vtu}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
AWS_REGION="${AWS_REGION:-us-east-1}"

# Parse arguments
UPLOAD_S3=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --upload)
            UPLOAD_S3=true
            shift
            ;;
        --retention)
            RETENTION_DAYS="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Generate timestamp and filename
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILENAME="nova_vtu_${TIMESTAMP}.sql.gz"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILENAME}"

# Logging functions
log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: $1"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" >&2
}

log_success() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS: $1"
}

# Ensure backup directory exists
mkdir -p "${BACKUP_DIR}"

# Start backup
log_info "Starting database backup..."
log_info "Database: ${POSTGRES_DB}@${POSTGRES_HOST}:${POSTGRES_PORT}"
log_info "Backup file: ${BACKUP_PATH}"

# Create backup using pg_dump with compression
export PGPASSWORD="${POSTGRES_PASSWORD}"

if pg_dump \
    -h "${POSTGRES_HOST}" \
    -p "${POSTGRES_PORT}" \
    -U "${POSTGRES_USER}" \
    -d "${POSTGRES_DB}" \
    --format=plain \
    --no-owner \
    --no-privileges \
    --clean \
    --if-exists \
    | gzip > "${BACKUP_PATH}"; then

    BACKUP_SIZE=$(du -h "${BACKUP_PATH}" | cut -f1)
    log_success "Backup created successfully: ${BACKUP_PATH} (${BACKUP_SIZE})"
else
    log_error "Backup failed!"
    rm -f "${BACKUP_PATH}"
    exit 1
fi

# Upload to S3 if enabled
if [ "$UPLOAD_S3" = true ] && [ -n "${S3_BUCKET:-}" ]; then
    log_info "Uploading backup to S3: s3://${S3_BUCKET}/backups/${BACKUP_FILENAME}"

    if aws s3 cp "${BACKUP_PATH}" "s3://${S3_BUCKET}/backups/${BACKUP_FILENAME}" \
        --region "${AWS_REGION}" \
        --storage-class STANDARD_IA; then
        log_success "Backup uploaded to S3"
    else
        log_error "S3 upload failed"
        exit 1
    fi
fi

# Clean up old backups locally
log_info "Cleaning up backups older than ${RETENTION_DAYS} days..."
DELETED_COUNT=$(find "${BACKUP_DIR}" -name "nova_vtu_*.sql.gz" -type f -mtime +${RETENTION_DAYS} -delete -print | wc -l)
log_info "Deleted ${DELETED_COUNT} old backup(s)"

# Clean up old S3 backups if enabled
if [ "$UPLOAD_S3" = true ] && [ -n "${S3_BUCKET:-}" ]; then
    log_info "Cleaning up old S3 backups..."
    # List and delete old backups from S3
    CUTOFF_DATE=$(date -d "-${RETENTION_DAYS} days" +%Y-%m-%d 2>/dev/null || date -v-${RETENTION_DAYS}d +%Y-%m-%d)
    aws s3 ls "s3://${S3_BUCKET}/backups/" \
        | awk -v cutoff="$CUTOFF_DATE" '$1 < cutoff {print $4}' \
        | xargs -I {} aws s3 rm "s3://${S3_BUCKET}/backups/{}" --region "${AWS_REGION}" 2>/dev/null || true
fi

# Print summary
log_success "Backup completed!"
log_info "Summary:"
log_info "  - File: ${BACKUP_FILENAME}"
log_info "  - Size: ${BACKUP_SIZE}"
log_info "  - Path: ${BACKUP_PATH}"
if [ "$UPLOAD_S3" = true ] && [ -n "${S3_BUCKET:-}" ]; then
    log_info "  - S3: s3://${S3_BUCKET}/backups/${BACKUP_FILENAME}"
fi

# List current backups
log_info "Current backups in ${BACKUP_DIR}:"
ls -lh "${BACKUP_DIR}"/*.sql.gz 2>/dev/null || echo "  No backups found"
