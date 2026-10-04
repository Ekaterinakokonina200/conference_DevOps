"""Требования ТЗ 6.5: оплаты."""


def create_payment(client, participant_id, **fields):
    body = {"participant_id": participant_id, "amount": 1500, **fields}
    return client.post("/payments/", json=body)


def test_create_pending_payment_without_date(client, participant):
    response = create_payment(client, participant["id"])

    assert response.status_code == 201
    assert response.json()["status"] == "pending"
    assert response.json()["payment_date"] is None


def test_create_paid_payment_sets_date(client, participant):
    response = create_payment(client, participant["id"], status="paid")

    assert response.status_code == 201
    assert response.json()["payment_date"] is not None


def test_payment_for_missing_participant_returns_404(client):
    response = create_payment(client, 999999)

    assert response.status_code == 404


def test_amount_boundaries(client, participant):
    assert create_payment(client, participant["id"], amount=0).status_code == 422
    assert create_payment(client, participant["id"], amount=-10).status_code == 422
    assert create_payment(client, participant["id"], amount=0.01).status_code == 201


def test_unknown_status_returns_422(client, participant):
    response = create_payment(client, participant["id"], status="refunded")

    assert response.status_code == 422


def test_update_status_to_paid_and_back(client, participant):
    payment = create_payment(client, participant["id"]).json()

    paid = client.put(f"/payments/{payment['id']}", json={"status": "paid"})
    cancelled = client.put(f"/payments/{payment['id']}", json={"status": "cancelled"})

    assert paid.json()["payment_date"] is not None
    assert cancelled.json()["status"] == "cancelled"
    assert cancelled.json()["payment_date"] is None


def test_list_get_delete_payment(client, participant):
    payment = create_payment(client, participant["id"]).json()

    assert [p["id"] for p in client.get("/payments/").json()] == [payment["id"]]
    assert client.get(f"/payments/{payment['id']}").json() == payment
    assert client.delete(f"/payments/{payment['id']}").status_code == 204
    assert client.get(f"/payments/{payment['id']}").status_code == 404


def test_missing_payment_returns_404(client):
    assert client.get("/payments/999999").status_code == 404
    assert client.put("/payments/999999", json={"status": "paid"}).status_code == 404
    assert client.delete("/payments/999999").status_code == 404
