from app.providers.base import MarketProvider

class MockProvider(MarketProvider):
    DATABASE = {
        "apple macbook air m1 8gb": 540,
        "apple iphone 15 pro": 760,
        "playstation 5": 340,
    }

    def get_market_price(self, query: str):
        return self.DATABASE.get(query.lower())