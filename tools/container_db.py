"""Обслуживание базы данных в контейнерном окружении (ЛР №4).

Все действия выполняются утилитами PostgreSQL внутри контейнера db
(docker compose exec), поэтому на компьютере не нужны ни psql, ни pg_dump,
а пароль не передаётся в командной строке: внутри контейнера он уже есть
в переменных окружения.

Команды (через make):
    make container-migrate                      миграции (сервис migrate)
    make container-backup                       копия в backups/container_*.dump
    make container-restore file=latest          восстановление в текущий том
    make container-restore-new file=latest volume=conference_pgdata_restored
                                                восстановление в НОВЫЙ том
    make container-sql q="SELECT ..."           SQL-запрос к базе
    make container-counts                       число записей в таблицах

Скрипт используется и проверкой make container-check — с отдельным
именем проекта и файлом настроек (класс Compose).
"""

import argparse
import datetime
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKUP_DIR = ROOT / "backups"
# psql внутри контейнера: имя пользователя и базы берутся из переменных
# окружения контейнера db, SQL передаётся через стандартный ввод.
IN_DB = 'psql -X -q -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'

COUNTS_SQL = (
    "SELECT table_name, (xpath('/row/c/text()', query_to_xml("
    "format('SELECT count(*) AS c FROM %I.%I', table_schema, table_name), "
    "false, true, '')))[1]::text::int "
    "FROM information_schema.tables "
    "WHERE table_schema = 'public' AND table_type = 'BASE TABLE' "
    "AND table_name <> 'alembic_version' ORDER BY 1"
)


class Compose:
    """docker compose с файлом настроек и (необязательно) своим проектом."""

    def __init__(self, env_file: Path, project: str | None = None, env=None):
        self.env_file, self.project, self.extra = env_file, project, env or {}
        self.base = ["docker", "compose", "--env-file", str(env_file)]
        if project:
            self.base += ["-p", project]
        self.env = dict(os.environ, **self.extra)

    def with_env(self, **extra) -> "Compose":
        """Тот же проект, но с переопределёнными переменными (например, томом)."""
        return Compose(self.env_file, self.project, {**self.extra, **extra})

    def run(self, *args, input_bytes=None, check=True, capture=True):
        result = subprocess.run(
            self.base + list(args),
            cwd=ROOT,
            env=self.env,
            input=input_bytes,
            capture_output=capture,
        )
        if check and result.returncode != 0:
            err = result.stderr.decode("utf-8", "replace") if capture else ""
            sys.exit(f"Ошибка: docker compose {' '.join(args)}\n{err.strip()}")
        return result

    def db_shell(self, command: str, input_bytes=None, check=True):
        return self.run(
            "exec",
            "-T",
            "db",
            "sh",
            "-c",
            command,
            input_bytes=input_bytes,
            check=check,
        )


def sql(compose: Compose, query: str, *options: str) -> str:
    command = " ".join([IN_DB, *options])
    out = compose.db_shell(command, input_bytes=query.encode("utf-8")).stdout
    return out.decode("utf-8", "replace")


def counts(compose: Compose) -> dict[str, int]:
    out = sql(compose, COUNTS_SQL + ";", "-At", "-F", "'|'")
    result = {}
    for line in out.splitlines():
        if "|" in line:
            table, value = line.split("|", 1)
            result[table] = int(value)
    return result


def print_counts(title: str, table_counts: dict[str, int]) -> None:
    print(title)
    for table, value in table_counts.items():
        print(f"  {table:16} {value}")


def backup(compose: Compose, suffix: str = "", directory: Path = BACKUP_DIR) -> Path:
    directory.mkdir(exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = directory / f"container_conference_{stamp}{suffix}.dump"
    dump = compose.db_shell('pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc').stdout
    path.write_bytes(dump)
    listing = compose.db_shell("pg_restore --list", input_bytes=dump).stdout
    tables = sum(1 for line in listing.decode().splitlines() if " TABLE DATA " in line)
    print(f"Копия создана: {path.relative_to(ROOT).as_posix()}")
    print(f"  размер: {len(dump)} байт, таблиц с данными: {tables}")
    return path


def resolve(argument: str) -> Path:
    if argument in ("", "latest"):
        candidates = sorted(
            p
            for p in BACKUP_DIR.glob("container_conference_*.dump")
            if "_before-restore" not in p.name
        )
        if not candidates:
            sys.exit("В backups/ нет контейнерных копий: make container-backup.")
        return candidates[-1]
    path = Path(argument)
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        sys.exit(f"Файл копии не найден: {argument}")
    return path


def check_archive(compose: Compose, data: bytes, name: str) -> None:
    result = compose.db_shell("pg_restore --list", input_bytes=data, check=False)
    if result.returncode != 0:
        sys.exit(
            f"Файл {name} повреждён или не является копией pg_dump: "
            f"{result.stderr.decode('utf-8', 'replace').strip()}\n"
            "Восстановление не выполнялось, база не изменена."
        )


def pg_restore(compose: Compose, data: bytes) -> None:
    result = compose.db_shell(
        'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists '
        "--single-transaction --exit-on-error --no-owner",
        input_bytes=data,
        check=False,
    )
    if result.returncode != 0:
        sys.exit(
            "Ошибка восстановления, транзакция отменена, база не изменена:\n"
            + result.stderr.decode("utf-8", "replace").strip()
        )


def restore(compose: Compose, argument: str) -> None:
    source = resolve(argument)
    data = source.read_bytes()
    check_archive(compose, data, source.name)
    print("Сохраняю текущее состояние перед восстановлением...")
    backup(compose, "_before-restore")
    print("Останавливаю приложение на время восстановления...")
    compose.run("stop", "app")
    print(f"Восстанавливаю из {source.relative_to(ROOT).as_posix()} ...")
    pg_restore(compose, data)
    compose.run("up", "-d", "--wait", "--wait-timeout", "120", "app")
    print_counts("Восстановление завершено. Записей в таблицах:", counts(compose))


def volume_exists(name: str) -> bool:
    return (
        subprocess.run(
            ["docker", "volume", "inspect", name], capture_output=True
        ).returncode
        == 0
    )


def set_env_value(env_file: Path, key: str, value: str) -> None:
    lines = env_file.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            break
    else:
        lines.append(f"{key}={value}")
    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def restore_new_volume(
    compose: Compose, argument: str, volume: str, env_file=None
) -> Compose:
    """Восстановление в новый том; возвращает Compose, работающий с этим томом."""
    if not volume:
        sys.exit("Укажите имя нового тома: volume=conference_pgdata_restored")
    if volume_exists(volume):
        sys.exit(f"Том {volume} уже существует — выберите другое имя.")
    source = resolve(argument)
    data = source.read_bytes()
    check_archive(compose, data, source.name)
    print("Останавливаю окружение (старый том не удаляется)...")
    compose.run("down")
    new = compose.with_env(PGDATA_VOLUME=volume)
    print(f"Запускаю БД с новым пустым томом {volume}...")
    new.run("up", "-d", "--wait", "--wait-timeout", "120", "db")
    print(f"Восстанавливаю из {source.name} ...")
    pg_restore(new, data)
    new.run("up", "-d", "--wait", "--wait-timeout", "180", "app")
    if env_file and Path(env_file).exists():
        set_env_value(Path(env_file), "PGDATA_VOLUME", volume)
        print(f"В {Path(env_file).name} записано PGDATA_VOLUME={volume}")
    print_counts(
        f"Восстановление в новый том {volume} завершено. Записей в таблицах:",
        counts(new),
    )
    return new


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=["migrate", "backup", "restore", "restore-new", "sql", "counts"],
    )
    parser.add_argument("--file", default="")
    parser.add_argument("--volume", default="")
    parser.add_argument("--query", default="")
    parser.add_argument("--env-file", default=str(ROOT / ".env.docker"))
    args = parser.parse_args()

    env_file = Path(args.env_file)
    if not env_file.exists():
        sys.exit("Нет .env.docker — выполните make container-env.")
    compose = Compose(env_file)

    if args.command == "migrate":
        compose.run("run", "--rm", "migrate", capture=False)
        out = compose.run("run", "--rm", "migrate", "alembic", "current").stdout
        print("Версия схемы:", out.decode().strip().splitlines()[-1])
    elif args.command == "backup":
        backup(compose)
    elif args.command == "restore":
        restore(compose, args.file)
    elif args.command == "restore-new":
        restore_new_volume(compose, args.file, args.volume, env_file)
    elif args.command == "sql":
        print(sql(compose, args.query.rstrip(";") + ";"))
    elif args.command == "counts":
        print_counts("Записей в таблицах:", counts(compose))


if __name__ == "__main__":
    main()
