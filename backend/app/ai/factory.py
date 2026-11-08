from app.ai.providers.base import AIProvider
from app.ai.providers.gemini import GeminiAIProvider
from app.ai.providers.mock import MockAIProvider
from app.config import Settings, get_settings


def create_ai_provider(settings: Settings | None = None) -> AIProvider:
    settings = settings or get_settings()
    provider = settings.ai_provider.strip().lower()

    if provider == "mock":
        return MockAIProvider()
    if provider == "gemini":
        return GeminiAIProvider(
            api_key=settings.gemini_api_key or "",
            model=settings.gemini_model,
            timeout_seconds=settings.ai_timeout_seconds,
            fallback_models=settings.gemini_fallback_models.split(","),
            max_attempts_per_model=settings.gemini_max_attempts,
        )

    raise ValueError(f"Unsupported AI_PROVIDER: {settings.ai_provider}")
