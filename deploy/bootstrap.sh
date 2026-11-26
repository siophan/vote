#!/usr/bin/env bash
# First-time server setup. Run once, as root, on the server, naming its domain:
#   ssh ubuntu@18.162.184.136 sudo bash -s -- vote.jh8.ai < deploy/bootstrap.sh
# Creates the service user `vote`, its directories, uv + Python 3.12 for that user, the Postgres
# role and database `linghuali`, and /www/wwwroot/vote/.env with fresh secrets. Safe to run again.
set -euo pipefail

DOMAIN=${1:?usage: bootstrap.sh <domain>}
BASE=/www/wwwroot/vote
USER_NAME=vote
DB_NAME=linghuali
UV="$BASE/.local/bin/uv"
# The BT panel installs PostgreSQL under /www/server/pgsql, off the PATH.
if [ -x /www/server/pgsql/bin/psql ]; then PSQL=/www/server/pgsql/bin/psql; else PSQL=psql; fi

if ! id -u "$USER_NAME" >/dev/null 2>&1; then
  useradd --system --create-home --home-dir "$BASE" --shell /usr/sbin/nologin "$USER_NAME"
fi
# uploads/ lives outside the code tree so releases (rsync --delete) never touch it.
mkdir -p "$BASE/app" "$BASE/uploads"
chown -R "$USER_NAME:$USER_NAME" "$BASE"
chmod 750 "$BASE"
cd "$BASE"

if [ ! -x "$UV" ]; then
  curl -LsSf https://astral.sh/uv/install.sh | sudo -u "$USER_NAME" env HOME="$BASE" sh
fi
sudo -u "$USER_NAME" env HOME="$BASE" "$UV" python install 3.12

if [ ! -f "$BASE/.env" ]; then
  umask 077
  DB_PASSWORD=$(openssl rand -hex 24)
  (cd /tmp && sudo -u postgres "$PSQL" -v ON_ERROR_STOP=1 \
    -c "create role $USER_NAME login password '$DB_PASSWORD'" \
    -c "create database $DB_NAME owner $USER_NAME")
  cat > "$BASE/.env" <<ENV
DATABASE_URL=postgresql+psycopg://$USER_NAME:$DB_PASSWORD@127.0.0.1:5432/$DB_NAME
JWT_SECRET=$(openssl rand -hex 32)
JWT_EXPIRE_DAYS=30
WECHAT_APPID=wx8438a00a54f5b94b
# From the mini-program admin console (开发管理 → 开发设置). Login fails until it is set.
WECHAT_SECRET=
WECHAT_MOCK_LOGIN=false
ASSET_BASE_URL=https://$DOMAIN/static/assets/
UPLOAD_BASE_URL=https://$DOMAIN/static/uploads/
ADMIN_TOKEN=$(openssl rand -hex 24)
CORS_ORIGINS=*
ENV
  chown "$USER_NAME:$USER_NAME" "$BASE/.env"
  chmod 600 "$BASE/.env"
  echo "wrote $BASE/.env: fill in WECHAT_SECRET"
fi

echo "bootstrap done. Next: deploy/deploy.sh from the development machine."
