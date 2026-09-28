"""Prediction-history retrieval."""
from __future__ import annotations

from fastapi import APIRouter, Query, Request

from ..schemas.history import HistoryResponse, PredictionRecord

router = APIRouter()


@router.get("/predictions", response_model=HistoryResponse, summary="Recent predictions")
async def list_predictions(
    request: Request,
    limit: int = Query(default=50, ge=1, le=100),
    risk_level: str | None = Query(default=None, pattern="^(LOW|MEDIUM|HIGH)$"),
):
    docs = await request.app.state.store.recent(limit=limit, risk_level=risk_level)
    return HistoryResponse(
        n=len(docs),
        records=[PredictionRecord(**{k: d.get(k) for k in PredictionRecord.model_fields}) for d in docs],
    )
