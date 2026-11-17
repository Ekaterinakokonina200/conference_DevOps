#!/usr/bin/env bash
# Развёртывание релиза в предэксплуатационное окружение staging (ЛР №6).
#
# Запускается на сервере conference-app (192.168.56.10) от имени отдельного
# пользователя deploy: из GitHub Actions (self-hosted runner с меткой staging)
# или администратором вручную (sudo -iu deploy).
#
#   deploy.sh deploy <тег>   развернуть ${APP_IMAGE}:<тег>, тег: sha-xxxxxxx или X.Y.Z
#   deploy.sh rollback       вернуть предыдущую принятую версию
#   deploy.sh status         что работает сейчас и история выпусков
#
# Порядок развёртывания:
#   1. проверка тега и файла настроек staging.env (до любых изменений);
#   2. docker pull образа из registry — на сервере образ НЕ собирается;
#   3. резервная копия БД, миграции из нового образа;
#   4. замена контейнера app, ожидание healthcheck;
#   5. проверка релиза tools/release_check.py: контейнеры, /health, /version,
#      веб-интерфейс, основной сценарий.
# Выпуск принимается (last_good) только если прошли все шаги. Ошибка на
# шагах 1–2 оставляет работающую версию без изменений; ошибка на шагах 3–5
# делает выпуск неуспешным (код выхода 1), возврат — deploy.sh rollback.
set -Eeuo pipefail

STAGING_DIR=${STAGING_DIR:-/srv/conference-staging}
ENV_FILE=$STAGING_DIR/staging.env
STATE_DIR=$STAGING_DIR/state
BACKUP_DIR=$STAGING_DIR/backups
RELEASES_LOG=$STATE_DIR/releases.log
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)
COMPOSE_FILE=$HERE/compose.yaml
PROJECT=conference-staging
HEALTH_TIMEOUT=${HEALTH_TIMEOUT:-90}
KEEP_BACKUPS=5
TAG_RE='^(sha-[0-9a-f]{7}|[0-9]+\.[0-9]+\.[0-9]+)$'
REQUIRED_VARS=(APP_IMAGE APP_BIND APP_PORT POSTGRES_DB POSTGRES_USER
  POSTGRES_PASSWORD JWT_SECRET_KEY ACCESS_TOKEN_EXPIRE_MINUTES)

TAG=""
MODE=""
SWITCHED=0

say() { printf '\n== %s\n' "$*"; }
ok() { printf '  ok  %s\n' "$*"; }

summary() {
  # Итог в сводке запуска GitHub Actions (если скрипт запущен из Actions)
  [[ -n ${GITHUB_STEP_SUMMARY:-} ]] && printf '%s\n' "$*" >>"$GITHUB_STEP_SUMMARY"
  return 0
}

state() { cat "$STATE_DIR/$1" 2>/dev/null || echo "-"; }
set_state() { printf '%s\n' "$2" >"$STATE_DIR/$1"; }

log_release() {
  printf '%s  %-8s  %-12s  %s\n' "$(date '+%F %T')" "$MODE" "$TAG" "$1" >>"$RELEASES_LOG"
}

die() {
  printf '\n  ОШИБКА  %s\n' "$1" >&2
  if [[ -n $TAG ]]; then
    log_release "FAILED  $1"
    if ((SWITCHED)); then
      printf '\nВыпуск %s НЕ ПРИНЯТ: в staging работает непроверенная версия.\n' "$TAG" >&2
      if [[ $TAG == "$(state last_good)" ]]; then
        printf 'Этот образ раньше уже был принят — вероятная причина в настройках %s.\n' \
          "$ENV_FILE" >&2
        printf 'Исправьте настройки и повторите развертывание (или выполните rollback).\n' >&2
      else
        printf 'Вернуть последнюю принятую версию (%s): Actions -> Deploy staging -> rollback\n' \
          "$(state last_good)" >&2
      fi
    else
      printf '\nВыпуск %s НЕ ПРИНЯТ. Работающая версия не изменена: %s\n' "$TAG" \
        "$(state running)" >&2
    fi
    summary "### Выпуск \`$TAG\` в staging: НЕ ПРИНЯТ" "" "$1"
  fi
  exit 1
}

trap 'die "непредвиденная ошибка в строке $LINENO: $BASH_COMMAND"' ERR

env_value() { sed -n "s/^$1=//p" "$ENV_FILE" | tail -n 1; }

compose() {
  APP_TAG=$TAG docker compose -p "$PROJECT" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

lock() {
  mkdir -p "$STATE_DIR" "$BACKUP_DIR"
  exec 9>"$STATE_DIR/deploy.lock"
  flock -n 9 || die "уже выполняется другое развертывание staging — дождитесь его окончания"
}

check_tag() {
  [[ $TAG =~ $TAG_RE ]] ||
    die "неверный формат тега «$TAG»: нужен sha-<7 символов SHA> или X.Y.Z (без v)"
  ok "тег $TAG"
}

check_env() {
  [[ -r $ENV_FILE ]] || die "нет файла настроек $ENV_FILE"
  local var value missing=()
  for var in "${REQUIRED_VARS[@]}"; do
    value=$(env_value "$var")
    if [[ -z $value ]]; then
      missing+=("$var")
    elif [[ $value == CHANGE_ME* ]]; then
      die "в $ENV_FILE у $var осталось значение-заглушка CHANGE_ME"
    fi
  done
  ((${#missing[@]} == 0)) ||
    die "в $ENV_FILE не задана переменная ${missing[*]} — развертывание остановлено до изменений"
  if [[ $(stat -c %a "$ENV_FILE") != 600 ]]; then
    printf '  предупреждение: права %s у %s, нужно 600\n' "$(stat -c %a "$ENV_FILE")" "$ENV_FILE"
  fi
  ok "staging.env: заданы все ${#REQUIRED_VARS[@]} обязательных настроек"
}

pull_image() {
  local out
  if ! out=$(docker pull "$IMAGE" 2>&1); then
    if grep -qiE 'manifest unknown|not found|no such manifest' <<<"$out"; then
      die "образ $IMAGE не найден в registry (неверный тег?)"
    fi
    die "registry недоступен, образ $IMAGE не получен: $(tail -n 1 <<<"$out")"
  fi
  REVISION=$(docker image inspect -f '{{index .Config.Labels "org.opencontainers.image.revision"}}' "$IMAGE")
  VERSION=$(docker image inspect -f '{{index .Config.Labels "org.opencontainers.image.version"}}' "$IMAGE")
  if [[ $TAG =~ ^[0-9] && -n $VERSION && $VERSION != "$TAG" ]]; then
    die "тег образа $TAG, а версия приложения в образе $VERSION — выпуск собран неверно"
  fi
  ok "образ получен из registry: $IMAGE"
  ok "метки образа: version=${VERSION:-?} revision=${REVISION:-?}"
}

backup_db() {
  if [[ -z $(compose ps -q --status running db) ]]; then
    ok "БД ещё не запущена — резервная копия не нужна (первое развертывание)"
    return
  fi
  local file
  file="$BACKUP_DIR/$(date +%Y%m%d-%H%M%S)-before-$TAG.dump"
  # Переменные раскрываются внутри контейнера db, поэтому одинарные кавычки
  # shellcheck disable=SC2016
  compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' >"$file"
  ok "резервная копия БД: $file ($(du -h "$file" | cut -f1))"
  # Храним только последние копии
  find "$BACKUP_DIR" -name '*.dump' -printf '%T@ %p\n' | sort -rn | tail -n +$((KEEP_BACKUPS + 1)) |
    cut -d' ' -f2- | xargs -r rm -f --
}

switch_app() {
  compose up -d --wait --wait-timeout 60 db >/dev/null || die "БД staging не запустилась (db не healthy)"
  ok "db: healthy"
  backup_db
  compose --profile migrate run --rm -T migrate || die "миграции из образа $IMAGE не применились"
  ok "миграции применены (alembic upgrade head)"
  compose up -d --no-deps --force-recreate app
  SWITCHED=1
  set_state running "$TAG"
  set_state running_status "не принят" # до успешной проверки релиза
  ok "app запущен из образа $IMAGE"
}

wait_healthy() {
  local cid status deadline=$((SECONDS + HEALTH_TIMEOUT))
  cid=$(compose ps -q app)
  while ((SECONDS < deadline)); do
    status=$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{end}}' "$cid")
    if [[ $status == healthy ]]; then
      ok "app: healthcheck healthy"
      return
    fi
    sleep 3
  done
  printf '\n  последние строки журнала app:\n' >&2
  compose logs --no-color --tail 30 app >&2 || true
  die "app не прошёл healthcheck за ${HEALTH_TIMEOUT} с (состояние: ${status:-нет})"
}

release_check() {
  local args=(--url "http://$(env_value APP_BIND):$(env_value APP_PORT)"
    --project "$PROJECT" --expect-image "$IMAGE")
  [[ -n $VERSION ]] && args+=(--expect-version "$VERSION")
  [[ -n $REVISION && $REVISION != local ]] && args+=(--expect-revision "$REVISION")
  python3 "$ROOT/tools/release_check.py" "${args[@]}" ||
    die "проверка релиза после развертывания не пройдена"
}

accept() {
  local last
  last=$(state last_good)
  if [[ $last != "$TAG" ]]; then
    set_state previous_good "$last"
    set_state last_good "$TAG"
  fi
  set_state running_status "принят"
  log_release "OK      revision=${REVISION:-?}"
  summary "### Выпуск \`$TAG\` в staging: ПРИНЯТ" "" \
    "Образ \`$IMAGE\`, коммит \`${REVISION:-?}\`, все проверки релиза пройдены."
  printf '\nВыпуск %s ПРИНЯТ: все проверки после развертывания пройдены.\n' "$TAG"
  printf 'Предыдущая принятая версия (для возврата): %s\n' "$(state previous_good)"
}

deploy() {
  TAG=$1
  say "Выпуск $TAG в staging ($MODE)"
  check_tag
  check_env
  IMAGE="$(env_value APP_IMAGE):$TAG"
  say "Образ из registry"
  pull_image
  say "Развертывание"
  switch_app
  wait_healthy
  say "Проверка релиза"
  release_check
  accept
}

rollback() {
  local running last previous target
  running=$(state running)
  last=$(state last_good)
  previous=$(state previous_good)
  if [[ $last != - && $(state running_status) != принят ]]; then
    target=$last # работающий выпуск не принят — возвращаем последний принятый
  elif [[ $previous != - ]]; then
    target=$previous # возвращаем версию, принятую до текущей
  else
    die "нет предыдущей принятой версии для возврата"
  fi
  printf 'Возврат: работает %s, возвращаем %s\n' "$running" "$target"
  deploy "$target"
}

status() {
  printf 'Работает:                    %s (%s)\n' "$(state running)" "$(state running_status)"
  printf 'Последняя принятая версия:   %s\n' "$(state last_good)"
  printf 'Предыдущая принятая версия:  %s\n' "$(state previous_good)"
  say "Контейнеры"
  TAG=$(state running) compose ps 2>/dev/null || true
  TAG=""
  say "История выпусков (последние 10)"
  tail -n 10 "$RELEASES_LOG" 2>/dev/null || echo "  выпусков ещё не было"
}

main() {
  MODE=${1:-}
  case $MODE in
    deploy)
      [[ -n ${2:-} ]] || die "укажите тег: deploy.sh deploy sha-xxxxxxx"
      lock
      deploy "$2"
      ;;
    rollback)
      lock
      rollback
      ;;
    status)
      mkdir -p "$STATE_DIR"
      status
      ;;
    *)
      echo "Использование: deploy.sh deploy <тег> | rollback | status" >&2
      exit 2
      ;;
  esac
}

main "$@"
