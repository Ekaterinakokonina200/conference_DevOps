#!/usr/bin/env bash
# Постоянный адрес host-only интерфейса и имя машины.
# Использование:
#   sudo bash scripts/setup-network.sh 192.168.56.10 conference-app
#   sudo bash scripts/setup-network.sh 192.168.56.11 conference-db
set -euo pipefail

IP="${1:?Укажите адрес, например 192.168.56.10}"
NAME="${2:?Укажите имя, например conference-app}"
IFACE="${IFACE:-enp0s8}"

cat > /etc/netplan/90-conference-hostonly.yaml <<EOF
network:
  version: 2
  ethernets:
    ${IFACE}:
      dhcp4: false
      addresses:
        - ${IP}/24
EOF
chmod 600 /etc/netplan/90-conference-hostonly.yaml
netplan generate
netplan apply

hostnamectl set-hostname "$NAME"
sed -i "s/^127\.0\.1\.1.*/127.0.1.1 ${NAME}/" /etc/hosts
grep -q "conference-app" /etc/hosts || echo "192.168.56.10 conference-app" >> /etc/hosts
grep -q "conference-db"  /etc/hosts || echo "192.168.56.11 conference-db"  >> /etc/hosts

ip -br addr show "$IFACE"
