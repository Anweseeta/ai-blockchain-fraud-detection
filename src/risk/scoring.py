"""Transparent, config-driven 0-100 risk scoring engine.

Formula (project-defined policy, NOT a universal fraud standard):
    risk = 100 * (w_fraud * fraud_probability + w_anomaly * anomaly_score)

where fraud_probability and anomaly_score are both in [0, 1] and the weights
sum to 1. Weights and category thresholds are loaded from models/risk_config.json
so the operating policy can change without code edits.
"""

from __future__ import annotations

import json


def load_config(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def compute_risk_score(fraud_probability: float, anomaly_score: float, weights: dict) -> float:
    """Return the 0-100 risk score (float; callers round for display)."""
    w_f = weights["fraud_probability"]
    w_a = weights["anomaly_score"]
    p = min(max(float(fraud_probability), 0.0), 1.0)
    a = min(max(float(anomaly_score), 0.0), 1.0)
    return 100.0 * (w_f * p + w_a * a)


def risk_level(score: float, thresholds: dict) -> str:
    """Map a 0-100 score to LOW / MEDIUM / HIGH using configured cutoffs."""
    if score <= thresholds["low_max"]:
        return "LOW"
    if score <= thresholds["medium_max"]:
        return "MEDIUM"
    return "HIGH"


def score_record(fraud_probability: float, anomaly_score: float, config: dict) -> dict:
    """Full per-record output matching the project schema."""
    score = compute_risk_score(fraud_probability, anomaly_score, config["weights"])
    return {
        "fraud_probability": round(float(fraud_probability), 4),
        "anomaly_score": round(float(anomaly_score), 4),
        "risk_score": int(round(score)),
        "risk_level": risk_level(score, config["thresholds"]),
    }
