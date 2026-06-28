from pydantic import BaseModel

class AnalyzeResponse(BaseModel):
    normalized_title: str
    estimated_market_price: float
    expected_profit: float
    roi: float
    score: int
    recommendation: str