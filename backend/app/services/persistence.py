"""Prediction-history persistence.

Stored document (deliberately minimal — no raw feature dump, no secrets):
{
  "prediction_id": uuid4 hex (unique),
  "created_at": ISO-8601 UTC,
  "model_version": str,
  "threshold": float,
  "prediction": "FRAUD" | "LEGITIMATE",
  "fraud_probability": float,
  "risk_score": int,
  "risk_level": "LOW" | "MEDIUM" | "HIGH",
  "top_factors": [ {feature, value, shap_value, direction, explanation_type} x top_k ],
}

Two backends share one interface: MongoPredictionStore (motor) and
InMemoryPredictionStore (used when MongoDB is disabled/unreachable, and in tests).
"""
from __future__ import annotations

from datetime import datetime, timezone


def build_document(prediction_id: str, model_version: str, threshold: float,
                   prediction: str, fraud_probability: float, risk_score: int,
                   risk_level: str, top_factors: list[dict]) -> dict:
    return {
        "prediction_id": prediction_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model_version": model_version,
        "threshold": float(threshold),
        "prediction": prediction,
        "fraud_probability": round(float(fraud_probability), 4),
        "risk_score": int(risk_score),
        "risk_level": risk_level,
        "top_factors": top_factors,
    }


class MongoPredictionStore:
    def __init__(self, collection):
        self._coll = collection

    async def save(self, doc: dict) -> None:
        await self._coll.insert_one(doc)

    async def recent(self, limit: int = 50, risk_level: str | None = None) -> list[dict]:
        q: dict = {}
        if risk_level:
            q["risk_level"] = risk_level
        cur = self._coll.find(q, {"_id": 0}).sort("created_at", -1).limit(min(limit, 100))
        return await cur.to_list(length=min(limit, 100))


class InMemoryPredictionStore:
    def __init__(self):
        self._docs: list[dict] = []

    async def save(self, doc: dict) -> None:
        self._docs.append(doc)

    async def recent(self, limit: int = 50, risk_level: str | None = None) -> list[dict]:
        docs = [d for d in self._docs if risk_level is None or d["risk_level"] == risk_level]
        return list(reversed(docs[-min(limit, 100):]))
