from fastapi import APIRouter

from app.schemas.analyze import AnalyzeRequest
from app.services.valuation import analyze_product

router = APIRouter()


@router.post("/analyze")
def analyze(request: AnalyzeRequest):
    return analyze_product(
        title=request.title,
        price=request.price
    )