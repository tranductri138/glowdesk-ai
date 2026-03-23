from src.models.base_models import BaseResponse, ErrorDetail, ErrorResponse


def test_base_response_serializes_to_camel_case() -> None:
    response = BaseResponse(success=True, data={"status": "ok"})
    dumped = response.model_dump(by_alias=True)
    assert "success" in dumped
    assert "data" in dumped
    assert "meta" in dumped


def test_error_detail_serializes_request_id_as_camel() -> None:
    detail = ErrorDetail(code="NOT_FOUND", message="Not found", request_id="req-123")
    dumped = detail.model_dump(by_alias=True)
    assert "requestId" in dumped
    assert dumped["requestId"] == "req-123"
    # snake_case key should NOT appear in alias output
    assert "request_id" not in dumped


def test_error_response_serializes_correctly() -> None:
    error = ErrorResponse(
        error=ErrorDetail(
            code="INTERNAL_ERROR", message="Something went wrong", request_id="req-456"
        )
    )
    dumped = error.model_dump(by_alias=True)
    assert dumped["success"] is False
    assert dumped["error"]["code"] == "INTERNAL_ERROR"
    assert dumped["error"]["requestId"] == "req-456"


def test_base_response_accepts_snake_case_input() -> None:
    """populate_by_name=True allows both snake_case and camelCase."""
    response = BaseResponse(success=True, data=None, meta=None)
    assert response.success is True


def test_base_response_json_output_is_camel() -> None:
    response = BaseResponse(success=True, data={"key": "value"})
    json_str = response.model_dump_json(by_alias=True)
    assert '"success"' in json_str
    assert '"data"' in json_str
