# Fraud Risk Console — frontend

React + Vite + TypeScript + Tailwind CSS dashboard for the
AI-Powered Blockchain Transaction Anomaly Detection system (Phase 7).

The frontend consumes the real FastAPI backend. There are no mock predictions,
no hard-coded metrics, no fake history, and no fabricated SHAP values —
every model output shown originates from the backend.

## Run

```bash
cd frontend
npm install
cp .env.example .env        # set VITE_API_URL to your backend
npm run dev                 # http://localhost:5173
```

The backend must be running, e.g.:

```bash
cd .. && .venv/bin/python -m uvicorn backend.app.main:app --port 8123
```

Production build: `npm run build` → `frontend/dist/`.

## Configuration

Only browser-safe configuration lives here:

| Variable       | Purpose                          |
| -------------- | -------------------------------- |
| `VITE_API_URL` | Public base URL of the FastAPI backend |

Never put MongoDB URIs, model secrets, or API credentials in frontend env files.

## Pages

| Route              | Page              | Backend calls                                   |
| ------------------ | ----------------- | ----------------------------------------------- |
| `/`                | Dashboard         | `GET /api/v1/predictions`                       |
| `/analyze`         | New analysis      | `POST /api/v1/predict`                          |
| `/predictions/:id` | Prediction result | (uses the prediction response, falls back to history) |
| `/batch`           | Batch CSV         | `POST /api/v1/predict/batch`                    |
| `/history`         | History           | `GET /api/v1/predictions`                       |
| `/status`          | System status     | `GET /api/v1/health`, `GET /api/v1/model-info`  |

## Structure

```
src/
├── components/   # RiskBadge, ScoreBar, ShapChart, ui (StatCard/Spinner/ErrorAlert/EmptyState/Card)
├── pages/        # Dashboard, Analyze, PredictionDetail, Batch, History, Status, NotFound
├── layouts/      # AppLayout (nav + API status pill)
├── hooks/        # TanStack Query hooks (useHealth, useModelInfo, useHistory, usePredict, useBatch)
├── services/     # api.ts — the only place fetch is called
├── types/        # TS types mirroring backend/app/schemas/
├── utils/        # validation.ts, csv.ts, format.ts
└── config/       # index.ts (API_URL), fields.ts (39 features, generated), samples.ts
```

## The 39 model features

Defined in `src/config/fields.ts`, generated from
`data/processed/split_metadata.json` so names match the backend exactly.
Organized into 6 sections in the analysis form:

1. Account / activity information (7)
2. Ethereum transaction behavior (4)
3. Received transaction behavior (4)
4. Sent transaction behavior (7)
5. ERC20 / token behavior (15)
6. Token type information (2)

`FLAG`, `Address`, `target`, and `label` are never model inputs and do not
appear in the form. Client-side validation rejects empty, non-numeric,
`NaN`/`Infinity`, and hostile token strings before anything is sent.

## Language rules (enforced in UI copy and tests)

- "Model prediction", never proof of fraud.
- SHAP is labelled "Model explanation — factors contributing to this prediction";
  copy states it shows model contribution, not causation.
- Risk is always communicated with icon + text, never color alone.

## Tests

```bash
npx vitest run     # 24 tests: validation, CSV checks, badges, SHAP chart, API client, dashboard states
npm run build      # tsc + vite production build
```

A sample batch file (5 real rows, 39 feature columns, no FLAG) is served at
`public/batch_sample.csv`.
