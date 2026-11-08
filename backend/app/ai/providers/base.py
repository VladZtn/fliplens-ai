from abc import ABC, abstractmethod

from app.ai.schemas import ListingAnalysis


class AIProvider(ABC):
    @abstractmethod
    async def analyze_listing(
        self,
        *,
        title: str,
        description: str | None = None,
        image_urls: list[str] | None = None,
        images: list[tuple[bytes, str]] | None = None,
    ) -> ListingAnalysis:
        """Extract structured product information from listing text and images.

        ``images`` contains ``(raw_bytes, mime_type)`` tuples.
        """
