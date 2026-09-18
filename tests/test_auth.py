from uuid import uuid4

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models.user import User

client = TestClient(app)

TEST_PASSWORD = "StrongPassword123!"


def create_username(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def delete_user(username: str) -> None:
    db = SessionLocal()

    try:
        user = (
            db.query(User)
            .filter(User.username == username)
            .first()
        )

        if user is not None:
            db.delete(user)
            db.commit()
    finally:
        db.close()


def register_user(username: str):
    return client.post(
        "/auth/register",
        json={
            "username": username,
            "password": TEST_PASSWORD,
        },
    )


def test_register_user():
    username = create_username("register")

    try:
        response = register_user(username)

        assert response.status_code == 201

        data = response.json()

        assert data["username"] == username
        assert data["is_active"] is True
        assert "id" in data
        assert "password" not in data
        assert "password_hash" not in data
    finally:
        delete_user(username)


def test_duplicate_username():
    username = create_username("duplicate")

    try:
        first_response = register_user(username)
        second_response = register_user(username)

        assert first_response.status_code == 201
        assert second_response.status_code == 409
        assert second_response.json() == {
            "detail": (
                "User with this username already exists"
            )
        }
    finally:
        delete_user(username)


def test_invalid_registration_body():
    response = client.post(
        "/auth/register",
        json={
            "username": create_username("invalid"),
        },
    )

    assert response.status_code == 422


def test_login_and_get_current_user():
    username = create_username("login")

    try:
        register_response = register_user(username)

        assert register_response.status_code == 201

        login_response = client.post(
            "/auth/login",
            data={
                "username": username,
                "password": TEST_PASSWORD,
            },
        )

        assert login_response.status_code == 200

        login_data = login_response.json()

        assert login_data["token_type"] == "bearer"
        assert login_data["access_token"]

        me_response = client.get(
            "/auth/me",
            headers={
                "Authorization": (
                    "Bearer "
                    f"{login_data['access_token']}"
                )
            },
        )

        assert me_response.status_code == 200

        me_data = me_response.json()

        assert me_data["username"] == username
        assert me_data["is_active"] is True
        assert "password" not in me_data
        assert "password_hash" not in me_data
    finally:
        delete_user(username)


def test_login_with_wrong_password():
    username = create_username("wrong_password")

    try:
        register_response = register_user(username)

        assert register_response.status_code == 201

        login_response = client.post(
            "/auth/login",
            data={
                "username": username,
                "password": "WrongPassword123!",
            },
        )

        assert login_response.status_code == 401
        assert login_response.json() == {
            "detail": "Incorrect username or password"
        }
    finally:
        delete_user(username)


def test_get_current_user_requires_valid_token():
    without_token_response = client.get(
        "/auth/me"
    )

    invalid_token_response = client.get(
        "/auth/me",
        headers={
            "Authorization": (
                "Bearer definitely.invalid.token"
            )
        },
    )

    assert without_token_response.status_code == 401
    assert invalid_token_response.status_code == 401


def test_web_interface_contains_authentication_forms():
    response = client.get("/")

    assert response.status_code == 200

    page = response.text

    assert 'id="register-form"' in page
    assert 'id="login-form"' in page
    assert 'id="logout-button"' in page
    assert 'id="current-username"' in page