from dataclasses import dataclass

from app.services.risk_engine import RiskAssessment, assess_risks


@dataclass(frozen=True)
class DealMetrics:
    purchase_price: float
    expected_resale_price: float
    extra_costs: float
    selling_fees: float
    expected_profit: float
    roi: float
    margin: float
    flip_score: int
    recommendation: str
    risk_penalty: int
    risk_level: str
    critical_risk: bool
    score_roi_points: int
    score_margin_points: int
    score_confidence_points: int
    score_risk_points: int
    base_deal_score: int
    decision_reason: str


def _decision_reason(*, recommendation: str, profit: float, roi: float, risk_level: str, critical: bool) -> str:
    if critical:
        return "A critical risk signal makes this deal unsafe regardless of the potential profit."
    if profit <= 0:
        return "The current numbers do not leave an expected profit after costs."
    if risk_level in {"HIGH", "CRITICAL"}:
        return f"The deal could make money, but {risk_level.lower()} risk outweighs the expected reward."
    if roi < 15:
        return "The expected return is too thin to leave a comfortable margin for error."
    if recommendation == "HIGH_RISK":
        return "The deal has potential, but the current margin and uncertainty need more verification."
    if recommendation == "CONSIDER":
        return "The economics are viable, but verify the remaining risks before buying."
    return "The expected return and current risk profile make this deal attractive."


def calculate_flipscore(
    *,
    purchase_price: float,
    expected_resale_price: float,
    extra_costs: float = 0.0,
    selling_fees: float = 0.0,
    confidence: float = 0.5,
    risk_flags: list[str] | None = None,
    risk_count: int | None = None,
) -> DealMetrics:
    if purchase_price <= 0:
        raise ValueError("purchase_price must be greater than 0")
    if expected_resale_price <= 0:
        raise ValueError("expected_resale_price must be greater than 0")
    if extra_costs < 0:
        raise ValueError("extra_costs cannot be negative")
    if selling_fees < 0:
        raise ValueError("selling_fees cannot be negative")

    total_cost = purchase_price + extra_costs
    profit = expected_resale_price - selling_fees - total_cost
    roi = (profit / total_cost) * 100
    margin = (profit / expected_resale_price) * 100

    assessment: RiskAssessment
    if risk_flags is not None:
        assessment = assess_risks(risk_flags)
    else:
        count = max(0, risk_count or 0)
        assessment = RiskAssessment(
            findings=(),
            total_penalty=min(35, count * 7),
            critical=False,
            highest_severity=None,
        )

    roi_points = int(round(max(0.0, min(60.0, roi * 1.2))))
    margin_points = int(round(max(0.0, min(20.0, margin * 0.8))))
    confidence_points = int(round(max(0.0, min(20.0, confidence * 20.0))))
    base_score = min(100, roi_points + margin_points + confidence_points)
    score = int(round(max(0.0, min(100.0, base_score - assessment.total_penalty))))

    risk_level = assessment.highest_severity.value if assessment.highest_severity else "NONE"

    if assessment.critical or profit <= 0 or score < 40:
        recommendation = "PASS"
    elif score < 60:
        recommendation = "HIGH_RISK"
    elif score < 75:
        recommendation = "CONSIDER"
    elif score < 90:
        recommendation = "STRONG_BUY"
    else:
        recommendation = "EXCEPTIONAL_DEAL"

    return DealMetrics(
        purchase_price=round(purchase_price, 2),
        expected_resale_price=round(expected_resale_price, 2),
        extra_costs=round(extra_costs, 2),
        selling_fees=round(selling_fees, 2),
        expected_profit=round(profit, 2),
        roi=round(roi, 2),
        margin=round(margin, 2),
        flip_score=score,
        recommendation=recommendation,
        risk_penalty=assessment.total_penalty,
        risk_level=risk_level,
        critical_risk=assessment.critical,
        score_roi_points=roi_points,
        score_margin_points=margin_points,
        score_confidence_points=confidence_points,
        score_risk_points=-assessment.total_penalty,
        base_deal_score=base_score,
        decision_reason=_decision_reason(
            recommendation=recommendation,
            profit=profit,
            roi=roi,
            risk_level=risk_level,
            critical=assessment.critical,
        ),
    )
