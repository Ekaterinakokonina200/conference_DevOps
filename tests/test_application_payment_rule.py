from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def create_test_participant():
    email = f"payment_rule_{uuid4()}@example.com"

    response = client.post(
        "/participants/",
        json={
            "full_name": "Payment Rule Test Participant",
            "email": email,
            "phone": "+79990000000",
            "organization": "Test University",
        },
    )

    assert response.status_code == 201

    return response.json()


def test_cannot_confirm_application_without_paid_payment():
    participant = create_test_participant()

    participant_id = participant["id"]
    application_id = None

    try:
        application_response = client.post(
            "/applications/",
            json={
                "participant_id": participant_id,
            },
        )

        assert application_response.status_code == 201

        application = application_response.json()
        application_id = application["id"]

        confirm_response = client.put(
            f"/applications/{application_id}",
            json={
                "status": "confirmed",
            },
        )

        assert confirm_response.status_code == 409
        assert confirm_response.json() == {
            "detail": (
                "Registration fee must be paid "
                "before confirmation"
            )
        }

    finally:
        if application_id is not None:
            client.delete(
                f"/applications/{application_id}"
            )

        client.delete(
            f"/participants/{participant_id}"
        )


def test_can_confirm_application_after_paid_payment():
    participant = create_test_participant()

    participant_id = participant["id"]
    application_id = None
    payment_id = None

    try:
        application_response = client.post(
            "/applications/",
            json={
                "participant_id": participant_id,
            },
        )

        assert application_response.status_code == 201

        application = application_response.json()
        application_id = application["id"]

        payment_response = client.post(
            "/payments/",
            json={
                "participant_id": participant_id,
                "amount": 1500,
                "status": "paid",
            },
        )

        assert payment_response.status_code == 201

        payment = payment_response.json()
        payment_id = payment["id"]

        confirm_response = client.put(
            f"/applications/{application_id}",
            json={
                "status": "confirmed",
            },
        )

        assert confirm_response.status_code == 200
        assert confirm_response.json()["status"] == "confirmed"

    finally:
        if payment_id is not None:
            client.delete(
                f"/payments/{payment_id}"
            )

        if application_id is not None:
            client.delete(
                f"/applications/{application_id}"
            )

        client.delete(
            f"/participants/{participant_id}"
        )