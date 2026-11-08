import asyncio
import json
import random
from datetime import date
from typing import Any
from google import genai
from google.genai import errors, types
from pydantic import ValidationError

from app.ai.providers.base import AIProvider
from app.ai.schemas import ListingAnalysis


class GeminiProviderError(RuntimeError):
    """A user-safe error raised when Gemini analysis cannot be completed."""


class GeminiAIProvider(AIProvider):
    RETRYABLE_CODES = {429, 500, 502, 503, 504}

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: float = 120.0,
        fallback_models: list[str] | None = None,
        max_attempts_per_model: int = 3,
    ) -> None:
        if not api_key.strip():
            raise ValueError("GEMINI_API_KEY is required when AI_PROVIDER=gemini")
        if not model.strip():
            raise ValueError("GEMINI_MODEL must not be empty")

        self.model = model.strip()
        self.timeout_seconds = float(timeout_seconds)
        self.max_attempts_per_model = max(1, int(max_attempts_per_model))
        self.fallback_models = [
            item.strip()
            for item in (fallback_models or [])
            if item.strip() and item.strip() != self.model
        ]
        self.client = genai.Client(
            api_key=api_key.strip(),
            http_options=types.HttpOptions(timeout=int(self.timeout_seconds * 1000)),
        )

    async def analyze_listing(
        self,
        *,
        title: str,
        description: str | None = None,
        image_urls: list[str] | None = None,
        images: list[tuple[bytes, str]] | None = None,
    ) -> ListingAnalysis:
        if image_urls:
            raise GeminiProviderError(
                "Remote image URLs are not enabled in the Gemini SDK provider. "
                "Upload the image directly instead."
            )

        contents: list[Any] = [self._build_prompt(title, description)]
        for raw_bytes, mime_type in images or []:
            if raw_bytes:
                contents.append(
                    types.Part.from_bytes(
                        data=raw_bytes,
                        mime_type=self._normalize_mime_type(mime_type),
                    )
                )

        models = [self.model, *self.fallback_models]
        failures: list[str] = []

        for model in models:
            try:
                return await self._analyze_with_model(model=model, contents=contents)
            except GeminiProviderError as exc:
                failures.append(f"{model}: {exc}")

        raise GeminiProviderError(
            "All configured Gemini models failed. " + " | ".join(failures)
        )

    async def _analyze_with_model(
        self,
        *,
        model: str,
        contents: list[Any],
    ) -> ListingAnalysis:
        last_error: Exception | None = None

        for attempt in range(1, self.max_attempts_per_model + 1):
            try:
                response = await self.client.aio.models.generate_content(
                    model=model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        response_mime_type="application/json",
                        response_json_schema=ListingAnalysis.model_json_schema(),
                    ),
                )
                return self._parse_response(response)

            except errors.APIError as exc:
                last_error = exc
                code = int(getattr(exc, "code", 0) or 0)
                if code not in self.RETRYABLE_CODES:
                    raise GeminiProviderError(
                        f"Gemini API error {code or 'unknown'}: {self._clean_error(exc)}"
                    ) from exc

            except (TimeoutError, ConnectionError) as exc:
                last_error = exc

            except Exception as exc:  # SDK transport exceptions vary by version.
                last_error = exc
                name = type(exc).__name__
                if name not in {
                    "ReadTimeout",
                    "ConnectTimeout",
                    "ConnectError",
                    "RemoteProtocolError",
                }:
                    raise GeminiProviderError(
                        f"Unexpected Gemini SDK error ({name}): {self._clean_error(exc)}"
                    ) from exc

            if attempt < self.max_attempts_per_model:
                await asyncio.sleep((2 ** (attempt - 1)) + random.uniform(0.0, 0.4))

        name = type(last_error).__name__ if last_error else "UnknownError"
        raise GeminiProviderError(
            f"Model remained unavailable after {self.max_attempts_per_model} attempts "
            f"({name}): {self._clean_error(last_error)}"
        )

    @staticmethod
    def _parse_response(response: Any) -> ListingAnalysis:
        parsed = getattr(response, "parsed", None)
        if isinstance(parsed, ListingAnalysis):
            return parsed
        if isinstance(parsed, dict):
            return ListingAnalysis.model_validate(parsed)

        raw_text = getattr(response, "text", None)
        if not raw_text:
            raise GeminiProviderError("Gemini returned an empty response")

        try:
            payload = json.loads(raw_text)
            return ListingAnalysis.model_validate(payload)
        except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
            raise GeminiProviderError(
                f"Gemini returned invalid structured output: {str(exc)[:300]}"
            ) from exc

    @staticmethod
    def _clean_error(exc: Exception | None) -> str:
        if exc is None:
            return "no details"
        message = str(exc).strip()
        return message[:400] if message else type(exc).__name__

    @staticmethod
    def _normalize_mime_type(value: str) -> str:
        return value.split(";", maxsplit=1)[0].strip().lower() or "image/jpeg"


    @staticmethod
    def _build_prompt(title: str, description: str | None) -> str:
        today = date.today().isoformat()

        return f"""
    You are FlipLens, a conservative analyst of second-hand marketplace listings.

    Inspect the title, description, and attached image. Extract only facts that are visible or explicitly stated.

    GENERAL RULES

    - Never invent model details, condition, accessories, defects, price, warranty, or missing information.
    - Confidence must be between 0 and 1 and represents confidence in extracted facts, NOT confidence that the listing is fraudulent.
    - Do not estimate resale value.
    - Put storage capacity (e.g. 256GB) in "variant" only when it is explicitly stated or readable; otherwise leave it null.
    - The current date is {today}.
    - A date is only considered "future" if it is later than the current date.

    PRODUCT AVAILABILITY

    - Never claim that a product model does not exist, is unreleased, or has not been launched based only on internal model knowledge.
    - Treat product availability as unverified unless confirmed by an authoritative current source.

    COUNTERFEIT RULES

    - Never call a product counterfeit solely because of the title, release assumption, colour, or general appearance.
    - Only describe concrete visible inconsistencies.
    - Prefer cautious flags such as:
    - product_identity_unverified
    - suspicious_device_identity

    - Do not emit duplicate flags such as:
    - unusual_hardware_design
    - suspicious_design
    - camera_layout_mismatch

    when suspicious_device_identity already represents the same concern.

    Put detailed hardware observations inside detected_issues or summary instead.

    CRITICAL PRODUCT IDENTITY RULES

    Never identify an exact smartphone generation solely from visual appearance.

    Modern smartphones, especially iPhones, often share nearly identical:

    - camera layout
    - camera proportions
    - camera size
    - colours
    - frame shape
    - button placement
    - display appearance

    These characteristics alone are NOT sufficient evidence that the device is a different generation.

    Only report model_mismatch when there is explicit readable evidence such as:

    - readable model number
    - readable Settings → General → About screen
    - readable retail box label
    - readable IMEI label
    - readable serial number
    - a unique hardware feature that definitively excludes the advertised model

    If explicit evidence does not exist:

    - Never guess another iPhone generation.
    - Never compare the phone to another model.
    - Never write:
    "This resembles an iPhone 13 Pro rather than the advertised iPhone 16 Pro Max."
    - Never emit model_mismatch.
    - Use product_identity_unverified only when identity genuinely cannot be verified.
    - State:
    "The exact model cannot be verified from the supplied image."

    Visual similarity alone is NEVER evidence of model mismatch.

    The inability to visually verify the exact model must NOT:

    - increase risk level
    - reduce confidence in other extracted facts
    - reduce FlipScore
    - change the recommendation
    - imply fraud
    - imply counterfeiting

    Always prefer uncertainty over an incorrect conclusion.

    TITLE:
    {title.strip()}

    DESCRIPTION:
    {(description or "Not provided").strip()}
    """.strip()
