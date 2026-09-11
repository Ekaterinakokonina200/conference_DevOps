from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_participant():
    response = client.post(
        "/participants/",
        json={
            "full_name": "Test Participant",
            "email": "test_create@example.com",
            "phone": "+79990000001",
            "organization": "Test University",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["full_name"] == "Test Participant"
    assert data["email"] == "test_create@example.com"
    assert "id" in data

    participant_id = data["id"]

    client.delete(f"/participants/{participant_id}")


def test_get_participants():
    response = client.get("/participants/")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_nonexistent_participant():
    response = client.get("/participants/999999")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Participant not found"
    }


def test_duplicate_email():
    participant = {
        "full_name": "First Participant",
        "email": "duplicate_test@example.com",
        "phone": "+79990000002",
        "organization": "Test University",
    }

    first_response = client.post(
        "/participants/",
        json=participant,
    )

    assert first_response.status_code == 201

    second_response = client.post(
        "/participants/",
        json={
            "full_name": "Second Participant",
            "email": "duplicate_test@example.com",
            "phone": "+79990000003",
            "organization": "Another University",
        },
    )

    assert second_response.status_code == 409

    assert second_response.json() == {
        "detail": "Participant with this email already exists"
    }

    participant_id = first_response.json()["id"]

    client.delete(f"/participants/{participant_id}")


def test_update_participant():
    create_response = client.post(
        "/participants/",
        json={
            "full_name": "Update Participant",
            "email": "update_test@example.com",
            "phone": "+79990000004",
            "organization": "Old Organization",
        },
    )

    assert create_response.status_code == 201

    participant_id = create_response.json()["id"]

    update_response = client.put(
        f"/participants/{participant_id}",
        json={
            "organization": "New Organization"
        },
    )

    assert update_response.status_code == 200
    assert (
        update_response.json()["organization"]
        == "New Organization"
    )

    client.delete(f"/participants/{participant_id}")


def test_delete_participant():
    create_response = client.post(
        "/participants/",
        json={
            "full_name": "Delete Participant",
            "email": "delete_test@example.com",
            "phone": "+79990000005",
            "organization": "Test University",
        },
    )

    assert create_response.status_code == 201

    participant_id = create_response.json()["id"]

    delete_response = client.delete(
        f"/participants/{participant_id}"
    )

    assert delete_response.status_code == 204

    get_response = client.get(
        f"/participants/{participant_id}"
    )

    assert get_response.status_code == 404