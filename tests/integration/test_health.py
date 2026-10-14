def test_health_returns_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_version_returns_version_and_instance(client):
    response = client.get("/version")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"version", "instance"}
    assert body["version"]
    assert body["instance"]
