# Phase 6 report — production-style backend/API

Date: 2026-09-25. Status: complete, tested, stopped for review. No frontend built,
no retraining, no artifact changes.

## 1. Backend architecture

`backend/app/` (FastAPI), strict separation per the brief:

- `main.py` — lifespan startup, CORS, body-size middleware, exception handlers, router wiring. No ML logic.
- `config.py` — env-based settings; defaults point at the validated artifacts.
- `schemas/` — `predict.py` generated from `data/processed/split_metadata.json`
  (39 exact features, `extra="forbid"`), plus explain/health/history response models.
- `routes/` — `predict.py`, `explain.py`, `system.py`, `history.py`.
- `services/` — `inference.py` (preprocess → predict_proba), `risk.py` (config-driven
  scoring), `persistence.py` (Mongo + in-memory stores, minimal document builder).
- `ml/loader.py` — loads preprocessor, XGBoost, metadata, risk config once; fails fast.
- `explainability/shap_explainer.py` — `TreeExplainer` built once (Phase-5 methodology).
- `database/mongo.py` — client + index creation.

## 2. Endpoint list

| Method | Path | Notes |
|---|---|---|
| POST | `/api/v1/predict` | 39 raw features → validation → preprocessing → XGBoost → p → threshold 0.55 → risk → SHAP top-10 → persisted |
| POST | `/api/v1/predict/batch` | CSV upload; requires the 39 columns; extra columns ignored; stateless (not persisted); ≤2000 rows / 5 MB |
| POST | `/api/v1/explain?top_k=` | top SHAP factors, `explanation_type: "model_contribution"` |
| GET | `/api/v1/predictions` | history, `limit` ≤100, optional `risk_level` filter |
| GET | `/api/v1/health` | `artifacts_loaded`, `database` status |
| GET | `/api/v1/model-info` | model_type, version, n_features=39, threshold, risk weights/thresholds; no secrets/paths |

## 3. Request/response schemas

Request: 39 aliased fields (37 finite floats, 2 token-type strings); missing →
422; wrong type → 422; non-finite → 422; any extra field (`FLAG`, `Address`, …) → 422.

Response example (real values, test row 1160, FLAG=1):

```json
{
  "prediction": "FRAUD",
  "fraud_probability": 1.0,
  "risk_score": 100,
  "risk_level": "HIGH",
  "threshold": 0.55,
  "top_factors": [
    {"feature": "Unique Received From Addresses", "value": "26.0",
     "shap_value": 3.65245, "direction": "increases_risk",
     "explanation_type": "model_contribution"},
    {"feature": " ERC20_most_rec_token_type_Blockwell say NOTSAFU",
     "value": "Blockwell say NOTSAFU", "shap_value": 3.05115,
     "direction": "increases_risk", "explanation_type": "model_contribution"}
  ],
  "prediction_id": "229cb12ad8c64642a71a8f947b517dea",
  "model_version": "1.0.0"
}
```

Live SHAP values are identical to the Phase-5 notebook for the same rows
(row 1160: 3.65245 / 3.05115 / 1.45939; row 498 legit: −2.24566 / −1.80450 / −1.51159).
Batch on rows {1160, 498, 1148} returned FRAUD/HIGH, LEGITIMATE/LOW, FRAUD/HIGH
(p=0.8111 — the known Phase-3 false positive), with a `FLAG` column present and ignored.

## 4. Database schema

Collection `predictions`:

```json
{
  "prediction_id": "<uuid4 hex>",
  "created_at": "<ISO-8601 UTC>",
  "model_version": "1.0.0",
  "threshold": 0.55,
  "prediction": "FRAUD | LEGITIMATE",
  "fraud_probability": 1.0,
  "risk_score": 100,
  "risk_level": "HIGH",
  "top_factors": [ {"feature","value","shap_value","direction","explanation_type"} × 10 ]
}
```

Indexes and why: `prediction_id` unique (point lookup of one record);
`created_at` descending (recent-history listing); `risk_level` (filter by
LOW/MEDIUM/HIGH). No raw feature dump and no secrets are stored.

## 5. Security decisions

- Secrets only via env (`.env` git-ignored; `.env.example` provided); no hard-coded
  credentials anywhere.
- CORS allow-list from `CORS_ORIGINS` (empty = same-origin only).
- Body limits: 1 MB JSON, 5 MB CSV; 413 on overflow.
- `extra="forbid"` + finite-number validation; 422 with sanitized details.
- No stack traces to clients (generic 500); no secrets in logs.
- MongoDB optional: API serves with in-memory fallback; `/health` reports
  `database: "disabled"/"degraded"` instead of crashing.
- No authentication (deferred per brief).

## 6. Test results

17/17 pass (`backend/tests/test_api.py`, run with `TZ=UTC`):

- health (artifacts loaded, db status sane), model-info (39 features, threshold 0.55,
  no paths/secrets leaked)
- valid fraud + legitimate predictions (probability ∈ [0,1], risk ∈ [0,100],
  level ∈ {LOW,MEDIUM,HIGH}, prediction matches ≥0.55 rule)
- missing feature → 422; wrong type → 422; inf → 422; `FLAG`/`Address`/`label`/`target` extras → 422
- batch: 2-row CSV → correct per-row results; `FLAG`+`Address` columns ignored;
  missing column → 400; garbage CSV → 400
- risk unit: score bounds 0/100, level boundaries 30/31/70/71
- explain: top_k respected, all factors `model_contribution`, causal disclaimer present
- persistence: prediction retrievable from `/predictions` with intact fields

## 7. Example API requests

```bash
# single prediction
curl -X POST http://127.0.0.1:8123/api/v1/predict \
  -H "Content-Type: application/json" -d @payload.json

# batch (FLAG column is ignored, never used)
curl -X POST http://127.0.0.1:8123/api/v1/predict/batch \
  -F "file=@accounts.csv"

# explain top 5
curl -X POST "http://127.0.0.1:8123/api/v1/explain?top_k=5" \
  -H "Content-Type: application/json" -d @payload.json

# health / model info / history
curl http://127.0.0.1:8123/api/v1/health
curl http://127.0.0.1:8123/api/v1/model-info
curl "http://127.0.0.1:8123/api/v1/predictions?limit=20&risk_level=HIGH"
```

Interactive docs: `http://127.0.0.1:8123/docs` (OpenAPI, generated from the schemas).

## 8. Files created

```
backend/
  requirements.txt  .env.example  README.md
  app/__init__.py  app/main.py  app/config.py
  app/schemas/{__init__,predict,explain,health,history}.py
  app/routes/{__init__,predict,explain,system,history}.py
  app/services/{__init__,inference,risk,persistence}.py
  app/ml/{__init__,loader}.py
  app/explainability/{__init__,shap_explainer}.py
  app/database/{__init__,mongo}.py
  tests/{__init__,test_api}.py
```

## 9. Issues encountered

1. `preprocessor.joblib` is pickled against `src.preprocessing.pipeline`; the backend
   adds the project root to `sys.path` in `app/__init__.py` before loading. Fixed.
2. `motor`/`httpx`/`python-multipart` were missing from the venv — installed.
3. No `mongod` on this machine — persistence degrades gracefully to in-memory
   when `MONGO_URI` is unset; tests cover the in-memory path and Mongo index
   creation is exercised at startup when a URI is configured.
4. Test client cannot JSON-encode `inf`; the non-finite test now sends a raw body.
5. The 422 handler crashed serializing `inf` inside error details (and on the
   `ValueError` object in `ctx`) — added a `_sanitize` step; verified 422 is returned.

## 10. Not done (per brief)

No React frontend, no deployment, no authentication, no Docker, no retraining,
no model/threshold/SHAP-methodology changes. XGBoost, threshold 0.55, risk weights
(1.0/0.0), and SHAP TreeExplainer methodology are exactly the validated ones.
