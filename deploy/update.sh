#!/usr/bin/env bash
# Routine code update. Deliberately needs NO sudo: nginx, the TLS cert and the
# systemd unit are already in place and unchanged, abeni owns the web root, and
# gunicorn reloads its workers on SIGHUP from the user that runs it.
#
# Use deploy/provision-vps.sh (root) only when infrastructure changes.
set -euo pipefail

APP=/home/abeni/apps/kingo-portfolio
WEBROOT=/var/www/kingo-portfolio
DOMAIN=littlekingo.duckdns.org
PORT=8140

cd "$APP"
set -a; . ./.env; set +a

echo "=== 1. dependencies ==="
./venv/bin/pip install --quiet -r requirements.txt
./venv/bin/python -c "import django; print('django', django.get_version())"

echo
echo "=== 2. migrations ==="
./venv/bin/python manage.py migrate --plan | tail -20
./venv/bin/python manage.py migrate --noinput

echo
echo "=== 3. static files ==="
./venv/bin/python manage.py collectstatic --noinput | tail -2
echo "static files: $(find "$WEBROOT/static" -type f | wc -l)"

echo
echo "=== 4. reload gunicorn (SIGHUP, no root needed) ==="
master=$(pgrep -u "$(id -un)" -f 'gunicorn sandbox.wsgi' | head -1)
[ -n "$master" ] || { echo "FATAL: gunicorn master not found - needs a real restart"; exit 1; }
kill -HUP "$master"
echo "sent HUP to pid $master"
sleep 5

echo
echo "=== 5. verify ==="
for i in 1 2 3 4 5 6; do
  code=$(curl -s -o /dev/null -w '%{http_code}' -m 20 -H "Host: $DOMAIN" "http://127.0.0.1:$PORT/")
  case "$code" in 2*|3*) break ;; esac
  sleep 3
done
echo "backend  -> $code"
curl -s -o /dev/null -w 'public   -> %{http_code}\n' -m 25 "https://$DOMAIN/"
curl -s -o /dev/null -w 'static   -> %{http_code}\n' -m 25 "https://$DOMAIN/static/portfolio/js/main.js"
case "$code" in 2*|3*) echo "=== DONE ===" ;; *) echo "FATAL: backend unhealthy ($code)"; exit 1 ;; esac
