"""API tests. Run from backend/:  TZ=UTC ../.venv/bin/python -m pytest tests/ -q"""
from __future__ import annotations

import io

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.predict import ORDERED_FEATURES
from app.services.risk import RiskService

TEST_CSV = "../data/processed/test.csv"


def _payload(row_idx: int) -> dict:
    df = pd.read_csv(TEST_CSV, nrows=row_idx + 1)
    row = df.iloc[row_idx]
    out = {}
    for f in ORDERED_FEATURES:
        v = row[f]
        out[f] = v.item() if hasattr(v, "item") else v
    return out


@pytest.fixture(scope="module")
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture(scope="module")
def fraud_payload():
    return _payload(1160)  # known fraud, p ~ 1.0


@pytest.fixture(scope="module")
def legit_payload():
    return _payload(498)  # known legitimate, p ~ 0.0


# ---- health / model-info ----
def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["artifacts_loaded"] is True
    assert body["database"] in ("connected", "disabled", "degraded")


def test_model_info(client):
    r = client.get("/api/v1/model-info")
    assert r.status_code == 200
    body = r.json()
    assert body["model_type"] == "xgboost"
    assert body["n_features"] == 39
    assert body["threshold"] == 0.55
    assert body["risk_weights"] == {"fraud_probability": 1.0, "anomaly_score": 0.0}
    assert "models/" not in str(body) and "home" not in str(body).lower()


# ---- single prediction ----
def test_valid_prediction_fraud(client, fraud_payload):
    r = client.post("/api/v1/predict", json=fraud_payload)
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["prediction"] == "FRAUD"
    assert 0.0 <= b["fraud_probability"] <= 1.0
    assert 0 <= b["risk_score"] <= 100
    assert b["risk_level"] in ("LOW", "MEDIUM", "HIGH")
    assert b["threshold"] == 0.55
    assert len(b["top_factors"]) > 0
    f0 = b["top_factors"][0]
    assert f0["explanation_type"] == "model_contribution"
    assert f0["direction"] in ("increases_risk", "decreases_risk")


def test_valid_prediction_legit(client, legit_payload):
    r = client.post("/api/v1/predict", json=legit_payload)
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["prediction"] == "LEGITIMATE"
    assert b["risk_level"] == "LOW"


def test_threshold_behavior(client, fraud_payload, legit_payload):
    for payload in (fraud_payload, legit_payload):
        b = client.post("/api/v1/predict", json=payload).json()
        expected = "FRAUD" if b["fraud_probability"] >= 0.55 else "LEGITIMATE"
        assert b["prediction"] == expected


def test_missing_feature(client, fraud_payload):
    bad = dict(fraud_payload)
    bad.pop("Sent tnx")
    r = client.post("/api/v1/predict", json=bad)
    assert r.status_code == 422


def test_invalid_type(client, fraud_payload):
    bad = dict(fraud_payload)
    bad["Sent tnx"] = "not-a-number"
    r = client.post("/api/v1/predict", json=bad)
    assert r.status_code == 422


def test_nonfinite_rejected(client, fraud_payload):
    import json as _json

    bad = dict(fraud_payload)
    bad["Sent tnx"] = float("inf")
    raw = _json.dumps(bad, allow_nan=True)  # emits Infinity literal
    r = client.post("/api/v1/predict", content=raw,
                    headers={"Content-Type": "application/json"})
    assert r.status_code == 422


def test_no_target_leakage(client, fraud_payload):
    for extra in ("FLAG", "Address", "label", "target"):
        bad = dict(fraud_payload)
        bad[extra] = 1
        r = client.post("/api/v1/predict", json=bad)
        assert r.status_code == 422, extra


def test_no_stack_trace_on_500(client):
    r = client.post("/api/v1/predict", json={"broken": "[[["})
    assert r.status_code in (400, 422)


# ---- batch ----
def _csv_bytes(rows: list[dict], extra_col: dict | None = None) -> bytes:
    df = pd.DataFrame(rows)
    if extra_col:
        for k, v in extra_col.items():
            df[k] = v
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode()


def test_batch_prediction(client, fraud_payload, legit_payload):
    data = _csv_bytes([fraud_payload, legit_payload])
    r = client.post("/api/v1/predict/batch", files={"file": ("b.csv", data, "text/csv")})
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["n_rows"] == 2 and b["n_errors"] == 0
    assert b["results"][0]["prediction"] == "FRAUD"
    assert b["results"][1]["prediction"] == "LEGITIMATE"
    for item in b["results"]:
        assert 0.0 <= item["fraud_probability"] <= 1.0
        assert 0 <= item["risk_score"] <= 100


def test_batch_ignores_flag_column(client, fraud_payload):
    data = _csv_bytes([fraud_payload], extra_col={"FLAG": [1], "Address": ["0xabc"]})
    r = client.post("/api/v1/predict/batch", files={"file": ("b.csv", data, "text/csv")})
    assert r.status_code == 200
    assert r.json()["n_errors"] == 0
    assert r.json()["results"][0]["prediction"] == "FRAUD"


def test_batch_missing_column(client, fraud_payload):
    bad = dict(fraud_payload)
    bad.pop("Sent tnx")
    data = _csv_bytes([bad])
    r = client.post("/api/v1/predict/batch", files={"file": ("b.csv", data, "text/csv")})
    assert r.status_code == 400


def test_batch_invalid_csv(client):
    r = client.post("/api/v1/predict/batch", files={"file": ("b.csv", b"\x00\x01not csv\xff", "text/csv")})
    assert r.status_code in (400, 422)


# ---- risk unit ----
def test_risk_bounds_and_levels():
    cfg = {"weights": {"fraud_probability": 1.0, "anomaly_score": 0.0},
           "thresholds": {"low_max": 30, "medium_max": 70, "high_min": 71}}
    rs = RiskService(cfg)
    assert rs.score(0.0) == 0 and rs.score(1.0) == 100
    assert rs.level(0) == "LOW" and rs.level(30) == "LOW"
    assert rs.level(31) == "MEDIUM" and rs.level(70) == "MEDIUM"
    assert rs.level(71) == "HIGH" and rs.level(100) == "HIGH"


# ---- explain ----
def test_explain_structure(client, fraud_payload):
    r = client.post("/api/v1/explain", json=fraud_payload, params={"top_k": 5})
    assert r.status_code == 200, r.text
    b = r.json()
    assert len(b["top_factors"]) == 5
    assert all(f["explanation_type"] == "model_contribution" for f in b["top_factors"])
    assert "not causal" in b["note"]


# ---- persistence ----
def test_prediction_persisted(client, fraud_payload):
    r = client.post("/api/v1/predict", json=fraud_payload)
    pid = r.json()["prediction_id"]
    h = client.get("/api/v1/predictions", params={"limit": 5})
    assert h.status_code == 200
    ids = [rec["prediction_id"] for rec in h.json()["records"]]
    assert pid in ids
    rec = next(rec for rec in h.json()["records"] if rec["prediction_id"] == pid)
    assert rec["risk_level"] == "HIGH" and rec["prediction"] == "FRAUD"
    assert len(rec["top_factors"]) > 0
