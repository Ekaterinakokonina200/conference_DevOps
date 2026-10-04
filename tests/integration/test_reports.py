"""Требования ТЗ 6.8: сводный отчёт считается по данным в базе."""


def test_empty_summary(client):
    response = client.get("/reports/summary")

    assert response.status_code == 200
    assert response.json() == {
        "participants": 0,
        "confirmed": 0,
        "payments_received": 0,
        "theses_submitted": 0,
        "hotel_required": 0,
    }


def test_summary_counts_only_matching_records(client, participant):
    """Каждого «неподходящего» вида записей больше, чем подходящих.

    Поэтому если в отчёте перепутать условие (например, считать pending
    вместо confirmed), число изменится и тест это заметит.
    """
    pid = participant["id"]
    other = client.post(
        "/participants/", json={"full_name": "Второй", "email": "two@example.com"}
    ).json()

    client.post(
        "/payments/", json={"participant_id": pid, "amount": 100, "status": "paid"}
    )
    for _ in range(2):
        client.post("/payments/", json={"participant_id": pid, "amount": 100})

    confirmed = client.post("/applications/", json={"participant_id": pid}).json()
    client.put(f"/applications/{confirmed['id']}", json={"status": "confirmed"})
    for _ in range(2):
        client.post("/applications/", json={"participant_id": other["id"]})

    client.post("/theses/", json={"participant_id": pid, "title": "Тезис"})

    client.post(
        "/hotel-requests/",
        json={
            "participant_id": pid,
            "required": True,
            "check_in": "2026-11-10",
            "check_out": "2026-11-12",
        },
    )
    for _ in range(2):
        client.post(
            "/hotel-requests/", json={"participant_id": other["id"], "required": False}
        )

    assert client.get("/reports/summary").json() == {
        "participants": 2,
        "confirmed": 1,
        "payments_received": 1,
        "theses_submitted": 1,
        "hotel_required": 1,
    }
