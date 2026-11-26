#!/usr/bin/env bash
# QuestFinder — one-command setup and run (Git Bash on Windows).
#
#   bash scripts/start.sh            # first time: full setup, then run
#   bash scripts/start.sh            # next times: just run
#   bash scripts/start.sh --reseed   # wipe the data and load the demo data again
#   bash scripts/start.sh --share    # let other devices connect (debug OFF, listens on your Wi-Fi)
#
# First run only: you will be asked ONCE for the password of your PostgreSQL
# "postgres" user (the one you chose when you installed PostgreSQL).
set -euo pipefail
cd "$(dirname "$0")/.."

PSQL="/c/Program Files/PostgreSQL/18/bin/psql.exe"
PY=".venv/Scripts/python.exe"
RESEED=0
SHARE=0
for arg in "$@"; do
  case "$arg" in
    --reseed) RESEED=1 ;;
    --share)  SHARE=1 ;;
  esac
done

say() { printf '\n\033[1;32m==> %s\033[0m\n' "$1"; }
fail() { printf '\n\033[1;31mERROR: %s\033[0m\n' "$1"; exit 1; }

# 1. Virtual environment + packages ---------------------------------------------
if [ ! -x "$PY" ]; then
  say "Creating virtual environment (.venv) with Python 3.13"
  py -3.13 -m venv .venv || fail "Python 3.13 not found. Install it from python.org."
fi
say "Installing / checking packages"
"$PY" -m pip install --disable-pip-version-check -q -r requirements.txt

# 2. Database + .env (first run only) -----------------------------------------------
if [ ! -f .env ]; then
  [ -x "$PSQL" ] || fail "psql not found at $PSQL. Is PostgreSQL 18 installed?"
  say "Generating secrets for .env"
  read -r SECRET_KEY DB_PW ADMIN_PW DEMO_PW < <("$PY" -c "
import secrets, string
a = string.ascii_letters + string.digits
r = lambda n: ''.join(secrets.choice(a) for _ in range(n))
print(secrets.token_hex(32), r(24), 'QfAdmin-' + r(6), 'QfDemo-' + r(6))")

  mkdir -p scripts
  cat > scripts/setup_database.sql <<SQL
-- Created by scripts/start.sh. Safe to run more than once. Not committed to git.
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'questfinder') THEN
    CREATE ROLE questfinder LOGIN PASSWORD '${DB_PW}';
  ELSE
    ALTER ROLE questfinder WITH LOGIN PASSWORD '${DB_PW}';
  END IF;
END \$\$;
SELECT 'CREATE DATABASE questfinder OWNER questfinder ENCODING ''UTF8'''
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'questfinder')\gexec
SQL

  say "Creating the questfinder database — type your PostgreSQL 'postgres' password"
  "$PSQL" -U postgres -h localhost -v ON_ERROR_STOP=1 -f scripts/setup_database.sql \
    || fail "Could not create the database. Check that PostgreSQL is running and the password is right, then run this again."

  cat > .env <<ENV
# Local settings for this PC only. Never commit this file (it is in .gitignore).
FLASK_APP=run.py
FLASK_ENV_NAME=development
SECRET_KEY=${SECRET_KEY}
DATABASE_URL=postgresql://questfinder:${DB_PW}@localhost:5432/questfinder

# Logins created by "flask seed"
ADMIN_EMAIL=admin@questfinder.test
ADMIN_PASSWORD=${ADMIN_PW}
SEED_USER_PASSWORD=${DEMO_PW}

REQUIRE_VERIFICATION=true
FACE_MATCH_THRESHOLD=0.55
DEFAULT_MAP_LAT=16.3954
DEFAULT_MAP_LNG=120.5968
DEFAULT_MAP_ZOOM=16
APPROX_LOCATION_METERS=300
DEFAULT_RADIUS_KM=5
MAX_UPLOAD_MB=8
SESSION_HOURS=12
SESSION_COOKIE_SECURE=false
ENV
  RESEED=1
fi

# 3. Migrations + demo data ---------------------------------------------------------
say "Applying database migrations"
"$PY" -m flask db upgrade
if [ "$RESEED" = "1" ]; then
  say "Loading demo data"
  "$PY" -m flask seed --reset
fi

# 4. Run ------------------------------------------------------------------------------------
ADMIN_PW_SHOWN=$(grep '^ADMIN_PASSWORD=' .env | cut -d= -f2-)
DEMO_PW_SHOWN=$(grep '^SEED_USER_PASSWORD=' .env | cut -d= -f2-)
if [ "$SHARE" = "1" ]; then
  # Debug mode is OFF here: the debugger must never be reachable from other devices.
  LAN_IP=$(ipconfig 2>/dev/null | grep -a "IPv4" | grep -v "127.0.0.1" | head -1 | sed 's/.*: //' | tr -d '\r')
  say "QuestFinder is shared on your network (debug OFF)"
  echo "   On this PC      : http://127.0.0.1:5000"
  echo "   Same Wi-Fi      : http://${LAN_IP:-<your-PC-IP>}:5000"
  echo "   Over the internet (HTTPS, camera + GPS work): in a 2nd terminal run"
  echo "                     cloudflared tunnel --url http://localhost:5000"
  echo "   If Windows Firewall asks, allow Python on Private networks."
  echo "   Demo members: ...@questfinder.test  password: ${DEMO_PW_SHOWN}"
  echo "   Stop sharing with Ctrl+C."
  export FLASK_DEBUG=0
  exec "$PY" -m flask run --host 0.0.0.0 --port 5000 --no-debugger --no-reload
fi

say "QuestFinder is starting → open http://127.0.0.1:5000"
echo "   Demo members : carl@ / jake@ / dave@ / bea@ (unverified) ...@questfinder.test   password: ${DEMO_PW_SHOWN}"
echo "   Barangay Admin: admin@questfinder.test   password: ${ADMIN_PW_SHOWN}"
echo "   Stop the server with Ctrl+C."
exec "$PY" -m flask run --debug
