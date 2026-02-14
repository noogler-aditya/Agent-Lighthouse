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
    supabase_url: str = Field(default="", alias="SUPABASE_URL")
    supabase_jwt_issuer: str = Field(default="", alias="SUPABASE_JWT_ISSUER")
    supabase_jwt_audience: str = Field(default="authenticated", alias="SUPABASE_JWT_AUDIENCE")
    supabase_role_claim: str = Field(default="app_metadata.role", alias="SUPABASE_ROLE_CLAIM")
    supabase_role_map: str = Field(default="authenticated:viewer,service_role:admin", alias="SUPABASE_ROLE_MAP")
    supabase_test_jwt_secret: str = Field(default="", alias="SUPABASE_TEST_JWT_SECRET")

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
    def supabase_jwks_url(self) -> str:
        base = self.supabase_url.rstrip("/")
        return f"{base}/auth/v1/.well-known/jwks.json" if base else ""

    @property
    def supabase_effective_issuer(self) -> str:
        if self.supabase_jwt_issuer:
            return self.supabase_jwt_issuer
        base = self.supabase_url.rstrip("/")
        return f"{base}/auth/v1" if base else ""

    @property
    def supabase_role_map_dict(self) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for raw in self.supabase_role_map.split(","):
            item = raw.strip()
            if not item:
                continue
            source, sep, target = item.partition(":")
            if not sep:
                continue
            mapping[source.strip()] = target.strip()
        return mapping

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
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_effective_issuer and self.supabase_jwks_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()
