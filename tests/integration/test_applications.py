"""Требования ТЗ 6.3 и 8.1: заявки и правило подтверждения после оплаты."""


def create_application(client, participant_id):
    response = client.post("/applications/", json={"participant_id": participant_id})
    assert response.status_code == 201
    return response.json()


def pay(client, participant_id, status="paid", amount=1500):
    response = client.post(
        "/payments/",
        json={"participant_id": participant_id, "amount": amount, "status": status},
    )
    assert response.status_code == 201
    return response.json()


def test_new_application_is_pending(client, participant):
    application = create_application(client, participant["id"])

    assert application["status"] == "pending"
    assert application["participant_id"] == participant["id"]


def test_application_for_missing_participant_returns_404(client):
    response = client.post("/applications/", json={"participant_id": 999999})

    assert response.status_code == 404
    assert response.json() == {"detail": "Participant not found"}


def test_cannot_confirm_without_payment(client, participant):
    application = create_application(client, participant["id"])

    response = client.put(
        f"/applications/{application['id']}", json={"status": "confirmed"}
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Registration fee must be paid before confirmation"
    }


def test_cannot_confirm_with_pending_payment(client, participant):
    application = create_application(client, participant["id"])
    pay(client, participant["id"], status="pending")

    response = client.put(
        f"/applications/{application['id']}", json={"status": "confirmed"}
    )

    assert response.status_code == 409


def test_cannot_confirm_with_payment_of_another_participant(client, participant):
    other = client.post(
        "/participants/", json={"full_name": "Другой", "email": "o@example.com"}
    ).json()
    application = create_application(client, participant["id"])
    pay(client, other["id"], status="paid")

    response = client.put(
        f"/applications/{application['id']}", json={"status": "confirmed"}
    )

    assert response.status_code == 409


def test_can_confirm_after_paid_payment(client, participant):
    application = create_application(client, participant["id"])
    pay(client, participant["id"], status="paid")

    response = client.put(
        f"/applications/{application['id']}", json={"status": "confirmed"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "confirmed"


def test_reject_application_without_payment(client, participant):
    application = create_application(client, participant["id"])

    response = client.put(
        f"/applications/{application['id']}", json={"status": "rejected"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


def test_unknown_status_returns_422(client, participant):
    application = create_application(client, participant["id"])

    response = client.put(
        f"/applications/{application['id']}", json={"status": "approved"}
    )

    assert response.status_code == 422


def test_list_get_and_delete_application(client, participant):
    application = create_application(client, participant["id"])

    assert [a["id"] for a in client.get("/applications/").json()] == [application["id"]]
    assert client.get(f"/applications/{application['id']}").json() == application
    assert client.delete(f"/applications/{application['id']}").status_code == 204
    assert client.get(f"/applications/{application['id']}").status_code == 404


def test_missing_application_returns_404(client):
    assert client.get("/applications/999999").status_code == 404
    assert (
        client.put("/applications/999999", json={"status": "rejected"}).status_code
        == 404
    )
    assert client.delete("/applications/999999").status_code == 404
