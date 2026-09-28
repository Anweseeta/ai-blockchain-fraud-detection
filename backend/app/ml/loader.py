"""Artifact loading. Called once at startup — never during a request."""
from __future__ import annotations

import json
from dataclasses import dataclass, field

import joblib


@dataclass
class Artifacts:
    preprocessor: object
    xgb_model: object
    threshold: float
    risk_config: dict
    feature_names_in: list = field(default_factory=list)   # 39 raw input features
    feature_names_out: list = field(default_factory=list)  # 52 model features
    model_version: str = "1.0.0"


def load_artifacts(preprocessor_path: str, xgb_path: str, metadata_path: str,
                   risk_config_path: str, model_version: str) -> Artifacts:
    """Load and cross-check every validated artifact. Raises RuntimeError on failure."""
    try:
        preprocessor = joblib.load(preprocessor_path)
    except Exception as e:
        raise RuntimeError(f"could not load preprocessor artifact: {type(e).__name__}") from e
    try:
        xgb_model = joblib.load(xgb_path)
    except Exception as e:
        raise RuntimeError(f"could not load xgboost artifact: {type(e).__name__}") from e
    try:
        with open(metadata_path) as f:
            metadata = json.load(f)
    except Exception as e:
        raise RuntimeError(f"could not load model metadata: {type(e).__name__}") from e
    try:
        with open(risk_config_path) as f:
            risk_config = json.load(f)
    except Exception as e:
        raise RuntimeError(f"could not load risk config: {type(e).__name__}") from e

    threshold = float(metadata["models"]["xgboost"]["threshold"])
    feature_names_out = list(metadata.get("feature_names_out", []))
    if not feature_names_out:
        # fallback: derive from preprocessor output
        try:
            feature_names_out = list(preprocessor.get_feature_names_out())
        except Exception:
            feature_names_out = []

    n_in = getattr(preprocessor, "n_features_in_", None)
    if n_in is not None and n_in != 39:
        raise RuntimeError(f"preprocessor expects {n_in} features, expected 39")

    return Artifacts(
        preprocessor=preprocessor,
        xgb_model=xgb_model,
        threshold=threshold,
        risk_config=risk_config,
        feature_names_out=feature_names_out,
        model_version=model_version,
    )
