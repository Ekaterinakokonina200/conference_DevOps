# Контейнерное окружение (ЛР №4)

## 1. Образ приложения

Файлы: `Dockerfile`, `.dockerignore`, `tools/pin_images.py`.

| Требование | Как выполнено |
|---|---|
| Воспроизводимая сборка | базовый образ `python:3.12.10-slim-bookworm` закреплён по дайджесту sha256 (`make pin-images`); зависимости ставятся строго по `requirements.txt` (`pip install --no-deps`) и проверяются `pip check`; контекст сборки ограничен белым списком `.dockerignore` |
| Непривилегированный пользователь | `USER 10001:10001` (пользователь `app` без оболочки и домашнего каталога); файлы приложения принадлежат `root`, процесс может их только читать |
| Настройки через окружение | `DATABASE_URL`, `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` передаются при запуске контейнера; файлы `.env*` в образ не попадают |
| Корректное завершение | форма exec в `CMD` — uvicorn является процессом № 1 и получает `SIGTERM`; `--timeout-graceful-shutdown 10` — текущие запросы завершаются, затем выход с кодом 0 |
| Проверка состояния | `HEALTHCHECK` обращается к `/health` встроенным Python (curl в slim-образе нет) |

Многоэтапная сборка: на этапе `builder` создаётся виртуальное окружение
`/opt/venv`, в итоговый образ копируется только оно и код приложения —
pip-кэша, исходников пакетов и инструментов сборки в образе нет.

### Сборка и запуск образа вручную

```bash
docker build -t conference-app:dev .
docker run --rm conference-app:dev id
```

Ожидается `uid=10001(app) gid=10001(app)`.

## 2. Compose: приложение и база данных

Файлы: `compose.yaml`, `.env.docker.example`, `tools/container_env.py`.

```text
            компьютер участника (Windows, Docker Desktop)
            http://127.0.0.1:8000
                    │  (порт опубликован только на 127.0.0.1)
   ── сеть frontend ┼──────────────────────────────
              ┌─────┴─────┐
              │    app    │  uvicorn, UID 10001, read-only ФС
              └─────┬─────┘
   ── сеть backend (internal: нет выхода наружу) ─────────
        ┌───────────┴───┐        ┌──────────┐
        │      db       │◄───────│ migrate  │ alembic upgrade head,
        │ PostgreSQL 17 │        └──────────┘ затем завершается
        └──────┬────────┘
          volume conference_pgdata  (порт 5432 наружу не публикуется)
```

| Требование | Как выполнено |
|---|---|
| Внутренняя сеть | `backend` с `internal: true`: БД видна только контейнерам этой сети и не имеет выхода в интернет; приложение подключено к `backend` и `frontend` |
| Volume | данные PostgreSQL в именованном томе `conference_pgdata` (имя задаёт `PGDATA_VOLUME`), он переживает `make down` и пересоздание контейнеров |
| Healthcheck | `db` — `pg_isready`; `app` — запрос к `/health`; `migrate` — разовая задача, проверка не отключается (она просто не успевает запуститься) |
| Порядок запуска | `db` (healthy) → `migrate` (завершился с кодом 0) → `app`; `make up` ждёт, пока `app` станет healthy |
| Порт БД | не публикуется; наружу опубликован только порт приложения и только на `127.0.0.1` |
| Настройки | все параметры и пароли — из `.env.docker` (создаётся `make container-env` со случайными паролями, в Git не попадает); обязательные переменные отмечены `:?` — без них Compose не запустится |
| Ограничения ресурсов | `deploy.resources.limits` (CPU, память, число процессов) у каждого сервиса, обоснование — `docs/container-resources.md` |
| Корректная остановка | uvicorn — процесс № 1 (форма exec, без промежуточной оболочки и init) и сам получает SIGTERM; `stop_grace_period: 20s` больше времени корректного завершения uvicorn (до 10 с) |
| Защита процессов | `read_only: true` + `tmpfs /tmp`, `cap_drop: ALL`, `no-new-privileges` |

### Команды

```bash
make container-env   # один раз: .env.docker со случайными паролями
make pin-images      # один раз: закрепить postgres по дайджесту
make up              # сборка образа и запуск, ждёт healthy
make ps              # состояние: db и app — healthy, migrate — exited (0)
make logs s=app      # журнал приложения
make down            # остановка; данные остаются в томе
```

## 3. Миграции, резервное копирование и восстановление в контейнерах

Файл: `tools/container_db.py`. Все действия выполняются утилитами PostgreSQL
внутри контейнера `db` (`docker compose exec`), поэтому версии `pg_dump` и
сервера совпадают, на компьютере не нужен установленный PostgreSQL, а пароль
не передаётся в командной строке.

| Команда | Что делает |
|---|---|
| `make container-migrate` | запускает разовый контейнер `migrate` (`alembic upgrade head`) и показывает версию схемы |
| `make container-backup` | `pg_dump -Fc` внутри `db` → `backups/container_conference_ГГГГММДД-ЧЧММСС.dump`, затем проверка архива `pg_restore --list` |
| `make container-restore file=latest` | проверяет архив; сохраняет текущее состояние (`_before-restore`); останавливает `app`; `pg_restore --clean --if-exists --single-transaction --exit-on-error`; запускает `app` и выводит число записей |
| `make container-restore-new file=latest volume=ИМЯ` | восстановление в **новый** том: `docker compose down` (старый том остаётся), запуск `db` с пустым томом `ИМЯ`, восстановление копии, запуск `app`; в `.env.docker` записывается `PGDATA_VOLUME=ИМЯ` |
| `make container-sql q="..."` | SQL-запрос к базе в контейнере |
| `make container-counts` | число записей в каждой таблице |

Откат после восстановления в новый том: вернуть в `.env.docker` прежнее
значение `PGDATA_VOLUME` и выполнить `make down && make up` — старый том не
удалялся.
