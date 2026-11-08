from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_deal_image_endpoint_uses_user_estimate_without_market_data(monkeypatch):
    from app.api.routes import deals

    async def no_market(listing):
        return None

    monkeypatch.setattr(deals, "price_listing", no_market)
    response = client.post(
        "/api/v1/deals/analyze-image",
        data={
            "title": "Apple iPhone 15 Pro 256GB",
            "description": "Used, unlocked, includes box",
            "purchase_price": "500",
            "expected_resale_price": "700",
            "extra_costs": "20",
            "sell_platform": "none",
        },
        files={"image": ("phone.jpg", b"fake-jpeg-data", "image/jpeg")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["listing"]["brand"] == "Apple"
    assert body["expected_profit"] == 180
    assert 0 <= body["flip_score"] <= 100
    assert body["pricing_source"] == "user_estimate"


def test_deal_image_endpoint_prices_from_market_when_model_unknown():
    # Mock AI leaves the model empty; pricing must still search by product name.
    response = client.post(
        "/api/v1/deals/analyze-image",
        data={"title": "Apple iPhone 15 Pro 256GB", "purchase_price": "500", "sell_platform": "none"},
        files={"image": ("phone.jpg", b"fake-jpeg-data", "image/jpeg")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["pricing_source"] == "mock_market_comps"
    assert body["market_pricing"]["query"].startswith("Apple iPhone 15 Pro")
