from app.providers.base import MarketProvider

class EbayProvider(MarketProvider):
    def get_market_price(self, query: str):
        print(f"Searching eBay for: {query}")
        return None