# Phase 3 Report — Supervised Modeling (Baseline + ML)

**Date:** 2026-09-25 · **Seed:** 42 (all models) · **Status:** complete, stopped before Isolation Forest / risk scoring / SHAP / API / UI.

> Every number below was measured from the actual experiment. Nothing is estimated or fabricated.

## 1. Protocol

- **Train:** 6,889 rows (22.14% fraud) — model fitting only.
- **Validation:** 1,476 rows (22.15% fraud) — hyperparameter selection (grid search maximizing F1 @ 0.5) and threshold tuning (argmax F1 on threshold sweep 0.05–0.95, step 0.05).
- **Test:** 1,476 rows (22.15% fraud) — evaluated **exactly once** per final model configuration. Never used for selection or tuning.
- **Preprocessing:** Phase-2 pipeline unchanged (signed log1p on 36/37 numerics, StandardScaler, one-hot token types; fitted on train only). 39 inputs → 52 features. No SMOTE.
- **Class imbalance:** `class_weight="balanced"` (LogReg), `balanced`/`balanced_subsample` grid (RF), `scale_pos_weight=3.517` (XGB).
- Accuracy treated as secondary; selection driven by fraud-relevant metrics.

## 2. Models trained

| Model | Selected hyperparameters | Val F1@0.5 (selection) |
|---|---|---|
| Logistic Regression | C=10.0, solver=lbfgs, class_weight=balanced, max_iter=5000 | 0.7938 |
| Random Forest | n_estimators=300, max_depth=None, min_samples_split=5, min_samples_leaf=1, max_features=sqrt, class_weight=balanced | 0.9228 |
| XGBoost | n_estimators=400, max_depth=6, learning_rate=0.1, subsample=0.8, colsample_bytree=0.8, min_child_weight=1, reg_lambda=1.0, scale_pos_weight=3.517 | 0.9321 |

Grids were deliberately small (4 / 32 / 8 configs). RF note: constraining `max_depth` to 15 consistently hurt; `min_samples_split=5` edged out 2.

## 3. Threshold analysis (validation)

Criterion: **argmax F1** on the validation sweep. 0.5 was *not* assumed optimal.

| Model | Chosen thr | Val P / R / F1 at chosen thr | Val FP / FN | F1 @ 0.5 |
|---|---|---|---|---|
| Logistic Regression | **0.70** | 0.8576 / 0.8654 / 0.8615 | 47 / 44 | 0.7938 |
| Random Forest | **0.50** | 0.9132 / 0.9327 / 0.9228 | 29 / 22 | 0.9228 |
| XGBoost | **0.55** | 0.9497 / 0.9235 / 0.9364 | 16 / 25 | 0.9321 |

Trade-off snapshots (validation):

- **LogReg:** thr 0.3 → R=0.963, P=0.593 (216 FP, 12 FN); thr 0.8 → P=0.903, R=0.801 (28 FP, 65 FN). The balanced class weighting shifted the operating point well above 0.5.
- **RF:** thr 0.3 → R=0.972, P=0.783 (88 FP, 9 FN); thr 0.8 → P=0.984, R=0.743 (4 FP, 84 FN).
- **XGB:** remarkably flat — F1 0.928–0.936 across thr 0.3–0.8; chosen 0.55.

**FP vs FN in fraud terms:** a false negative is a missed fraud (direct loss, undetected scam); a false positive is a legitimate account flagged (frozen funds, support cost, user harm). Missing fraud is usually costlier, which argues for recall — but with a 22% base rate, collapsing precision floods reviewers. The F1 criterion balances both; the sweep tables above let a deployer re-pick the operating point once real FP/FN costs are known.

## 4. Final test results (each model evaluated once)

Test support: 1,149 legitimate / 327 fraud.

| Model | Precision | Recall | F1 | ROC-AUC | PR-AUC | Accuracy* | FP | FN | TP | TN | Thr |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Logistic Regression | 0.8959 | 0.8685 | 0.8820 | 0.9752 | 0.9418 | 0.9485 | 33 | 43 | 284 | 1116 | 0.70 |
| Random Forest | 0.9669 | 0.8930 | 0.9285 | 0.9908 | 0.9764 | 0.9695 | 10 | 35 | 292 | 1139 | 0.50 |
| XGBoost | **0.9801** | **0.9052** | **0.9412** | **0.9937** | **0.9848** | 0.9749 | **6** | **31** | 296 | 1143 | 0.55 |

\*Accuracy secondary only.

Per-class test metrics (derived from the confusion matrices):

| Model | Legit P / R / F1 | Fraud P / R / F1 |
|---|---|---|
| Logistic Regression | 0.9629 / 0.9713 / 0.9671 | 0.8959 / 0.8685 / 0.8820 |
| Random Forest | 0.9702 / 0.9913 / 0.9806 | 0.9669 / 0.8930 / 0.9285 |
| XGBoost | 0.9736 / 0.9948 / 0.9841 | 0.9801 / 0.9052 / 0.9412 |

Confusion matrices, ROC and PR curves: `reports/figures/fig_cm_*_test.png`, `fig_roc_comparison_test.png`, `fig_pr_comparison_test.png`.

## 5. Selected supervised model: **XGBoost**

Justification is on the fraud-detection objective, not accuracy:

1. **Fewest missed frauds:** recall 0.9052, FN=31 — vs 35 (RF) and 43 (LogReg). Every additional caught fraud is the point of the system.
2. **Fewest false alarms:** precision 0.9801, FP=6 on 1,149 legitimate accounts — the lowest reviewer burden of the three.
3. **Best ranking quality:** PR-AUC 0.9848 and ROC-AUC 0.9937 — the strongest separation of fraud from legitimate across all thresholds, which matters because the operating threshold may be re-tuned later against real costs.
4. **Best balance:** F1 0.9412, the highest harmonic mean of the two error types above.

Random Forest is a close second and the honest fallback: nearly identical performance, simpler to explain, less tuning surface, and natively robust. Logistic Regression is the weakest classifier but the most interpretable baseline and the cheapest to serve.

## 6. Feature importance

- **LogReg (|coefficient|, standardized features):** `ERC20_most_rec_token_type_Blockwell say NOTSAFU` (6.65), `total transactions (incl. contract creation)` (5.59), `ERC20 total Ether received` (4.38), `ERC20 max val rec` (3.33), `avg val received` (3.19). Token-type features dominate — consistent with the Phase-2 EDA finding that fraud accounts are disproportionately ERC20-active.
- **RF (impurity):** `Time Diff between first and last (Mins)` (0.099), `avg val received` (0.091), `total ether received` (0.073), `Avg min between received tnx` (0.063), `Unique Received From Addresses` (0.057) — the "short-lived burner account" signature from EDA.
- **XGB (gain):** `..._Blockwell say NOTSAFU` (81.8), `total ether received` (31.2), `ERC20 min val rec` (16.1), `Unique Received From Addresses` (15.2), `..._OmiseGO` (12.8).

Caveats: impurity importance is biased toward high-cardinality features; LogReg coefficients are only comparable because features were standardized, and multicollinearity (correlated transaction-count / ERC20-value blocks found in Phase 2) spreads weight across correlated features — L2 regularization keeps this stable for prediction but individual coefficients should not be read as causal effects. SHAP (later phase) will give cleaner attributions.

## 7. Ablation: do trees need the log/scale transform?

Controlled side experiment (validation only, not used for selection): RandomForest with identical hyperparameters (300 trees, `balanced_subsample`) trained on **raw** features (imputation + one-hot only, no log1p, no scaling) vs the **transformed** Phase-2 features.

| Representation | Val F1@0.5 | Val PR-AUC | Val ROC-AUC |
|---|---|---|---|
| Raw (no log/scale) | 0.9024 | 0.9745 | 0.9898 |
| Transformed (log+scale) | 0.8935 | 0.9737 | 0.9898 |

No meaningful benefit — as expected, tree splits are invariant to monotonic transforms. The shared pipeline is therefore harmless but unnecessary for RF/XGBoost; the main comparison was kept on identical features for reproducibility, and this ablation is documented separately without contaminating the evaluation.

## 8. Limitations

- **Single validation split**, not k-fold: hyperparameter and threshold choices carry split noise. Mitigated by the large validation set (1,476 rows) but CIs would be tighter under repeated CV.
- **Threshold criterion is a placeholder for cost:** argmax F1 assumes equal FP/FN cost, which is not true in fraud. Real deployment needs cost-weighted thresholding.
- **Recall ceiling ~0.90:** even the best model misses ~1 in 11 frauds (31/327). The remaining frauds likely need graph/network features (planned GNN extension), not more tuning of aggregates.
- **Label semantics:** `FLAG` mixes confirmed and *suspected* fraud; "false positives" may include undetected fraud — precision is a lower bound on true precision.
- **Duplicate addresses (50 rows, 25 addresses)** were kept in-split per the group-aware design; their influence is small but nonzero.
- **Interpretability:** impurity/gain importances are model-specific heuristics; proper explanations await the SHAP phase.

## 9. Unexpected findings

1. **LogReg's optimal threshold was 0.70, not 0.5** — balanced class weighting shifted the operating point substantially. Assuming 0.5 would have cost ~7 F1 points (0.794 → 0.862).
2. **RF's optimal threshold was exactly 0.50** — the default happened to be right, verified rather than assumed.
3. **XGBoost is nearly threshold-insensitive** (F1 0.928–0.936 for thr 0.3–0.8) — unusually stable operating characteristics.
4. **The log/scale pipeline adds nothing for trees** (ablation §7) — the Phase-2 transform was designed for the linear baseline; trees don't need it.
5. **Unconstrained RF depth won** — `max_depth=None` beat `max_depth=15` across the grid; with 300 bagged trees, variance was controlled without depth limits.
6. **A token literally named "Blockwell say NOTSAFU" is the single strongest signal** for both LogReg and XGBoost — token-identity features carry outsized weight, worth a data-quality review before any production use (is it signal or a labeling artifact of the source dataset?).

## 10. Artifacts

- `models/logistic_regression.joblib`, `models/random_forest.joblib`, `models/xgboost.joblib` (all reload-tested)
- `models/model_metadata.json` — hyperparameters, thresholds, val/test metrics, training config, seeds, versions
- `models/threshold_config.json` — chosen validation thresholds and criterion
- `reports/model_comparison.csv`, `reports/threshold_sweep_{lr,rf,xgb}.csv`
- `reports/feature_importance_{lr,rf,xgb}.csv`
- `reports/figures/fig_cm_*_test.png`, `fig_roc_comparison_test.png`, `fig_pr_comparison_test.png`, `fig_threshold_*_val.png`, `fig_importance_*.png`
- Driver: `notebooks/03_supervised.py`; shared utils: `src/models/training.py`

**STOP.** Isolation Forest, risk scoring, SHAP, FastAPI, React, and deployment are not started.
