import time
from statistics import median

from app.ai.schemas import ListingAnalysis
from app.pricing.factory import create_pricing_provider
from app.pricing.identity import apply_identity_scores
from app.pricing.provider import PricingProvider
from app.pricing.query import pricing_queries, wants_new_condition
from app.pricing.schemas import MarketComparable, MarketPricing

EXCLUDED_TERMS = (
    "case", "cover", "screen protector", "empty box", "box only",
    "for parts", "parts only", "broken", "replica", "clone",
)


def _filter_comparables(items: list[MarketComparable]) -> list[MarketComparable]:
    seen: set[tuple[str, float]] = set()
    clean: list[MarketComparable] = []
    for item in items:
        title = item.title.lower()
        if any(term in title for term in EXCLUDED_TERMS):
            continue
        key = (" ".join(title.split()), round(item.price, 2))
        if key in seen:
            continue
        seen.add(key)
        clean.append(item)

    if len(clean) < 4:
        return clean

    prices = sorted(item.price for item in clean)
    center = median(prices)
    deviations = [abs(price - center) for price in prices]
    mad = median(deviations)
    if mad > 0:
        robust_limit = 3.5 * 1.4826 * mad
        clean = [item for item in clean if abs(item.price - center) <= robust_limit]

    if len(clean) < 4:
        return clean

    prices = sorted(item.price for item in clean)
    mid = len(prices) // 2
    lower = prices[:mid]
    upper = prices[mid + (len(prices) % 2):]
    q1, q3 = median(lower), median(upper)
    iqr = q3 - q1
    if iqr <= 0:
        return clean
    low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    return [item for item in clean if low <= item.price <= high]


_CACHE_TTL_SECONDS = 30 * 60
_CACHE_MAX_ENTRIES = 500
_comps_cache: dict[tuple[str, str, str], tuple[float, list[MarketComparable]]] = {}


def clear_pricing_cache() -> None:
    _comps_cache.clear()


async def _cached_comparables(
    provider: PricingProvider,
    listing: ListingAnalysis,
    query: str,
) -> list[MarketComparable]:
    """Reuse comparables for the same search for 30 minutes.

    Saves eBay API calls when several users check the same product.
    """
    condition = "new" if wants_new_condition(listing) else "used"
    key = (provider.__class__.__name__, query.lower(), condition)
    now = time.monotonic()
    hit = _comps_cache.get(key)
    if hit and now - hit[0] < _CACHE_TTL_SECONDS:
        return hit[1]

    items = await provider.get_comparables(listing, query)
    if len(_comps_cache) >= _CACHE_MAX_ENTRIES:
        oldest = min(_comps_cache, key=lambda k: _comps_cache[k][0])
        _comps_cache.pop(oldest, None)
    _comps_cache[key] = (now, items)
    return items


def _representative(comps: list[MarketComparable], center: float, limit: int = 8) -> list[MarketComparable]:
    """Comparables closest to the median, for showing to the user."""
    return sorted(comps, key=lambda item: abs(item.price - center))[:limit]


def _confidence(count: int, spread_ratio: float) -> float:
    volume = min(1.0, count / 15)
    consistency = max(0.0, 1.0 - min(1.0, spread_ratio))
    return round(min(.95, .25 + volume * .45 + consistency * .25), 2)


async def price_listing(
    listing: ListingAnalysis,
    provider: PricingProvider | None = None,
) -> MarketPricing | None:
    provider = provider or create_pricing_provider()
    queries = pricing_queries(listing)
    if not queries:
        return None

    # Try the most specific search first (with storage), then a broader one.
    for query in queries:
        raw_comps = await _cached_comparables(provider, listing, query)
        same_currency = [item for item in raw_comps if (item.currency or "GBP").upper() == "GBP"]
        identity_matched = apply_identity_scores(listing, same_currency)
        comps = _filter_comparables(identity_matched)
        if len(comps) >= 3:
            break
    else:
        return None

    prices = sorted(item.price for item in comps)
    estimate = median(prices)
    low_index = max(0, round((len(prices) - 1) * .25))
    high_index = min(len(prices) - 1, round((len(prices) - 1) * .75))
    market_low, market_high = prices[low_index], prices[high_index]
    spread_ratio = (market_high - market_low) / estimate if estimate else 1.0
    confidence = _confidence(len(prices), spread_ratio)

    # Conservative MVP offer: target 20% gross ROI and reserve 5% for friction.
    safe_buy = estimate / 1.20 - estimate * .05

    return MarketPricing(
        query=query,
        estimated_market_price=round(estimate, 2),
        market_low=round(market_low, 2),
        market_high=round(market_high, 2),
        comparable_count=len(prices),
        raw_comparable_count=len(raw_comps),
        pricing_confidence=confidence,
        safe_buy_price=round(max(0, safe_buy), 2),
        source=(
            "ebay_active_listings"
            if provider.__class__.__name__ == "EbayBrowsePricingProvider"
            else "mock_market_comps"
        ),
        data_kind="active_listings",
        condition_filter="new" if wants_new_condition(listing) else "used",
        comparables=_representative(comps, estimate),
    )
