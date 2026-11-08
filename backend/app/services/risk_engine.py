from dataclasses import dataclass
from enum import StrEnum
import re


class RiskSeverity(StrEnum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class RiskFinding:
    flag: str
    severity: RiskSeverity
    penalty: int
    matched_rule: str


@dataclass(frozen=True)
class RiskAssessment:
    findings: tuple[RiskFinding, ...]
    total_penalty: int
    critical: bool
    highest_severity: RiskSeverity | None


# Informational flags are useful to show to the user,
# but they must not affect FlipScore or risk level.
_INFORMATIONAL_FLAGS = {
    "product_identity_unverified",
    "identity_not_verified",
    "exact_model_not_verified",
}


# More specific and critical rules are evaluated first.
_RULES: tuple[tuple[str, RiskSeverity, int, tuple[str, ...]], ...] = (
    (
        "reported_stolen",
        RiskSeverity.CRITICAL,
        100,
        ("reported_stolen", "stolen_device", "stolen_item"),
    ),
    (
        "imei_blacklisted",
        RiskSeverity.CRITICAL,
        100,
        ("imei_blacklisted", "blacklisted_imei", "blacklisted"),
    ),
    (
        "activation_lock",
        RiskSeverity.CRITICAL,
        100,
        ("activation_lock", "icloud_lock", "google_lock", "account_lock"),
    ),
    (
        "confirmed_counterfeit",
        RiskSeverity.CRITICAL,
        100,
        ("confirmed_counterfeit", "counterfeit_confirmed"),
    ),
    (
        "model_mismatch",
        RiskSeverity.HIGH,
        25,
        (
            "model_mismatch",
            "model_identity_mismatch",
            "older_generation_appearance",
        ),
    ),
    (
        "serial_mismatch",
        RiskSeverity.HIGH,
        30,
        ("serial_mismatch", "imei_mismatch", "identifier_mismatch"),
    ),
    (
        "suspicious_device_identity",
        RiskSeverity.HIGH,
        28,
        (
            "suspicious_device_identity",
            "counterfeit_device",
            "suspicious_design",
        ),
    ),
    (
        "high_fraud_risk",
        RiskSeverity.HIGH,
        30,
        ("high_fraud_risk", "fraud_risk", "likely_scam", "scam_indicator"),
    ),
    (
        "suspicious_claim",
        RiskSeverity.MEDIUM,
        10,
        (
            "suspicious_claim",
            "suspicious_upgrade_claim",
            "inconsistent_details",
            "misrepresentation",
        ),
    ),
    (
        "unclear_model",
        RiskSeverity.MEDIUM,
        10,
        ("unclear_model", "unverified_model", "unclear_identity"),
    ),
    (
        "poor_condition",
        RiskSeverity.MEDIUM,
        8,
        ("poor_condition", "heavy_damage", "screen_damage", "water_damage"),
    ),
    (
        "missing_accessories",
        RiskSeverity.LOW,
        3,
        (
            "missing_accessories",
            "missing_box_and_accessories",
            "missing_charger",
        ),
    ),
    (
        "missing_box",
        RiskSeverity.LOW,
        2,
        ("missing_box",),
    ),
    (
        "collection_only",
        RiskSeverity.LOW,
        2,
        ("collection_only", "cash_only"),
    ),
)


def _normalize(flag: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "_", flag.strip().lower())
    return re.sub(r"_+", "_", value).strip("_")


def assess_risks(risk_flags: list[str]) -> RiskAssessment:
    findings: list[RiskFinding] = []
    seen_rules: set[str] = set()

    for original_flag in risk_flags:
        normalized = _normalize(original_flag)

        if not normalized:
            continue

        if normalized in _INFORMATIONAL_FLAGS:
            findings.append(
                RiskFinding(
                    flag=original_flag,
                    severity=RiskSeverity.INFO,
                    penalty=0,
                    matched_rule="identity_not_verified",
                )
            )
            continue

        matched = False

        for rule_name, severity, penalty, tokens in _RULES:
            if any(token in normalized for token in tokens):
                if rule_name not in seen_rules:
                    findings.append(
                        RiskFinding(
                            flag=original_flag,
                            severity=severity,
                            penalty=penalty,
                            matched_rule=rule_name,
                        )
                    )
                    seen_rules.add(rule_name)

                matched = True
                break

        if not matched:
            findings.append(
                RiskFinding(
                    flag=original_flag,
                    severity=RiskSeverity.LOW,
                    penalty=2,
                    matched_rule="unclassified_risk",
                )
            )

    severity_rank = {
        RiskSeverity.INFO: 0,
        RiskSeverity.LOW: 1,
        RiskSeverity.MEDIUM: 2,
        RiskSeverity.HIGH: 3,
        RiskSeverity.CRITICAL: 4,
    }

    actionable_findings = [
        finding
        for finding in findings
        if finding.severity is not RiskSeverity.INFO
    ]

    highest = max(
        (finding.severity for finding in actionable_findings),
        key=lambda severity: severity_rank[severity],
        default=None,
    )

    critical = any(
        finding.severity is RiskSeverity.CRITICAL
        for finding in actionable_findings
    )

    total_penalty = (
        100
        if critical
        else min(
            70,
            sum(finding.penalty for finding in actionable_findings),
        )
    )

    return RiskAssessment(
        findings=tuple(findings),
        total_penalty=total_penalty,
        critical=critical,
        highest_severity=highest,
    )