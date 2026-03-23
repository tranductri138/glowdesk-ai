from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", extra="ignore")

    ai_service_api_key: str = "dev-api-key"
    redis_url: str = "redis://localhost:6379"
    sqlite_db_path: str = "./data/glowdesk-ai.db"
    openai_api_key: str = ""
    glowdesk_be_url: str = "http://localhost:3000/api/v1/internal"
    glowdesk_ai_port: int = 8000


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
