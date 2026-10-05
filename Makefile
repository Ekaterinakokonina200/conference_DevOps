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
	backup-check seed mutation critical-changes verify clean

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

clean:
	$(PY) -c "import shutil; [shutil.rmtree(p, ignore_errors=True) for p in ('reports', '.pytest_cache', '.ruff_cache')]"
