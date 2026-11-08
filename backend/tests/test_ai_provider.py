from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


def test_mock_ai_listing_analysis(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "mock")
    get_settings.cache_clear()

    with TestClient(app) as client:
        response = client.post(
            "/ai/analyze-listing",
            json={
                "title": "Used Apple MacBook Air M1 8GB £300",
                "description": "Works well, charger included",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["brand"] == "Apple"
    assert body["category"] == "Laptop"
    assert body["currency"] == "GBP"
    assert body["asking_price"] == 300.0


def test_existing_valuation_endpoint_still_works():
    with TestClient(app) as client:
        response = client.post(
            "/analyze",
            json={"title": "Apple MacBook Air M1 8GB", "price": 300},
        )

    assert response.status_code == 200
    assert response.json()["recommendation"] == "BUY"
