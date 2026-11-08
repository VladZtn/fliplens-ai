from pydantic import BaseModel, Field

from app.ai.schemas import ListingAnalysis
from app.pricing.schemas import MarketPricing


class NextActionResponse(BaseModel):
    code: str
    title: str
    message: str
    suggested_offer: float | None = None


class FeeBreakdown(BaseModel):
    platform: str
    platform_label: str
    total: float
    final_value_fee: float
    per_order_fee: float
    vat: float
    rule: str
    note: str


class UsageInfo(BaseModel):
    limit: int
    remaining: int
    unlimited: bool = False


class DealAnalysis(BaseModel):
    listing: ListingAnalysis
    purchase_price: float
    expected_resale_price: float
    market_pricing: MarketPricing | None = None
    next_action: NextActionResponse
    extra_costs: float
    selling_fees: float = 0.0
    fees: FeeBreakdown | None = None
    usage: UsageInfo | None = None
    expected_profit: float
    roi: float
    margin: float
    flip_score: int = Field(ge=0, le=100)
    recommendation: str
    risk_penalty: int = Field(ge=0, le=100)
    risk_level: str = "NONE"
    critical_risk: bool = False
    score_roi_points: int = 0
    score_margin_points: int = 0
    score_confidence_points: int = 0
    score_risk_points: int = 0
    base_deal_score: int = 0
    decision_reason: str
    pricing_source: str = "user_estimate"
    pricing_warning: str | None = None
    disclaimer: str = (
        "Expected resale price is supplied by the user in this MVP and is not yet verified against live sold-market data."
    )
