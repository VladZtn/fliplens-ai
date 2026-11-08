from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FlipLens AI"
    app_version: str = "1.6.0"

    ai_provider: str = "mock"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.5-flash"
    gemini_fallback_models: str = "gemini-3.5-flash,gemini-2.5-flash"
    gemini_max_attempts: int = 2

    ai_timeout_seconds: float = 45.0

    pricing_provider: str = "mock"
    ebay_client_id: str | None = None
    ebay_client_secret: str | None = None
    ebay_marketplace_id: str = "EBAY_GB"
    ebay_scope: str = "https://api.ebay.com/oauth/api_scope"
    ebay_result_limit: int = 50

    # Free analyses per client per day (UTC). 0 disables the limit.
    free_daily_limit: int = 5
    # Number of reverse proxies in front of the app (Railway/Render: 1).
    trusted_proxy_hops: int = 1

    cors_origins: str = (
        "http://localhost:3000,"
        "http://127.0.0.1:3000"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()