"""Требования ТЗ 6.2 и 8.2: управление участниками, уникальность email."""

NEW_PARTICIPANT = {
    "full_name": "Петров Пётр",
    "email": "petrov@example.com",
    "phone": "+79991112233",
    "organization": "МГУ",
}


def test_create_participant(client):
    response = client.post("/participants/", json=NEW_PARTICIPANT)

    assert response.status_code == 201
    data = response.json()
    assert data["full_name"] == "Петров Пётр"
    assert data["email"] == "petrov@example.com"
    assert isinstance(data["id"], int)


def test_create_participant_without_optional_fields(client):
    response = client.post(
        "/participants/",
        json={"full_name": "Без телефона", "email": "nophone@example.com"},
    )

    assert response.status_code == 201
    assert response.json()["phone"] is None
    assert response.json()["organization"] is None


def test_list_participants(client, participant):
    response = client.get("/participants/")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [participant["id"]]


def test_get_participant_by_id(client, participant):
    response = client.get(f"/participants/{participant['id']}")

    assert response.status_code == 200
    assert response.json() == participant


def test_get_missing_participant_returns_404(client):
    response = client.get("/participants/999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Participant not found"}


def test_duplicate_email_returns_409(client, participant):
    response = client.post(
        "/participants/",
        json={"full_name": "Двойник", "email": participant["email"]},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Participant with this email already exists"}


def test_update_participant(client, participant):
    response = client.put(
        f"/participants/{participant['id']}",
        json={"organization": "Новая организация"},
    )

    assert response.status_code == 200
    assert response.json()["organization"] == "Новая организация"
    assert response.json()["email"] == participant["email"]


def test_update_to_existing_email_returns_409(client, participant):
    other = client.post(
        "/participants/",
        json={"full_name": "Другой", "email": "other@example.com"},
    ).json()

    response = client.put(
        f"/participants/{other['id']}", json={"email": participant["email"]}
    )

    assert response.status_code == 409


def test_update_missing_participant_returns_404(client):
    response = client.put("/participants/999999", json={"full_name": "Никто"})

    assert response.status_code == 404


def test_delete_participant(client, participant):
    response = client.delete(f"/participants/{participant['id']}")

    assert response.status_code == 204
    assert client.get(f"/participants/{participant['id']}").status_code == 404


def test_delete_missing_participant_returns_404(client):
    assert client.delete("/participants/999999").status_code == 404


def test_invalid_email_returns_422(client):
    response = client.post(
        "/participants/",
        json={"full_name": "Ошибка", "email": "not-an-email"},
    )

    assert response.status_code == 422


def test_missing_full_name_returns_422(client):
    response = client.post("/participants/", json={"email": "x@example.com"})

    assert response.status_code == 422


def test_delete_participant_with_related_records(client, participant):
    pid = participant["id"]
    client.post("/applications/", json={"participant_id": pid})
    client.post("/payments/", json={"participant_id": pid, "amount": 100})

    response = client.delete(f"/participants/{pid}")

    assert response.status_code == 204
    assert client.get("/applications/").json() == []
    assert client.get("/payments/").json() == []
