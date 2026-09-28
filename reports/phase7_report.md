# Phase 7 Report — React frontend / dashboard

Date: 2026-09-25
Status: **Complete. STOPPED after Phase 7 — not deployed.**

## 1. Frontend architecture

React 19 + Vite 8 + TypeScript + Tailwind CSS v4, React Router, TanStack Query.
Location: `frontend/`.

```
src/
├── components/   # RiskBadge (icon+text, never color-only), ScoreBar,
│                 # ShapChart (horizontal contributions + tooltip), ui.tsx
│                 # (StatCard, Spinner, ErrorAlert, EmptyState, Card)
├── pages/        # Dashboard, Analyze, PredictionDetail, Batch,
│                 # History, Status, NotFound
├── layouts/      # AppLayout — nav + live API/DB status pill
├── hooks/        # TanStack Query: useHealth, useModelInfo, useHistory,
│                 # usePredict, useBatch
├── services/     # api.ts — the ONLY module that calls fetch; ApiError class
├── types/        # TS types mirroring backend/app/schemas/ exactly
├── utils/        # validation.ts, csv.ts, format.ts
└── config/       # index.ts (VITE_API_URL), fields.ts (39 features, generated
                  # from split_metadata.json), samples.ts (real test-set rows)
```

Design rules enforced: no mock predictions, no hard-coded metrics/SHAP/history;
every model output originates from the backend. No secrets in frontend env —
only `VITE_API_URL` (see `.env.example`).

## 2. Page list

| Route | Page | Part |
|---|---|---|
| `/` | Dashboard: total/HIGH/MEDIUM/LOW from `GET /predictions`, risk-distribution bars, recent predictions, empty state when no history | B |
| `/analyze` | 39-feature form in 6 sections; per-field validation; rejects NaN/Infinity/garbage; FLAG/Address never inputs; "fill example" buttons use real test rows | C |
| `/predictions/:id` | Result: prediction, fraud probability, risk score/100, risk level, threshold; "model prediction, not proof of fraud" notice; SHAP chart | D, E, F, I |
| `/batch` | CSV upload → client header check → `POST /predict/batch` → counts, results table, download results CSV; FLAG not required, ignored if present | G |
| `/history` | `GET /predictions`: ID, timestamp, prediction, probability, score, level, model version; filters by risk level + prediction; pagination (25/page) | H |
| `/status` | `GET /health` + `GET /model-info`: API status, artifacts, DB status, model type, 39 features, threshold 0.55, risk weights/bands | J |

Every API interaction has loading / success / empty / validation-error /
backend-error states (Part K). Layout is responsive desktop-first with
tablet/laptop grids (Part L). Professional restrained aesthetic, no fake
badges/gradients/live data (Part M). Labels, keyboard-focus rings, contrast,
icon+text risk badges, semantic landmarks (Part N).

## 3. API integration details

- Central client `src/services/api.ts`: `predict`, `explain`, `predictBatch`
  (multipart), `predictions`, `health`, `modelInfo`. Network failure →
  `ApiError(0, "Could not reach the API. Is the backend running?")`.
- TanStack Query hooks wrap the client; mutations invalidate history.
- TS types (`PredictRequest`, `PredictionResponse`, `ShapFactor`,
  `BatchResponse`, `HistoryResponse`, `HealthResponse`, `ModelInfoResponse`)
  match the FastAPI schemas field-for-field.
- **No backend changes were needed.** The validated model, preprocessing,
  threshold (0.55), risk weights (1.0/0.0), and SHAP methodology are untouched.

## 4. Screenshots / visual summary

No headless browser is available in this environment, so pixel screenshots
could not be captured. Visual verification was done via: production build
artifact inspection, component render tests (jsdom), and live dev-server
serving. The UI follows the design in `frontend/README.md`.

## 5. Test results

`npx vitest run`: **24/24 passed** (6 files).
`npm run build` (tsc -b + vite): **clean**.

| File | Covers |
|---|---|
| `utils/validation.test.ts` | number/token validation: blanks, NaN, Infinity, `1e999`, hex, overlong/hostile tokens; 39-field coverage; FLAG/Address absent |
| `utils/csv.test.ts` | header check accepts 39+extras, rejects missing columns/empty |
| `components/RiskBadge.test.tsx` | badges carry text + icon + aria-label (not color-only) |
| `components/ShapChart.test.tsx` | inc/dec separation, real values, "model contribution, not causation" wording, no "proves fraud", tooltip fields, empty list |
| `services/api.test.ts` | success parse, 422 detail surfaced, unreachable → human-readable ApiError, multipart batch |
| `pages/Dashboard.test.tsx` | backend-down → error + Retry; empty history → empty state, no fake numbers; real counts render |

## 6. Manual testing results (live backend :8123 + dev server :5173)

| # | Check | Result |
|---|---|---|
| 1 | Fraud prediction (sample fraud row via same payload the form sends) | 200 → FRAUD, p=1.0000, risk 100 HIGH; top factor "Unique Received From Addresses +3.652" (matches Phase 5) |
| 2 | Legitimate prediction | 200 → LEGITIMATE, p=0.0000, risk 0 LOW |
| 3 | Malformed input | 422 "request validation failed" |
| 4 | Batch CSV (`public/batch_sample.csv`, 5 real rows) | 200 → 5 rows, 3 fraud, 2 legit, 0 errors |
| 5 | History | `GET /predictions` returns the 2 single predictions with IDs, timestamps, levels |
| 6 | System status | `/health` ok, db disabled; `/model-info` xgboost, 39 features, thr 0.55 |
| 7 | Backend unavailable | backend killed → API 000; frontend still serves 200; UI renders the tested error state with Retry |

## 7. Files created

33 source files under `frontend/src/` + `frontend/public/batch_sample.csv`
(5 real test-set rows, 39 feature columns, no FLAG), `.env.example`,
`frontend/README.md`, this report. Full list in §1 / `frontend/README.md`.

## 8. Issues encountered

1. `src/App.tsx` — first write was rejected (read-before-write rule) and the
   router component never landed; template App remained until caught by
   inspection. Fixed by writing the real component.
2. `@testing-library/jest-dom` v7 matchers not registered under `tsc -b`:
   switched test setup to `@testing-library/jest-dom/vitest` and typed
   `vitest/globals`.
3. `vite.config.ts` `test` key unknown to `vite`'s `defineConfig` types:
   import from `vitest/config`.
4. CSV header check trimmed leading spaces, breaking the 8 space-prefixed
   feature names — now exact-match like the backend.
5. ShapChart tooltip test: hover opens, click toggles shut — test uses hover.
6. Dashboard error test needed a longer `findBy` timeout due to query retry.
7. First `batch_sample.csv` contained a row with a missing value (real data
   quirk) → backend correctly returned a row error; regenerated with 5
   NaN-free rows.
8. Vite dev server bound to `[::1]:5173` — reachable via `localhost`, not
   `127.0.0.1`.

## 9. Not deployed

Per instruction: built and verified locally only. To run:
`VITE_API_URL=http://<backend> npm run dev` with the FastAPI backend up.
