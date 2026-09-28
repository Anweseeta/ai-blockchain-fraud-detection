# Phase 5 Report — SHAP Explainability

**Date:** 2026-09-25 · **Model:** validated Phase-3 XGBoost (not retrained) · **Status:** complete, stopped before API/frontend.

> Wording discipline throughout: SHAP reports **association with model output**, never
> causation. "Proves fraud" appears nowhere in this report.

## Part A — Setup

- Explainer: `shap.TreeExplainer`, tree_path_dependent, model_output="raw" — the exact,
  supported path (interventional/probability mode is blocked by a shap-0.52/xgboost-3.x
  incompatibility; documented in `docs/methodology/explainability.md`).
- SHAP values are in **log-odds units**: Σ SHAP + base = model margin, sigmoid(margin) =
  fraud probability. Sign = direction of effect.
- Background data: none required. Explained: **1,476 test records × 52 features in 1.1 s**.
- Additivity verified: max abs error 0.037 log-odds units. Base value 0.6467.
- Isolation Forest signal excluded from explanations per the operating risk policy.
- Metadata for backend reuse: `reports/shap/shap_metadata.json`.

## Part B — Global explainability

Top 10 by mean |SHAP| (log-odds units), with direction as Spearman(feature value, SHAP):

| Rank | Feature | mean\|SHAP\| | Direction (association) |
|---|---|---|---|
| 1 | Unique Received From Addresses | 1.4106 | higher values → higher fraud output (+0.88) |
| 2 | Time Diff between first and last (Mins) | 1.2232 | shorter lifespan → higher fraud output (−0.46) |
| 3 | total ether received | 1.1032 | lower received value → higher fraud output (−0.91) |
| 4 | avg val received | 0.9547 | lower avg value → higher fraud output (−0.82) |
| 5 | Avg min between received tnx | 0.7808 | more frequent receives → higher fraud output (−0.82) |
| 6 | ERC20_most_rec_token_type_Blockwell say NOTSAFU | 0.6473 | presence → higher fraud output (+0.47) |
| 7 | total ether balance | 0.6376 | weak positive association (+0.13) |
| 8 | total transactions (incl. contract) | 0.6250 | fewer transactions → higher fraud output (−0.83) |
| 9 | Avg min between sent tnx | 0.5720 | longer gaps between sends → higher fraud output (+0.63) |
| 10 | min val sent | 0.5186 | higher minimum sent → higher fraud output (+0.60) |

**Which features contribute most strongly to fraud predictions?** Counterparty breadth
(#1), account lifespan (#2), and received-value features (#3, #4) dominate. The learned
profile is coherent with the Phase-2 EDA: many distinct senders, short-lived accounts,
low/frequent receives, few transactions. These are **associations the model learned**,
not causal claims about fraud.

Plots: `reports/shap/shap_summary.png` (beeswarm), `reports/shap/shap_bar.png`.
Table: `reports/shap/global_feature_importance.csv` (all 52).

## Part C — Local explainability (test set, operating threshold 0.55)

**1. High-risk correctly classified fraud** — row 1160, FLAG=1, p=1.0000, risk 100 HIGH.
Top contributors (all increase risk): Unique Received From Addresses=26 (+3.65),
Blockwell token present (+3.05), total ether balance=0.00086 (+1.46),
ERC20 min val rec=1.337 (+1.20), min val sent=30.23 (+1.14). No offsetting factors —
unanimous fraud signal.

**2. Medium-risk correctly classified fraud** — row 1416, FLAG=1, p=0.5772, risk 58 MEDIUM.
Contested: ERC20 min val rec=99 (+1.46) and total ether received=1.34 (+0.73) push toward
fraud, while only 2 unique senders (−1.27), min val sent=0.001 (−0.93), and infrequent
receives (−0.72) pull away. Positive and negative forces nearly balance — hence p≈0.58.

**3. Low-risk correctly classified legitimate** — row 498, FLAG=0, p=0.0000, risk 0 LOW.
All top factors decrease risk: 1 unique sender (−2.25), 19,070 min between receives
(−1.80), 534,050-min lifespan (−1.51), 64.36 ETH received (−1.28). Textbook established
account.

**4. High-risk false positive** — row 1148, FLAG=0, p=0.8111, risk 81 HIGH. 5 unique
senders (+1.22), 32,811-min lifespan (+0.66), ERC20 max val rec=3046 (+0.62) push toward
fraud; min val sent=0 (−0.78) and 14 sent tnx (−0.69) pull back. Net: the model finds
this record fraud-like. (Prediction ≠ proof of fraud — the label says legitimate.)

**5. False negative** — row 1414, FLAG=1, p=0.5114, risk 51 MEDIUM. Fraud signals (5
unique senders +2.01, short-ish 2,966-min lifespan +1.01) are outweighed by
"established account" features (min val sent=0.0016 −1.13, sent-tnx pacing −1.06).
Misses the 0.55 threshold by 0.04.

Per-record tables: `reports/shap/local_explanations.csv`; JSON: `local_examples.json`;
waterfall plots: `waterfall_<case>.png` (5).

## Part F — Error analysis

- **False positives (n=6):** top-10 features overlap **7/10** with correctly-classified
  frauds. No distinct "FP signature" — FPs are driven by the same features as true
  frauds (unique senders, lifespan, balances). They are fraud-profile accounts that carry
  legitimate labels; with n=6, no stronger conclusion is warranted (label noise in
  "suspected fraud" labels cannot be ruled out).
- **False negatives (n=31):** top-10 overlap **9/10** with correctly-classified
  **legitimate** accounts. Recurring pattern: missed frauds are pulled below threshold by
  the "established account" features — longer lifespans, higher received values, steadier
  pacing. In other words, the model misses frauds that **don't fit the burner stereotype**,
  consistent with the Phase-3 recall-ceiling finding (~1 in 11 frauds missed).
- Tables: `false_positive_explanations.csv`, `false_negative_explanations.csv`
  (+ `correct_fraud/correct_legit_explanations.csv` for comparison).

## Part G — Blockwell feature

Global SHAP rank **6/52** (mean|SHAP|=0.647); rank 2 among correctly-classified frauds
(1.609); presence associated with higher model output (+0.47). Phase-4 ablation:
removing it changed F1 0.9412 → 0.9377 with PR-AUC essentially unchanged (0.9848 →
0.9852) — hence retained. It is a strong **associative** signal in this dataset, **not**
a proven causal fraud indicator.

## Part H — Artifacts

`reports/shap/`: `global_feature_importance.csv`, `local_explanations.csv`,
`local_examples.json`, `false_positive_explanations.csv`,
`false_negative_explanations.csv`, `correct_fraud/correct_legit_explanations.csv`,
`shap_summary.png`, `shap_bar.png`, `shap_metadata.json`, 5 waterfall plots.
Copies of key figures also in `reports/figures/`.

## Limitations

1. SHAP explains the **model**, including its mistakes — a large SHAP value on a false
   positive does not make the record fraudulent.
2. Correlated feature blocks (counts, ERC20 values) share credit; small rank differences
   between correlated features should not be over-interpreted.
3. Tree-path-dependent computation assumes feature independence; heavy correlation can
   leak attribution between correlated features.
4. Log-odds units: sign gives direction, magnitudes are comparable across features, but
   values are not probabilities.
5. FP analysis is limited by n=6.

**STOP.** The primary XGBoost model was not changed based on these findings. No API,
no frontend, no retraining.
