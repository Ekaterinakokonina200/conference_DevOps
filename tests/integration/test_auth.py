"""Требования ТЗ 6.1, 8.3, 8.4: регистрация, вход, JWT, хранение пароля."""

from datetime import UTC, datetime, timedelta

import jwt
from sqlalchemy import select

from app.models.user import User

PASSWORD = "StrongPassword123!"


def register(client, username="anna_user", password=PASSWORD):
    return client.post(
        "/auth/register", json={"username": username, "password": password}
    )


def login(client, username="anna_user", password=PASSWORD):
    return client.post("/auth/login", data={"username": username, "password": password})


def test_register_user(client):
    response = register(client)

    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "anna_user"
    assert data["is_active"] is True
    assert "password" not in data
    assert "password_hash" not in data


def test_password_is_stored_as_argon2_hash(client, db_session):
    register(client)

    user = db_session.scalar(select(User).where(User.username == "anna_user"))

    assert user.password_hash != PASSWORD
    assert user.password_hash.startswith("$argon2")


def test_duplicate_username_returns_409(client):
    register(client)

    response = register(client)

    assert response.status_code == 409
    assert response.json() == {"detail": "User with this username already exists"}


def test_registration_boundaries(client):
    assert register(client, username="ab").status_code == 422
    assert register(client, username="abc").status_code == 201
    assert register(client, username="bad name").status_code == 422
    assert register(client, username="short_pw", password="1234567").status_code == 422
    assert register(client, username="exact_pw", password="12345678").status_code == 201


def test_registration_without_password_returns_422(client):
    response = client.post("/auth/register", json={"username": "nopass"})

    assert response.status_code == 422


def test_login_and_get_current_user(client):
    register(client)

    token_response = login(client)

    assert token_response.status_code == 200
    token = token_response.json()
    assert token["token_type"] == "bearer"

    me = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {token['access_token']}"}
    )

    assert me.status_code == 200
    assert me.json()["username"] == "anna_user"
    assert "password_hash" not in me.json()


def test_token_contains_subject_and_expiration(client):
    register(client)

    token = login(client).json()["access_token"]
    payload = jwt.decode(token, options={"verify_signature": False})

    assert payload["sub"] == "anna_user"
    expires_in = datetime.fromtimestamp(payload["exp"], UTC) - datetime.now(UTC)
    assert timedelta(minutes=29) < expires_in <= timedelta(minutes=30)


def test_login_with_wrong_password_returns_401(client):
    register(client)

    response = login(client, password="WrongPassword123!")

    assert response.status_code == 401
    assert response.json() == {"detail": "Incorrect username or password"}


def test_login_unknown_user_returns_401(client):
    assert login(client, username="ghost").status_code == 401


def test_me_requires_token(client):
    assert client.get("/auth/me").status_code == 401


def test_me_rejects_invalid_token(client):
    response = client.get(
        "/auth/me", headers={"Authorization": "Bearer definitely.invalid.token"}
    )

    assert response.status_code == 401


def test_me_rejects_token_with_foreign_signature(client):
    register(client)
    forged = jwt.encode(
        {"sub": "anna_user", "exp": datetime.now(UTC) + timedelta(minutes=5)},
        "another-secret-key-that-is-long-enough-123456",
        algorithm="HS256",
    )

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {forged}"})

    assert response.status_code == 401


def test_me_rejects_expired_token(client):
    register(client)
    expired = jwt.encode(
        {"sub": "anna_user", "exp": datetime.now(UTC) - timedelta(seconds=1)},
        "test-only-secret-key-for-automated-tests-0123456789",
        algorithm="HS256",
    )

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {expired}"})

    assert response.status_code == 401


def test_inactive_user_cannot_login(client, db_session):
    register(client)
    user = db_session.scalar(select(User).where(User.username == "anna_user"))
    user.is_active = False
    db_session.commit()

    assert login(client).status_code == 401


def test_web_interface_contains_authentication_forms(client):
    response = client.get("/")

    assert response.status_code == 200
    for element in ('id="register-form"', 'id="login-form"', 'id="logout-button"'):
        assert element in response.text
