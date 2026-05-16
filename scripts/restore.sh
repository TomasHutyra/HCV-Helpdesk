#!/bin/bash
# Obnova HCV Helpdesk ze zálohy
# Použití: bash /root/HCV-Helpdesk/scripts/restore.sh

set -euo pipefail

BACKUP_DIR="/root/backups"
APP_DIR="/root/HCV-Helpdesk"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

echo "=============================="
echo " HCV Helpdesk — Obnova dat"
echo "=============================="
echo ""

# Zobrazit dostupné zálohy DB
echo "Dostupné zálohy databáze:"
echo ""
ls -lh "$BACKUP_DIR/db/" | grep ".sql.gz" || { echo "Žádné zálohy nenalezeny v $BACKUP_DIR/db/"; exit 1; }
echo ""

read -rp "Zadej název souboru zálohy DB (např. hcv_helpdesk_2026-05-16_02-00.sql.gz): " DB_FILE

DB_PATH="$BACKUP_DIR/db/$DB_FILE"
if [ ! -f "$DB_PATH" ]; then
    echo "CHYBA: Soubor nenalezen: $DB_PATH"
    exit 1
fi

echo ""
echo "Dostupné zálohy media:"
ls -lh "$BACKUP_DIR/media/" | grep ".tar.gz" 2>/dev/null || echo "(žádné media zálohy)"
echo ""
read -rp "Název souboru zálohy media (Enter = přeskočit obnovu media): " MEDIA_FILE

echo ""
echo "!!! VAROVÁNÍ !!!"
echo "Tato operace PŘEPÍŠE aktuální databázi daty ze zálohy: $DB_FILE"
if [ -n "$MEDIA_FILE" ]; then
    echo "A přepíše media soubory ze zálohy: $MEDIA_FILE"
fi
echo ""
read -rp "Opravdu pokračovat? Zadej 'ano' pro potvrzení: " CONFIRM

if [ "$CONFIRM" != "ano" ]; then
    echo "Obnova zrušena."
    exit 0
fi

cd "$APP_DIR"

# Zastavit web, worker, beat (DB a Redis necháme běžet)
log "Zastavuji web, worker, beat..."
docker compose stop web worker beat

# Obnova databáze
log "Obnovuji databázi z: $DB_FILE"
gunzip -c "$DB_PATH" | docker compose exec -T db psql -U helpdesk hcv_helpdesk
log "Databáze obnovena."

# Obnova media (volitelné)
if [ -n "$MEDIA_FILE" ]; then
    MEDIA_PATH="$BACKUP_DIR/media/$MEDIA_FILE"
    if [ ! -f "$MEDIA_PATH" ]; then
        log "VAROVÁNÍ: Media soubor nenalezen: $MEDIA_PATH — přeskakuji."
    else
        log "Obnovuji media soubory z: $MEDIA_FILE"
        # Spustit dočasný kontejner se stejným media volume
        docker compose run --rm -T \
            -v "$MEDIA_PATH":/restore/media.tar.gz \
            web bash -c "rm -rf /app/media/* && tar xzf /restore/media.tar.gz -C / --strip-components=1 app/media/"
        log "Media obnovena."
    fi
fi

# Spustit vše zpět
log "Spouštím web, worker, beat..."
docker compose start web worker beat

log "=== Obnova dokončena ==="
echo ""
echo "Ověř funkčnost na https://helpdesk.hcvdesk.eu"
