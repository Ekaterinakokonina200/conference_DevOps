"""Общие настройки pytest: отдельная тестовая конфигурация.

Переменные окружения задаются ДО импорта приложения, поэтому app.database
подключается к тестовой базе из .env.test, а не к рабочей базе из .env.
"""

import os
from pathlib import Path

import pytest
from dotenv import dotenv_values
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL") or dotenv_values(
    ROOT / ".env.test"
).get("TEST_DATABASE_URL")

if not TEST_DATABASE_URL:
    raise pytest.UsageError(
        "Не задан TEST_DATABASE_URL. Выполните make setup или создайте .env.test "
        "по образцу .env.test.example."
    )

if not make_url(TEST_DATABASE_URL).database.endswith("_test"):
    raise pytest.UsageError(
        "Тесты запускаются только на базе, имя которой оканчивается на _test: "
        "они удаляют и заново создают все таблицы."
    )

# Тестовые значения перекрывают .env (load_dotenv их не заменит).
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["JWT_SECRET_KEY"] = "test-only-secret-key-for-automated-tests-0123456789"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"


def pytest_collection_modifyitems(config, items):
    """Маркер по каталогу: tests/unit -> unit, tests/integration -> integration."""
    for item in items:
        parts = Path(str(item.fspath)).parts
        for marker in ("unit", "integration", "migrations"):
            if marker in parts:
                item.add_marker(marker)


def pytest_sessionfinish(session, exitstatus):
    """Запрет пропуска тестов: skipped/xfailed/xpassed делают прогон неуспешным."""
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is None:
        return
    banned = {
        kind: len(reporter.stats.get(kind, []))
        for kind in ("skipped", "xfailed", "xpassed")
    }
    if any(banned.values()):
        reporter.write_line(
            f"Запрещено пропускать тесты (docs/quality-rules.md): {banned}",
            red=True,
        )
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
