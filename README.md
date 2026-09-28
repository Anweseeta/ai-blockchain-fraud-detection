# AI-Powered Blockchain Transaction Anomaly Detection and Fraud Risk Scoring System

Final-year university project. Supervised fraud classification (XGBoost) on
Ethereum account-level aggregates, plus a validated anomaly/risk-scoring layer,
SHAP model explanations, a FastAPI backend, and a React dashboard.

**Language rules used throughout this project:** prediction is *not* proof of
fraud; anomaly is *not* fraud; high risk is *not* confirmed fraud; SHAP shows
model contribution (association), *not* causation.

## Quick start (run the complete application)

Prerequisites: Python 3.12, Node 18+, the validated artifacts in `models/`
(committed).

```bash
# 1. backend (from the project root)
TZ=UTC .venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8123
# API docs: http://127.0.0.1:8123/docs

# 2. frontend (new terminal)
cd frontend
cp .env.example .env        # set VITE_API_URL to the backend URL
npm install
npm run dev                 # http://localhost:5173
```

MongoDB is **optional**. Without `MONGO_URI` the API runs with an in-memory
prediction store and `/api/v1/health` reports `"database": "disabled"`; with an
unreachable URI it reports `"degraded"`. Inference works in all three states.
See `backend/README.md` for details.

## Pipeline overview

| Stage | What happens | Key files |
|---|---|---|
| Dataset | `data/raw/transaction_dataset.csv` — 9,841 rows × 51 cols, target `FLAG` (22.1% fraud). Leakage columns (`Unnamed: 0`, `Index`) and identifier (`Address`) excluded; 7 constant-zero + 1 unverifiable ERC20 column dropped → **39 features** (37 numeric + 2 categorical) | `docs/data_dictionary.md` |
| Split | Fixed group-aware stratified 70/15/15 split on `Address` (6,889 / 1,476 / 1,476; fraud ≈22.15%; zero addresses cross partitions). **Do not re-split.** | `data/processed/split_metadata.json`, `docs/methodology/group_aware_split.md` |
| Preprocess | Train-only fit: ERC20 NaN→0, token types→`'none'`+one-hot, signed log1p on 36/37 numerics, StandardScaler. No SMOTE. 39 → 52 processed features | `models/preprocessor.joblib`, `reports/phase2_report.md` |
| Train / validate / test | LogReg / RandomForest / **XGBoost** (seed 42, class weighting). Threshold tuned on validation only (argmax F1). Test scored **once** | `reports/phase3_report.md` |
| Risk | `risk = 100 × (1.0 × fraud_probability + 0.0 × anomaly_score)`; LOW 0–30, MEDIUM 31–70, HIGH 71–100. Anomaly weight is 0 per the evidence-backed Phase-4 policy | `models/risk_config.json`, `reports/phase4_report.md` |
| Explain | `shap.TreeExplainer`, tree-path-dependent, raw log-odds; built once, never retrained | `models/xgboost.joblib`, `reports/phase5_report.md` |
| Backend | FastAPI: `POST /predict`, `POST /predict/batch`, `POST /explain`, `GET /predictions`, `GET /health`, `GET /model-info`. Artifacts load once at startup; requests never train | `backend/README.md`, `reports/phase6_report.md` |
| Frontend | React + Vite + TS + Tailwind dashboard; consumes only the real backend | `frontend/README.md`, `reports/phase7_report.md` |
| Validation | End-to-end consistency, thresholds, boundaries, leakage, security, DB reliability | `reports/phase8_report.md` |

## Validated operating point (do not change without re-validation)

- Model: XGBoost, `models/xgboost.joblib` (version `1.0.0`)
- Threshold: **0.55** (`p ≥ 0.55 → FRAUD`), from `models/threshold_config.json`
- Test: precision 0.9801, recall 0.9052, F1 0.9412, ROC-AUC 0.9937, PR-AUC 0.9848
- Risk: `models/risk_config.json` (weights 1.0/0.0)

## Environment variables

Backend (`backend/.env.example`, git-ignored):

| Variable | Purpose | Default |
|---|---|---|
| `MONGO_URI` | MongoDB connection (optional) | unset → in-memory store |
| `MONGO_DB` / `MONGO_COLLECTION` | DB / collection names | `fraud_detection` / `predictions` |
| `CORS_ORIGINS` | Comma-separated allowed origins | unset → CORS disabled (deny-by-default) |
| `MAX_JSON_BYTES` / `MAX_CSV_BYTES` | Request size limits | 1,000,000 / 5,000,000 |
| `PREDICT_THRESHOLD` | Explicit threshold override (avoid) | validated 0.55 |

Frontend (`frontend/.env.example`): only `VITE_API_URL` — never secrets.

## Tests

```bash
cd backend  && TZ=UTC ../.venv/bin/pytest tests/ -q   # 17 tests
cd frontend && npx vitest run                          # 24 tests
cd frontend && npm run build                           # tsc + vite production build
```

## Repository layout

```
├── backend/            # FastAPI app (app/) + tests/
├── frontend/           # React dashboard (src/) 
├── models/             # validated artifacts: preprocessor, xgboost, *_config.json
├── data/processed/     # fixed split (train/val/test) + split_metadata.json
├── data/raw/           # original dataset (read-only reference)
├── notebooks/          # phase analysis scripts (NOT used by the API)
├── reports/            # phase1–phase8 reports + figures
└── docs/               # data dictionary, methodology notes
```

**Never retrain or re-split casually**: the notebooks under `notebooks/` are
analysis history. The API loads only `models/*.joblib` + `models/*.json`.
Changing the model, preprocessing, threshold, risk policy, or SHAP methodology
requires re-running the full validation protocol (see `reports/phase8_report.md`).
