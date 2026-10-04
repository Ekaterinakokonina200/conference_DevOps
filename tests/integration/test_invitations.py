"""Требования ТЗ 6.4: приглашения."""


def create_invitation(client, participant_id):
    response = client.post("/invitations/", json={"participant_id": participant_id})
    assert response.status_code == 201
    return response.json()


def test_new_invitation_is_created_and_not_sent(client, participant):
    invitation = create_invitation(client, participant["id"])

    assert invitation["status"] == "created"
    assert invitation["sent_at"] is None


def test_invitation_for_missing_participant_returns_404(client):
    response = client.post("/invitations/", json={"participant_id": 999999})

    assert response.status_code == 404


def test_sending_invitation_sets_time(client, participant):
    invitation = create_invitation(client, participant["id"])

    response = client.put(f"/invitations/{invitation['id']}", json={"status": "sent"})

    assert response.status_code == 200
    assert response.json()["sent_at"] is not None


def test_accepting_keeps_sent_time(client, participant):
    invitation = create_invitation(client, participant["id"])
    sent = client.put(f"/invitations/{invitation['id']}", json={"status": "sent"})

    accepted = client.put(
        f"/invitations/{invitation['id']}", json={"status": "accepted"}
    )

    assert accepted.json()["status"] == "accepted"
    assert accepted.json()["sent_at"] == sent.json()["sent_at"]


def test_unknown_status_returns_422(client, participant):
    invitation = create_invitation(client, participant["id"])

    response = client.put(f"/invitations/{invitation['id']}", json={"status": "lost"})

    assert response.status_code == 422


def test_list_get_delete_invitation(client, participant):
    invitation = create_invitation(client, participant["id"])

    assert len(client.get("/invitations/").json()) == 1
    assert client.get(f"/invitations/{invitation['id']}").json() == invitation
    assert client.delete(f"/invitations/{invitation['id']}").status_code == 204
    assert client.get(f"/invitations/{invitation['id']}").status_code == 404


def test_missing_invitation_returns_404(client):
    assert client.put("/invitations/999999", json={"status": "sent"}).status_code == 404
    assert client.delete("/invitations/999999").status_code == 404
