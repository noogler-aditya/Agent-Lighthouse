"""
Application settings for Agent Lighthouse backend.
"""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = Field(default="development", alias="APP_ENV")
    redis_url: str = Field(default="redis://localhost:6379", alias="REDIS_URL")
    allowed_origins: str = Field(default="http://localhost:3000", alias="ALLOWED_ORIGINS")
    api_key: str = Field(default="change-me-in-production", alias="LIGHTHOUSE_API_KEY")
    require_auth: bool = Field(default=True, alias="REQUIRE_AUTH")
    trace_ttl_hours: int = Field(default=24, alias="TRACE_TTL_HOURS")
    cors_allow_credentials: bool = Field(default=False, alias="CORS_ALLOW_CREDENTIALS")

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()] or [
            "http://localhost:3000"
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
