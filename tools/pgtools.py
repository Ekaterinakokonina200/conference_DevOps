"""Общие функции для служебных скриптов: настройки и утилиты PostgreSQL."""

import glob
import os
import shutil
import sys
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy.engine import URL, make_url

ROOT = Path(__file__).resolve().parents[1]


def read_setting(name: str, env_file: str = ".env") -> str:
    """Берёт настройку из переменной окружения, иначе из файла .env/.env.test."""
    value = os.getenv(name) or dotenv_values(ROOT / env_file).get(name)
    if not value:
        sys.exit(f"Ошибка: не задан {name} (ни в окружении, ни в {env_file}).")
    return value


def database_url() -> URL:
    """Адрес рабочей базы из DATABASE_URL."""
    return make_url(read_setting("DATABASE_URL"))


def test_database_url() -> URL:
    """Адрес тестовой базы из TEST_DATABASE_URL с защитой от ошибки."""
    url = make_url(read_setting("TEST_DATABASE_URL", ".env.test"))
    ensure_test_database(url)
    return url


def ensure_test_database(url: URL) -> None:
    """Не даёт запустить разрушающие действия на рабочей базе."""
    if not (url.database or "").endswith("_test"):
        sys.exit(
            f"Ошибка: база '{url.database}' не похожа на тестовую. "
            "Имя тестовой базы должно оканчиваться на _test."
        )


def find_tool(name: str) -> str:
    """Ищет pg_dump / pg_restore / psql: PG_BIN, PATH, стандартный путь Windows."""
    exe = name + (".exe" if os.name == "nt" else "")
    pg_bin = os.getenv("PG_BIN")
    if pg_bin and Path(pg_bin, exe).exists():
        return str(Path(pg_bin, exe))
    found = shutil.which(name)
    if found:
        return found
    if os.name == "nt":
        pattern = os.path.join(r"C:\Program Files\PostgreSQL", "*", "bin", exe)
        candidates = sorted(
            glob.glob(pattern),
            key=lambda p: int(Path(p).parents[1].name.split(".")[0]),
        )
        if candidates:
            return candidates[-1]
    sys.exit(
        f"Ошибка: не найдена утилита {name}. Добавьте каталог bin PostgreSQL "
        "в PATH или укажите его в переменной PG_BIN."
    )


def libpq_env(url: URL) -> dict[str, str]:
    """Параметры подключения для утилит PostgreSQL.

    Пароль передаётся через переменную PGPASSWORD, а не в командной строке,
    чтобы он не был виден в списке процессов и в истории команд.
    """
    env = dict(os.environ)
    env.update(
        {
            "PGHOST": url.host or "localhost",
            "PGPORT": str(url.port or 5432),
            "PGUSER": url.username or "postgres",
            "PGDATABASE": url.database or "",
        }
    )
    if url.password:
        env["PGPASSWORD"] = str(url.password)
    return env
