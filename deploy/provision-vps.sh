#!/usr/bin/env bash
# Provisions the Kingo Abel portfolio (Django) on the shared VPS. Run as root (sudo bash).
# Internal port 8140; public https://littlekingo.duckdns.org.
# Mirrors the existing spot-* units + nginx sites, with the same safety rule:
# every nginx change is validated with `nginx -t` BEFORE reload, so the other
# clients' sites (restaurant-*, korecha, vegas-games, spot-*) can never break.
#
# Re-runnable: use it for the first install AND for later updates (pull, then re-run).
set -euo pipefail

DOMAIN=littlekingo.duckdns.org
PORT=8140
APP=/home/abeni/apps/kingo-portfolio
# nginx's www-data worker cannot traverse /home/abeni (mode 750), so static and
# media live here instead. Widening /home would expose the other apps' secrets.
WEBROOT=/var/www/kingo-portfolio
RUN_USER=abeni
UNIT=/etc/systemd/system/kingo-portfolio.service
SITE=/etc/nginx/sites-available/kingo-portfolio
PY=$APP/venv/bin/python
GUNICORN=$APP/venv/bin/gunicorn
# Django caps uploads at 300MB (MAX_VIDEO_SIZE_MB); nginx defaults to 1MB and would 413 first.
MAX_BODY=310m

echo "=== 0. preflight ==="
[ -f "$APP/manage.py" ] || { echo "FATAL: $APP/manage.py missing - clone/rsync the repo there first"; exit 1; }
id "$RUN_USER" >/dev/null 2>&1 || { echo "FATAL: user $RUN_USER does not exist"; exit 1; }
if ss -tln | grep -q ":$PORT " && ! systemctl is-active --quiet kingo-portfolio.service; then
  echo "FATAL: port $PORT already in use by something else"; exit 1
fi
nginx -t >/dev/null 2>&1 || { echo "FATAL: nginx config ALREADY broken before my changes - aborting"; exit 1; }
getent hosts "$DOMAIN" >/dev/null || echo "WARNING: $DOMAIN does not resolve yet - set the DuckDNS record to this VPS IP or certbot will fail"
echo "ok (repo, user, port $PORT, existing nginx config valid)"

echo
echo "=== 1. python env ==="
apt-get update -qq
apt-get install -y -qq python3-venv python3-dev sqlite3 >/dev/null
[ -d "$APP/venv" ] || sudo -u "$RUN_USER" python3 -m venv "$APP/venv"
sudo -u "$RUN_USER" "$APP/venv/bin/pip" install --quiet --upgrade pip
sudo -u "$RUN_USER" "$APP/venv/bin/pip" install --quiet -r "$APP/requirements.txt"
echo "ok ($($PY --version), deps installed)"

echo
echo "=== 2. environment file ==="
if [ ! -f "$APP/.env" ]; then
  SECRET=$("$PY" -c 'import secrets; print(secrets.token_urlsafe(64))')
  cat > "$APP/.env" <<EOF
DJANGO_SECRET_KEY=$SECRET
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=$DOMAIN
DJANGO_CSRF_TRUSTED_ORIGINS=https://$DOMAIN
# nginx terminates TLS and forwards plain HTTP; without this SECURE_SSL_REDIRECT loops forever.
DJANGO_BEHIND_TLS_PROXY=True
DJANGO_SECURE_SSL_REDIRECT=True
# Outside /home so nginx (www-data) can actually read them.
DJANGO_STATIC_ROOT=$WEBROOT/static
DJANGO_MEDIA_ROOT=$WEBROOT/media
# Left unset (off): nginx serves /media/ directly, so WhiteNoise never needs to rescan.
# DJANGO_WHITENOISE_AUTOREFRESH=False
EOF
  chown "$RUN_USER:$RUN_USER" "$APP/.env"
  chmod 600 "$APP/.env"
  echo "created $APP/.env with a fresh SECRET_KEY"
else
  echo "kept existing $APP/.env (not overwriting your SECRET_KEY)"
fi

# Settings added after the first install still need to reach an existing .env.
ensure_env() {
  grep -q "^$1=" "$APP/.env" || { echo "$1=$2" >> "$APP/.env"; echo "added $1 to .env"; }
}
ensure_env DJANGO_BEHIND_TLS_PROXY True
ensure_env DJANGO_STATIC_ROOT "$WEBROOT/static"
ensure_env DJANGO_MEDIA_ROOT "$WEBROOT/media"

echo
echo "=== 3. web root + migrate + collectstatic ==="
install -d -o "$RUN_USER" -g www-data -m 755 "$WEBROOT" "$WEBROOT/static" "$WEBROOT/media"
# One-time move of any uploads that predate the web root.
if [ -d "$APP/media" ] && [ -n "$(ls -A "$APP/media" 2>/dev/null)" ]; then
  cp -an "$APP/media/." "$WEBROOT/media/" 2>/dev/null || true
  echo "copied existing uploads into $WEBROOT/media"
fi
chown -R "$RUN_USER:www-data" "$WEBROOT"
chmod -R u=rwX,g=rX,o=rX "$WEBROOT"

# `set -a; . .env` rather than piping through xargs, which mangles any value
# containing spaces or quotes.
run_manage() { sudo -u "$RUN_USER" bash -c "set -a; . '$APP/.env'; set +a; '$PY' '$APP/manage.py' $*"; }
run_manage migrate --noinput
run_manage collectstatic --noinput >/dev/null
chown -R "$RUN_USER:www-data" "$WEBROOT"
echo "ok (static: $(find "$WEBROOT/static" -type f | wc -l) files, media: $(find "$WEBROOT/media" -type f | wc -l) files)"

echo
echo "=== 4. systemd unit ==="
cat > "$UNIT" <<EOF
[Unit]
Description=Kingo Abel portfolio (Django/gunicorn)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$RUN_USER
WorkingDirectory=$APP
EnvironmentFile=$APP/.env
# --timeout 120: a 300MB upload over a slow link must not be killed mid-flight.
ExecStart=$GUNICORN sandbox.wsgi:application --bind 127.0.0.1:$PORT --workers 3 --timeout 120
Restart=always
RestartSec=5
# Same hardening shape as aviator-admin-bot: this process accepts file uploads
# from the public internet on a box that also runs the money-handling services.
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=$APP $WEBROOT/media
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
LockPersonality=true

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable kingo-portfolio.service >/dev/null
systemctl restart kingo-portfolio.service
sleep 4
systemctl is-active kingo-portfolio.service || { journalctl -u kingo-portfolio -n 40 --no-pager; exit 1; }
# Must send the real Host header: ALLOWED_HOSTS only lists $DOMAIN, so a plain
# request to 127.0.0.1 correctly gets a 400 DisallowedHost.
curl -fsS -o /dev/null -w 'backend HTTP %{http_code}\n' -H "Host: $DOMAIN" "http://127.0.0.1:$PORT/"

echo
echo "=== 5. nginx vhost (http only; certbot adds TLS) ==="
cat > "$SITE" <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    client_max_body_size $MAX_BODY;

    # Served straight off disk - never proxied to Django.
    location /static/ {
        alias $WEBROOT/static/;
        access_log off;
        expires 30d;
        add_header X-Content-Type-Options nosniff always;
    }

    # Owner-uploaded files. nosniff matters here: these are user-supplied bytes.
    location /media/ {
        alias $WEBROOT/media/;
        access_log off;
        expires 7d;
        add_header X-Content-Type-Options nosniff always;
    }

    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
    }
}
EOF
ln -sfn "$SITE" /etc/nginx/sites-enabled/kingo-portfolio
if ! nginx -t; then
  echo "FATAL: nginx test failed - rolling back my site, other clients untouched"
  rm -f /etc/nginx/sites-enabled/kingo-portfolio
  nginx -t && echo "rollback verified"
  exit 1
fi
systemctl reload nginx
# `systemctl reload` returns before the new workers take over, so an immediate
# request can still hit the old config and fall through to the default 404.
for i in 1 2 3 4 5; do
  code=$(curl -s -o /dev/null -w '%{http_code}' -H "Host: $DOMAIN" "http://127.0.0.1/")
  case "$code" in 2*|3*) break ;; esac
  sleep 2
done
echo "via nginx :80 HTTP $code"
case "$code" in 2*|3*) ;; *) echo "FATAL: nginx not routing $DOMAIN (got $code)"; exit 1 ;; esac

echo
echo "=== 6. certbot (TLS) ==="
if certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --redirect --keep-until-expiring; then
  echo "certbot ok"
else
  echo "WARNING: certbot failed; site still serving on plain http"
fi
if ! nginx -t; then
  echo "FATAL: nginx broken after certbot"; exit 1
fi
systemctl reload nginx

echo
echo "=== 7. verify (nothing else disturbed) ==="
echo "-- portfolio --"
curl -fsS -o /dev/null -w '  https://'"$DOMAIN"'/ -> %{http_code}\n' "https://$DOMAIN/" || echo "  https FAILED"
curl -fsS -o /dev/null -w '  static  -> %{http_code}\n' "https://$DOMAIN/static/portfolio/css/style.css" || echo "  static FAILED"
echo "-- neighbours still up --"
for u in aviator spot-aviator spot-chicken-cross spot-triple-dragon; do
  printf '  %-22s %s\n' "$u" "$(systemctl is-active $u.service 2>/dev/null || echo absent)"
done
for h in chickencross.duckdns.org spotgames.duckdns.org vegasgames.duckdns.org tripledragon.duckdns.org; do
  printf '  %-28s %s\n' "$h" "$(curl -s -o /dev/null -w '%{http_code}' -m 10 https://$h/ || echo ERR)"
done
echo "  pm2:"; sudo -u "$RUN_USER" pm2 list 2>/dev/null | grep -E 'online|stopped|errored' | sed 's/^/    /' || true
echo
echo "=== DONE ==="
echo "Owner logs in at https://$DOMAIN/login/ and clicks 'Edit this page'."
echo "REMINDER: db.sqlite3 + media/ are the only copy of his content - see deploy/backup.sh"
