from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.ai import router as ai_router
from app.api.routes.deals import router as deals_router
from app.config import get_settings
from app.schemas.analyze import AnalyzeRequest
from app.schemas.response import AnalyzeResponse
from app.services.engine import ValuationEngine

settings = get_settings()
app = FastAPI(title=settings.app_name, version=settings.app_version)
engine = ValuationEngine()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-FlipLens-Remaining", "Server-Timing"],
)
app.include_router(ai_router)
app.include_router(deals_router)


@app.get("/")
def root():
    return {
        "status": "running",
        "project": settings.app_name,
        "version": settings.app_version,
        "ai_provider": settings.ai_provider,
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest):
    return engine.analyze(request.title, request.price)
