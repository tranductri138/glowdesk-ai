from fastapi import Depends
from fastapi.testclient import TestClient

from src.dependencies import validate_api_key
from src.main import app
from src.models.base_models import BaseResponse

# Add a test-only protected endpoint
_test_router_added = False

if not _test_router_added:

    @app.get("/api/v1/test-protected")
    async def _protected_endpoint(
        request_id: str = Depends(validate_api_key),
    ) -> BaseResponse[dict]:
        return BaseResponse(success=True, data={"request_id": request_id})

    _test_router_added = True


def test_valid_api_key_returns_200(
    client: TestClient, api_key_headers: dict[str, str]
) -> None:
    response = client.get("/api/v1/test-protected", headers=api_key_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True


def test_invalid_api_key_returns_401(
    client: TestClient, invalid_api_key_headers: dict[str, str]
) -> None:
    response = client.get("/api/v1/test-protected", headers=invalid_api_key_headers)
    assert response.status_code == 401


def test_missing_api_key_returns_422(client: TestClient) -> None:
    """Missing X-API-Key header returns 422 (FastAPI validation error)."""
    response = client.get("/api/v1/test-protected")
    assert response.status_code == 422


def test_invalid_api_key_error_format(
    client: TestClient, invalid_api_key_headers: dict[str, str]
) -> None:
    response = client.get("/api/v1/test-protected", headers=invalid_api_key_headers)
    body = response.json()
    detail = body["detail"]
    assert detail["success"] is False
    assert detail["error"]["code"] == "AUTH_INVALID_API_KEY"
    assert detail["error"]["message"] == "Invalid API key"
    assert detail["error"]["requestId"] == "test-request-id"


def test_request_id_passed_through(
    client: TestClient, api_key_headers: dict[str, str]
) -> None:
    response = client.get("/api/v1/test-protected", headers=api_key_headers)
    body = response.json()
    assert body["data"]["request_id"] == "test-request-id"
