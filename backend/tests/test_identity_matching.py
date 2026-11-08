from app.ai.schemas import ListingAnalysis
from app.pricing.identity import apply_identity_scores, score_identity
from app.pricing.schemas import MarketComparable


def listing():
    return ListingAnalysis(
        product_name="Apple iPhone 17 Pro Max 256GB",
        brand="Apple",
        model="iPhone 17 Pro Max 256GB",
        category="Phones",
        condition="Used",
        confidence=.8,
        summary="test",
    )


def test_exact_model_and_storage_scores_high():
    comp = MarketComparable(title="Apple iPhone 17 Pro Max 256GB Unlocked", price=1099)
    assert score_identity(listing(), comp) >= .8


def test_wrong_storage_scores_lower():
    exact = MarketComparable(title="iPhone 17 Pro Max 256GB", price=1099)
    wrong = MarketComparable(title="iPhone 17 Pro Max 512GB", price=1199)
    assert score_identity(listing(), exact) > score_identity(listing(), wrong)


def test_accessory_is_rejected():
    items = [
        MarketComparable(title="iPhone 17 Pro Max case cover", price=20),
        MarketComparable(title="Apple iPhone 17 Pro Max 256GB", price=1099),
    ]
    matched = apply_identity_scores(listing(), items)
    assert len(matched) == 1
    assert matched[0].price == 1099
