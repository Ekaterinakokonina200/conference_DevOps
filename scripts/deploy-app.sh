#!/usr/bin/env bash
# Развёртывание или обновление приложения на сервере приложения.
# Использование: sudo bash scripts/deploy-app.sh
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/Ekaterinakokonina200/conference_DevOps.git}"
APP_DIR="/opt/conference/app"
CONF_DIR="/etc/conference"
ENV_FILE="${CONF_DIR}/conference.env"

apt-get update
apt-get install -y python3 python3-venv python3-pip git curl

id conference >/dev/null 2>&1 || \
  adduser --system --group --no-create-home --home /nonexistent --shell /usr/sbin/nologin conference

mkdir -p /opt/conference
if [ -d "${APP_DIR}/.git" ]; then
  git -C "$APP_DIR" pull --ff-only
else
  git clone "$REPO_URL" "$APP_DIR"
fi

python3 -m venv "${APP_DIR}/.venv"
"${APP_DIR}/.venv/bin/pip" install --upgrade pip
"${APP_DIR}/.venv/bin/pip" install -r "${APP_DIR}/requirements.txt"

mkdir -p "$CONF_DIR"
if [ ! -f "$ENV_FILE" ]; then
  cp "${APP_DIR}/deploy/conference.env.example" "$ENV_FILE"
  chown -R root:conference "$CONF_DIR"; chmod 750 "$CONF_DIR"; chmod 640 "$ENV_FILE"
  echo "Создан ${ENV_FILE}. Заполните пароль БД и JWT_SECRET_KEY и запустите скрипт снова."
  exit 1
fi

# Проверка файла настроек: убрать \r и убедиться, что строки не склеены
sed -i 's/\r$//' "$ENV_FILE"
for KEY in DATABASE_URL JWT_SECRET_KEY JWT_ALGORITHM ACCESS_TOKEN_EXPIRE_MINUTES; do
  grep -Eq "^${KEY}=[^ ]+$" "$ENV_FILE" || { echo "Ошибка в ${ENV_FILE}: строка ${KEY}"; exit 1; }
done
if grep -q "CHANGE_ME" "$ENV_FILE"; then
  echo "В ${ENV_FILE} остались значения CHANGE_ME"; exit 1
fi

chown -R root:conference "$CONF_DIR"; chmod 750 "$CONF_DIR"; chmod 640 "$ENV_FILE"
chown -R root:conference "$APP_DIR"
chmod -R u=rwX,g=rX,o= "$APP_DIR"
chmod 755 /opt/conference

sudo -u conference bash -c "set -a; . ${ENV_FILE}; set +a; cd ${APP_DIR} && .venv/bin/alembic upgrade head"

install -m 644 "${APP_DIR}/deploy/conference.service" /etc/systemd/system/conference.service
systemctl daemon-reload
systemctl enable conference
systemctl restart conference
sleep 2
systemctl is-active conference
curl -s http://127.0.0.1:8000/health; echo
