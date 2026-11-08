# FlipLens AI backend v1.0

FastAPI backend with direct image upload, pluggable AI providers, Gemini structured output, retries, model fallback, and FlipScore.

## Start locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs`.

## Enable Gemini

Edit `.env`:

```env
AI_PROVIDER=gemini
GEMINI_API_KEY=YOUR_NEW_KEY
GEMINI_MODEL=gemini-3.5-flash
GEMINI_FALLBACK_MODELS=gemini-3.1-flash-lite
GEMINI_MAX_ATTEMPTS=3
AI_TIMEOUT_SECONDS=120
```

The provider uses the official `google-genai` SDK. It retries temporary 429/5xx errors and switches to configured fallback models when the primary model remains unavailable.

## Test

```bash
python -m pytest -q
```

Never upload `.env` or an API key to GitHub.


## Risk Engine v1

Risk flags are weighted by severity instead of counted equally. Critical risks such as activation lock, stolen status, IMEI blacklist, or confirmed counterfeit force a PASS. The deal response includes `risk_penalty`, `risk_level`, and `critical_risk`.
