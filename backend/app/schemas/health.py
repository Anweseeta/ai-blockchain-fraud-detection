"""Health / model-info schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    artifacts_loaded: bool
    database: str = Field(description="'connected', 'disabled', or 'degraded'")
    model_version: str


class ModelInfoResponse(BaseModel):
    model_type: str
    model_version: str
    n_features: int
    threshold: float
    risk_weights: dict
    risk_thresholds: dict
    risk_config_version: str
    shap_explainer: str
