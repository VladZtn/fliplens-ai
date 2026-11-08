from app.services.flipscore import calculate_flipscore


def test_profitable_deal_scores_as_buy():
    result = calculate_flipscore(
        purchase_price=500,
        expected_resale_price=750,
        extra_costs=25,
        confidence=0.9,
        risk_count=0,
    )
    assert result.expected_profit == 225
    assert result.roi > 40
    assert result.flip_score >= 75
    assert result.recommendation in {"STRONG_BUY", "EXCEPTIONAL_DEAL"}


def test_loss_is_pass():
    result = calculate_flipscore(
        purchase_price=700,
        expected_resale_price=650,
        confidence=1,
    )
    assert result.expected_profit == -50
    assert result.recommendation == "PASS"


def test_critical_risk_forces_pass():
    result = calculate_flipscore(
        purchase_price=100,
        expected_resale_price=500,
        confidence=1.0,
        risk_flags=["activation_lock"],
    )
    assert result.recommendation == "PASS"
    assert result.flip_score == 0
    assert result.critical_risk is True


def test_weighted_model_mismatch_penalty():
    result = calculate_flipscore(
        purchase_price=590,
        expected_resale_price=750,
        confidence=0.4,
        risk_flags=[
            "potential_model_mismatch_older_generation_appearance",
            "suspicious_upgrade_claim_for_latest_model",
            "missing_box_and_accessories",
            "collection_only_restriction",
        ],
    )
    assert result.risk_penalty == 40
    assert result.risk_level == "HIGH"
    assert result.recommendation == "PASS"
