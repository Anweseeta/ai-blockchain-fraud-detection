# Phase 1 Findings — Dataset Inspection (2026-09-25)

## Dataset at a glance
- File: `data/raw/transaction_dataset.csv` (inside `transaction_dataset.csv.zip`)
- **9,841 rows × 51 columns**, account-level Ethereum behavioral aggregates (~5.7 MB)
- Target: `FLAG` ∈ {0,1} — 7,662 legit (77.9%) vs 2,179 fraud (22.1%), imbalance **1 : 3.5**
- No fully-duplicated rows; 25 addresses appear twice (labels consistent — rows kept)
- Zero missing values outside the ERC20 block; 829 rows (8.4%) have no ERC20 activity at all

## Critical finding: label-sorted leakage
The dataset was exported sorted by label. Two columns encode this order and must be dropped:
- `Unnamed: 0` (pandas index artifact): r = **0.72** with FLAG; first 4,920 rows are 100% legit
- `Index`: r = −0.32 with FLAG (fraud concentrates at low Index values)

If kept, any model would learn row order instead of fraud behavior. Both are removed before any
preprocessing. `Address` is removed as a unique identifier. This is the project's headline
leakage case — worth a paragraph in the report's methodology section.

## Data quality notes
- ERC20 numerics missing in exactly the same 829 rows = "no token activity" → impute with 0,
  not drop (dropping would bias the sample against non-token users).
- Token-type columns (` ERC20 most sent token type`, ` ERC20_most_rec_token_type`): messy
  encoding — `'0'`, `' '`, NaN all mean "none/unknown"; NaN rate differs by class (38% fraud vs
  24% legit), so impute as the `'none'` category rather than dropping.
- 7 ERC20 timing/value-contract columns are constant 0 → dropped (zero variance).
- ` ERC20 uniq sent addr.1`: meaning unverifiable from data, near-constant → dropped.
- `total ether balance` can be strongly negative (min −15.6M): source-scrape accounting artifact,
  not invalid data. Keep, document.
- Counts are capped at 10,000 in the source (max 10,000 on several count columns) — mild
  ceiling effect, acceptable.
- Heavy right tails on value/time columns (e.g. avg minutes between txns, ETH amounts) — log1p
  transform justified for distance/linear models; tree models can use raw values.

## Recommended preprocessing strategy
1. Drop the 10 identified columns (3 leaky/identifier, 7 zero-variance/unverifiable).
2. **Split first**: stratified 70/15/15 train/validation/test. No timestamps exist (only relative
   minutes), so a time-aware split is not applicable — random stratified split is correct.
   Group-aware note: 25 addresses appear twice; ideally keep both rows of an address in the
   same split to avoid a tiny leakage path.
3. Fit imputers/encoders/scalers **only on train** via sklearn Pipeline/ColumnTransformer:
   - ERC20 numerics: NaN → 0
   - Token-type: `'0'`/`' '`/NaN → `'none'`, then top-k one-hot or target encoding (train-only fit)
   - Amount/time numerics: log1p + StandardScaler for LogReg/distances; raw for trees
4. Imbalance 1:3.5 is moderate: start with `class_weight` and threshold tuning; try SMOTE
   (train-only) as a comparison point, not the default.
5. Never fit anything on the full dataset before splitting.

## Recommended experimental strategy
- Baselines: Logistic Regression (log1p-scaled) → Random Forest (class_weight) → XGBoost
  (scale_pos_weight) — compare precision/recall/F1/PR-AUC, not accuracy alone.
- Threshold: sweep 0.1–0.9 on validation; report F1-optimal and recall-oriented operating points.
- Calibration: check calibration curve + Brier score on the selected classifier.
- Isolation Forest: fit on train features (no labels), contamination ≈ observed fraud rate
  (~0.22) as starting point; evaluate anomaly-score distribution by class — ANOMALY ≠ FRAUD.
- Risk engine: `risk = w1·P(fraud) + w2·norm(anomaly) + w3·behavioral`, 0–100 normalized,
  configurable thresholds (LOW/MED/HIGH), sensitivity analysis over weights.
- SHAP on the selected tree model for global + local explanations.
- Ablation: feature groups = base activity | value profile | temporal | contract | ERC20 token.
- Test set stays locked until final evaluation.

## Decisions needing no further debate
- Do not engineer absolute-time features: the file has no timestamps, only relative minutes.
- Do not one-hot 304/466 raw token names directly: rare-binning or target encoding.
- `Time Diff between first and last (Mins)` stays: short-lived accounts are genuine fraud
  behavior (burner accounts), not leakage — document the interpretation.

## Open questions for the report
- `FLAG` semantics beyond "fraud/suspicious" cannot be verified — no dataset documentation was
  shipped with the file. State this explicitly in the report.
- Whether contract-value columns (near-zero variance) survive ablation — test, don't assume.
