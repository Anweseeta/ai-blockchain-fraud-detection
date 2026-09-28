"""Health and model-info routes. No secrets, no filesystem paths exposed."""
from __future__ import annotations

from fastapi import APIRouter, Request

from ..config import settings
from ..schemas.health import HealthResponse, ModelInfoResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, summary="Service health")
async def health(request: Request):
    return HealthResponse(
        status="ok" if request.app.state.artifacts is not None else "degraded",
        artifacts_loaded=request.app.state.artifacts is not None,
        database=request.app.state.db_status,
        model_version=settings.MODEL_VERSION,
    )


@router.get("/model-info", response_model=ModelInfoResponse, summary="Model metadata")
async def model_info(request: Request):
    artifacts = request.app.state.artifacts
    return ModelInfoResponse(
        model_type="xgboost",
        model_version=artifacts.model_version,
        n_features=39,
        threshold=artifacts.threshold,
        risk_weights=artifacts.risk_config["weights"],
        risk_thresholds=artifacts.risk_config["thresholds"],
        risk_config_version=settings.RISK_CONFIG_VERSION,
        shap_explainer="shap.TreeExplainer (tree_path_dependent, raw log-odds output)",
    )
