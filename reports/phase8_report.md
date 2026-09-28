# Phase 8 — End-to-End Validation, Security, Reproducibility & Final Verification

Date: 2026-09-25. Scope: validation/testing/security/reproducibility only.
**Not deployed. No new features. No redesign.**

The validated ML model, preprocessing, XGBoost threshold (0.55), SHAP
methodology, risk configuration (weights 1.0/0.0), and API contract were
**not modified**. Two cosmetic/documentation fixes were made (see §12).

## 1. End-to-end consistency (Part A)

10 representative held-out test records (4 fraud, 6 legitimate, including a
near-threshold p=0.5772 row and the known false positive p=0.8111) were scored
three ways: direct artifact inference (preprocessor.joblib + xgboost.joblib +
shap.TreeExplainer), live `POST /api/v1/predict`, and the frontend display path
(`PredictionDetail`/`ShapChart` render the API response verbatim — verified by
code inspection; no transformation exists in that path).

**Tolerances (documented, not arbitrary):** the API rounds `fraud_probability`
to 4 decimals (`round(proba, 4)` in the route) and SHAP values to 5 decimals
(`round(v, 5)` in the explainer) — so max expected deltas are 5e-5 and 5e-6.

Result: **all 10 records match** — probability within 5e-5, prediction,
risk score, risk level, and threshold exact; top-10 SHAP feature names and
ordering identical; SHAP values within 5e-6; directions consistent.
(2 of 12 sampled rows had NaN ERC20 columns and were excluded — the backend
rejects NaN with 422 by design; see §6/§7.)

## 2. Threshold tests (Part B)

Operating rule `p >= 0.55 → FRAUD`, implemented as
`proba >= artifacts.threshold` (threshold 0.55 from `models/threshold_config.json`).

- Synthetic: 0.5499 → LEGITIMATE, 0.5500 → FRAUD, 0.5501 → FRAUD. ✔
- Real near-boundary rows through the live API: p=0.4646 → LEGITIMATE,
  p=0.5154 → LEGITIMATE, p=0.5724 → FRAUD, p=0.5772 → FRAUD. ✔
- Threshold **unchanged**.

## 3. Risk boundary tests (Part C)

Scores are integers (`int(round(100·p))`, clamped to [0,100]); levels from
`models/risk_config.json`: LOW ≤30, MEDIUM ≤70, HIGH ≥71.

| Input | Score | Level | Expected |
|---|---|---|---|
| 0 | 0 | LOW | LOW ✔ |
| 30 | 30 | LOW | LOW ✔ |
| 30.01 | 30 | LOW | LOW ✔ (int rounding) |
| 31 | 31 | MEDIUM | MEDIUM ✔ |
| 70 | 70 | MEDIUM | MEDIUM ✔ |
| 70.01 | 70 | MEDIUM | MEDIUM ✔ (int rounding) |
| 71 | 71 | HIGH | HIGH ✔ |
| 100 | 100 | HIGH | HIGH ✔ |

Out-of-range inputs clamp: p=−0.5 → 0, p=1.5 → 100, p=inf → 100. Scores never
leave [0,100]. ✔

## 4. Batch consistency (Part D)

25 random held-out rows scored individually via `/predict` and together via
`/predict/batch`: **all 25 match** (probability within 5e-5; prediction, risk
score, risk level exact; 0 errors). Batch summary counts consistent.

## 5. SHAP consistency (Part E)

Phase-5 recorded values vs live backend SHAP vs frontend display, on rows
1160 (fraud), 1416 (medium fraud), 498 (legitimate):

- Unique Received From Addresses +3.65245 ✔ (row 1160)
- Blockwell token one-hot +3.05115 ✔
- ERC20 min val rec +1.46359 ✔ (row 1416)
- Avg min between received tnx −1.80450 ✔ (row 498)

Feature names, values (within 5e-5), directions, and ordering all match. No
regeneration or retraining anywhere; frontend renders backend values verbatim
with model-contribution (non-causal) labeling.

## 6. Leakage audit (Part F)

- `POST /predict` with each of `FLAG`, `Address`, `Index`, `Unnamed: 0`,
  `label`, `target` → **422** in all six cases (`extra="forbid"`). ✔
- Batch CSV containing `FLAG` + `Address` → 200, extra columns ignored,
  predictions **bit-identical** to the same rows without those columns. ✔
- Frontend: `fields.ts` contains exactly the 39 features; banned names absent
  (asserted in vitest); the form cannot submit them. ✔

## 7. Security test results (Part G)

16/16 pass against the live backend:

- missing fields → 422 ✔ · invalid types → 422 ✔ · extra fields → 422 ✔
- NaN → 422 ✔ · Infinity → 422 ✔ · 1e308 → handled, no 500 ✔
- oversized JSON (1.2 MB > 1 MB limit) → 413 ✔
- oversized CSV (6.4 MB > 5 MB limit) → 413, server healthy afterwards ✔
- malformed CSV → 400 ✔ · wrong content type → 400 ✔
- malformed query param → 422 ✔ · `limit=10000` clamped, no 500 ✔
- unknown endpoint → 404 ✔ · wrong method → 405 ✔
- CORS: allow-list via `CORS_ORIGINS`; allowed origin receives
  `Access-Control-Allow-Origin`, disallowed origin does not; unset → no CORS
  headers (deny-by-default) ✔
- Error bodies: no stack traces, filesystem paths, env vars, Mongo credentials,
  or secrets (verified on 422/400/404/413 bodies) ✔

## 8. Database reliability (Part H)

- No `MONGO_URI` → `/health` reports `"database": "disabled"`; predictions
  return 200 and persist to the in-memory store. ✔
- Unreachable `MONGO_URI` → `"database": "degraded"`; prediction still 200 via
  in-memory fallback (graceful degradation as designed). ✔
- History retrieval (5/5 records), pagination (`limit=2`, most-recent-first),
  and `risk_level` filtering all work on the fallback store. ✔
- Stored documents contain no raw feature columns and no secrets. ✔
- **Limitation:** the `connected` (real MongoDB) path was not tested — no
  mongod/docker is available in this environment.

## 9. Frontend/backend integration (Part I)

- API URL comes only from `VITE_API_URL`; the single fallback
  (`http://127.0.0.1:8123`) is centralized in `src/config/index.ts` and
  documented as the dev default. No other hard-coded localhost in `src/`. ✔
- No mock/fake prediction logic in production code (`samples.ts` explicitly
  submits real rows to the real backend). ✔
- Loading states on all six pages; Dashboard has error + Retry and an empty
  state ("No predictions recorded yet"); backend-downtime handling was verified
  live in Phase 7. ✔
- Only browser-safe settings in frontend env (`.env.example` has just
  `VITE_API_URL`). ✔

## 10. Reproducibility audit (Part J)

- **Added `README.md` at the project root** — the single entry point a clean
  developer needs: quick start, pipeline overview, validated operating point,
  env vars, tests, layout, and the "never retrain casually" warning. This was
  the main gap (backend/frontend READMEs existed and are accurate).
- A new developer can follow: dataset prep → preprocessing → training →
  evaluation → artifact generation → backend setup → frontend setup → MongoDB
  config → env vars → tests → full run, from `README.md` + the two sub-READMEs.
- Fixed three documentation errors (no methodology rewritten):
  1. `reports/split_report.md`: "40 features" → **39 features**
  2. `docs/data_dictionary.md`: "Removed (10)" → **Removed (11)**
     (3 leakage/identifiers + 7 zero-variance + 1 unverifiable)
  3. `reports/phase2_report.md`: "7 EDA figures" → **6 EDA figures**

## 11. Complete test counts (Part K)

- Backend: **17/17 pytest pass** (`cd backend && TZ=UTC ../.venv/bin/python -m pytest tests/ -q`).
  Note: must run from `backend/` — tests use relative `../data/...` paths (documented in `backend/README.md`).
- Frontend: **24/24 vitest pass** (6 files).
- Frontend production build: **clean** (`tsc` + vite; title fix verified in `dist/index.html`).
- Clean-environment install: fresh dir, `npm ci` (133 packages, lockfile-respecting) →
  24/24 tests pass → production build succeeds. ✔
- Total: **41 automated tests, all passing.**

## 12. Bugs found and fixed

1. **Generic HTML title** (`<title>frontend</title>`) → "Blockchain Fraud Risk
   Analyzer". Cosmetic; verified in the production bundle.
2. **Three documentation errors** listed in §10 (feature count, removed-column
   count, EDA figure count).
3. **No functional bugs** found in the model, preprocessing, threshold, risk
   policy, SHAP methodology, or API contract — none were changed.

## 13. Remaining limitations

- No pixel screenshots were captured (same as Phase 7); verification is via
  component tests, build inspection, and live-server API checks.
- Real-MongoDB `connected` path untested here (no mongod/docker); degraded and
  disabled paths verified.
- Dashboard counts derive from up to 100 history records, not full-lifetime
  totals (existing design, unchanged).
- Backend pytest must run from `backend/` (relative test-data paths).
- Project is not under git version control.

## 14. Go / no-go recommendation

**GO for deployment**, with the limitations in §13 noted. The full chain —
artifacts → API → frontend — is numerically consistent within the API's
documented rounding, boundaries behave exactly as configured, leakage is
blocked at both layers, security responses are clean, the service degrades
gracefully without MongoDB, and 41/41 automated tests pass including a
clean-environment install. Nothing about the model, threshold, risk policy, or
SHAP methodology changed during this phase.
