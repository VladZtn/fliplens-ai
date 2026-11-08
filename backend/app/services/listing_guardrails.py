from __future__ import annotations

from datetime import date
import re

from app.ai.schemas import ListingAnalysis


_UNSUPPORTED_MODEL_PATTERNS = (
    "non-existent",
    "nonexistent",
    "does not exist",
    "not been released",
    "unreleased model",
    "non existent",
)

_FUTURE_DATE_PATTERNS = (
    "future date",
    "future dates",
    "impossible date",
    "impossible dates",
)

_COUNTERFEIT_PATTERNS = (
    "counterfeit",
    "fake device",
    "clone device",
)

_VISIBLE_IDENTITY_PATTERNS = (
    "camera layout",
    "camera module",
    "hardware design",
    "box design",
    "logo",
    "label",
    "serial",
    "imei",
    "physical design",
    "visual",
)

_VISUAL_IDENTITY_FLAG_PATTERNS = (
    "unusual_hardware_design",
    "unusual_camera_design",
    "camera_layout_mismatch",
    "camera_module_mismatch",
    "suspicious_hardware_design",
    "suspicious_design",
    "hardware_design_inconsistent",
    "visual_design_inconsistency",
    "non_standard_hardware_design",
)


def _is_visual_identity_flag(value: str) -> bool:
    return any(pattern in value for pattern in _VISUAL_IDENTITY_FLAG_PATTERNS)


def _contains_any(value: str, patterns: tuple[str, ...]) -> bool:
    lowered = value.lower()
    return any(pattern in lowered for pattern in patterns)


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def apply_listing_guardrails(
    listing: ListingAnalysis,
    *,
    today: date | None = None,
) -> ListingAnalysis:
    """Remove unsupported time-sensitive claims and soften authenticity conclusions.

    Gemini is useful for extracting visible details, but its internal product-release
    knowledge can be stale. This post-processor makes those claims non-authoritative.
    """

    current_date = today or date.today()
    cleaned_issues: list[str] = []
    normalized_flags: list[str] = []
    identity_uncertain = False
    date_uncertain = False
    visible_identity_evidence = False

    all_issue_text = " ".join(listing.detected_issues)
    visible_identity_evidence = _contains_any(
        all_issue_text,
        _VISIBLE_IDENTITY_PATTERNS,
    )

    for issue in listing.detected_issues:
        text = _clean_text(issue)
        if not text:
            continue

        if _contains_any(text, _UNSUPPORTED_MODEL_PATTERNS):
            identity_uncertain = True
            continue

        if _contains_any(text, _FUTURE_DATE_PATTERNS):
            date_uncertain = True
            continue

        if _contains_any(text, _COUNTERFEIT_PATTERNS):
            identity_uncertain = True
            if visible_identity_evidence:
                cleaned_issues.append(
                    "Visible design details appear inconsistent with the claimed "
                    "product identity and should be verified against official images "
                    "and device identifiers."
                )
            continue

        cleaned_issues.append(text)

    for flag in listing.risk_flags:
        normalized = re.sub(r"[^a-z0-9]+", "_", flag.lower()).strip("_")
        if not normalized:
            continue

        if _contains_any(normalized.replace("_", " "), _UNSUPPORTED_MODEL_PATTERNS):
            identity_uncertain = True
            continue

        if "non_existent" in normalized or "unreleased" in normalized:
            identity_uncertain = True
            continue

        if "future_date" in normalized or "impossible_date" in normalized:
            date_uncertain = True
            continue

        if "counterfeit" in normalized or "clone" in normalized:
            identity_uncertain = True
            if visible_identity_evidence:
                normalized_flags.append("suspicious_device_identity")
            else:
                normalized_flags.append("product_identity_unverified")
            continue

        # Visual-design anomalies are evidence for an identity concern, not a
        # separate user-facing risk. Collapse them into one canonical flag.
        if _is_visual_identity_flag(normalized):
            identity_uncertain = True
            visible_identity_evidence = True
            normalized_flags.append("suspicious_device_identity")
            continue

        normalized_flags.append(normalized)

    if identity_uncertain:
        normalized_flags.append("product_identity_unverified")
        if not any("identity" in issue.lower() for issue in cleaned_issues):
            cleaned_issues.append(
                "The claimed model or authenticity cannot be verified from the "
                "provided evidence alone. Check the serial number, IMEI, settings "
                "screen, receipt, and official product imagery before purchase."
            )

    if date_uncertain:
        normalized_flags.append("date_details_require_verification")
        cleaned_issues.append(
            f"Displayed manufacturing or first-use dates require verification. "
            f"They must be interpreted relative to the current date "
            f"({current_date.isoformat()}) and checked against device records."
        )

    # Preserve order while deduplicating. If a concrete suspicious identity
    # signal exists, hide the weaker product_identity_unverified alias in the UI.
    deduped_flags = list(dict.fromkeys(normalized_flags))
    if "suspicious_device_identity" in deduped_flags:
        deduped_flags = [
            flag for flag in deduped_flags
            if flag != "product_identity_unverified"
        ]
    deduped_issues = list(dict.fromkeys(cleaned_issues))

    confidence = listing.confidence
    if identity_uncertain or date_uncertain:
        confidence = min(confidence, 0.75)

    if deduped_issues:
        summary = (
            f"{listing.product_name}: "
            + " ".join(deduped_issues[:3])
        )
    else:
        summary = _clean_text(listing.summary)
        if _contains_any(summary, _UNSUPPORTED_MODEL_PATTERNS + _FUTURE_DATE_PATTERNS):
            summary = (
                f"{listing.product_name}: the listing was parsed, but product "
                "identity and time-sensitive claims require independent verification."
            )

    return listing.model_copy(
        update={
            "detected_issues": deduped_issues,
            "risk_flags": deduped_flags,
            "confidence": confidence,
            "summary": summary,
        }
    )
