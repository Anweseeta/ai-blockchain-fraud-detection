# Blockchain Fraud Risk API — backend

FastAPI backend for Phase 6. Uses the validated artifacts from earlier phases;
**nothing here trains a model**.

## Run

```bash
cd backend
cp .env.example .env        # optional; MongoDB is optional
TZ=UTC ../.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8123
# docs: http://127.0.0.1:8123/docs
```

Tests: `cd backend && TZ=UTC ../.venv/bin/python -m pytest tests/ -q` (17 tests).

## Endpoints (`/api/v1`)

| Method | Path | Purpose |
|---|---|---|
| POST | `/predict` | score one account (39 raw features) |
| POST | `/predict/batch` | score a CSV (39 feature columns; extra cols like `FLAG`/`Address` ignored) |
| POST | `/explain?top_k=` | top SHAP factors, labeled `model_contribution` |
| GET | `/predictions?limit=&risk_level=` | recent prediction history |
| GET | `/health` | artifact load status + database status |
| GET | `/model-info` | model type, version, threshold, risk config (no secrets/paths) |

## Key design decisions

- **Artifacts load once at startup** (`lifespan`); requests never train. If artifacts
  are missing/corrupt the service fails fast with a clear log message.
- **No target leakage**: `PredictRequest` has `extra="forbid"` — `FLAG`, `Address`,
  or any other extra field is rejected with 422. Batch CSVs ignore extra columns.
- **Threshold 0.55** comes from `models/model_metadata.json` (validated Phase-3 value).
- **Risk** uses `models/risk_config.json` (weights 1.0/0.0, LOW ≤30, MEDIUM ≤70).
  Anomaly weight stays 0 per the evidence-backed Phase-4 policy.
- **SHAP** uses the Phase-5 methodology: `TreeExplainer`, tree-path-dependent,
  raw log-odds output; explainer built once, per-request cost is milliseconds.
- **Persistence** is graceful: with `MONGO_URI` set it writes to MongoDB
  (indexes: `prediction_id` unique, `created_at` desc, `risk_level`); without it
  the API still serves, using an in-memory store, and `/health` reports
  `database: "disabled"/"degraded"`. Stored docs contain no raw feature dump
  and no secrets.
- **Security**: CORS allow-list via env, JSON body limit (1 MB), CSV limit
  (5 MB / 2000 rows), finite-number validation, no stack traces to clients,
  sanitized 422 payloads, no secrets in logs, `.env` git-ignored.

## Layout

```
backend/app/
  main.py            # lifespan, CORS, size limits, error handlers, router wiring
  config.py          # env-based settings (no hard-coded secrets)
  schemas/           # predict.py (39-feature request, generated), explain/health/history
  routes/            # predict.py, explain.py, system.py, history.py
  services/          # inference.py, risk.py, persistence.py
  ml/loader.py       # one-time artifact loading + validation
  explainability/    # shap_explainer.py (built once at startup)
  database/mongo.py  # client + index creation
tests/test_api.py    # 17 tests
```
