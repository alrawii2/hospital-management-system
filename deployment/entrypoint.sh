#!/bin/sh
# ---------------------------------------------------------------------------
# Backend container entrypoint.
# Runs at container start (after settings.py reads env vars) and before the
# CMD process (gunicorn) is exec'd.
# ---------------------------------------------------------------------------
set -eu

echo "[entrypoint] Waiting for database to accept connections…"
python - <<'PY'
import os, sys, time
import socket
host = os.environ.get("POSTGRES_HOST", "db")
port = int(os.environ.get("POSTGRES_PORT", "5432"))
deadline = time.time() + 60
while time.time() < deadline:
    try:
        s = socket.create_connection((host, port), timeout=2)
        s.close()
        print(f"[entrypoint]   {host}:{port} is up")
        sys.exit(0)
    except OSError:
        time.sleep(1)
print(f"[entrypoint]   timed out waiting for {host}:{port}")
sys.exit(1)
PY

echo "[entrypoint] Applying database migrations…"
python manage.py migrate --noinput

echo "[entrypoint] Collecting static files…"
python manage.py collectstatic --noinput --clear

# Optional: seed demo data on first boot. Controlled by HMS_SEED_ON_START.
if [ "${HMS_SEED_ON_START:-0}" = "1" ]; then
    echo "[entrypoint] Seeding demo data (HMS_SEED_ON_START=1)…"
    python manage.py seed_data || true
fi

echo "[entrypoint] Starting: $*"
exec "$@"
