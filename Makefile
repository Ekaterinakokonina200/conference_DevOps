# Единая точка входа для всех команд проекта.
# Работает в Linux и в Git Bash на Windows (GNU make 4.x).
# Список команд: make help

ifeq ($(OS),Windows_NT)
VENV_BIN := .venv/Scripts
PYTHON_BOOT ?= py -3.12
else
VENV_BIN := .venv/bin
PYTHON_BOOT ?= python3.12
endif

PY := $(VENV_BIN)/python
VENV_STAMP := .venv/.installed

# Вывод Python в UTF-8 (иначе в Git Bash кириллица превращается в «кракозябры»)
export PYTHONUTF8 := 1

.DEFAULT_GOAL := help
.PHONY: help setup install run quality format format-check lint sast rules-check \
	test migrate migrate-down migration migrations-check backup restore \
	backup-check seed mutation critical-changes verify clean \
	container-env pin-images up down ps logs container-migrate container-backup \
	container-restore container-restore-new container-sql container-counts \
	container-check container-policy up-scale down-scale scale-check

help:
	@echo "Установка и запуск"
	@echo "  make setup             первоначальная настройка проекта (один раз)"
	@echo "  make install           установка зафиксированных зависимостей"
	@echo "  make run               запуск приложения на http://127.0.0.1:8000"
	@echo "Проверки"
	@echo "  make verify            ВСЕ обязательные проверки перед Pull Request"
	@echo "  make quality           форматирование и статический анализ (format-check, lint, sast)"
	@echo "  make format            автоматическое форматирование кода"
	@echo "  make format-check      проверка форматирования (ruff format)"
	@echo "  make lint              линтер (ruff check)"
	@echo "  make sast              анализ безопасности кода (bandit)"
	@echo "  make rules-check       запрет пропуска тестов и исключений без обоснования"
	@echo "  make test              unit- и интеграционные тесты, отчёты и покрытие"
	@echo "  make migrations-check  миграции на чистой и заполненной БД"
	@echo "  make backup-check      копия -> порча данных -> восстановление (тестовая БД)"
	@echo "  make mutation          мутационная проверка основной логики"
	@echo "  make critical-changes  изменённые критические файлы приёмки (для описания PR)"
	@echo "База данных"
	@echo "  make migrate           применить миграции к рабочей БД"
	@echo "  make migrate-down      откатить последнюю миграцию рабочей БД"
	@echo "  make migration m=\"...\" создать новую миграцию"
	@echo "  make seed              заполнить рабочую БД демонстрационными данными"
	@echo "  make backup            резервная копия рабочей БД в backups/"
	@echo "  make restore file=...  восстановление рабочей БД из копии"
	@echo "Контейнеры (ЛР 4)"
	@echo "  make container-check   ВСЕ проверки контейнерного окружения перед Pull Request"
	@echo "  make container-policy  только правила (latest, root, секреты, healthcheck, порты)"
	@echo "  make up-scale          доп. задание: Nginx + 2 экземпляра приложения (порт 8080)"
	@echo "  make scale-check       доп. задание: балансировка, отказ экземпляра, 429"
	@echo "  make down-scale        остановить окружение с Nginx"
	@echo "  make container-env     создать .env.docker со случайными паролями (один раз)"
	@echo "  make up                собрать образ и запустить окружение (db, migrate, app)"
	@echo "  make down              остановить и удалить контейнеры (данные в volume остаются)"
	@echo "  make ps                состояние контейнеров"
	@echo "  make logs s=app        журналы сервиса"
	@echo "  make pin-images        закрепить внешние образы по дайджесту"
	@echo "  make container-migrate миграции в контейнерном окружении"
	@echo "  make container-backup  резервная копия БД из контейнера в backups/"
	@echo "  make container-restore file=latest   восстановление в текущий том"
	@echo "  make container-restore-new file=latest volume=ИМЯ   восстановление в новый том"
	@echo "  make container-sql q=\"SELECT ...\"   SQL-запрос к БД в контейнере"
	@echo "  make container-counts  число записей в таблицах БД в контейнере"

$(VENV_STAMP): requirements.txt requirements-dev.txt
	$(PYTHON_BOOT) -m venv .venv
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r requirements-dev.txt
	$(PY) -c "import pathlib; pathlib.Path('$(VENV_STAMP)').touch()"

install: $(VENV_STAMP)

setup: $(VENV_STAMP)
	$(PY) tools/setup_project.py

run: $(VENV_STAMP)
	$(PY) -m uvicorn app.main:app --reload

reports:
	$(PY) -c "import os; os.makedirs('reports', exist_ok=True)"

format: $(VENV_STAMP)
	$(PY) -m ruff format .
	$(PY) -m ruff check --fix .

format-check: $(VENV_STAMP)
	$(PY) -m ruff format --check --diff .

lint: $(VENV_STAMP)
	$(PY) -m ruff check .

sast: $(VENV_STAMP) reports
	$(PY) -m bandit -c pyproject.toml -r app -q
	$(PY) -m bandit -c pyproject.toml -r app -q -f html -o reports/bandit.html
	@echo "bandit: замечаний нет, отчёт reports/bandit.html"

# Рекомендуемая общая команда курса: форматирование и статический анализ
quality: format-check lint sast

rules-check: $(VENV_STAMP)
	$(PY) tools/check_rules.py

test: $(VENV_STAMP) reports
	$(PY) -m pytest -m "not migrations" --cov --cov-report=term-missing \
		--cov-report=html:reports/htmlcov --cov-report=xml:reports/coverage.xml \
		--junitxml=reports/junit.xml

migrations-check: $(VENV_STAMP)
	$(PY) -m pytest -m migrations -p no:cacheprovider

backup-check: $(VENV_STAMP)
	$(PY) tools/backup_check.py

mutation: $(VENV_STAMP)
	$(PY) tools/mutation_check.py

critical-changes: $(VENV_STAMP)
	$(PY) tools/critical_changes.py "$(base)"

migrate: $(VENV_STAMP)
	$(PY) -m alembic upgrade head

migrate-down: $(VENV_STAMP)
	$(PY) -m alembic downgrade -1

migration: $(VENV_STAMP)
	$(PY) -m alembic revision --autogenerate -m "$(m)"

seed: $(VENV_STAMP)
	$(PY) tools/seed_demo_data.py

backup: $(VENV_STAMP)
	$(PY) tools/db_backup.py

restore: $(VENV_STAMP)
	$(PY) tools/db_restore.py "$(file)"

# Обязательный набор проверок. Убирать шаги запрещено (см. make rules-check).
verify: format-check lint sast rules-check test migrations-check backup-check mutation
	@echo "make verify: все проверки пройдены"

# ---------- Контейнерное окружение (ЛР №4) ----------
# Все настройки и пароли берутся из .env.docker (в Git не попадает).
COMPOSE := docker compose --env-file .env.docker

.env.docker:
	$(MAKE) container-env

container-env: $(VENV_STAMP)
	$(PY) tools/container_env.py

pin-images: $(VENV_STAMP)
	$(PY) tools/pin_images.py $(if $(update),--update)

# --wait: команда завершается, только когда app прошёл healthcheck
up: .env.docker
	$(COMPOSE) up -d --build --wait --wait-timeout 180 app

down: .env.docker
	$(COMPOSE) down

ps: .env.docker
	$(COMPOSE) ps -a

logs: .env.docker
	$(COMPOSE) logs --tail=100 $(s)

# Обязательная проверка контейнерного окружения (docs/container-rules.md).
# Изменения Dockerfile, compose.yaml, .dockerignore принимаются только после неё.
container-check: $(VENV_STAMP) reports
	$(PY) tools/container_check.py $(if $(keep),--keep)

container-policy: $(VENV_STAMP)
	$(PY) tools/container_check.py --policy-only $(if $(scale),--with-scale)

# Дополнительное задание: Nginx и два экземпляра приложения
COMPOSE_SCALE := $(COMPOSE) -f compose.yaml -f compose.scale.yaml

up-scale: .env.docker
	$(COMPOSE_SCALE) up -d --build --wait --wait-timeout 180

down-scale: .env.docker
	$(COMPOSE_SCALE) down

scale-check: .env.docker
	$(PY) tools/scale_check.py

CONTAINER_DB := $(PY) tools/container_db.py

container-migrate: .env.docker
	$(CONTAINER_DB) migrate

container-backup: .env.docker
	$(CONTAINER_DB) backup

container-restore: .env.docker
	$(CONTAINER_DB) restore --file "$(file)"

container-restore-new: .env.docker
	$(CONTAINER_DB) restore-new --file "$(file)" --volume "$(volume)"

container-sql: .env.docker
	$(CONTAINER_DB) sql --query "$(q)"

container-counts: .env.docker
	$(CONTAINER_DB) counts

clean:
	$(PY) -c "import shutil; [shutil.rmtree(p, ignore_errors=True) for p in ('reports', '.pytest_cache', '.ruff_cache')]"
