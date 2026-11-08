from pydantic import BaseModel, Field


class ListingAnalysis(BaseModel):
    product_name: str = Field(description="Concise normalized product name")
    brand: str | None = None
    model: str | None = None
    variant: str | None = Field(
        default=None,
        description="Storage or size variant only when explicitly stated or readable, e.g. '256GB'",
    )
    category: str | None = None
    condition: str | None = None
    currency: str | None = None
    asking_price: float | None = None
    included_items: list[str] = Field(default_factory=list)
    detected_issues: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    summary: str


class ListingAIRequest(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    image_urls: list[str] = Field(default_factory=list, max_length=5)
