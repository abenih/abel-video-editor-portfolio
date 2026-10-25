#!/usr/bin/env bash
set -euo pipefail

APP=/opt/littlekingo
DOMAIN=littlekingo.duckdns.org
PORT=8140

cd "$APP"
set -a; . ./.env; set +a

echo "=== 1. dependencies ==="
.venv/bin/pip install --quiet -r requirements.txt
.venv/bin/python -c "import django; print('django', django.get_version())"

echo
echo "=== 2. migrations ==="
.venv/bin/python manage.py migrate --plan | tail -20
.venv/bin/python manage.py migrate --noinput

echo
echo "=== 3. static files ==="
.venv/bin/python manage.py collectstatic --noinput | tail -2

echo
echo "=== 4. reload gunicorn ==="
master=$(pgrep -u "$(id -un)" -f 'gunicorn sandbox.wsgi' | head -1)
if [ -n "$master" ]; then
  kill -HUP "$master"
  echo "sent HUP to pid $master"
else
  echo "gunicorn master not running under this user - using systemctl"
  sudo systemctl restart littlekingo.service
fi
sleep 3

echo
echo "=== 5. verify ==="
code=$(curl -s -o /dev/null -w '%{http_code}' -m 15 -H "Host: $DOMAIN" -H "X-Forwarded-Proto: https" "http://127.0.0.1:$PORT/")
echo "backend -> $code"
case "$code" in 2*|3*) echo "=== DONE ===" ;; *) echo "FATAL: backend unhealthy ($code)"; exit 1 ;; esac
