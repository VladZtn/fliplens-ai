import pytest

from app.config import get_settings
from app.pricing.engine import clear_pricing_cache
from app.services.usage import limiter


@pytest.fixture(autouse=True)
def use_mock_ai_by_default(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "mock")
    monkeypatch.setenv("PRICING_PROVIDER", "mock")
    monkeypatch.setenv("FREE_DAILY_LIMIT", "1000")
    monkeypatch.setenv("TRUSTED_PROXY_HOPS", "1")
    get_settings.cache_clear()
    limiter.reset()
    clear_pricing_cache()
    yield
    get_settings.cache_clear()
    limiter.reset()
    clear_pricing_cache()
