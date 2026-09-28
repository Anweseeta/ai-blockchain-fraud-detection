# Phase 2 report — preprocessing + EDA (2026-09-25)

No model training was performed. All analysis below uses the **training split only**
(n=6,889), except the final transform-shape verification.

## Preprocessing decisions (summary)

Full per-decision record: `docs/methodology/preprocessing_decisions.md`. Implementation:
`src/preprocessing/pipeline.py`; driver: `notebooks/02_preprocess_eda.py`.

| # | Decision | Key point |
|---|----------|-----------|
| D1 | ERC20 NaN → 0 | Assumption **verified on train first**: identical 574-row missing set across all 15 ERC20 numeric cols; all 574 also lack token type; observed `Total ERC20 tnxs==0` rows all carry token type `'0'` |
| D2 | Token types → `none` + one-hot (infrequent grouping, min_frequency=0.01) | Missingness is class-informative (NaN 38% fraud vs 24% legit), kept as explicit `none` category |
| D3 | Other numerics → median impute | Safety net; zero missing observed |
| D4 | Signed log1p on 36/37 numerics (\|skew\|>2, train-fit) | Handles 6–12 order-of-magnitude tails; signed form keeps negative `total ether balance` valid; monotonic so trees unaffected |
| D5 | StandardScaler on all numerics | For the LogReg baseline; single artifact for all model families |
| D6 | No SMOTE yet | Deferred to modeling-phase comparison (class weights / threshold first) |
| D7 | Address / Unnamed: 0 / Index excluded | Grouping-only / leakage / identifier |
| D8 | Artifact portability | `models/preprocessor.joblib` pickles as `src.preprocessing.pipeline.*`; fresh-interpreter load + inference smoke test passed |
| D9 | EDA on train only | Test set untouched |

## Final feature list

- **Input:** 39 features = 37 numeric (15 ERC20 + 22 base) + 2 categorical
  (most-sent / most-received token type). See `data/processed/split_metadata.json`.
- **Output:** 52 columns = 37 scaled numerics + 15 one-hot
  (per token column: frequent tokens such as EOS, Golem, OmiseGO + `none` + `infrequent_sklearn`).
  See `data/processed/processed_metadata.json`.
- **Transformed shapes:** train (6889, 52), val (1476, 52), test (1476, 52). Zero NaNs in all splits.

## EDA findings (train split)

**Target:** 22.14% fraud — moderate imbalance (1:3.5). Accuracy alone will be misleading;
precision/recall/F1/PR-AUC are the operative metrics.

**Strongest linear signals (|pearson r| with FLAG):** all weak (≤ 0.27) — no single
dominant feature; the model will need interactions.
1. `Time Diff between first and last (Mins)` −0.27 — fraud accounts are short-lived
2. `Avg min between received tnx` −0.12
3. `total transactions` −0.10, `Received Tnx` −0.08, `Sent tnx` −0.08

**Blockchain behavioral patterns (class medians, legit vs fraud):**
- Activity span: 119,900 min vs **6,661 min** — fraud looks like burner accounts
- Sent txns: 3 vs 1; received: 5 vs 3; total ETH sent: 33.0 vs 0.99; received: 71.4 vs 1.63
- Contract creation: 15.8% of legit vs 8.6% of fraud created ≥1 contract
- **ERC20 participation is inverted:** 62.4% of fraud vs 42.7% of legit touched tokens —
  token activity is a fraud-associated behavior here, worth calling out in the report
- Median time between sent txns: 22.3 min (legit) vs 0 (fraud — many fraud accounts sent ≤1 txn)

**Outliers:** IQR-outlier fractions up to 31% (`total ether balance`, ERC20 value cols).
Per the brief these are *not* removed — in fraud data, extremes may be the signal.

**Correlation structure (modeling-relevant):**
- Activity counts (`Sent tnx`, `Received Tnx`, total txns, unique counterparties) are
  mutually correlated — multicollinearity to watch for Logistic Regression.
- ERC20 sent-value block (`min/avg/max val sent`, `total ether sent`) is nearly
  perfectly intercorrelated — redundant features; candidate for selection/ablation later.
- `total ether balance` negatives (min −15.6M) confirmed as source accounting artifact.

**Categorical:** after cleaning, `none` dominates both token-type columns; top real tokens
are EOS, Golem, OmiseGO, Livepeer, DATAcoin, XENON — one-hot captured the head of each.

## Potential modeling considerations

1. LogReg baseline will need the scaled features (have them) and may suffer from the
   correlated count/value blocks — consider L1 or feature selection as a follow-up.
2. Trees (RF/XGBoost) can consume the same artifact directly.
3. Start imbalance handling with `class_weight`/`scale_pos_weight` + threshold sweep on
   validation; SMOTE only as a labeled comparison.
4. Isolation Forest contamination starting point ≈ 0.22 (observed fraud rate).
5. Feature-group ablation candidates: base activity | value profile | temporal |
   contract | ERC20 token behavior.

## Issues discovered

1. **pandas 3.0 `str` dtype:** string columns infer as `str`, not `object` — the
   categorical detector initially missed both token columns (fixed in
   `split_feature_groups`; documented so future code doesn't repeat it).
2. **Feature count correction:** 39 input features (37+2), not 40 as stated in Phase 1 —
   recount confirmed 39; dictionary and memory corrected.
3. `Total ERC20 tnxs` was initially bucketed as non-ERC20 (name starts with "Total") and
   would have received median imputation — caught by the missingness check (d), fixed by
   matching `"erc20" in name.lower()`.
4. Custom transformers needed `get_feature_names_out` + `set_output(transform="pandas")`
   for the ColumnTransformer to emit named features; artifact import path fixed to
   `src.preprocessing.pipeline` for backend portability.

## Artifacts

- `models/preprocessor.joblib` — fitted pipeline (train only)
- `data/processed/{train,val,test}_processed.npz` — transformed arrays
- `data/processed/processed_metadata.json`, `split_metadata.json`
- `reports/figures/` — 6 EDA figures; `reports/eda_corr_with_flag.csv`,
  `reports/eda_class_medians.csv`, `reports/eda_blockchain_patterns.json`
