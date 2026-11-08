from app.services.risk_engine import RiskSeverity, assess_risks


def test_weighted_risks_are_not_equal():
    assessment = assess_risks([
        "missing_box_and_accessories",
        "potential_model_mismatch_older_generation_appearance",
    ])
    penalties = {finding.matched_rule: finding.penalty for finding in assessment.findings}
    assert penalties["missing_accessories"] == 3
    assert penalties["model_mismatch"] == 25
    assert assessment.total_penalty == 28
    assert assessment.highest_severity == RiskSeverity.HIGH


def test_critical_risk_forces_full_penalty():
    assessment = assess_risks(["activation_lock"])
    assert assessment.critical is True
    assert assessment.total_penalty == 100
    assert assessment.highest_severity == RiskSeverity.CRITICAL


def test_duplicate_semantic_flags_are_not_double_charged():
    assessment = assess_risks([
        "potential_model_mismatch",
        "model_identity_mismatch",
    ])
    assert assessment.total_penalty == 25
    assert len(assessment.findings) == 1
