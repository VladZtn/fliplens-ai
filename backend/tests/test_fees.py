import pytest

from app.services.fees import estimate_selling_fees, max_buy_price
from app.services.flipscore import calculate_flipscore


def test_ebay_business_phone_uses_tiered_rate_order_fee_and_vat():
    fees = estimate_selling_fees(platform="ebay_business", sale_price=700, category_text="Phone Apple iPhone 15 Pro")
    # 6.9% of 700 = 48.30, + 0.40 order fee = 48.70, + 20% VAT = 58.44
    assert fees.final_value_fee == 48.30
    assert fees.per_order_fee == 0.40
    assert fees.total == 58.44


def test_ebay_business_phone_above_threshold_uses_lower_rate():
    fees = estimate_selling_fees(platform="ebay_business", sale_price=1200, category_text="iPhone 17 Pro Max", include_vat=False)
    # 6.9% of 1000 + 3% of 200 = 69 + 6 = 75
    assert fees.final_value_fee == 75.0


def test_console_threshold_is_400():
    fees = estimate_selling_fees(platform="ebay_business", sale_price=500, category_text="Game Console PlayStation 5", include_vat=False)
    # 6.9% of 400 + 2% of 100 = 27.6 + 2 = 29.6
    assert fees.final_value_fee == 29.60


def test_unknown_category_uses_conservative_default():
    fees = estimate_selling_fees(platform="ebay_business", sale_price=100, category_text="garden furniture", include_vat=False)
    assert fees.final_value_fee == 12.90


def test_small_order_fee():
    fees = estimate_selling_fees(platform="ebay_business", sale_price=8, category_text="", include_vat=False)
    assert fees.per_order_fee == 0.30


@pytest.mark.parametrize("platform", ["ebay_private", "vinted", "facebook_local", "none"])
def test_zero_fee_platforms(platform):
    assert estimate_selling_fees(platform=platform, sale_price=500).total == 0


def test_unknown_platform_rejected():
    with pytest.raises(ValueError):
        estimate_selling_fees(platform="gumtree", sale_price=100)


def test_max_buy_price_hits_target_roi_after_fees_and_costs():
    resale, fees, extra = 700.0, 58.44, 15.0
    buy = max_buy_price(resale_price=resale, selling_fees=fees, extra_costs=extra, target_roi=0.20)
    profit = resale - fees - buy - extra
    assert profit / (buy + extra) == pytest.approx(0.20, abs=0.001)


def test_flipscore_profit_subtracts_selling_fees():
    metrics = calculate_flipscore(purchase_price=500, expected_resale_price=700, extra_costs=20, selling_fees=58.44)
    assert metrics.expected_profit == 121.56
    assert metrics.selling_fees == 58.44
