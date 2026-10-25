#!/usr/bin/env bash
set -euo pipefail

APP=/opt/littlekingo
MEDIA=$APP/media
DEST=$APP/backups
KEEP_DAYS=30
STAMP=$(date +%Y%m%d-%H%M%S)

mkdir -p "$DEST"
[ -d "$MEDIA" ] || { echo "FATAL: $MEDIA missing"; exit 1; }

sqlite3 "$APP/db.sqlite3" ".backup '$DEST/db-$STAMP.sqlite3'"
gzip -f "$DEST/db-$STAMP.sqlite3"
tar -czf "$DEST/media-$STAMP.tar.gz" -C "$APP" "media"
find "$DEST" -type f -mtime +$KEEP_DAYS -delete

echo "$(date -Is) backed up db-$STAMP.sqlite3.gz ($(du -h "$DEST/db-$STAMP.sqlite3.gz" | cut -f1)) and media-$STAMP.tar.gz ($(du -h "$DEST/media-$STAMP.tar.gz" | cut -f1))"
