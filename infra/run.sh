#!/usr/bin/env bash
# Запуск Ansible на управляющем узле conference-app (ЛР №7).
#
#   bash infra/run.sh bootstrap <окружение>  подготовка чистой машины (один раз,
#                                           с паролем пользователя установщика)
#   bash infra/run.sh check     <окружение>  что изменится (--check --diff), без изменений
#   bash infra/run.sh apply     <окружение>  применить site.yml, затем повторный
#                                           запуск (должен быть changed=0) и verify.yml
#   bash infra/run.sh verify    <окружение>  только проверка узлов и приложения
#   bash infra/run.sh vault     <окружение>  создать или изменить зашифрованный
#                                           vault.yml окружения (редактор nano)
#
# Окружения: staging, production. Пароль vault: переменная ANSIBLE_VAULT_PASSWORD
# (pipeline), файл ~/.config/conference-infra/vault-<окружение> (права 600) или
# запрос с клавиатуры. Ansible ставится в отдельное виртуальное окружение
# пользователя строго по requirements-infra.txt.
set -Eeuo pipefail

MODE=${1:-}
ENV_NAME=${2:-}
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(cd "$HERE/.." && pwd)
INVENTORY=$HERE/inventories/$ENV_NAME
LOG_DIR=${INFRA_LOG_DIR:-$HOME/.cache/conference-infra/logs}
export ANSIBLE_CONFIG=$HERE/ansible.cfg
export ANSIBLE_FORCE_COLOR=${ANSIBLE_FORCE_COLOR:-1}

usage() {
  echo "Использование: bash infra/run.sh bootstrap|check|apply|verify|vault staging|production" >&2
  exit 2
}

[[ $MODE =~ ^(bootstrap|check|apply|verify|vault)$ ]] || usage
[[ $ENV_NAME =~ ^(staging|production)$ && -d $INVENTORY ]] || usage

summary() {
  [[ -n ${GITHUB_STEP_SUMMARY:-} ]] && printf '%s\n' "$@" >>"$GITHUB_STEP_SUMMARY"
  return 0
}

# --- Ansible строго нужной версии в виртуальном окружении пользователя
venv() {
  local hash dir
  hash=$(sha256sum "$ROOT/requirements-infra.txt" | cut -c1-12)
  dir=$HOME/.cache/conference-infra/venv-$hash
  if [[ ! -x $dir/bin/ansible-playbook ]]; then
    echo "== Установка Ansible (requirements-infra.txt) в $dir"
    python3 -m venv "$dir"
    "$dir/bin/pip" install --quiet --disable-pip-version-check -r "$ROOT/requirements-infra.txt"
  fi
  export PATH=$dir/bin:$PATH
}

# --- Пароль vault: из pipeline, из файла пользователя или с клавиатуры
VAULT_ARGS=()
VAULT_TMP=""
vault() {
  local file=$HOME/.config/conference-infra/vault-$ENV_NAME
  if [[ -n ${ANSIBLE_VAULT_PASSWORD:-} ]]; then
    VAULT_TMP=$(mktemp)
    chmod 600 "$VAULT_TMP"
    printf '%s\n' "$ANSIBLE_VAULT_PASSWORD" >"$VAULT_TMP"
    VAULT_ARGS=(--vault-password-file "$VAULT_TMP")
  elif [[ -r $file ]]; then
    [[ $(stat -c %a "$file") == 600 ]] || { echo "Права $file должны быть 600" >&2; exit 1; }
    VAULT_ARGS=(--vault-password-file "$file")
  else
    VAULT_ARGS=(--ask-vault-pass)
  fi
}
cleanup() { [[ -n $VAULT_TMP ]] && rm -f "$VAULT_TMP"; return 0; }
trap cleanup EXIT

# --- Ключи SSH узлов: при первом подключении добавляются в known_hosts.
# Узлы находятся в изолированной host-only сети (ЛР №2).
known_hosts() {
  local host
  mkdir -p "$HOME/.ssh" && chmod 700 "$HOME/.ssh"
  touch "$HOME/.ssh/known_hosts"
  for host in $(ansible-inventory -i "$INVENTORY" "${VAULT_ARGS[@]}" --list |
    MODE=$MODE python3 -c 'import json,os,sys; d=json.load(sys.stdin)["_meta"]["hostvars"]; local=os.environ["MODE"]=="bootstrap"; print(" ".join(v.get("ansible_host","") for v in d.values() if not (local and v.get("bootstrap_local"))))'); do
    if ! ssh-keygen -F "$host" >/dev/null; then
      echo "== Ключ узла $host добавлен в known_hosts"
      ssh-keyscan -H -t ed25519 "$host" 2>/dev/null >>"$HOME/.ssh/known_hosts"
    fi
  done
}

playbook() {
  # $1 — файл журнала, дальше — аргументы ansible-playbook
  local log=$1
  shift
  mkdir -p "$LOG_DIR"
  set +e
  ansible-playbook -i "$INVENTORY" "${VAULT_ARGS[@]}" "$@" 2>&1 | tee "$log"
  local code=${PIPESTATUS[0]}
  set -e
  return "$code"
}

cd "$HERE"
venv

if [[ $MODE == vault ]]; then
  # Секретные параметры окружения: создаются и меняются только в
  # зашифрованном виде; пароль — новый для каждого окружения
  file=inventories/$ENV_NAME/group_vars/all/vault.yml
  password_file=$HOME/.config/conference-infra/vault-$ENV_NAME
  args=()
  [[ -r $password_file ]] && args=(--vault-password-file "$password_file")
  export EDITOR=${EDITOR:-nano}
  if [[ -f $file ]]; then
    ansible-vault edit "${args[@]}" "$file"
  else
    echo "Образец содержимого: infra/vault.example.yml"
    ansible-vault create "${args[@]}" "$file"
  fi
  head -1 "$file"
  exit 0
fi

vault
STAMP=$(date +%Y%m%d-%H%M%S)

case $MODE in
  bootstrap)
    known_hosts
    echo "== Подготовка машины ($ENV_NAME): учётная запись Ansible"
    if [[ $ENV_NAME == staging ]]; then
      # staging — это сам управляющий узел: без SSH, только пароль sudo
      echo "   Локально от имени $(id -un) (пароль sudo — с клавиатуры)"
      playbook "$LOG_DIR/$STAMP-$ENV_NAME-bootstrap.log" bootstrap.yml --ask-become-pass
    else
      echo "   Пользователь установщика: ${BOOTSTRAP_USER:-katy} (пароли SSH и sudo — с клавиатуры)"
      playbook "$LOG_DIR/$STAMP-$ENV_NAME-bootstrap.log" bootstrap.yml \
        -e "ansible_user=${BOOTSTRAP_USER:-katy}" --ask-pass --ask-become-pass
    fi
    ;;
  check)
    known_hosts
    playbook "$LOG_DIR/$STAMP-$ENV_NAME-check.log" site.yml --check --diff
    ;;
  verify)
    known_hosts
    playbook "$LOG_DIR/$STAMP-$ENV_NAME-verify.log" verify.yml
    summary "### Инфраструктура $ENV_NAME: проверка пройдена"
    ;;
  apply)
    known_hosts
    echo "== [1/3] Применение site.yml ($ENV_NAME)"
    playbook "$LOG_DIR/$STAMP-$ENV_NAME-apply.log" site.yml --diff
    echo "== [2/3] Повторный запуск: изменений быть не должно"
    playbook "$LOG_DIR/$STAMP-$ENV_NAME-repeat.log" site.yml
    changed=$(sed 's/\x1b\[[0-9;]*m//g' "$LOG_DIR/$STAMP-$ENV_NAME-repeat.log" |
      grep -oE 'changed=[0-9]+' | awk -F= '{s += $2} END {print s + 0}')
    if [[ ${changed:-0} != 0 ]]; then
      echo "ОШИБКА: повторный запуск изменил задач: $changed — код не идемпотентен" >&2
      summary "### Инфраструктура $ENV_NAME: повторный запуск изменил $changed задач"
      exit 1
    fi
    echo "   ok  повторный запуск: changed=0"
    echo "== [3/3] Проверка узлов и приложения (verify.yml)"
    if [[ ! -f verify.yml ]]; then
      echo "   verify.yml ещё нет (появится на этапе 3) — проверка пропущена"
      exit 0
    fi
    playbook "$LOG_DIR/$STAMP-$ENV_NAME-verify.log" verify.yml
    summary "### Инфраструктура $ENV_NAME: применено, повторный запуск changed=0, проверка пройдена"
    echo "Инфраструктура $ENV_NAME в требуемом состоянии и проверена."
    ;;
esac
