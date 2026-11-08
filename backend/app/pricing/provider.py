from typing import Protocol

from app.ai.schemas import ListingAnalysis
from app.pricing.schemas import MarketComparable


class PricingProvider(Protocol):
    async def get_comparables(self, listing: ListingAnalysis, query: str) -> list[MarketComparable]:
        ...
