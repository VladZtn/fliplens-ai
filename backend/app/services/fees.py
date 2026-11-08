"""Selling-fee estimates for UK resale platforms.

eBay UK business-seller rates follow eBay's published fee page
("Fees for business sellers", ebay.co.uk help id 4809, rate card effective
12 February 2026). Fees on that page are exclusive of VAT; most small
resellers are not VAT-registered and cannot reclaim it, so VAT is added by
default.

eBay's rules say people who buy items to resell should register as business
sellers, which is why ``ebay_business`` is the default platform.

Rates change. Keep this table in one place and re-check it against eBay's
page when they announce a new rate card.
"""

from dataclasses import dataclass
from enum import StrEnum


class SellPlatform(StrEnum):
    EBAY_BUSINESS = "ebay_business"
    EBAY_PRIVATE = "ebay_private"
    VINTED = "vinted"
    FACEBOOK_LOCAL = "facebook_local"
    NONE = "none"


PLATFORM_LABELS = {
    SellPlatform.EBAY_BUSINESS: "eBay UK (business seller)",
    SellPlatform.EBAY_PRIVATE: "eBay UK (private seller)",
    SellPlatform.VINTED: "Vinted UK",
    SellPlatform.FACEBOOK_LOCAL: "Facebook Marketplace (local collection)",
    SellPlatform.NONE: "No platform fees",
}

VAT_RATE = 0.20


@dataclass(frozen=True)
class _TierRule:
    name: str
    keywords: tuple[str, ...]
    rate: float
    threshold: float | None = None
    rate_above: float | None = None


# Ordered: first keyword match wins. Matched against the AI category,
# product name and model, lower-cased.
_EBAY_BUSINESS_RULES: tuple[_TierRule, ...] = (
    _TierRule(
        "Video game consoles",
        ("console", "playstation", "ps5", "ps4", "xbox", "nintendo switch", "steam deck"),
        0.069, 400.0, 0.02,
    ),
    _TierRule(
        "Mobile & smart phones",
        ("phone", "iphone", "smartphone", "galaxy s", "pixel"),
        0.069, 1000.0, 0.03,
    ),
    _TierRule(
        "Laptops & tablets",
        ("laptop", "macbook", "notebook", "netbook", "chromebook", "tablet", "ipad", "e-reader", "kindle"),
        0.069, 1000.0, 0.03,
    ),
    _TierRule(
        "Cameras & lenses",
        ("camera", "camcorder", "lens", "dslr", "mirrorless"),
        0.069, 1000.0, 0.03,
    ),
    _TierRule(
        "TV, headphones & home audio",
        ("television", " tv", "headphone", "earbuds", "airpods", "hifi", "hi-fi", "soundbar", "speaker", "home cinema"),
        0.069, 1000.0, 0.03,
    ),
    _TierRule(
        "Computers, tablets & networking (other)",
        ("computer", "desktop", "monitor", "graphics card", "gpu", "router"),
        0.099,
    ),
    _TierRule(
        "Video games & consoles (other)",
        ("video game", "controller", "gaming"),
        0.099,
    ),
)

# Conservative default for categories not matched above: eBay's published
# range for most categories tops out at 12.9%.
_EBAY_BUSINESS_DEFAULT = _TierRule("Other categories (conservative default)", (), 0.129)


@dataclass(frozen=True)
class FeeEstimate:
    platform: str
    platform_label: str
    total: float
    final_value_fee: float
    per_order_fee: float
    vat: float
    rule: str
    note: str


def _ebay_per_order_fee(sale_price: float) -> float:
    return 0.30 if sale_price <= 10 else 0.40


def _match_rule(category_text: str) -> _TierRule:
    text = f" {category_text.lower()} "
    for rule in _EBAY_BUSINESS_RULES:
        if any(keyword in text for keyword in rule.keywords):
            return rule
    return _EBAY_BUSINESS_DEFAULT


def _tiered_fee(rule: _TierRule, sale_price: float) -> float:
    if rule.threshold is None or rule.rate_above is None or sale_price <= rule.threshold:
        return sale_price * rule.rate
    return rule.threshold * rule.rate + (sale_price - rule.threshold) * rule.rate_above


def _describe(rule: _TierRule) -> str:
    if rule.threshold is None or rule.rate_above is None:
        return f"{rule.name}: {rule.rate * 100:.1f}%"
    return (
        f"{rule.name}: {rule.rate * 100:.1f}% up to £{rule.threshold:,.0f}, "
        f"{rule.rate_above * 100:.0f}% above"
    )


def estimate_selling_fees(
    *,
    platform: str,
    sale_price: float,
    category_text: str = "",
    include_vat: bool = True,
) -> FeeEstimate:
    try:
        selected = SellPlatform(platform.strip().lower())
    except ValueError as exc:
        raise ValueError(f"Unsupported sell platform: {platform}") from exc

    label = PLATFORM_LABELS[selected]
    sale_price = max(0.0, float(sale_price))

    if selected is SellPlatform.EBAY_BUSINESS:
        rule = _match_rule(category_text)
        fvf = _tiered_fee(rule, sale_price)
        per_order = _ebay_per_order_fee(sale_price)
        vat = (fvf + per_order) * VAT_RATE if include_vat else 0.0
        total = fvf + per_order + vat
        return FeeEstimate(
            platform=selected.value,
            platform_label=label,
            total=round(total, 2),
            final_value_fee=round(fvf, 2),
            per_order_fee=round(per_order, 2),
            vat=round(vat, 2),
            rule=_describe(rule) + f" + £{per_order:.2f} per order",
            note=(
                "eBay business-seller rates, plus 20% VAT on fees (not reclaimable unless you are VAT-registered)."
                if include_vat
                else "eBay business-seller rates, excluding VAT."
            ),
        )

    notes = {
        SellPlatform.EBAY_PRIVATE: (
            "eBay UK charges private sellers no final value fee in most categories. "
            "eBay expects people who buy to resell to register as business sellers."
        ),
        SellPlatform.VINTED: "Vinted charges buyers, not sellers. Optional promotions are extra.",
        SellPlatform.FACEBOOK_LOCAL: "No platform fee for local collection and cash/in-person payment.",
        SellPlatform.NONE: "No selling fees applied.",
    }
    return FeeEstimate(
        platform=selected.value,
        platform_label=label,
        total=0.0,
        final_value_fee=0.0,
        per_order_fee=0.0,
        vat=0.0,
        rule="0%",
        note=notes[selected],
    )


def max_buy_price(
    *,
    resale_price: float,
    selling_fees: float,
    extra_costs: float = 0.0,
    target_roi: float = 0.20,
) -> float:
    """Highest purchase price that still returns ``target_roi`` on money spent.

    ROI = (resale - fees - purchase - extra) / (purchase + extra) >= target
    =>   purchase <= (resale - fees) / (1 + target) - extra
    """
    value = (resale_price - selling_fees) / (1 + target_roi) - extra_costs
    return round(max(0.0, value), 2)
