"""Фикстуры интеграционных тестов: изоляция данных в тестовой базе.

1. Один раз за прогон схема тестовой базы удаляется и создаётся заново
   миграциями Alembic (alembic upgrade head) — тесты проверяют ту же схему,
   что будет на сервере.
2. Каждый тест выполняется внутри транзакции, которая в конце откатывается.
   Приложение делает commit, но это commit вложенной точки сохранения
   (SAVEPOINT), поэтому после теста в базе не остаётся никаких данных
   и тесты не влияют друг на друга.
"""

from pathlib import Path

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from alembic import command
from app.database import engine, get_db
from app.main import app

ROOT = Path(__file__).resolve().parents[2]


def reset_schema() -> None:
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    reset_schema()
    command.upgrade(Config(str(ROOT / "alembic.ini")), "head")
    yield
    engine.dispose()


@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def participant(client):
    """Готовый участник для тестов заявок, оплат, тезисов и т. п."""
    response = client.post(
        "/participants/",
        json={
            "full_name": "Иванова Анна Петровна",
            "email": "anna.ivanova@example.com",
            "phone": "+79990000000",
            "organization": "Московский Политех",
        },
    )
    assert response.status_code == 201
    return response.json()
