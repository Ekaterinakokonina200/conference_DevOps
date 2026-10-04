"""Проверка миграций на чистой и заполненной базе (make migrations-check).

Тесты работают с тестовой базой из .env.test: удаляют схему, применяют
миграции и проверяют результат. Рабочая база не затрагивается.
"""

import os
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from alembic import command

ROOT = Path(__file__).resolve().parents[2]
V010_HEAD = "c027a5eb74d0"  # схема версии v0.1.0 (до ЛР3)
APP_TABLES = {
    "participants",
    "applications",
    "invitations",
    "payments",
    "theses",
    "hotel_requests",
    "users",
}


@pytest.fixture
def config():
    return Config(str(ROOT / "alembic.ini"))


@pytest.fixture
def engine():
    engine = create_engine(os.environ["DATABASE_URL"])
    reset_schema(engine)
    yield engine
    reset_schema(engine)
    engine.dispose()


def reset_schema(engine):
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))


def current_revision(engine):
    with engine.connect() as connection:
        return connection.scalar(text("SELECT version_num FROM alembic_version"))


def test_migrations_have_single_head(config):
    heads = ScriptDirectory.from_config(config).get_heads()

    assert len(heads) == 1, f"несколько веток миграций: {heads}"


def test_upgrade_clean_database(config, engine):
    command.upgrade(config, "head")

    head = ScriptDirectory.from_config(config).get_current_head()
    assert current_revision(engine) == head
    assert APP_TABLES <= set(inspect(engine).get_table_names())
    # Модели SQLAlchemy совпадают со схемой, созданной миграциями
    command.check(config)


def fill_database(connection, payment_status="Paid ", application_status="unknown"):
    """Тестовые данные. По умолчанию — «грязные» статусы из старых версий."""
    connection.execute(
        text(
            "INSERT INTO participants (id, full_name, email) VALUES "
            "(1, 'Иванова Анна', 'anna@example.com'), "
            "(2, 'Петров Пётр', 'petr@example.com')"
        )
    )
    connection.execute(
        text(
            "INSERT INTO payments (participant_id, amount, status) VALUES "
            "(1, 1500, :payment_status), (2, 1500, 'pending')"
        ),
        {"payment_status": payment_status},
    )
    connection.execute(
        text(
            "INSERT INTO applications (participant_id, status) VALUES "
            "(1, 'confirmed'), (2, :application_status)"
        ),
        {"application_status": application_status},
    )
    connection.execute(
        text(
            "INSERT INTO theses (participant_id, title, status) "
            "VALUES (1, 'Тезис', 'submitted')"
        )
    )


def test_upgrade_filled_database_keeps_data(config, engine):
    command.upgrade(config, V010_HEAD)
    with engine.begin() as connection:
        fill_database(connection)

    command.upgrade(config, "head")

    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM participants")) == 2
        payment_statuses = connection.scalars(
            text("SELECT status FROM payments ORDER BY id")
        ).all()
        application_statuses = connection.scalars(
            text("SELECT status FROM applications ORDER BY id")
        ).all()
    assert payment_statuses == ["paid", "pending"]
    assert application_statuses == ["confirmed", "pending"]


def test_upgrade_refuses_to_hide_bad_payments(config, engine):
    command.upgrade(config, V010_HEAD)
    with engine.begin() as connection:
        fill_database(connection)
        connection.execute(text("UPDATE payments SET amount = 0 WHERE id = 2"))

    with pytest.raises(RuntimeError, match="amount <= 0"):
        command.upgrade(config, "head")

    assert current_revision(engine) == V010_HEAD


def test_constraints_reject_invalid_data(config, engine):
    command.upgrade(config, "head")
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO participants (id, full_name, email) "
                "VALUES (1, 'А', 'a@x.ru')"
            )
        )

    invalid_rows = [
        "INSERT INTO payments (participant_id, amount, status) VALUES (1, 0, 'paid')",
        "INSERT INTO payments (participant_id, amount, status) VALUES (1, 10, 'done')",
        "INSERT INTO applications (participant_id, status) VALUES (1, 'approved')",
    ]
    for statement in invalid_rows:
        with pytest.raises(IntegrityError), engine.begin() as connection:
            connection.execute(text(statement))


def test_deleting_participant_cascades_to_related_rows(config, engine):
    command.upgrade(config, "head")
    with engine.begin() as connection:
        fill_database(connection, "paid", "pending")
        connection.execute(text("DELETE FROM participants WHERE id = 1"))

    with engine.connect() as connection:
        for table in ("payments", "applications", "theses"):
            count = connection.scalar(
                text(f"SELECT count(*) FROM {table} WHERE participant_id = 1")
            )
            assert count == 0, table


def test_downgrade_to_v010_and_upgrade_again(config, engine):
    command.upgrade(config, "head")
    with engine.begin() as connection:
        fill_database(connection, "paid", "pending")

    command.downgrade(config, V010_HEAD)
    assert current_revision(engine) == V010_HEAD

    command.upgrade(config, "head")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM participants")) == 2
