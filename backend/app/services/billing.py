"""Stripe subscription access without user accounts.

Stripe is the only source of truth, so no database or webhook is needed:
1. /billing/checkout opens a Stripe Checkout page for the monthly price.
   A Stripe Payment Link whose redirect URL ends in
   ?session_id={CHECKOUT_SESSION_ID} works the same way.
2. Stripe sends the buyer back with ?session_id=..., which is exchanged for
   the subscription id. The browser keeps that id as its "pass".
3. Every request carrying the pass is checked against Stripe (cached for a
   few minutes), so a cancelled or unpaid subscription stops working by itself.
"""

import re
import time

import httpx

from app.config import get_settings

API = "https://api.stripe.com/v1"
ACTIVE_STATUSES = {"active", "trialing"}
SESSION_ID = re.compile(r"^cs_(test|live)_[A-Za-z0-9]+$")
SUBSCRIPTION_ID = re.compile(r"^sub_[A-Za-z0-9]+$")

_cache: dict[str, tuple[float, bool]] = {}


class BillingError(Exception):
    pass


def is_configured() -> bool:
    settings = get_settings()
    return bool(settings.stripe_secret_key and settings.stripe_price_id)


async def _stripe(method: str, path: str, data: dict[str, str] | None = None) -> dict:
    settings = get_settings()
    if not settings.stripe_secret_key:
        raise BillingError("Stripe is not configured")
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.request(
                method,
                f"{API}{path}",
                data=data,
                headers={"Authorization": f"Bearer {settings.stripe_secret_key}"},
            )
    except httpx.HTTPError as exc:
        raise BillingError(f"Stripe request failed: {type(exc).__name__}") from exc
    if response.status_code >= 400:
        raise BillingError(f"Stripe returned {response.status_code} for {path.split('/')[1]}")
    return response.json()


async def create_checkout_url() -> str:
    settings = get_settings()
    if not is_configured():
        raise BillingError("Stripe is not configured")
    base = settings.frontend_url.rstrip("/")
    session = await _stripe(
        "POST",
        "/checkout/sessions",
        {
            "mode": "subscription",
            "line_items[0][price]": settings.stripe_price_id or "",
            "line_items[0][quantity]": "1",
            "success_url": f"{base}/?session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": f"{base}/",
        },
    )
    return session["url"]


async def pass_from_session(session_id: str) -> str | None:
    """Exchange a finished Checkout session for the subscription id."""
    if not SESSION_ID.match(session_id):
        return None
    session = await _stripe("GET", f"/checkout/sessions/{session_id}")
    subscription = session.get("subscription")
    if session.get("status") != "complete" or not isinstance(subscription, str):
        return None
    return subscription


async def has_active_pass(subscription_id: str | None) -> bool:
    if not subscription_id or not SUBSCRIPTION_ID.match(subscription_id):
        return False
    now = time.monotonic()
    cached = _cache.get(subscription_id)
    if cached and cached[0] > now:
        return cached[1]
    try:
        subscription = await _stripe("GET", f"/subscriptions/{subscription_id}")
    except BillingError:
        # Stripe unreachable or unknown id: fall back to the free allowance.
        return False
    active = subscription.get("status") in ACTIVE_STATUSES
    _cache[subscription_id] = (now + get_settings().pass_cache_seconds, active)
    return active


def clear_cache() -> None:
    _cache.clear()
