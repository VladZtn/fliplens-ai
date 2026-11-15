import logging
import time
from typing import Annotated

from fastapi import APIRouter, File, Form, Header, HTTPException, Request, Response, UploadFile, status

from app.ai import create_ai_provider
from app.ai.providers.gemini import GeminiProviderError
from app.api.routes.ai import ALLOWED_IMAGE_TYPES, MAX_IMAGE_BYTES
from app.config import get_settings
from app.pricing import price_listing
from app.pricing.ebay import EbayPricingError
from app.schemas.deal import DealAnalysis, FeeBreakdown, UsageInfo
from app.services.billing import has_active_pass
from app.services.fees import SellPlatform, estimate_selling_fees, max_buy_price
from app.services.flipscore import calculate_flipscore
from app.services.listing_guardrails import apply_listing_guardrails
from app.services.next_action import build_next_action
from app.services.usage import UsageStatus, client_id_from_request, limiter

logger = logging.getLogger("fliplens.deals")

router = APIRouter(prefix="/api/v1/deals", tags=["Deals"])

AI_UNAVAILABLE = "AI analysis is temporarily unavailable. Please try again in a minute."
PRICING_UNAVAILABLE = (
    "Live market pricing is temporarily unavailable. "
    "Add your resale price to check this deal now."
)
TARGET_ROI = 0.20


def _usage_info(limit: int, remaining: int) -> UsageInfo:
    return UsageInfo(limit=limit, remaining=remaining, unlimited=limit <= 0)


@router.get("/usage", response_model=UsageInfo)
async def get_usage(
    request: Request,
    x_fliplens_pass: Annotated[str | None, Header()] = None,
) -> UsageInfo:
    settings = get_settings()
    if await has_active_pass(x_fliplens_pass):
        return _usage_info(0, 0)
    client_id = client_id_from_request(request, settings.trusted_proxy_hops)
    current = limiter.status(client_id, settings.free_daily_limit)
    return _usage_info(current.limit, current.remaining)


@router.post("/analyze-image", response_model=DealAnalysis)
async def analyze_deal_image(
    request: Request,
    response: Response,
    title: Annotated[str, Form(min_length=3, max_length=300)],
    purchase_price: Annotated[float, Form(gt=0)],
    expected_resale_price: Annotated[float | None, Form(gt=0)] = None,
    description: Annotated[str | None, Form(max_length=5000)] = None,
    extra_costs: Annotated[float, Form(ge=0)] = 0.0,
    sell_platform: Annotated[SellPlatform, Form()] = SellPlatform.EBAY_BUSINESS,
    x_fliplens_pass: Annotated[str | None, Header()] = None,
    image: Annotated[
        UploadFile | None, File(description="Optional JPEG, PNG, or WebP image")
    ] = None,
) -> DealAnalysis:
    settings = get_settings()

    # The photo is optional: many listings shared in forums are text only,
    # and the title plus description are enough to price them.
    images: list[tuple[bytes, str]] = []
    if image is not None and image.filename:
        content_type = (image.content_type or "").lower()
        if content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported image type: {content_type or 'unknown'}",
            )

        raw_bytes = await image.read(MAX_IMAGE_BYTES + 1)
        await image.close()
        if len(raw_bytes) > MAX_IMAGE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Image must be no larger than {MAX_IMAGE_BYTES // 1024 // 1024} MB",
            )
        if not raw_bytes:
            raise HTTPException(status_code=422, detail="Uploaded image is empty")
        images.append((raw_bytes, content_type))

    # Subscribers skip the allowance; everyone else reserves one free analysis
    # before paid APIs are called.
    client_id = client_id_from_request(request, settings.trusted_proxy_hops)
    subscribed = await has_active_pass(x_fliplens_pass)
    usage = (
        UsageStatus(limit=0, used=0)
        if subscribed
        else limiter.try_consume(client_id, settings.free_daily_limit)
    )

    def refund() -> None:
        if not subscribed:
            limiter.refund(client_id)

    if usage is None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"You have used all {settings.free_daily_limit} free analyses for today. "
                "Your allowance resets at midnight UTC, or subscribe for unlimited checks."
            ),
        )

    started = time.perf_counter()
    try:
        listing = await create_ai_provider().analyze_listing(
            title=title,
            description=description,
            images=images,
        )
    except ValueError as exc:
        refund()
        logger.error("AI provider misconfigured: %s", exc)
        raise HTTPException(status_code=500, detail="The analysis service is not configured correctly.") from exc
    except GeminiProviderError as exc:
        refund()
        logger.warning("Gemini analysis failed: %s", exc)
        raise HTTPException(status_code=502, detail=AI_UNAVAILABLE) from exc
    listing = apply_listing_guardrails(listing)
    ai_ms = (time.perf_counter() - started) * 1000

    pricing_warning: str | None = None
    pricing_started = time.perf_counter()
    try:
        market_pricing = await price_listing(listing)
    except (EbayPricingError, ValueError) as exc:
        logger.warning("Market pricing failed: %s", exc)
        market_pricing = None
        if expected_resale_price is None:
            refund()
            raise HTTPException(status_code=502, detail=PRICING_UNAVAILABLE) from exc
        pricing_warning = "Live market pricing was unavailable, so your own resale estimate was used."

    pricing_ms = (time.perf_counter() - pricing_started) * 1000
    logger.info("Analysis timing: ai=%.0fms pricing=%.0fms", ai_ms, pricing_ms)

    resale_price = (
        market_pricing.estimated_market_price
        if market_pricing is not None
        else expected_resale_price
    )
    if resale_price is None:
        refund()
        raise HTTPException(
            status_code=422,
            detail=(
                "Not enough matching eBay listings were found to price this item. "
                "Add your resale price to continue."
            ),
        )

    category_text = " ".join(
        filter(None, [listing.category, listing.product_name, listing.model, title])
    )
    fees = estimate_selling_fees(
        platform=sell_platform.value,
        sale_price=resale_price,
        category_text=category_text,
    )

    if market_pricing is not None:
        market_pricing.safe_buy_price = max_buy_price(
            resale_price=market_pricing.estimated_market_price,
            selling_fees=fees.total,
            extra_costs=extra_costs,
            target_roi=TARGET_ROI,
        )

    metrics = calculate_flipscore(
        purchase_price=purchase_price,
        expected_resale_price=resale_price,
        extra_costs=extra_costs,
        selling_fees=fees.total,
        confidence=listing.confidence,
        risk_flags=listing.risk_flags,
    )

    pricing_source = market_pricing.source if market_pricing else "user_estimate"
    if market_pricing:
        disclaimer = (
            f"Market price is the median asking price of {market_pricing.comparable_count} "
            f"filtered {market_pricing.condition_filter or 'used'} eBay listings. Items often sell "
            "below their asking price, so check recently sold listings before buying."
        )
    else:
        disclaimer = (
            "Expected resale price is supplied by you and is not verified against live market data."
        )

    next_action = build_next_action(
        recommendation=metrics.recommendation,
        purchase_price=purchase_price,
        safe_buy_price=market_pricing.safe_buy_price if market_pricing else None,
        risk_level=metrics.risk_level,
        critical_risk=metrics.critical_risk,
        risk_flags=listing.risk_flags,
    )

    response.headers["X-FlipLens-Remaining"] = str(usage.remaining)
    # Visible in the browser's network tab; shows where the wait comes from.
    response.headers["Server-Timing"] = f"ai;dur={ai_ms:.0f}, pricing;dur={pricing_ms:.0f}"

    return DealAnalysis(
        listing=listing,
        market_pricing=market_pricing,
        next_action=next_action.__dict__,
        pricing_source=pricing_source,
        pricing_warning=pricing_warning,
        disclaimer=disclaimer,
        fees=FeeBreakdown(**fees.__dict__),
        usage=_usage_info(usage.limit, usage.remaining),
        **metrics.__dict__,
    )
