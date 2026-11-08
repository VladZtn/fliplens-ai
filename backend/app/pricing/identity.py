import re

from app.ai.schemas import ListingAnalysis
from app.pricing.schemas import MarketComparable

_ACCESSORY_WORDS = {
    "case", "cover", "protector", "charger", "cable", "box", "screen",
    "strap", "skin", "wallet", "mount",
}
_STOP_WORDS = {"apple", "phone", "smartphone", "used", "new", "unlocked"}


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) > 1 and token not in _STOP_WORDS
    }


def _storage_tokens(value: str) -> set[str]:
    return set(re.findall(r"\b(?:64|128|256|512|1024)\s*(?:gb|tb)?\b", value.lower()))


def score_identity(listing: ListingAnalysis, comparable: MarketComparable) -> float:
    target = " ".join(filter(None, [listing.brand, listing.product_name, listing.model]))
    target_tokens = _tokens(target)
    title_tokens = _tokens(comparable.title)

    if not target_tokens:
        return 0.0

    accessory_hits = len(title_tokens & _ACCESSORY_WORDS)
    if accessory_hits:
        accessory_ratio = accessory_hits / max(1, len(title_tokens))
        if accessory_ratio >= 0.2 or any(
            phrase in comparable.title.lower()
            for phrase in ("case cover", "screen protector", "box only", "charger only")
        ):
            return 0.05

    overlap = len(target_tokens & title_tokens) / len(target_tokens)
    score = overlap

    target_storage = _storage_tokens(target)
    title_storage = _storage_tokens(comparable.title)
    if target_storage:
        if target_storage & title_storage:
            score += 0.12
        elif title_storage:
            score -= 0.18

    model_tokens = _tokens(listing.model or "")
    if model_tokens:
        model_overlap = len(model_tokens & title_tokens) / len(model_tokens)
        score = score * 0.65 + model_overlap * 0.35

    if any(word in comparable.title.lower() for word in ("parts", "broken", "replica", "clone")):
        score -= 0.5

    return round(max(0.0, min(1.0, score)), 3)


def apply_identity_scores(
    listing: ListingAnalysis,
    comparables: list[MarketComparable],
    threshold: float = 0.72,
) -> list[MarketComparable]:
    matched: list[MarketComparable] = []
    for item in comparables:
        score = score_identity(listing, item)
        updated = item.model_copy(update={"identity_score": score})
        if score >= threshold:
            matched.append(updated)
    return matched
