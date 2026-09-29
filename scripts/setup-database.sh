#!/usr/bin/env bash
# Установка PostgreSQL, базы conference и роли conference_app.
# Пароль вводится с клавиатуры и нигде не сохраняется.
# Использование: sudo bash scripts/setup-database.sh
set -euo pipefail

APP_HOST="${APP_HOST:-192.168.56.10}"
DB_HOST="${DB_HOST:-192.168.56.11}"

apt-get update
apt-get install -y postgresql

PGVER="$(ls /etc/postgresql/)"
CONF="/etc/postgresql/${PGVER}/main"

if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='conference_app'" | grep -q 1; then
  read -r -s -p "Пароль для conference_app (латиница и цифры): " DB_PASSWORD; echo
  sudo -u postgres psql -v ON_ERROR_STOP=1 -v pass="$DB_PASSWORD" <<'SQL'
CREATE ROLE conference_app LOGIN PASSWORD :'pass';
SQL
  unset DB_PASSWORD
fi

if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='conference'" | grep -q 1; then
  sudo -u postgres createdb --owner=conference_app conference
fi
sudo -u postgres psql -v ON_ERROR_STOP=1 -c "REVOKE ALL ON DATABASE conference FROM PUBLIC;"
sudo -u postgres psql -v ON_ERROR_STOP=1 -c "GRANT CONNECT, TEMPORARY ON DATABASE conference TO conference_app;"

sed -i "s/^#\?listen_addresses.*/listen_addresses = 'localhost,${DB_HOST}'/" "${CONF}/postgresql.conf"

RULE="host    conference    conference_app    ${APP_HOST}/32    scram-sha-256"
grep -qF "$RULE" "${CONF}/pg_hba.conf" || echo "$RULE" >> "${CONF}/pg_hba.conf"

systemctl restart postgresql
ss -ltnp | grep 5432
