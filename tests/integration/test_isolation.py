"""Проверка изоляции: данные одного теста не видны в другом."""


def test_first_test_creates_participant(client):
    response = client.post(
        "/participants/", json={"full_name": "Изоляция", "email": "iso@example.com"}
    )

    assert response.status_code == 201


def test_second_test_sees_empty_database(client):
    assert client.get("/participants/").json() == []
