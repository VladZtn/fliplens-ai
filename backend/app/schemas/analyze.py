from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    price: float = Field(..., gt=0)