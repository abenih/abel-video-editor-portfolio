#!/usr/bin/env bash
# Nightly backup of the portfolio's only irreplaceable data: the SQLite DB and
# the owner's uploads. Everything else can be rebuilt from git.
#
# Install as a cron job (as abeni):
#   crontab -e
#   15 3 * * * /home/abeni/apps/kingo-portfolio/deploy/backup.sh >> /home/abeni/logs/portfolio-backup.log 2>&1
set -euo pipefail

APP=/home/abeni/apps/kingo-portfolio
# Uploads live in the web root, not under $APP - nginx (www-data) cannot traverse /home.
MEDIA=/var/www/kingo-portfolio/media
DEST=/home/abeni/backups/kingo-portfolio
KEEP_DAYS=30
STAMP=$(date +%Y%m%d-%H%M%S)

mkdir -p "$DEST"
[ -d "$MEDIA" ] || { echo "FATAL: $MEDIA missing - is the site provisioned?"; exit 1; }

# .backup is the only safe way to copy a live SQLite file - a plain cp can catch
# a half-written page and produce a restore that silently fails later.
sqlite3 "$APP/db.sqlite3" ".backup '$DEST/db-$STAMP.sqlite3'"
gzip -f "$DEST/db-$STAMP.sqlite3"

tar -czf "$DEST/media-$STAMP.tar.gz" -C "$(dirname "$MEDIA")" "$(basename "$MEDIA")"

find "$DEST" -type f -mtime +$KEEP_DAYS -delete

echo "$(date -Is) backed up db-$STAMP.sqlite3.gz ($(du -h "$DEST/db-$STAMP.sqlite3.gz" | cut -f1)) and media-$STAMP.tar.gz ($(du -h "$DEST/media-$STAMP.tar.gz" | cut -f1))"
echo "$(date -Is) REMINDER: these live on the same disk as the site - copy them off the box to be a real backup"
