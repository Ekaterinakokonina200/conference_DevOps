"""Восстановление рабочей базы данных из копии (make restore file=...).

Перед восстановлением текущее состояние базы автоматически сохраняется
в backups/..._before-restore.dump — восстановление можно отменить.
Восстановление выполняется одной транзакцией: при ошибке база остаётся
в прежнем состоянии.

Примеры:
  make restore file=backups/conference_20261002-153000.dump
  make restore file=latest      # самая свежая копия рабочей базы
"""

import subprocess
import sys
from pathlib import Path

from db_backup import BACKUP_DIR, backup_path, create_backup
from pgtools import ROOT, database_url, find_tool, libpq_env
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL


def restore_backup(url: URL, path: Path) -> None:
    subprocess.run(
        [
            find_tool("pg_restore"),
            "--clean",
            "--if-exists",
            "--no-owner",
            "--no-privileges",
            "--single-transaction",
            "--exit-on-error",
            "--dbname",
            url.database,
            str(path),
        ],
        env=libpq_env(url),
        check=True,
    )


def row_counts(url: URL) -> dict[str, int]:
    engine = create_engine(url)
    with engine.connect() as connection:
        tables = sorted(inspect(connection).get_table_names())
        counts = {
            table: connection.scalar(text(f'SELECT count(*) FROM "{table}"'))
            for table in tables
        }
    engine.dispose()
    return counts


def resolve(argument: str, url: URL) -> Path:
    if argument in ("", "latest"):
        candidates = sorted(BACKUP_DIR.glob(f"{url.database}_*.dump"))
        candidates = [p for p in candidates if "before-restore" not in p.name]
        if not candidates:
            sys.exit("В каталоге backups/ нет копий. Сначала выполните make backup.")
        return candidates[-1]
    path = Path(argument)
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        sys.exit(f"Файл копии не найден: {argument}")
    return path


def main() -> None:
    url = database_url()
    source = resolve(sys.argv[1] if len(sys.argv) > 1 else "", url)

    check = subprocess.run(
        [find_tool("pg_restore"), "--list", str(source)],
        capture_output=True,
        text=True,
        errors="replace",
    )
    if check.returncode != 0:
        sys.exit(
            f"Файл {source.name} повреждён или не является копией pg_dump: "
            f"{check.stderr.strip()}\nВосстановление не выполнялось, база не изменена."
        )

    print("Сохраняю текущее состояние перед восстановлением...")
    safety = create_backup(url, backup_path(url, "_before-restore"))

    print(f"Восстанавливаю базу {url.database} из {source.relative_to(ROOT)} ...")
    try:
        restore_backup(url, source)
    except subprocess.CalledProcessError:
        sys.exit(
            "Ошибка восстановления. Транзакция отменена, база осталась в прежнем "
            f"состоянии. Копия этого состояния: {safety.relative_to(ROOT)}"
        )
    print("Восстановление завершено. Записей в таблицах:")
    for table, count in row_counts(url).items():
        print(f"  {table:16} {count}")


if __name__ == "__main__":
    main()
