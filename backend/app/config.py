"""Environment-based configuration. No secrets hard-coded; .env is git-ignored."""
from __future__ import annotations

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BACKEND_DIR.parent  # ai-blockchain-fraud-detection/


def _get(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


class Settings:
    # artifact locations (configurable; defaults point at the validated artifacts)
    MODELS_DIR: str = _get("MODELS_DIR", str(PROJECT_DIR / "models"))
    PREPROCESSOR_PATH: str = _get("PREPROCESSOR_PATH", str(Path(_get("MODELS_DIR", str(PROJECT_DIR / "models"))) / "preprocessor.joblib"))
    XGBOOST_PATH: str = _get("XGBOOST_PATH", str(Path(_get("MODELS_DIR", str(PROJECT_DIR / "models"))) / "xgboost.joblib"))
    MODEL_METADATA_PATH: str = _get("MODEL_METADATA_PATH", str(Path(_get("MODELS_DIR", str(PROJECT_DIR / "models"))) / "model_metadata.json"))
    RISK_CONFIG_PATH: str = _get("RISK_CONFIG_PATH", str(Path(_get("MODELS_DIR", str(PROJECT_DIR / "models"))) / "risk_config.json"))

    MODEL_VERSION: str = _get("MODEL_VERSION", "1.0.0")
    RISK_CONFIG_VERSION: str = _get("RISK_CONFIG_VERSION", "1.0.0")

    # operating threshold comes from the validated metadata; env override is explicit
    THRESHOLD_OVERRIDE: str = _get("PREDICT_THRESHOLD", "")

    # MongoDB (optional). If unset/unreachable, the API runs with an in-memory store
    # and reports database="disabled"/"degraded" on /health — never crashes.
    MONGO_URI: str = _get("MONGO_URI", "")
    MONGO_DB: str = _get("MONGO_DB", "fraud_detection")
    MONGO_COLLECTION: str = _get("MONGO_COLLECTION", "predictions")

    # security
    CORS_ORIGINS: list[str] = [o.strip() for o in _get("CORS_ORIGINS", "").split(",") if o.strip()]
    MAX_JSON_BYTES: int = int(_get("MAX_JSON_BYTES", 1_000_000))
    MAX_CSV_BYTES: int = int(_get("MAX_CSV_BYTES", 5_000_000))
    MAX_BATCH_ROWS: int = int(_get("MAX_BATCH_ROWS", 2000))
    TOP_K_FACTORS: int = int(_get("TOP_K_FACTORS", 10))


settings = Settings()
