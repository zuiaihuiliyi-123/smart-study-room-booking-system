def test_openapi_contains_all_modules(client) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/rooms" in paths
    assert "/api/v1/reservations" in paths
    assert "/api/v1/dashboard/overview" in paths
    assert "/api/v1/messages/me" in paths


def test_unimplemented_endpoint_returns_501(client) -> None:
    response = client.get("/api/v1/rooms")
    assert response.status_code == 501
    assert response.json()["code"] == "NOT_IMPLEMENTED"


def test_login_payload_is_validated(client) -> None:
    response = client.post("/api/v1/auth/login", json={})
    assert response.status_code == 422
