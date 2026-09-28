"""Explain-endpoint schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field

from .predict import TopFactor


class ExplainResponse(BaseModel):
    fraud_probability: float = Field(ge=0.0, le=1.0)
    prediction: str
    top_factors: list[TopFactor]
    note: str = Field(
        default="Factors are model contributions (SHAP), not causal explanations."
    )
