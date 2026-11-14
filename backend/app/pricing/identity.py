import re

from app.ai.schemas import ListingAnalysis
from app.pricing.schemas import MarketComparable

_ACCESSORY_WORDS = {
    "case", "cover", "protector", "charger", "cable", "box", "screen",
    "strap", "skin", "wallet", "mount",
}
_STOP_WORDS = {"apple", "phone", "smartphone", "used", "new", "unlocked"}

# Words that name a different product tier. "RTX 3060" and "RTX 3060 Ti", or
# "iPhone 16" and "iPhone 16 Pro", sell at different prices, so these must
# match exactly in both directions.
_TIER_WORDS = {
    "pro", "max", "plus", "mini", "ultra", "ti", "super", "xt", "xtx",
    "lite", "se", "air",
}

_CAPACITY = re.compile(r"\b(\d+)\s*(gb|tb|g)\b")
_CAPACITY_TOKEN = re.compile(r"^(\d+)(gb|tb)$")


def _tokens(value: str) -> set[str]:
    # "12 GB", "12G" and "12GB" are the same thing in listing titles.
    text = _CAPACITY.sub(
        lambda match: f"{match.group(1)}{'tb' if match.group(2) == 'tb' else 'gb'}",
        value.lower(),
    )
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text)
        if len(token) > 1 and token not in _STOP_WORDS
    }


def _capacities(tokens: set[str]) -> tuple[set[str], set[str]]:
    """Split capacity tokens into memory-sized (<64GB) and storage-sized."""
    small: set[str] = set()
    large: set[str] = set()
    for token in tokens:
        match = _CAPACITY_TOKEN.match(token)
        if not match:
            continue
        size = int(match.group(1)) * (1024 if match.group(2) == "tb" else 1)
        (large if size >= 64 else small).add(token)
    return small, large


def _capacity_conflict(target: set[str], title: set[str]) -> bool:
    for wanted, offered in zip(_capacities(target), _capacities(title)):
        if wanted and offered and not wanted & offered:
            return True
    return False


def score_identity(listing: ListingAnalysis, comparable: MarketComparable) -> float:
    """How likely the comparable is the same product, from 0 to 1.

    Model numbers and capacities ("3060", "12gb", "256gb") decide most of the
    score. Descriptive words ("GeForce", "Graphics Card", "OC") only add a
    little, because sellers who write short titles are still selling the same
    item, and leaving them out pushes the market price up.
    """
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

    key_tokens = {token for token in target_tokens if any(char.isdigit() for char in token)}
    word_tokens = target_tokens - key_tokens

    word_overlap = len(word_tokens & title_tokens) / len(word_tokens) if word_tokens else 1.0
    if key_tokens:
        key_overlap = len(key_tokens & title_tokens) / len(key_tokens)
        score = key_overlap * 0.7 + word_overlap * 0.3
    else:
        score = word_overlap

    different_tier = (target_tokens & _TIER_WORDS) != (title_tokens & _TIER_WORDS)
    if different_tier or _capacity_conflict(target_tokens, title_tokens):
        score = min(score, 0.3)

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
