"""Требования ТЗ 6.6: тезисы."""


def create_thesis(client, participant_id, title="DevOps в учебных проектах"):
    return client.post(
        "/theses/",
        json={"participant_id": participant_id, "title": title},
    )


def test_new_thesis_is_submitted(client, participant):
    response = create_thesis(client, participant["id"])

    assert response.status_code == 201
    assert response.json()["status"] == "submitted"
    assert response.json()["file_url"] is None


def test_thesis_for_missing_participant_returns_404(client):
    assert create_thesis(client, 999999).status_code == 404


def test_thesis_without_title_returns_422(client, participant):
    response = client.post("/theses/", json={"participant_id": participant["id"]})

    assert response.status_code == 422


def test_approve_thesis(client, participant):
    thesis = create_thesis(client, participant["id"]).json()

    response = client.put(f"/theses/{thesis['id']}", json={"status": "approved"})

    assert response.status_code == 200
    assert response.json()["status"] == "approved"


def test_unknown_thesis_status_returns_422(client, participant):
    thesis = create_thesis(client, participant["id"]).json()

    response = client.put(f"/theses/{thesis['id']}", json={"status": "published"})

    assert response.status_code == 422


def test_list_get_delete_thesis(client, participant):
    thesis = create_thesis(client, participant["id"]).json()

    assert len(client.get("/theses/").json()) == 1
    assert client.get(f"/theses/{thesis['id']}").json() == thesis
    assert client.delete(f"/theses/{thesis['id']}").status_code == 204
    assert client.get(f"/theses/{thesis['id']}").status_code == 404


def test_missing_thesis_returns_404(client):
    assert client.put("/theses/999999", json={"status": "approved"}).status_code == 404
    assert client.delete("/theses/999999").status_code == 404
