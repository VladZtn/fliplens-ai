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


def gpu():
    return ListingAnalysis(
        product_name="Gigabyte GeForce RTX 3060 VISION OC 12GB Graphics Card",
        brand="Gigabyte",
        model="RTX 3060 VISION OC",
        variant="12GB",
        category="Graphics Cards",
        confidence=.8,
        summary="test",
    )


def test_short_titles_of_the_same_product_are_kept():
    # Real eBay UK titles. Dropping the short ones left only the dearest
    # listings and pushed the market price up by about £45.
    titles = [
        "nvidia geforce rtx 3060 12gb graphics card",
        "Gigabyte RTX 3060 12GB Graphics Card",
        "GeForce RTX 3060 VENTUS 12GB OC",
        "MSI NVIDIA GeForce RTX 3060 VENTUS 3X 12G OC GDDR6 Graphics Card",
        "ASUS Dual GeForce RTX 3060 12GB GDDR6 Graphics Card NON-LHR",
    ]
    items = [MarketComparable(title=title, price=320) for title in titles]
    assert len(apply_identity_scores(gpu(), items)) == len(titles)


def test_other_tier_and_other_memory_size_are_rejected():
    items = [
        MarketComparable(title="Gigabyte GeForce RTX 3060 Ti Gaming OC 8G graphics card", price=275),
        MarketComparable(title="ASUS Dual NVIDIA GeForce RTX 3060 Ti OC - White", price=260),
        MarketComparable(title="Gigabyte GeForce RTX 3060 OC 8GB Graphics Card", price=240),
        MarketComparable(title="Gigabyte GeForce RTX 4060 OC 12GB Graphics Card", price=400),
    ]
    assert apply_identity_scores(gpu(), items) == []


def test_phone_tier_must_match_both_ways():
    pro = ListingAnalysis(product_name="Apple iPhone 16 Pro 128GB", brand="Apple", confidence=.9, summary="t")
    items = [
        MarketComparable(title="Apple iPhone 16 128GB Unlocked", price=450),
        MarketComparable(title="Apple iPhone 16 Pro Max 128GB Unlocked", price=700),
        MarketComparable(title="Apple iPhone 16 Pro 128GB Unlocked", price=600),
    ]
    matched = apply_identity_scores(pro, items)
    assert [item.price for item in matched] == [600]
