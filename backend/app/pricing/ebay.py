import base64
import time

import httpx

from app.ai.schemas import ListingAnalysis
from app.pricing.query import wants_new_condition
from app.pricing.schemas import MarketComparable


class EbayPricingError(RuntimeError):
    pass


class EbayBrowsePricingProvider:
    """Live comparables from the eBay Browse API.

    The Browse API only returns *active* listings, so prices are asking prices,
    not sold prices. Auctions are excluded because their current bid is not a
    market price until the auction ends.
    """

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        marketplace_id: str = "EBAY_GB",
        scope: str = "https://api.ebay.com/oauth/api_scope",
        result_limit: int = 50,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.marketplace_id = marketplace_id
        self.scope = scope
        self.result_limit = max(10, min(200, result_limit))
        self.timeout_seconds = timeout_seconds
        self._token: str | None = None
        self._token_expires_at = 0.0

    async def _access_token(self, client: httpx.AsyncClient) -> str:
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token

        basic = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()
        response = await client.post(
            "https://api.ebay.com/identity/v1/oauth2/token",
            headers={
                "Authorization": f"Basic {basic}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "client_credentials",
                "scope": self.scope,
            },
        )
        if response.is_error:
            raise EbayPricingError(
                f"eBay OAuth failed ({response.status_code}): {response.text[:300]}"
            )
        payload = response.json()
        self._token = payload["access_token"]
        self._token_expires_at = time.time() + int(payload.get("expires_in", 7200))
        return self._token

    @staticmethod
    def build_filter(listing: ListingAnalysis) -> str:
        condition = "NEW" if wants_new_condition(listing) else "USED"
        return f"buyingOptions:{{FIXED_PRICE}},conditions:{{{condition}}}"

    async def get_comparables(
        self,
        listing: ListingAnalysis,
        query: str,
    ) -> list[MarketComparable]:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            token = await self._access_token(client)
            response = await client.get(
                "https://api.ebay.com/buy/browse/v1/item_summary/search",
                params={
                    "q": query,
                    "limit": self.result_limit,
                    "filter": self.build_filter(listing),
                },
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-EBAY-C-MARKETPLACE-ID": self.marketplace_id,
                },
            )
        if response.is_error:
            raise EbayPricingError(
                f"eBay Browse search failed ({response.status_code}): {response.text[:400]}"
            )

        payload = response.json()
        items: list[MarketComparable] = []
        for row in payload.get("itemSummaries", []):
            price = row.get("price") or {}
            try:
                value = float(price.get("value"))
            except (TypeError, ValueError):
                continue
            if value <= 0:
                continue
            items.append(
                MarketComparable(
                    title=row.get("title") or "Untitled eBay listing",
                    price=value,
                    currency=price.get("currency") or "GBP",
                    condition=row.get("condition"),
                    item_url=row.get("itemWebUrl"),
                    source_id=row.get("itemId"),
                )
            )
        return items
