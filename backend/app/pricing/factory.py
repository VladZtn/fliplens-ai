from functools import lru_cache

from app.config import get_settings
from app.pricing.ebay import EbayBrowsePricingProvider
from app.pricing.mock import MockPricingProvider
from app.pricing.provider import PricingProvider


@lru_cache(maxsize=4)
def _ebay_provider(
    client_id: str,
    client_secret: str,
    marketplace_id: str,
    scope: str,
    result_limit: int,
) -> EbayBrowsePricingProvider:
    # Cached so the OAuth token (valid ~2h) is reused across requests
    # instead of being fetched on every analysis.
    return EbayBrowsePricingProvider(
        client_id=client_id,
        client_secret=client_secret,
        marketplace_id=marketplace_id,
        scope=scope,
        result_limit=result_limit,
    )


def create_pricing_provider() -> PricingProvider:
    settings = get_settings()
    provider = settings.pricing_provider.strip().lower()

    if provider == "ebay":
        if not settings.ebay_client_id or not settings.ebay_client_secret:
            raise ValueError(
                "EBAY_CLIENT_ID and EBAY_CLIENT_SECRET are required when PRICING_PROVIDER=ebay"
            )
        return _ebay_provider(
            settings.ebay_client_id,
            settings.ebay_client_secret,
            settings.ebay_marketplace_id,
            settings.ebay_scope,
            settings.ebay_result_limit,
        )
    if provider == "mock":
        return MockPricingProvider()

    raise ValueError(f"Unsupported PRICING_PROVIDER: {settings.pricing_provider}")
