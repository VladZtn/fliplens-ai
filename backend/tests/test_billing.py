from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.services import billing

client = TestClient(app)

SUB = "sub_1TestSubscription"
SESSION = "cs_test_a1B2c3"


def _post(headers=None):
    return client.post(
        "/api/v1/deals/analyze-image",
        data={"title": "MSI RTX 3070 8GB", "purchase_price": "170", "expected_resale_price": "240"},
        files={"image": ("gpu.jpg", b"fake-jpeg-data", "image/jpeg")},
        headers={"X-Forwarded-For": "1.2.3.4", **(headers or {})},
    )


def _fake_stripe(monkeypatch, responses):
    calls = []

    async def fake(method, path, data=None):
        calls.append((method, path, data))
        if path not in responses:
            raise billing.BillingError("Stripe returned 404")
        return responses[path]

    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_dummy")
    monkeypatch.setenv("STRIPE_PRICE_ID", "price_dummy")
    monkeypatch.setenv("FRONTEND_URL", "https://fliplens.example")
    get_settings.cache_clear()
    billing.clear_cache()
    monkeypatch.setattr(billing, "_stripe", fake)
    return calls


def test_active_subscription_skips_daily_limit(monkeypatch):
    calls = _fake_stripe(monkeypatch, {f"/subscriptions/{SUB}": {"status": "active"}})
    monkeypatch.setenv("FREE_DAILY_LIMIT", "1")
    get_settings.cache_clear()

    for _ in range(3):
        response = _post({"X-FlipLens-Pass": SUB})
        assert response.status_code == 200
        assert response.json()["usage"]["unlimited"] is True
    # Stripe is asked once; later checks come from the cache.
    assert len(calls) == 1

    # The free allowance of the same IP was not touched by the paid checks.
    assert _post().status_code == 200
    assert _post().status_code == 429


def test_cancelled_or_unknown_pass_gets_free_allowance_only(monkeypatch):
    _fake_stripe(monkeypatch, {f"/subscriptions/{SUB}": {"status": "canceled"}})
    monkeypatch.setenv("FREE_DAILY_LIMIT", "1")
    get_settings.cache_clear()

    assert _post({"X-FlipLens-Pass": SUB}).status_code == 200
    assert _post({"X-FlipLens-Pass": SUB}).status_code == 429
    assert _post({"X-FlipLens-Pass": "sub_doesNotExist"}).status_code == 429
    assert _post({"X-FlipLens-Pass": "../customers"}).status_code == 429


def test_usage_endpoint_reports_unlimited_for_subscriber(monkeypatch):
    _fake_stripe(monkeypatch, {f"/subscriptions/{SUB}": {"status": "active"}})
    body = client.get("/api/v1/deals/usage", headers={"X-FlipLens-Pass": SUB}).json()
    assert body["unlimited"] is True


def test_checkout_returns_stripe_url(monkeypatch):
    calls = _fake_stripe(
        monkeypatch, {"/checkout/sessions": {"url": "https://checkout.stripe.com/c/pay/x"}}
    )
    response = client.post("/api/v1/billing/checkout")
    assert response.status_code == 200
    assert response.json()["url"].startswith("https://checkout.stripe.com/")
    _, _, data = calls[0]
    assert data["mode"] == "subscription"
    assert data["line_items[0][price]"] == "price_dummy"
    assert data["success_url"] == "https://fliplens.example/?session_id={CHECKOUT_SESSION_ID}"


def test_checkout_is_unavailable_without_keys():
    billing.clear_cache()
    assert client.post("/api/v1/billing/checkout").status_code == 503


def test_pass_is_issued_only_for_completed_checkout(monkeypatch):
    _fake_stripe(
        monkeypatch,
        {
            f"/checkout/sessions/{SESSION}": {"status": "complete", "subscription": SUB},
            "/checkout/sessions/cs_test_open": {"status": "open", "subscription": None},
        },
    )
    done = client.get("/api/v1/billing/pass", params={"session_id": SESSION})
    assert done.status_code == 200
    assert done.json() == {"pass": SUB}
    assert client.get("/api/v1/billing/pass", params={"session_id": "cs_test_open"}).status_code == 402
    assert client.get("/api/v1/billing/pass", params={"session_id": "not-a-session"}).status_code == 402
