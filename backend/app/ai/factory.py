from functools import lru_cache

from app.ai.providers.base import AIProvider
from app.ai.providers.gemini import GeminiAIProvider
from app.ai.providers.mock import MockAIProvider
from app.config import Settings, get_settings


@lru_cache(maxsize=4)
def _gemini_provider(
    api_key: str,
    model: str,
    timeout_seconds: float,
    fallback_models: str,
    max_attempts: int,
    thinking_level: str,
) -> GeminiAIProvider:
    # Cached so the HTTPS connection to Gemini is reused between analyses
    # instead of being opened again for every request.
    return GeminiAIProvider(
        api_key=api_key,
        model=model,
        timeout_seconds=timeout_seconds,
        fallback_models=fallback_models.split(","),
        max_attempts_per_model=max_attempts,
        thinking_level=thinking_level,
    )


def create_ai_provider(settings: Settings | None = None) -> AIProvider:
    settings = settings or get_settings()
    provider = settings.ai_provider.strip().lower()

    if provider == "mock":
        return MockAIProvider()
    if provider == "gemini":
        return _gemini_provider(
            settings.gemini_api_key or "",
            settings.gemini_model,
            settings.ai_timeout_seconds,
            settings.gemini_fallback_models,
            settings.gemini_max_attempts,
            settings.gemini_thinking_level,
        )

    raise ValueError(f"Unsupported AI_PROVIDER: {settings.ai_provider}")
