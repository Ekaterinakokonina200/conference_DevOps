#!/usr/bin/env bash
# Firewall сервера БД: SSH из host-only сети, PostgreSQL только с сервера приложения.
# Использование: sudo bash scripts/setup-db-firewall.sh
set -euo pipefail

APP_HOST="${APP_HOST:-192.168.56.10}"
NET="${NET:-192.168.56.0/24}"

ufw default deny incoming
ufw default allow outgoing
ufw allow from "$NET" to any port 22 proto tcp comment 'SSH from host-only'
ufw allow from "$APP_HOST" to any port 5432 proto tcp comment 'PostgreSQL from app server'
ufw --force enable
ufw status verbose
