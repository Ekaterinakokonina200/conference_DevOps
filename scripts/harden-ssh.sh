#!/usr/bin/env bash
# Запрет входа root и входа по паролю.
# Запускать ТОЛЬКО после проверки входа по ключу у всех администраторов.
# Использование: sudo bash scripts/harden-ssh.sh
set -euo pipefail

cat > /etc/ssh/sshd_config.d/00-conference-hardening.conf <<'EOF'
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
EOF

sshd -t
systemctl restart ssh
sshd -T | grep -Ei '^(permitrootlogin|passwordauthentication|pubkeyauthentication)'
