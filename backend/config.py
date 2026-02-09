"""
Application settings for Agent Lighthouse backend.
"""
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().with_name(".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = Field(default="development", alias="APP_ENV")
    build_version: str = Field(default="dev", alias="BUILD_VERSION")

    redis_url: str = Field(default="redis://localhost:6379", alias="REDIS_URL")
    redis_connect_timeout_seconds: int = Field(default=5, alias="REDIS_CONNECT_TIMEOUT_SECONDS")
    redis_required_appendonly: str = Field(default="yes", alias="REDIS_REQUIRED_APPENDONLY")
    redis_required_save: str = Field(default="", alias="REDIS_REQUIRED_SAVE")
    redis_enforce_persistence_policy: bool = Field(default=True, alias="REDIS_ENFORCE_PERSISTENCE_POLICY")

    allowed_origins: str = Field(default="http://localhost:5173", alias="ALLOWED_ORIGINS")
    cors_allow_credentials: bool = Field(default=False, alias="CORS_ALLOW_CREDENTIALS")

    require_auth: bool = Field(default=True, alias="REQUIRE_AUTH")
    jwt_secret: str = Field(default="change-me-jwt-secret", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_issuer: str = Field(default="agent-lighthouse", alias="JWT_ISSUER")
    jwt_audience: str = Field(default="agent-lighthouse-ui", alias="JWT_AUDIENCE")
    access_token_ttl_minutes: int = Field(default=15, alias="ACCESS_TOKEN_TTL_MINUTES")
    refresh_token_ttl_minutes: int = Field(default=43200, alias="REFRESH_TOKEN_TTL_MINUTES")

    auth_users: str = Field(
        default="admin:admin:admin,operator:operator:operator,viewer:viewer:viewer",
        alias="AUTH_USERS",
    )

    machine_api_keys: str = Field(default="", alias="MACHINE_API_KEYS")
    legacy_api_key: str = Field(default="local-dev-key", alias="LIGHTHOUSE_API_KEY")

    trace_ttl_hours: int = Field(default=24, alias="TRACE_TTL_HOURS")

    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")
    rate_limit_window_seconds: int = Field(default=60, alias="RATE_LIMIT_WINDOW_SECONDS")
    rate_limit_read_per_window: int = Field(default=300, alias="RATE_LIMIT_READ_PER_WINDOW")
    rate_limit_write_per_window: int = Field(default=120, alias="RATE_LIMIT_WRITE_PER_WINDOW")
    rate_limit_ws_connect_per_window: int = Field(default=60, alias="RATE_LIMIT_WS_CONNECT_PER_WINDOW")
    rate_limit_ws_subscribe_per_window: int = Field(default=180, alias="RATE_LIMIT_WS_SUBSCRIBE_PER_WINDOW")

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def auth_users_map(self) -> dict[str, dict[str, str]]:
        users: dict[str, dict[str, str]] = {}
        for raw in self.auth_users.split(","):
            raw = raw.strip()
            if not raw:
                continue
            parts = [segment.strip() for segment in raw.split(":")]
            if len(parts) != 3:
                continue
            username, password, role = parts
            users[username] = {"password": password, "role": role}
        return users

    @property
    def machine_api_keys_map(self) -> dict[str, set[str]]:
        scoped: dict[str, set[str]] = {}
        for raw in self.machine_api_keys.split(","):
            raw = raw.strip()
            if not raw:
                continue
            key, sep, scope_blob = raw.partition(":")
            if not sep:
                continue
            scopes = {scope.strip() for scope in scope_blob.split("|") if scope.strip()}
            if scopes:
                scoped[key.strip()] = scopes
        if not scoped and self.legacy_api_key.strip():
            scoped[self.legacy_api_key.strip()] = {"trace:write", "trace:read"}
        return scoped

    @property
    def jwt_secret_uses_default(self) -> bool:
        default_value = self.__class__.model_fields["jwt_secret"].default
        return self.jwt_secret == default_value


@lru_cache
def get_settings() -> Settings:
    return Settings()
