#!/bin/bash
# =============================================================================
# Nova VTU - PostgreSQL Database Restore Script
#
# Usage:
#   ./restore.sh <backup_file>                    # Restore from local file
#   ./restore.sh --latest                         # Restore latest local backup
#   ./restore.sh --from-s3 <backup_filename>      # Download and restore from S3
#   ./restore.sh --list-s3                        # List available S3 backups
#
# Environment Variables:
#   POSTGRES_HOST      - Database host (default: db)
#   POSTGRES_PORT      - Database port (default: 5432)
#   POSTGRES_DB        - Database name (default: nova_vtu)
#   POSTGRES_USER      - Database user (default: nova_vtu)
#   POSTGRES_PASSWORD  - Database password (required)
#   BACKUP_DIR         - Local backup directory (default: /backups)
#
# S3 Download:
#   S3_BUCKET          - S3 bucket name
#   AWS_ACCESS_KEY_ID  - AWS access key
#   AWS_SECRET_ACCESS_KEY - AWS secret key
#   AWS_REGION         - AWS region (default: us-east-1)
#
# WARNING: This script will OVERWRITE the existing database!
# =============================================================================

set -euo pipefail

# Configuration with defaults
POSTGRES_HOST="${POSTGRES_HOST:-db}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_DB="${POSTGRES_DB:-nova_vtu}"
POSTGRES_USER="${POSTGRES_USER:-nova_vtu}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
AWS_REGION="${AWS_REGION:-us-east-1}"

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

log_warning() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $1"
}

# Show usage
usage() {
    echo "Usage: $0 [OPTIONS] [BACKUP_FILE]"
    echo ""
    echo "Options:"
    echo "  --latest        Restore the latest local backup"
    echo "  --from-s3 FILE  Download and restore from S3"
    echo "  --list-s3       List available S3 backups"
    echo "  --list          List available local backups"
    echo "  --dry-run       Show what would be restored without executing"
    echo "  --force         Skip confirmation prompt"
    echo "  -h, --help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 /backups/nova_vtu_20250101_120000.sql.gz"
    echo "  $0 --latest"
    echo "  $0 --from-s3 nova_vtu_20250101_120000.sql.gz"
    exit 1
}

# Parse arguments
RESTORE_FILE=""
FROM_S3=false
LIST_S3=false
LIST_LOCAL=false
DRY_RUN=false
FORCE=false
USE_LATEST=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --latest)
            USE_LATEST=true
            shift
            ;;
        --from-s3)
            FROM_S3=true
            RESTORE_FILE="$2"
            shift 2
            ;;
        --list-s3)
            LIST_S3=true
            shift
            ;;
        --list)
            LIST_LOCAL=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        -*)
            echo "Unknown option: $1"
            usage
            ;;
        *)
            RESTORE_FILE="$1"
            shift
            ;;
    esac
done

# List S3 backups
if [ "$LIST_S3" = true ]; then
    if [ -z "${S3_BUCKET:-}" ]; then
        log_error "S3_BUCKET environment variable is required"
        exit 1
    fi
    log_info "Available backups in s3://${S3_BUCKET}/backups/:"
    aws s3 ls "s3://${S3_BUCKET}/backups/" --region "${AWS_REGION}" | grep ".sql.gz" || echo "No backups found"
    exit 0
fi

# List local backups
if [ "$LIST_LOCAL" = true ]; then
    log_info "Available backups in ${BACKUP_DIR}:"
    ls -lht "${BACKUP_DIR}"/*.sql.gz 2>/dev/null || echo "No backups found"
    exit 0
fi

# Get latest backup if requested
if [ "$USE_LATEST" = true ]; then
    RESTORE_FILE=$(ls -t "${BACKUP_DIR}"/*.sql.gz 2>/dev/null | head -1)
    if [ -z "$RESTORE_FILE" ]; then
        log_error "No backup files found in ${BACKUP_DIR}"
        exit 1
    fi
    log_info "Using latest backup: ${RESTORE_FILE}"
fi

# Validate backup file specified
if [ -z "$RESTORE_FILE" ]; then
    log_error "No backup file specified"
    usage
fi

# Download from S3 if requested
if [ "$FROM_S3" = true ]; then
    if [ -z "${S3_BUCKET:-}" ]; then
        log_error "S3_BUCKET environment variable is required"
        exit 1
    fi

    S3_PATH="s3://${S3_BUCKET}/backups/${RESTORE_FILE}"
    LOCAL_PATH="${BACKUP_DIR}/${RESTORE_FILE}"

    log_info "Downloading from S3: ${S3_PATH}"
    if aws s3 cp "${S3_PATH}" "${LOCAL_PATH}" --region "${AWS_REGION}"; then
        log_success "Downloaded backup: ${LOCAL_PATH}"
        RESTORE_FILE="${LOCAL_PATH}"
    else
        log_error "Failed to download from S3"
        exit 1
    fi
fi

# Validate file exists
if [ ! -f "$RESTORE_FILE" ]; then
    log_error "Backup file not found: ${RESTORE_FILE}"
    exit 1
fi

BACKUP_SIZE=$(du -h "${RESTORE_FILE}" | cut -f1)
log_info "Backup file: ${RESTORE_FILE} (${BACKUP_SIZE})"

# Dry run mode
if [ "$DRY_RUN" = true ]; then
    log_info "DRY RUN: Would restore ${RESTORE_FILE} to ${POSTGRES_DB}@${POSTGRES_HOST}:${POSTGRES_PORT}"
    log_info "DRY RUN: No changes were made"
    exit 0
fi

# Confirmation prompt
if [ "$FORCE" != true ]; then
    log_warning "This will OVERWRITE the database: ${POSTGRES_DB}"
    log_warning "All existing data will be LOST!"
    echo ""
    read -p "Are you sure you want to continue? [y/N]: " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Restore cancelled"
        exit 0
    fi
fi

# Start restore
log_info "Starting database restore..."
log_info "Target: ${POSTGRES_DB}@${POSTGRES_HOST}:${POSTGRES_PORT}"

export PGPASSWORD="${POSTGRES_PASSWORD}"

# Terminate existing connections (optional, may need superuser)
log_info "Terminating existing connections..."
psql -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d postgres \
    -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${POSTGRES_DB}' AND pid <> pg_backend_pid();" \
    2>/dev/null || log_warning "Could not terminate connections (may need superuser privileges)"

# Restore database
log_info "Restoring database..."
if gunzip -c "${RESTORE_FILE}" | psql \
    -h "${POSTGRES_HOST}" \
    -p "${POSTGRES_PORT}" \
    -U "${POSTGRES_USER}" \
    -d "${POSTGRES_DB}" \
    --quiet \
    --single-transaction \
    2>&1 | grep -v "^SET\|^COMMENT\|^ALTER\|^CREATE\|^DROP"; then

    log_success "Database restored successfully!"
else
    log_error "Restore failed!"
    exit 1
fi

# Verify restore
log_info "Verifying restore..."
TABLE_COUNT=$(psql -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
    -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" | tr -d ' ')

log_success "Restore completed!"
log_info "Summary:"
log_info "  - Source: ${RESTORE_FILE}"
log_info "  - Database: ${POSTGRES_DB}"
log_info "  - Tables restored: ${TABLE_COUNT}"
