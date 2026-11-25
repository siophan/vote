#!/usr/bin/env bash
# Release from the development machine: rsync the server code and images, install, migrate,
# seed (idempotent), install the systemd unit, restart and check /api/v1/health.
#   deploy/deploy.sh [user@host]      (default ubuntu@18.162.184.136)
# server/static/assets is not in git (scripts/sync_assets.py builds it from ui/dist); it is
# rsynced from this checkout, so run that script first on a fresh clone.
set -euo pipefail
cd "$(dirname "$0")/.."
. deploy/require-main.sh

HOST=${1:-ubuntu@18.162.184.136}
BASE=/www/wwwroot/vote
APP=$BASE/app

if [ "$(ls server/static/assets 2>/dev/null | wc -l)" -lt 100 ]; then
  echo "server/static/assets looks empty; run: cd server && uv run python scripts/sync_assets.py" >&2
  exit 1
fi

rsync -az --delete --rsync-path='sudo rsync' \
  --exclude '__pycache__' --exclude '.pytest_cache' --exclude '*.pyc' --exclude '.venv' \
  --exclude '.env' --exclude '.DS_Store' --exclude 'static/uploads' --exclude 'tests' \
  server/ deploy "$HOST:$APP/"

ssh "$HOST" sudo bash -s <<SH
set -euo pipefail
cd "$APP"
# uploads persist outside the release tree
ln -sfn "$BASE/uploads" static/uploads
chown -R vote:vote "$APP"
sudo -u vote env HOME="$BASE" "$BASE/.local/bin/uv" sync --frozen --no-dev --python 3.12
sudo -u vote bash -c 'set -a; . "$BASE/.env"; set +a; cd "$APP" && .venv/bin/alembic upgrade head && .venv/bin/python -m app.seed'
install -m 644 deploy/vote-api.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable vote-api >/dev/null
systemctl restart vote-api
for i in {1..60}; do
  if curl -fs http://127.0.0.1:8030/api/v1/health; then break; fi
  if [ "\$i" -eq 60 ]; then echo "API did not answer /health in time" >&2; exit 1; fi
  sleep 1
done
echo
systemctl is-active vote-api
SH
