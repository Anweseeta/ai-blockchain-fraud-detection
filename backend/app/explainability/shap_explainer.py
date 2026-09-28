"""SHAP explanations for the validated XGBoost model.

Uses the exact Phase-5 methodology: shap.TreeExplainer, tree_path_dependent,
raw (log-odds) output. The explainer is built once at startup; per-request
explanation of a single row is milliseconds. No retraining, ever.
"""
from __future__ import annotations

import numpy as np
import shap


"""Map transformed feature names back to human-readable raw input values.

Numeric (incl. log1p/scaled) outputs keep their original column names, so they
map 1:1. One-hot outputs (e.g. ' ERC20_most_rec_token_type_Blockwell say NOTSAFU')
map to the request's raw category string for that token column.
"""


def raw_value_map(request_dict: dict, feature_names_out: list[str]) -> dict:
    from ..schemas.predict import CATEGORICAL_INPUTS

    out: dict[str, str] = {}
    for t in feature_names_out:
        if t in request_dict:
            out[t] = str(request_dict[t])
        else:
            for c in CATEGORICAL_INPUTS:
                if t.startswith(c + "_"):
                    out[t] = str(request_dict.get(c, ""))
                    break
            else:
                out[t] = ""
    return out


class ShapExplainerService:
    def __init__(self, xgb_model, feature_names_out: list[str]):
        self._explainer = shap.TreeExplainer(xgb_model)
        self._base = float(np.atleast_1d(self._explainer.expected_value)[0])
        self.feature_names = list(feature_names_out) or [f"f{i}" for i in range(52)]

    def explain_row(self, x_row: np.ndarray, raw_values: dict, top_k: int = 10) -> list[dict]:
        """Return top-k factors for one transformed feature row.

        Each factor is labeled "model_contribution" — association, not causation.
        """
        sv = np.asarray(self._explainer.shap_values(x_row.reshape(1, -1))).ravel()
        order = np.argsort(np.abs(sv))[::-1][: max(1, top_k)]
        factors = []
        for j in order:
            v = float(sv[j])
            factors.append({
                "feature": self.feature_names[j],
                "value": str(raw_values.get(self.feature_names[j], "")),
                "shap_value": round(v, 5),
                "direction": "increases_risk" if v > 0 else "decreases_risk",
                "explanation_type": "model_contribution",
            })
        return factors
