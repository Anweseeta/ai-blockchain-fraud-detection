"""ML inference: validate -> DataFrame -> saved preprocessor -> saved XGBoost.

The model is NEVER trained here. Artifacts are loaded once at startup.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..schemas.predict import ORDERED_FEATURES, PredictRequest


class InferenceService:
    def __init__(self, artifacts):
        self.artifacts = artifacts

    def _frame(self, requests: list[PredictRequest]) -> pd.DataFrame:
        rows = []
        for r in requests:
            d = r.model_dump(by_alias=True)
            rows.append([d[f] for f in ORDERED_FEATURES])
        return pd.DataFrame(rows, columns=ORDERED_FEATURES)

    def predict_proba(self, requests: list[PredictRequest]) -> np.ndarray:
        """Return fraud probabilities in [0, 1] for each request."""
        frame = self._frame(requests)
        X = self.artifacts.preprocessor.transform(frame)
        return self.artifacts.xgb_model.predict_proba(X)[:, 1]

    def transform_single(self, request: PredictRequest) -> np.ndarray:
        """Transformed feature row for one request (used by the SHAP explainer)."""
        return self.artifacts.preprocessor.transform(self._frame([request]))[0]
