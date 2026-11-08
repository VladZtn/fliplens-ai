import hashlib
import random
import re

from app.ai.schemas import ListingAnalysis
from app.pricing.schemas import MarketComparable


def _anchor_price(listing: ListingAnalysis) -> float:
    text = f"{listing.product_name} {listing.model or ''}".lower()
    if "iphone" in text and ("17 pro max" in text or "pro max" in text):
        return 1080.0
    if "iphone" in text:
        return 650.0
    if "macbook" in text:
        return 700.0
    if "playstation" in text or "ps5" in text:
        return 390.0
    return 500.0


class MockPricingProvider:
    async def get_comparables(self, listing: ListingAnalysis, query: str) -> list[MarketComparable]:
        seed = int(hashlib.sha256(query.lower().encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)
        anchor = _anchor_price(listing)
        clean = [
            MarketComparable(title=f"{query} used excellent condition", price=round(anchor * rng.uniform(.94, 1.06), 2))
            for _ in range(18)
        ]
        noise = [
            MarketComparable(title=f"{query} case cover", price=19.99),
            MarketComparable(title=f"{query} empty box only", price=34.0),
            MarketComparable(title=f"{query} broken for parts", price=220.0),
            MarketComparable(title=f"{query} replica clone", price=160.0),
            MarketComparable(title=f"{query} sealed collector listing", price=anchor * 2.7),
        ]
        return clean + noise
