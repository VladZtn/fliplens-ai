from app.services.next_action import build_next_action


def test_identity_risk_requires_verification_before_negotiation():
    action = build_next_action(
        recommendation="PASS",
        purchase_price=895,
        safe_buy_price=848,
        risk_level="HIGH",
        critical_risk=False,
        risk_flags=["suspicious_device_identity"],
    )
    assert action.code == "VERIFY_IDENTITY"
    assert action.suggested_offer is None


def test_price_above_safe_offer_recommends_negotiation():
    action = build_next_action(
        recommendation="CONSIDER",
        purchase_price=895,
        safe_buy_price=848,
        risk_level="LOW",
        critical_risk=False,
        risk_flags=[],
    )
    assert action.code == "NEGOTIATE"
    assert action.suggested_offer == 848


def test_critical_risk_skips_listing():
    action = build_next_action(
        recommendation="PASS",
        purchase_price=500,
        safe_buy_price=700,
        risk_level="CRITICAL",
        critical_risk=True,
        risk_flags=["activation_lock"],
    )
    assert action.code == "SKIP_LISTING"


def test_strong_scores_are_not_told_to_skip():
    # calculate_flipscore names its best results STRONG_BUY and EXCEPTIONAL_DEAL.
    for recommendation in ("STRONG_BUY", "EXCEPTIONAL_DEAL"):
        action = build_next_action(
            recommendation=recommendation,
            purchase_price=275,
            safe_buy_price=329,
            risk_level="NONE",
            critical_risk=False,
            risk_flags=[],
        )
        assert action.code == "CONTACT_SELLER"
