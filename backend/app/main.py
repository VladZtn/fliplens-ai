from fastapi import FastAPI

from app.schemas.analyze import AnalyzeRequest
from app.schemas.response import AnalyzeResponse
from app.services.engine import ValuationEngine

app = FastAPI(
    title="FlipLens AI",
    version="0.1.0",
)

engine = ValuationEngine()


@app.get("/")
def root():
    return {
        "status": "running",
        "project": "FlipLens AI",
    }


@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    return engine.analyze(
        request.title,
        request.price,
    )