import pytest

from app.ai.schemas import ListingAnalysis
from app.pricing.engine import _filter_comparables, price_listing
from app.pricing.schemas import MarketComparable


def listing():
    return ListingAnalysis(
        product_name="iPhone 17 Pro Max 256GB",
        brand="Apple",
        model="17 Pro Max",
        category="Phones",
        condition="Used",
        confidence=.8,
        summary="test",
    )


def test_filters_accessories_parts_replicas_and_outlier():
    items = [
        MarketComparable(title="iPhone 17 Pro Max used", price=1050),
        MarketComparable(title="iPhone 17 Pro Max excellent", price=1080),
        MarketComparable(title="iPhone 17 Pro Max phone", price=1100),
        MarketComparable(title="iPhone 17 Pro Max clean", price=1090),
        MarketComparable(title="iPhone 17 Pro Max case cover", price=20),
        MarketComparable(title="iPhone 17 Pro Max broken for parts", price=200),
        MarketComparable(title="iPhone 17 Pro Max replica clone", price=150),
        MarketComparable(title="iPhone 17 Pro Max collector", price=9999),
    ]
    prices = [item.price for item in _filter_comparables(items)]
    assert 20 not in prices
    assert 200 not in prices
    assert 150 not in prices
    assert 9999 not in prices


@pytest.mark.asyncio
async def test_market_pricing_returns_median_range_and_safe_buy():
    result = await price_listing(listing())
    assert result is not None
    assert result.comparable_count >= 10
    assert result.market_low <= result.estimated_market_price <= result.market_high
    assert result.safe_buy_price < result.estimated_market_price
    assert result.pricing_confidence >= .7


@pytest.mark.asyncio
async def test_market_pricing_returns_representative_comparables():
    result = await price_listing(listing())
    assert result is not None
    assert 0 < len(result.comparables) <= 8
    assert result.condition_filter == "used"
    prices = [c.price for c in result.comparables]
    assert all(result.market_low * 0.9 <= p <= result.market_high * 1.1 for p in prices)


def test_query_includes_storage_but_not_ram():
    from app.pricing.query import build_pricing_query

    phone = listing()
    assert build_pricing_query(phone) == "Apple 17 Pro Max 256GB"

    laptop = ListingAnalysis(
        product_name="MacBook Air M1 8GB 256GB",
        brand="Apple",
        model="MacBook Air M1",
        confidence=.8,
        summary="test",
    )
    assert build_pricing_query(laptop) == "Apple MacBook Air M1 256GB"


def test_ebay_filter_excludes_auctions_and_matches_condition():
    from app.pricing.ebay import EbayBrowsePricingProvider

    used = listing()
    assert EbayBrowsePricingProvider.build_filter(used) == "buyingOptions:{FIXED_PRICE},conditions:{USED}"
    sealed = used.model_copy(update={"condition": "Brand new, sealed"})
    assert EbayBrowsePricingProvider.build_filter(sealed).endswith("conditions:{NEW}")
    like_new = used.model_copy(update={"condition": "Like new"})
    assert EbayBrowsePricingProvider.build_filter(like_new).endswith("conditions:{USED}")


def test_query_uses_product_name_when_model_unknown():
    from app.pricing.query import build_pricing_query, pricing_queries

    unverified = ListingAnalysis(
        product_name="iPhone 16 Pro (Desert Titanium)",
        brand="Apple",
        model=None,
        confidence=.9,
        summary="test",
    )
    assert build_pricing_query(unverified) == "Apple iPhone 16 Pro"

    with_storage = unverified.model_copy(update={"variant": "128GB"})
    assert pricing_queries(with_storage) == ["Apple iPhone 16 Pro 128GB", "Apple iPhone 16 Pro"]

    brand_only = ListingAnalysis(product_name="", brand="Apple", confidence=.5, summary="test")
    assert build_pricing_query(brand_only) == ""


def test_no_duplicate_brand_and_storage_removed_for_broad_query():
    from app.pricing.query import pricing_queries

    item = ListingAnalysis(product_name="Apple iPhone 16 Pro 256GB", brand="Apple", model=None, confidence=.9, summary="t")
    assert pricing_queries(item) == ["Apple iPhone 16 Pro 256GB", "Apple iPhone 16 Pro"]


@pytest.mark.asyncio
async def test_falls_back_to_broader_query_when_specific_one_is_thin():
    from app.pricing.schemas import MarketComparable

    class Provider:
        def __init__(self):
            self.queries = []

        async def get_comparables(self, listing, query):
            self.queries.append(query)
            if "256GB" in query:
                return []
            return [
                MarketComparable(title=f"Apple iPhone 16 Pro Unlocked {i}", price=500 + i, currency="GBP")
                for i in range(6)
            ]

    provider = Provider()
    item = ListingAnalysis(product_name="iPhone 16 Pro", brand="Apple", model=None, variant="256GB", confidence=.9, summary="t")
    result = await price_listing(item, provider=provider)
    assert provider.queries == ["Apple iPhone 16 Pro 256GB", "Apple iPhone 16 Pro"]
    assert result is not None and result.query == "Apple iPhone 16 Pro"
