from app.services.parser import parse_product
from app.providers.mock_provider import MockProvider
from app.providers.ebay_provider import EbayProvider


class ValuationEngine:
    def __init__(self):
        self.provider = MockProvider()

    def analyze(self, title: str, price: float):
        product = parse_product(title)
        market_price = self.provider.get_market_price(
            product.normalized_title
        )

        if market_price is None:
            market_price = price * 1.35

        profit = market_price - price
        roi = (profit / price) * 100
        score = max(0, min(100, int(roi)))
        recommendation = "BUY" if roi >= 10 else "PASS"
        return {
            "normalized_title": product.normalized_title,
            "estimated_market_price": round(market_price, 2),
            "expected_profit": round(profit, 2),
            "roi": round(roi, 2),
            "score": score,
            "recommendation": recommendation,
        }