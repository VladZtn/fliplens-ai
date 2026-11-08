from typing import Annotated

import httpx

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.ai import create_ai_provider
from app.ai.providers.gemini import GeminiProviderError
from app.ai.schemas import ListingAIRequest, ListingAnalysis

router = APIRouter(prefix="/ai", tags=["AI"])

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_BYTES = 8 * 1024 * 1024


@router.post("/analyze-listing", response_model=ListingAnalysis)
async def analyze_listing(request: ListingAIRequest) -> ListingAnalysis:
    """Analyze listing text and optional publicly accessible image URLs."""
    return await _run_analysis(
        title=request.title,
        description=request.description,
        image_urls=request.image_urls,
    )


@router.post("/analyze-image", response_model=ListingAnalysis)
async def analyze_image(
    title: Annotated[str, Form(min_length=3, max_length=300)],
    image: Annotated[UploadFile, File(description="JPEG, PNG, or WebP image")],
    description: Annotated[str | None, Form(max_length=5000)] = None,
) -> ListingAnalysis:
    """Upload one marketplace screenshot or product photo directly for analysis."""
    content_type = (image.content_type or "").lower()
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported image type for {image.filename or 'upload'}: "
                f"{content_type or 'unknown'}"
            ),
        )

    raw_bytes = await image.read(MAX_IMAGE_BYTES + 1)
    await image.close()
    if len(raw_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image must be no larger than {MAX_IMAGE_BYTES // 1024 // 1024} MB",
        )
    if not raw_bytes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Uploaded image is empty",
        )

    prepared_images = [(raw_bytes, content_type)]

    return await _run_analysis(
        title=title,
        description=description,
        images=prepared_images,
    )


async def _run_analysis(
    *,
    title: str,
    description: str | None = None,
    image_urls: list[str] | None = None,
    images: list[tuple[bytes, str]] | None = None,
) -> ListingAnalysis:
    try:
        provider = create_ai_provider()
        return await provider.analyze_listing(
            title=title,
            description=description,
            image_urls=image_urls,
            images=images,
        )
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except GeminiProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except HTTPException:
        raise
    except httpx.HTTPError as exc:  # pragma: no cover - provider/network boundary
        raise HTTPException(status_code=502, detail="Unable to download listing image") from exc
    except Exception as exc:  # pragma: no cover - defensive API boundary
        raise HTTPException(status_code=503, detail="AI analysis is temporarily unavailable") from exc
