from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

client = TestClient(app)


def _post(ip="1.2.3.4"):
    return client.post(
        "/api/v1/deals/analyze-image",
        data={"title": "Apple iPhone 15 Pro 256GB", "purchase_price": "500", "expected_resale_price": "700"},
        files={"image": ("phone.jpg", b"fake-jpeg-data", "image/jpeg")},
        headers={"X-Forwarded-For": ip},
    )


def test_daily_limit_blocks_after_allowance(monkeypatch):
    monkeypatch.setenv("FREE_DAILY_LIMIT", "2")
    get_settings.cache_clear()

    first = _post()
    assert first.status_code == 200
    assert first.json()["usage"] == {"limit": 2, "remaining": 1, "unlimited": False}
    assert _post().status_code == 200
    blocked = _post()
    assert blocked.status_code == 429
    assert "free analyses" in blocked.json()["detail"]

    # A different client still has its own allowance.
    assert _post(ip="5.6.7.8").status_code == 200


def test_spoofed_forwarded_for_prefix_does_not_reset_allowance(monkeypatch):
    monkeypatch.setenv("FREE_DAILY_LIMIT", "1")
    get_settings.cache_clear()

    assert _post(ip="1.2.3.4").status_code == 200
    # Client prepends a fake IP; the proxy-appended last hop is still 1.2.3.4.
    assert _post(ip="9.9.9.9, 1.2.3.4").status_code == 429


def test_usage_endpoint_reports_remaining(monkeypatch):
    monkeypatch.setenv("FREE_DAILY_LIMIT", "3")
    get_settings.cache_clear()
    _post()
    body = client.get("/api/v1/deals/usage", headers={"X-Forwarded-For": "1.2.3.4"}).json()
    assert body["remaining"] == 2


def test_failed_pricing_without_estimate_refunds_allowance(monkeypatch):
    from app.api.routes import deals
    from app.pricing.ebay import EbayPricingError

    monkeypatch.setenv("FREE_DAILY_LIMIT", "1")
    get_settings.cache_clear()

    async def broken_pricing(listing):
        raise EbayPricingError("eBay Browse search failed (500): secret internals")

    monkeypatch.setattr(deals, "price_listing", broken_pricing)
    response = client.post(
        "/api/v1/deals/analyze-image",
        data={"title": "Unknown gadget", "purchase_price": "50"},
        files={"image": ("x.jpg", b"fake", "image/jpeg")},
        headers={"X-Forwarded-For": "1.2.3.4"},
    )
    assert response.status_code == 502
    assert "secret" not in response.json()["detail"]
    # The failed attempt did not use up the only free analysis.
    monkeypatch.undo()
    monkeypatch.setenv("AI_PROVIDER", "mock")
    monkeypatch.setenv("PRICING_PROVIDER", "mock")
    monkeypatch.setenv("FREE_DAILY_LIMIT", "1")
    get_settings.cache_clear()
    assert _post().status_code == 200


def test_pricing_failure_falls_back_to_user_estimate(monkeypatch):
    from app.api.routes import deals
    from app.pricing.ebay import EbayPricingError

    async def broken_pricing(listing):
        raise EbayPricingError("boom")

    monkeypatch.setattr(deals, "price_listing", broken_pricing)
    response = _post()
    assert response.status_code == 200
    body = response.json()
    assert body["pricing_source"] == "user_estimate"
    assert body["pricing_warning"]
    # eBay business fees on a £700 phone are deducted from profit.
    assert body["fees"]["platform"] == "ebay_business"
    assert body["expected_profit"] == round(700 - 500 - body["selling_fees"], 2)
