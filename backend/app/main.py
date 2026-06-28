from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.schemas.analyze import AnalyzeRequest
from app.schemas.response import AnalyzeResponse
from app.services.engine import ValuationEngine

app = FastAPI(
    title="FlipLens AI",
    version="0.1.0",
)

engine = ValuationEngine()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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