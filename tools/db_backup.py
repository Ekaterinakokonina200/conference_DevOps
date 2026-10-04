"""Резервная копия рабочей базы данных (make backup).

Копия создаётся утилитой pg_dump в формате custom (сжатый архив, из которого
pg_restore восстанавливает и схему, и данные, и таблицу alembic_version).
Файл сохраняется в каталог backups/ (в Git не попадает). После создания
архив сразу проверяется: pg_restore --list должен его прочитать.
"""

import subprocess
from datetime import datetime
from pathlib import Path

from pgtools import ROOT, database_url, find_tool, libpq_env
from sqlalchemy.engine import URL

BACKUP_DIR = ROOT / "backups"


def create_backup(url: URL, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            find_tool("pg_dump"),
            "--format=custom",
            "--no-owner",
            "--no-privileges",
            "--file",
            str(path),
            url.database,
        ],
        env=libpq_env(url),
        check=True,
    )
    listing = subprocess.run(
        [find_tool("pg_restore"), "--list", str(path)],
        capture_output=True,
        text=True,
        errors="replace",
        check=True,
    )
    tables = sum(" TABLE DATA " in line for line in listing.stdout.splitlines())
    print(f"Копия создана: {path.relative_to(ROOT)}")
    print(f"  размер: {path.stat().st_size} байт, таблиц с данными: {tables}")
    return path


def backup_path(url: URL, suffix: str = "") -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return BACKUP_DIR / f"{url.database}_{stamp}{suffix}.dump"


def main() -> None:
    url = database_url()
    create_backup(url, backup_path(url))


if __name__ == "__main__":
    main()
