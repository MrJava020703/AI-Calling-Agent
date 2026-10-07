from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: str = "development"
    demo_mode: bool = True
    database_url: str = "sqlite:///./voxagent-demo.db"
    jwt_secret: str = "development-only-change-me"
    jwt_expires_minutes: int = 480
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_phone_number: str | None = None
    frontend_url: str = "http://localhost:5173"
    backend_url: str = "http://localhost:8000"
    human_handoff_number: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
