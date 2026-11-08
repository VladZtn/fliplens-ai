from datetime import date

from app.ai.schemas import ListingAnalysis
from app.services.listing_guardrails import apply_listing_guardrails


def make_listing(**updates):
    data = {
        "product_name": "iPhone 17 Pro Max",
        "brand": "Apple",
        "model": "17 Pro Max",
        "category": "Phones",
        "condition": "Used",
        "currency": "GBP",
        "asking_price": 995,
        "included_items": [],
        "detected_issues": [],
        "risk_flags": [],
        "confidence": 1.0,
        "summary": "Listing parsed.",
    }
    data.update(updates)
    return ListingAnalysis(**data)


def test_removes_nonexistent_model_claim_and_caps_confidence():
    result = apply_listing_guardrails(
        make_listing(
            detected_issues=["The iPhone 17 Pro Max is a non-existent product model"],
            risk_flags=["Non-existent product model"],
            summary="This is a non-existent model.",
        ),
        today=date(2026, 7, 13),
    )

    assert "product_identity_unverified" in result.risk_flags
    assert all("non-existent" not in issue.lower() for issue in result.detected_issues)
    assert "non-existent" not in result.summary.lower()
    assert result.confidence == 0.75


def test_future_date_claim_is_replaced_with_verification_warning():
    result = apply_listing_guardrails(
        make_listing(
            detected_issues=["The screen displays impossible future dates"],
            risk_flags=["Impossible system dates"],
        ),
        today=date(2026, 7, 13),
    )

    assert "date_details_require_verification" in result.risk_flags
    assert any("2026-07-13" in issue for issue in result.detected_issues)
    assert result.confidence == 0.75


def test_counterfeit_claim_is_softened_to_visible_identity_risk():
    result = apply_listing_guardrails(
        make_listing(
            detected_issues=[
                "The camera layout and box design indicate a counterfeit clone device"
            ],
            risk_flags=["Counterfeit suspect"],
        )
    )

    assert "suspicious_device_identity" in result.risk_flags
    assert "product_identity_unverified" not in result.risk_flags
    assert all("counterfeit" not in issue.lower() for issue in result.detected_issues)


def test_visual_hardware_flags_collapse_into_single_identity_risk():
    listing = ListingAnalysis(
        product_name="Phone",
        brand="Apple",
        model="Pro Max",
        category="Phones",
        condition="Used",
        confidence=0.7,
        summary="Unusual camera module.",
        detected_issues=[
            "The camera module design is inconsistent with the claimed product."
        ],
        risk_flags=[
            "product_identity_unverified",
            "suspicious_device_identity",
            "unusual_hardware_design",
            "camera_layout_mismatch",
        ],
    )

    cleaned = apply_listing_guardrails(listing)

    assert cleaned.risk_flags == ["suspicious_device_identity"]
    assert "camera module" in cleaned.summary.lower()
