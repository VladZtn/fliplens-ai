from dataclasses import dataclass
import re


@dataclass(frozen=True)
class NextAction:
    code: str
    title: str
    message: str
    suggested_offer: float | None = None


NEUTRAL_IDENTITY_FLAGS = {
    "product_identity_unverified",
    "identity_not_verified",
    "exact_model_not_verified",
}

ACTIONABLE_IDENTITY_FLAGS = {
    "model_mismatch",
    "serial_mismatch",
    "imei_mismatch",
    "identifier_mismatch",
    "suspicious_device_identity",
    "confirmed_counterfeit",
    "counterfeit_device",
}


def _normalize_flag(flag: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "_", flag.strip().lower())
    return re.sub(r"_+", "_", value).strip("_")


def build_next_action(
    *,
    recommendation: str,
    purchase_price: float,
    safe_buy_price: float | None,
    risk_level: str,
    critical_risk: bool,
    risk_flags: list[str],
) -> NextAction:
    normalized_flags = {
        _normalize_flag(flag)
        for flag in risk_flags
        if flag.strip()
    }

    neutral_identity_present = bool(
        normalized_flags & NEUTRAL_IDENTITY_FLAGS
    )

    actionable_identity_present = bool(
        normalized_flags & ACTIONABLE_IDENTITY_FLAGS
    )

    upper_recommendation = recommendation.strip().upper()
    upper_risk_level = risk_level.strip().upper()

    if critical_risk:
        return NextAction(
            code="SKIP_LISTING",
            title="Skip this listing",
            message=(
                "A critical risk was detected. Do not send money or continue "
                "with the deal."
            ),
        )

    if actionable_identity_present:
        return NextAction(
            code="VERIFY_IDENTITY",
            title="Verify device identity",
            message=(
                "The listing contains a specific identity inconsistency. Ask for "
                "the Settings → General → About screen, IMEI or serial number, "
                "proof of purchase, and fresh close-up photos."
            ),
        )

    if upper_risk_level == "HIGH":
        return NextAction(
            code="REQUEST_DETAILS",
            title="Request more evidence",
            message=(
                "The listing contains material risk signals. Clarify the device "
                "condition, identifiers, included items, and collection terms "
                "before discussing price."
            ),
        )

    if safe_buy_price is not None and purchase_price > safe_buy_price:
        gap = round(purchase_price - safe_buy_price, 2)

        return NextAction(
            code="NEGOTIATE",
            title=f"Negotiate to £{safe_buy_price:,.0f} or below",
            message=(
                f"The asking price is £{gap:,.0f} above the current "
                "risk-adjusted safe offer."
            ),
            suggested_offer=round(safe_buy_price, 2),
        )

    if neutral_identity_present:
        return NextAction(
            code="VERIFY_DETAILS",
            title="Confirm details before buying",
            message=(
                "The exact model could not be confirmed from the supplied image. "
                "This is not treated as a risk signal, but you should check "
                "Settings → General → About, IMEI or serial number, battery health, "
                "and activation lock before purchase."
            ),
        )

    # Names produced by calculate_flipscore for scores of 75 and above.
    if upper_recommendation in {"BUY", "STRONG_BUY", "EXCEPTIONAL_DEAL"}:
        return NextAction(
            code="CONTACT_SELLER",
            title="Contact the seller",
            message=(
                "The price and risk profile are attractive. Verify the final "
                "details and move quickly."
            ),
            suggested_offer=round(purchase_price, 2),
        )

    if upper_recommendation in {"CONSIDER", "HIGH_RISK", "NEGOTIATE", "VERIFY"}:
        return NextAction(
            code="REQUEST_DETAILS",
            title="Request more evidence",
            message=(
                "Clarify condition, included items, identifiers, and collection "
                "terms before committing."
            ),
        )

    return NextAction(
        code="SKIP_LISTING",
        title="Skip this listing",
        message="The current risk-adjusted return is not strong enough.",
    )