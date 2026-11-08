import re

from app.ai.schemas import ListingAnalysis

_STORAGE = re.compile(r"\b(\d{2,4})\s*(gb|tb)\b", re.IGNORECASE)


def storage_variant(listing: ListingAnalysis) -> str | None:
    """Return a normalised storage token such as '256GB' when one is stated.

    Values under 64GB are ignored so RAM sizes ("8GB 256GB") are not mistaken
    for storage.
    """
    for value in (listing.variant, listing.model, listing.product_name):
        candidates = []
        for number, unit in _STORAGE.findall(value or ""):
            size = int(number) * (1024 if unit.lower() == "tb" else 1)
            if size >= 64:
                candidates.append((size, f"{number}{unit.upper()}"))
        if candidates:
            return max(candidates)[1]
    return None


def _base_name(listing: ListingAnalysis) -> str:
    """Brand + model, falling back to the product name when the model is unknown.

    Gemini leaves ``model`` empty when it cannot verify it. Searching eBay for
    the brand alone ("Apple") returns unrelated items, so the advertised
    product name is used instead.
    """
    name = (listing.model or "").strip() or (listing.product_name or "").strip()
    name = re.sub(r"\(.*?\)", " ", name)          # drop "(Desert Titanium)"
    name = re.split(r"\s[-–|]\s", name)[0]         # drop " - extra seller text"
    name = re.sub(r"\s+", " ", name).strip()
    if not name:
        return ""

    brand = (listing.brand or "").strip()
    if brand and not name.lower().startswith(brand.lower()):
        return f"{brand} {name}"
    return name


def build_pricing_query(listing: ListingAnalysis, *, include_storage: bool = True) -> str:
    value = _base_name(listing)
    if not value:
        return ""

    storage = storage_variant(listing)
    compact = value.lower().replace(" ", "")
    if include_storage and storage and storage.lower() not in compact:
        value = f"{value} {storage}"
    elif not include_storage and storage:
        value = re.sub(rf"\b{re.escape(storage[:-2])}\s*{storage[-2:]}\b", " ", value, flags=re.IGNORECASE)

    return re.sub(r"\s+", " ", value).strip()


def pricing_queries(listing: ListingAnalysis) -> list[str]:
    """Most specific query first, then a broader one without the storage size."""
    queries = [build_pricing_query(listing), build_pricing_query(listing, include_storage=False)]
    return [query for query in dict.fromkeys(queries) if query]


def wants_new_condition(listing: ListingAnalysis) -> bool:
    """True only when the listing is clearly new/sealed (not 'like new')."""
    text = (listing.condition or "").lower()
    if not text or "like new" in text or "as new" in text:
        return False
    return any(word in text for word in ("brand new", "sealed", "unopened", "bnib")) or text.strip() == "new"
