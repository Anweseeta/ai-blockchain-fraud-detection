"""History-endpoint schemas."""
from __future__ import annotations

from pydantic import BaseModel

from .predict import TopFactor


class PredictionRecord(BaseModel):
    prediction_id: str
    created_at: str
    model_version: str
    threshold: float
    prediction: str
    fraud_probability: float
    risk_score: int
    risk_level: str
    top_factors: list[TopFactor]


class HistoryResponse(BaseModel):
    n: int
    records: list[PredictionRecord]
