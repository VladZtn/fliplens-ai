import re

from app.ai.providers.base import AIProvider
from app.ai.schemas import ListingAnalysis


class MockAIProvider(AIProvider):
    async def analyze_listing(
        self,
        *,
        title: str,
        description: str | None = None,
        image_urls: list[str] | None = None,
        images: list[tuple[bytes, str]] | None = None,
    ) -> ListingAnalysis:
        text = f"{title} {description or ''}".lower()
        brand = "Apple" if any(x in text for x in ("macbook", "iphone", "ipad")) else None
        category = None
        if "macbook" in text or "laptop" in text:
            category = "Laptop"
        elif "iphone" in text or "phone" in text:
            category = "Phone"
        elif "playstation" in text or "ps5" in text:
            brand, category = "Sony", "Game Console"

        price_match = re.search(r"(?:£|\$|€)\s?(\d+(?:\.\d{1,2})?)", text)
        currency = None
        if "£" in text:
            currency = "GBP"
        elif "$" in text:
            currency = "USD"
        elif "€" in text:
            currency = "EUR"

        issues = []
        for phrase in ("cracked", "damaged", "faulty", "not working", "icloud locked"):
            if phrase in text:
                issues.append(phrase)

        return ListingAnalysis(
            product_name=title.strip(),
            brand=brand,
            model=None,
            category=category,
            condition="Used" if "used" in text else None,
            currency=currency,
            asking_price=float(price_match.group(1)) if price_match else None,
            included_items=[],
            detected_issues=issues,
            risk_flags=issues.copy(),
            confidence=0.55,
            summary=(
                "Mock analysis generated locally without an external AI API. "
                f"Received {len(images or []) + len(image_urls or [])} image(s)."
            ),
        )
