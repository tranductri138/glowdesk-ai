from fastapi.testclient import TestClient


def test_health_returns_200(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_health_returns_correct_body(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "healthy"


def test_health_does_not_require_api_key(client: TestClient) -> None:
    """Health endpoint is public — no X-API-Key needed."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_health_response_has_camel_case_keys(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    body = response.json()
    # Verify camelCase: "success" not "Success", no snake_case keys
    assert "success" in body
    assert "data" in body
