"""Risk scoring. Formula and policy come from the validated risk_config.json —
the backend never invents weights or thresholds."""
from __future__ import annotations


class RiskService:
    def __init__(self, risk_config: dict):
        self.weights = risk_config["weights"]
        self.thresholds = risk_config["thresholds"]
        wsum = self.weights["fraud_probability"] + self.weights["anomaly_score"]
        if abs(wsum - 1.0) > 1e-9:
            raise ValueError("risk weights must sum to 1")

    def score(self, fraud_probability: float, anomaly_score: float = 0.0) -> int:
        p = min(max(float(fraud_probability), 0.0), 1.0)
        a = min(max(float(anomaly_score), 0.0), 1.0)
        return int(round(100.0 * (self.weights["fraud_probability"] * p
                                  + self.weights["anomaly_score"] * a)))

    def level(self, score: int) -> str:
        if score <= self.thresholds["low_max"]:
            return "LOW"
        if score <= self.thresholds["medium_max"]:
            return "MEDIUM"
        return "HIGH"
