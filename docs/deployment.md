# Deployment guide

Architecture:

```
Browser ──HTTPS──> Vercel (React/Vite SPA, static)
                        │  VITE_API_URL
                        ▼
                   Render (FastAPI + uvicorn, Python 3.12)
                        │  MONGO_URI (secret, server-side only)
                        ▼
                   MongoDB Atlas (M0 free tier)
```

The backend serves the validated XGBoost model (threshold 0.55, risk weights
1.0/0.0). The frontend is a static SPA that calls the backend over HTTPS.
Secrets exist only as hosting-platform environment variables — never in git,
never in the frontend bundle.

## What gets deployed

| Piece | Source | Needs at runtime |
|---|---|---|
| Backend | `backend/` | `backend/requirements.txt`, `models/preprocessor.joblib`, `models/xgboost.joblib`, `models/model_metadata.json`, `models/threshold_config.json`, `models/risk_config.json` |
| Frontend | `frontend/` | `VITE_API_URL` pointing at the Render backend |
| Database | Atlas | connection string in Render env only |

`data/processed/*.csv` are committed as test fixtures (backend tests need
them); the raw dataset (`data/raw/`) is git-ignored and never deployed.
The API never reads `data/` at runtime — only `models/`.

## Backend deployment (Render)

1. Push this repo to GitHub (see "How to deploy" below).
2. Render dashboard → New → **Blueprint** → connect the repo (`render.yaml`
   defines the service) — or New → Web Service manually:
   - Build: `pip install -r backend/requirements.txt`
   - Start: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
     (`$PORT` is supplied by Render — never hard-code a port)
   - Health check: `/api/v1/health`
3. Environment variables in the Render dashboard:
   - `PYTHON_VERSION=3.12.4`
   - `MONGO_URI` = Atlas connection string (**secret**)
   - `MONGO_DB=fraud_detection`, `MONGO_COLLECTION=predictions`
   - `CORS_ORIGINS=https://<your-app>.vercel.app` (set after the Vercel deploy)
   - `MODEL_VERSION=1.0.0`, `RISK_CONFIG_VERSION=1.0.0`
   - Optional: `MAX_JSON_BYTES`, `MAX_CSV_BYTES`, `MAX_BATCH_ROWS`
   - Leave `PREDICT_THRESHOLD` unset — the validated 0.55 is used.

Startup behavior: artifacts load once in `lifespan`; if any artifact is
missing/corrupt the service fails fast with a `RuntimeError` naming the file
(visible in Render logs). Requests never train. If MongoDB is unreachable the
API still serves with in-memory history and `/health` reports
`"database": "degraded"`.

## Frontend deployment (Vercel)

1. Vercel dashboard → Add New → Project → import the repo.
2. Root Directory: `frontend`. Framework preset: Vite.
3. Environment variable: `VITE_API_URL=https://<your-render-service>.onrender.com`
   (no trailing slash). This is the **only** production configuration the
   frontend needs — it is not hard-coded anywhere in `src/`.
4. Deploy. SPA routing is handled by `frontend/vercel.json` rewrites.

## MongoDB Atlas setup

1. Create a free (M0) cluster.
2. Database Access → add a user with read/write on `fraud_detection`
   (least privilege; not an Atlas admin).
3. Network Access → allow Render's outbound IPs (or 0.0.0.0/0 for simplicity on
   a free tier; restrict if you can).
4. Connect → Drivers → Python → copy the connection string; replace
   `<password>` with the DB user's password.
5. Paste it as `MONGO_URI` in the Render dashboard. **Never commit it, never
   put it in frontend env.**

On first connect the backend creates three indexes: `prediction_id` (unique),
`created_at` (descending), `risk_level`. Stored documents contain the
prediction, probability, risk score/level, threshold, and SHAP factors —
**no raw transaction features**.

## Environment variables (complete reference)

Backend: `MONGO_URI` (secret, optional), `MONGO_DB`, `MONGO_COLLECTION`,
`CORS_ORIGINS`, `MODEL_VERSION`, `RISK_CONFIG_VERSION`, `MAX_JSON_BYTES`,
`MAX_CSV_BYTES`, `MAX_BATCH_ROWS`, `PYTHON_VERSION`, (`PREDICT_THRESHOLD` —
leave unset). See `backend/.env.example` and the root `.env.example`
(placeholders only).

Frontend: `VITE_API_URL` only. See `frontend/.env.example`.

## CORS configuration

`CORS_ORIGINS` is a comma-separated allow-list read at startup; when empty the
CORS middleware is not installed (deny-by-default). Production must list the
exact Vercel origin, e.g. `https://fraud-console.vercel.app` — never `"*"`.
The local dev origin (`http://localhost:5173`) stays in the local `.env`, not
in production config.

## How to run locally

```bash
# backend
TZ=UTC .venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8123
# frontend
cd frontend && cp .env.example .env && npm install && npm run dev
```

## How to deploy (end to end)

```bash
git init && git add -A && git commit -m "fraud risk system"
gh repo create <name> --private --source=. --push   # or push manually
```

Then follow the Render / Atlas / Vercel sections above in order:
Atlas → Render (note the `onrender.com` URL) → Vercel (set `VITE_API_URL`) →
back to Render to set `CORS_ORIGINS` to the Vercel URL → redeploy if prompted.

## Health checks

- Backend: `GET https://<render>/api/v1/health` → `{"status":"ok", ...}`
- Model: `GET https://<render>/api/v1/model-info` → version, threshold, risk config
- Frontend: the Status page (`/status`) surfaces both.

## Known limitations

- Render free tier sleeps after inactivity: the first request cold-starts
  (artifact + SHAP explainer load, several seconds). The frontend shows loading
  states; the API has no fake "real-time" behavior.
- Prediction history on the free tier is in-memory unless Atlas is connected.
- Batch CSV limit: 5 MB / 2000 rows; JSON body limit: 1 MB.
