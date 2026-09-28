"""Explain route: top SHAP contributors for one prediction.

Factors are labeled "model_contribution" — association, not causation.
"""
from __future__ import annotations

from fastapi import APIRouter, Query, Request

from ..config import settings
from ..explainability.shap_explainer import raw_value_map
from ..schemas.explain import ExplainResponse
from ..schemas.predict import PredictRequest, TopFactor

router = APIRouter()


@router.post("/explain", response_model=ExplainResponse, summary="Explain one prediction")
async def explain(
    req: PredictRequest,
    request: Request,
    top_k: int = Query(default=10, ge=1, le=20, description="number of factors to return"),
):
    inference = request.app.state.inference
    shap_svc = request.app.state.shap
    artifacts = request.app.state.artifacts

    proba = float(inference.predict_proba([req])[0])
    x_row = inference.transform_single(req)
    raw_map = raw_value_map(req.model_dump(by_alias=True), shap_svc.feature_names)
    factors = [
        TopFactor(**f) for f in shap_svc.explain_row(x_row, raw_map, top_k=top_k)
    ]
    return ExplainResponse(
        fraud_probability=round(proba, 4),
        prediction="FRAUD" if proba >= artifacts.threshold else "LEGITIMATE",
        top_factors=factors,
    )
