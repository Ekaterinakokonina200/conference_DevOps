"""Демонстрационные данные в РАБОЧЕЙ базе (make seed).

Нужны для защиты: показать обновление заполненной базы миграциями и
восстановление из резервной копии. Повторный запуск не создаёт дубликатов.
"""

from pgtools import database_url
from sqlalchemy import create_engine, text

PARTICIPANTS = [
    ("Демо Иванова Анна", "demo.anna@example.com", "Московский Политех"),
    ("Демо Петров Пётр", "demo.petr@example.com", "МГУ"),
    ("Демо Сидорова Мария", "demo.maria@example.com", "МФТИ"),
]


def main() -> None:
    engine = create_engine(database_url())
    with engine.begin() as connection:
        for full_name, email, organization in PARTICIPANTS:
            exists = connection.scalar(
                text("SELECT id FROM participants WHERE email = :email"),
                {"email": email},
            )
            if exists:
                continue
            participant_id = connection.scalar(
                text(
                    "INSERT INTO participants (full_name, email, organization) "
                    "VALUES (:name, :email, :org) RETURNING id"
                ),
                {"name": full_name, "email": email, "org": organization},
            )
            connection.execute(
                text(
                    "INSERT INTO payments (participant_id, amount, status, "
                    "payment_date) VALUES (:pid, 1500, 'paid', now())"
                ),
                {"pid": participant_id},
            )
            connection.execute(
                text(
                    "INSERT INTO applications (participant_id, status) "
                    "VALUES (:pid, 'confirmed')"
                ),
                {"pid": participant_id},
            )
        counts = {
            table: connection.scalar(text(f"SELECT count(*) FROM {table}"))
            for table in ("participants", "payments", "applications")
        }
    engine.dispose()
    print("Демонстрационные данные в рабочей базе:", counts)


if __name__ == "__main__":
    main()
