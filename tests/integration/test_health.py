
def test_version_returns_version_and_instance(client):
    response = client.get("/version")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"version", "instance"}
    assert body["version"]
    assert body["instance"]
