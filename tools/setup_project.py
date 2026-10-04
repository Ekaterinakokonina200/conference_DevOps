"""Единый сценарий первоначальной настройки проекта.

Запускается командой make setup (после создания .venv и установки
зависимостей). Повторный запуск безопасен: уже сделанные шаги пропускаются.

Шаги:
1. проверка версии Python;
2. создание .env и .env.test из шаблонов, генерация JWT_SECRET_KEY;
3. проверка, что пароль PostgreSQL вписан в .env и .env.test;
4. проверка наличия pg_dump, pg_restore, psql;
5. создание рабочей и тестовой баз данных, если их нет;
6. применение миграций к рабочей базе.
"""

import platform
import secrets
import shutil
import subprocess
import sys

from pgtools import (
    ROOT,
    database_url,
    ensure_test_database,
    find_tool,
    test_database_url,
)
from sqlalchemy import create_engine, text

PLACEHOLDER_PASSWORD = "LOCAL_PASSWORD"
PLACEHOLDER_SECRET = "GENERATE_A_RANDOM_SECRET_FOR_LOCAL_ENV"


def step(number: int, title: str) -> None:
    print(f"\n[{number}/6] {title}")


def check_python() -> None:
    step(1, "Версия Python")
    version = platform.python_version()
    if tuple(int(part) for part in version.split(".")[:2]) < (3, 12):
        sys.exit(f"Нужен Python 3.12 или новее, сейчас {version}.")
    print(f"  Python {version} — подходит")


def create_env_files() -> None:
    step(2, "Файлы настроек .env и .env.test")
    templates = {".env": ".env.example", ".env.test": ".env.test.example"}
    for target, template in templates.items():
        path = ROOT / target
        if path.exists():
            print(f"  {target} уже есть — не изменяю")
            continue
        shutil.copyfile(ROOT / template, path)
        print(f"  {target} создан из {template}")

    env_path = ROOT / ".env"
    content = env_path.read_text(encoding="utf-8")
    if PLACEHOLDER_SECRET in content:
        content = content.replace(PLACEHOLDER_SECRET, secrets.token_hex(32))
        env_path.write_text(content, encoding="utf-8")
        print("  JWT_SECRET_KEY сгенерирован автоматически")


def check_passwords() -> None:
    step(3, "Пароль PostgreSQL в настройках")
    missing = [
        name
        for name in (".env", ".env.test")
        if PLACEHOLDER_PASSWORD in (ROOT / name).read_text(encoding="utf-8")
    ]
    if missing:
        print(
            f"  В файлах {', '.join(missing)} вместо пароля стоит "
            f"{PLACEHOLDER_PASSWORD}.\n"
            "  Впишите пароль пользователя postgres вашего локального PostgreSQL\n"
            "  и запустите make setup ещё раз. Эти файлы в Git не попадают."
        )
        sys.exit(1)
    print("  пароль указан")


def check_tools() -> None:
    step(4, "Утилиты PostgreSQL")
    for tool in ("psql", "pg_dump", "pg_restore"):
        print(f"  {tool}: {find_tool(tool)}")


def create_databases() -> None:
    step(5, "Рабочая и тестовая базы данных")
    test_url = test_database_url()
    ensure_test_database(test_url)
    for url in (database_url(), test_url):
        admin = create_engine(
            url.set(database="postgres"), isolation_level="AUTOCOMMIT"
        )
        with admin.connect() as connection:
            exists = connection.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": url.database},
            )
            if exists:
                print(f"  база {url.database} уже есть")
            else:
                connection.execute(text(f'CREATE DATABASE "{url.database}"'))
                print(f"  база {url.database} создана")
        admin.dispose()


def migrate() -> None:
    step(6, "Миграции рабочей базы (alembic upgrade head)")
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"], cwd=ROOT, check=True
    )


def main() -> None:
    check_python()
    create_env_files()
    check_passwords()
    check_tools()
    create_databases()
    migrate()
    print(
        "\nГотово. Дальше:\n"
        "  make run     — запустить приложение (http://127.0.0.1:8000)\n"
        "  make verify  — полный набор проверок перед Pull Request"
    )


if __name__ == "__main__":
    main()
