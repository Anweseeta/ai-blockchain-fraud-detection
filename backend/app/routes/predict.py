"""Prediction routes: single + batch. No training happens here."""
from __future__ import annotations

import logging
import uuid

import pandas as pd
from fastapi import APIRouter, HTTPException, Request, UploadFile, status

from ..config import settings
from ..schemas.predict import (
    ORDERED_FEATURES,
    BatchPredictionItem,
    BatchPredictionResponse,
    PredictionResponse,
    PredictRequest,
    TopFactor,
)
from ..services.persistence import build_document

log = logging.getLogger("fraud_api")
router = APIRouter()


@router.post("/predict", response_model=PredictionResponse, summary="Score one account")
async def predict(req: PredictRequest, request: Request):
    """Validate 39 raw features -> preprocess -> XGBoost -> threshold -> risk -> SHAP."""
    resp = _predict_with_map(req, request)
    doc = build_document(
        resp.prediction_id, resp.model_version, resp.threshold, resp.prediction,
        resp.fraud_probability, resp.risk_score, resp.risk_level,
        [f.model_dump() for f in resp.top_factors],
    )
    try:
        await request.app.state.store.save(doc)
    except Exception:
        log.exception("prediction persistence failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="prediction computed but could not be stored; please retry",
        )
    return resp


def _predict_with_map(req: PredictRequest, request: Request) -> PredictionResponse:
    inference = request.app.state.inference
    risk = request.app.state.risk
    shap_svc = request.app.state.shap
    artifacts = request.app.state.artifacts

    proba = float(inference.predict_proba([req])[0])
    prediction = "FRAUD" if proba >= artifacts.threshold else "LEGITIMATE"
    score = risk.score(proba)
    level = risk.level(score)

    from ..explainability.shap_explainer import raw_value_map

    x_row = inference.transform_single(req)
    raw_map = raw_value_map(req.model_dump(by_alias=True), shap_svc.feature_names)
    factors = [
        TopFactor(**f)
        for f in shap_svc.explain_row(x_row, raw_map, top_k=settings.TOP_K_FACTORS)
    ]
    return PredictionResponse(
        prediction=prediction,
        fraud_probability=round(proba, 4),
        risk_score=score,
        risk_level=level,
        threshold=artifacts.threshold,
        top_factors=factors,
        prediction_id=uuid.uuid4().hex,
        model_version=artifacts.model_version,
    )


@router.post("/predict/batch", response_model=BatchPredictionResponse,
             summary="Score a CSV of accounts")
async def predict_batch(file: UploadFile, request: Request):
    """CSV must contain the 39 model features as columns.

    Extra columns (e.g. FLAG, Address) are ignored and never used in prediction.
    Batch scoring is stateless: results are not persisted to history.
    """
    if file.content_type not in ("text/csv", "application/vnd.ms-excel", "application/octet-stream", None):
        raise HTTPException(status_code=400, detail="upload must be a CSV file")
    content = await file.read()
    if len(content) > settings.MAX_CSV_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"CSV exceeds size limit of {settings.MAX_CSV_BYTES} bytes",
        )
    try:
        import io

        df = pd.read_csv(io.BytesIO(content))
    except Exception:
        raise HTTPException(status_code=400, detail="could not parse CSV")

    missing = [f for f in ORDERED_FEATURES if f not in df.columns]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"CSV is missing required feature columns: {missing}",
        )
    if len(df) > settings.MAX_BATCH_ROWS:
        raise HTTPException(
            status_code=400,
            detail=f"CSV has {len(df)} rows; limit is {settings.MAX_BATCH_ROWS}",
        )
    if len(df) == 0:
        raise HTTPException(status_code=400, detail="CSV contains no rows")

    inference = request.app.state.inference
    risk = request.app.state.risk
    artifacts = request.app.state.artifacts

    results: list[BatchPredictionItem] = []
    valid_rows: list[tuple[int, PredictRequest]] = []
    for i, (_, row) in enumerate(df.iterrows()):
        payload = {f: row[f] for f in ORDERED_FEATURES}
        try:
            valid_rows.append((i, PredictRequest(**payload)))
        except Exception as e:
            results.append(BatchPredictionItem(
                row=i, prediction="LEGITIMATE", fraud_probability=0.0,
                risk_score=0, risk_level="LOW",
                error=f"invalid row: {type(e).__name__}",
            ))

    if valid_rows:
        idx = [i for i, _ in valid_rows]
        reqs = [r for _, r in valid_rows]
        probas = inference.predict_proba(reqs)
        scored = {}
        for j, p in enumerate(probas):
            p = float(p)
            pred = "FRAUD" if p >= artifacts.threshold else "LEGITIMATE"
            s = risk.score(p)
            scored[idx[j]] = BatchPredictionItem(
                row=idx[j], prediction=pred, fraud_probability=round(p, 4),
                risk_score=s, risk_level=risk.level(s),
            )
        results.extend(scored.values())

    results.sort(key=lambda r: r.row)
    return BatchPredictionResponse(
        n_rows=len(df),
        n_fraud=sum(1 for r in results if r.error is None and r.prediction == "FRAUD"),
        n_legitimate=sum(1 for r in results if r.error is None and r.prediction == "LEGITIMATE"),
        n_errors=sum(1 for r in results if r.error is not None),
        results=results,
        model_version=artifacts.model_version,
    )
