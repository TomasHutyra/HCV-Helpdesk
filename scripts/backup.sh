#!/bin/bash
# Denní záloha HCV Helpdesk
# Záloha: PostgreSQL dump + media soubory + .env.production
# Spouštět přes cron: 0 2 * * * /root/HCV-Helpdesk/scripts/backup.sh >> /var/log/hcv-backup.log 2>&1

set -euo pipefail

BACKUP_DIR="/root/backups"
APP_DIR="/root/HCV-Helpdesk"
KEEP_DAYS=7
DATE=$(date +%Y-%m-%d_%H-%M)

# Volitelné offsite zálohování přes rsync (odkomentovat a nastavit)
# REMOTE="u123456@u123456.your-storagebox.de:/backups/hcv-helpdesk"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

mkdir -p "$BACKUP_DIR/db" "$BACKUP_DIR/media" "$BACKUP_DIR/env"

log "=== Záloha $DATE zahájení ==="

# 1. PostgreSQL dump
log "Zálohuji databázi..."
cd "$APP_DIR"
docker compose exec -T db pg_dump -U helpdesk --clean --if-exists hcv_helpdesk \
    | gzip > "$BACKUP_DIR/db/hcv_helpdesk_${DATE}.sql.gz"
log "Databáze OK → $BACKUP_DIR/db/hcv_helpdesk_${DATE}.sql.gz ($(du -sh "$BACKUP_DIR/db/hcv_helpdesk_${DATE}.sql.gz" | cut -f1))"

# 2. Media soubory (streamovány z běžícího web kontejneru)
log "Zálohuji media soubory..."
docker compose exec -T web tar czf - /app/media \
    > "$BACKUP_DIR/media/media_${DATE}.tar.gz"
log "Media OK → $BACKUP_DIR/media/media_${DATE}.tar.gz ($(du -sh "$BACKUP_DIR/media/media_${DATE}.tar.gz" | cut -f1))"

# 3. .env.production (obsahuje hesla a SECRET_KEY — uchovávat bezpečně)
log "Zálohuji .env.production..."
cp "$APP_DIR/.env.production" "$BACKUP_DIR/env/env_${DATE}"
chmod 600 "$BACKUP_DIR/env/env_${DATE}"
log ".env OK → $BACKUP_DIR/env/env_${DATE}"

# 4. Rotace — smazat zálohy starší než KEEP_DAYS
log "Mažu zálohy starší než ${KEEP_DAYS} dní..."
find "$BACKUP_DIR/db"    -name "*.sql.gz" -mtime +"$KEEP_DAYS" -delete
find "$BACKUP_DIR/media" -name "*.tar.gz" -mtime +"$KEEP_DAYS" -delete
find "$BACKUP_DIR/env"   -name "env_*"    -mtime +"$KEEP_DAYS" -delete

# 5. Offsite sync (volitelné — odkomentovat pokud je REMOTE nastaveno)
# if [ -n "${REMOTE:-}" ]; then
#     log "Syncing na vzdálené úložiště: $REMOTE"
#     rsync -az --delete "$BACKUP_DIR/" "$REMOTE/"
#     log "Offsite sync OK"
# fi

log "Lokální zálohy:"
ls -lh "$BACKUP_DIR/db/" | tail -"$KEEP_DAYS"

log "=== Záloha dokončena ==="
