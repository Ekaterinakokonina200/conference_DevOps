"""Требования ТЗ 6.7: запросы на гостиницу (граничные даты)."""

STAY = {"required": True, "check_in": "2026-11-10", "check_out": "2026-11-12"}


def create_request(client, participant_id, **fields):
    body = {"participant_id": participant_id, **STAY, **fields}
    return client.post("/hotel-requests/", json=body)


def test_create_hotel_request(client, participant):
    response = create_request(client, participant["id"])

    assert response.status_code == 201
    assert response.json()["check_out"] == "2026-11-12"


def test_request_without_hotel_needs_no_dates(client, participant):
    response = client.post(
        "/hotel-requests/",
        json={"participant_id": participant["id"], "required": False},
    )

    assert response.status_code == 201


def test_hotel_request_for_missing_participant_returns_404(client):
    assert create_request(client, 999999).status_code == 404


def test_same_day_check_out_returns_422(client, participant):
    response = create_request(client, participant["id"], check_out="2026-11-10")

    assert response.status_code == 422


def test_missing_dates_return_422(client, participant):
    response = create_request(client, participant["id"], check_in=None)

    assert response.status_code == 422


def test_update_hotel_request(client, participant):
    request = create_request(client, participant["id"]).json()

    response = client.put(
        f"/hotel-requests/{request['id']}",
        json={"required": True, "check_in": "2026-11-10", "check_out": "2026-11-11"},
    )

    assert response.status_code == 200
    assert response.json()["check_out"] == "2026-11-11"


def test_update_with_wrong_dates_returns_422(client, participant):
    request = create_request(client, participant["id"]).json()

    response = client.put(
        f"/hotel-requests/{request['id']}",
        json={"required": True, "check_in": "2026-11-10", "check_out": "2026-11-09"},
    )

    assert response.status_code == 422


def test_list_get_delete_hotel_request(client, participant):
    request = create_request(client, participant["id"]).json()

    assert len(client.get("/hotel-requests/").json()) == 1
    assert client.get(f"/hotel-requests/{request['id']}").json() == request
    assert client.delete(f"/hotel-requests/{request['id']}").status_code == 204
    assert client.get(f"/hotel-requests/{request['id']}").status_code == 404


def test_missing_hotel_request_returns_404(client):
    body = {"required": False}
    assert client.put("/hotel-requests/999999", json=body).status_code == 404
    assert client.delete("/hotel-requests/999999").status_code == 404
