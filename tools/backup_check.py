"""Автоматическая проверка резервного копирования (make backup-check).

На ТЕСТОВОЙ базе (.env.test) выполняется полный сценарий:
1) база создаётся миграциями и заполняется данными;
2) создаётся резервная копия;
3) данные намеренно портятся: удаляются оплаты, меняются имена участников;
4) база восстанавливается из копии;
5) содержимое всех таблиц сравнивается с исходным — оно должно совпасть.
"""

import os
import subprocess
import sys

from db_backup import create_backup
from db_restore import restore_backup
from pgtools import ROOT, test_database_url
from sqlalchemy import create_engine, inspect, text

SEED = [
    "INSERT INTO participants (full_name, email, organization) VALUES "
    "('Иванова Анна', 'anna@example.com', 'Московский Политех'), "
    "('Петров Пётр', 'petr@example.com', 'МГУ')",
    "INSERT INTO payments (participant_id, amount, status) "
    "SELECT id, 1500, 'paid' FROM participants",
    "INSERT INTO applications (participant_id, status) "
    "SELECT id, 'confirmed' FROM participants",
    "INSERT INTO theses (participant_id, title, status) "
    "SELECT id, 'Тезис ' || full_name, 'submitted' FROM participants",
]
DAMAGE = [
    "DELETE FROM payments",
    "UPDATE participants SET full_name = 'ИСПОРЧЕНО'",
]


def snapshot(engine) -> dict[str, list[tuple]]:
    with engine.connect() as connection:
        tables = sorted(inspect(connection).get_table_names())
        return {
            table: [
                tuple(row)
                for row in connection.execute(text(f'SELECT * FROM "{table}"'))
            ]
            for table in tables
        }


def main() -> None:
    url = test_database_url()
    engine = create_engine(url)
    env = dict(os.environ, DATABASE_URL=url.render_as_string(hide_password=False))

    print("1. Чистая тестовая база + миграции + данные")
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
    )
    with engine.begin() as connection:
        for statement in SEED:
            connection.execute(text(statement))
    original = snapshot(engine)

    print("2. Резервная копия")
    dump = ROOT / "reports" / "backup-check.dump"
    create_backup(url, dump)

    print("3. Намеренная порча данных")
    with engine.begin() as connection:
        for statement in DAMAGE:
            connection.execute(text(statement))
    if snapshot(engine) == original:
        sys.exit("Ошибка проверки: данные не изменились после порчи")
    print("   оплаты удалены, имена участников заменены")

    print("4. Восстановление из копии")
    engine.dispose()
    restore_backup(url, dump)

    print("5. Сравнение с исходными данными")
    restored = snapshot(engine)
    engine.dispose()
    if restored != original:
        sys.exit("Ошибка: восстановленные данные отличаются от исходных")
    rows = sum(len(rows) for rows in restored.values())
    print(f"backup-check: восстановлено {rows} записей в {len(restored)} таблицах")


if __name__ == "__main__":
    main()
