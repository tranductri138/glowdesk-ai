import os

from src.config.settings import Settings


def test_settings_loads_defaults() -> None:
    # Remove env vars set by conftest to test actual defaults
    saved = os.environ.pop("SQLITE_DB_PATH", None)
    try:
        settings = Settings(
            _env_file=None,  # type: ignore[call-arg]
        )
        assert settings.redis_url == "redis://localhost:6379"
        assert settings.sqlite_db_path == "./data/glowdesk-ai.db"
        assert settings.glowdesk_ai_port == 8000
    finally:
        if saved is not None:
            os.environ["SQLITE_DB_PATH"] = saved


def test_settings_loads_from_env() -> None:
    os.environ["AI_SERVICE_API_KEY"] = "custom-key"
    os.environ["REDIS_URL"] = "redis://custom:6380"
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
    )
    assert settings.ai_service_api_key == "custom-key"
    assert settings.redis_url == "redis://custom:6380"

    # Cleanup
    os.environ["AI_SERVICE_API_KEY"] = "test-api-key"
    os.environ["REDIS_URL"] = "redis://localhost:6379"


def test_settings_has_all_required_fields() -> None:
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
    )
    assert hasattr(settings, "ai_service_api_key")
    assert hasattr(settings, "redis_url")
    assert hasattr(settings, "sqlite_db_path")
    assert hasattr(settings, "openai_api_key")
    assert hasattr(settings, "glowdesk_be_url")
    assert hasattr(settings, "glowdesk_ai_port")
