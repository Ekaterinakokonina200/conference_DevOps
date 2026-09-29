#!/usr/bin/env bash
# Firewall сервера приложения: SSH и порт приложения только из host-only сети.
# Использование: sudo bash scripts/setup-app-firewall.sh
set -euo pipefail

NET="${NET:-192.168.56.0/24}"

ufw default deny incoming
ufw default allow outgoing
ufw allow from "$NET" to any port 22 proto tcp comment 'SSH from host-only'
ufw allow from "$NET" to any port 8000 proto tcp comment 'Conference app for clients'
ufw --force enable
ufw status verbose
