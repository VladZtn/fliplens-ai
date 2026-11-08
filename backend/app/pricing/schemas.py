from pydantic import BaseModel, Field


class MarketComparable(BaseModel):
    title: str
    price: float = Field(gt=0)
    currency: str = "GBP"
    condition: str | None = None
    item_url: str | None = None
    source_id: str | None = None
    identity_score: float = Field(default=0.0, ge=0, le=1)


class MarketPricing(BaseModel):
    query: str
    estimated_market_price: float
    market_low: float
    market_high: float
    comparable_count: int = Field(ge=0)
    raw_comparable_count: int = Field(default=0, ge=0)
    pricing_confidence: float = Field(ge=0, le=1)
    safe_buy_price: float
    source: str
    data_kind: str = "active_listings"
    condition_filter: str | None = None
    comparables: list[MarketComparable] = Field(default_factory=list)
