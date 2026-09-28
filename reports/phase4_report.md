# Phase 4 Report — Anomaly Detection + Risk Scoring

**Date:** 2026-09-25 · **Seed:** 42 · **Status:** complete, stopped before SHAP / FastAPI / React / deployment.

> Every number below was measured from actual experiments. The headline result of this phase is a negative one, reported honestly: **the Isolation Forest anomaly signal does not track fraud on these aggregate features, and blending it into the risk score hurts.** The risk engine's operating policy was set from that evidence.

## Part A — Isolation Forest

**Why Isolation Forest:** unsupervised (never sees `FLAG`), no distributional assumptions, scales to 6,889×52, and in principle complements a supervised classifier by flagging records that are *unusual* whether or not they resemble known fraud. Fitted on the **train split only**.

**Configuration search (validation):**

| contamination | val F1 (flag) | val PR-AUC | flagged | fraud among flagged |
|---|---|---|---|---|
| 0.05 | 0.0342 | 0.2000 | 82 (5.6%) | 0.085 |
| 0.10 | 0.0765 | 0.2000 | 170 (11.5%) | 0.112 |
| 0.15 | 0.1034 | 0.2000 | 253 (17.1%) | 0.119 |
| 0.22 | 0.1123 | 0.2000 | 350 (23.7%) | 0.109 |
| 0.30 | **0.1379** | 0.2000 | 456 (30.9%) | 0.118 |

`n_estimators` / `max_samples` check at contamination 0.30 (val PR-AUC): (100, auto)=0.2139, (200, auto)=0.2000, (300, auto)=0.2105, **(200, 0.5)=0.2173** ← selected.

**Selected:** `n_estimators=200, max_samples=0.5, contamination=0.30, random_state=42`. Contamination was chosen by max validation F1 of the induced flag — it is an **operating assumption about review capacity, not an estimate of fraud prevalence** (fraud rate is 22.1%; copying it would conflate anomaly with fraud). The honest caveat: even the winning F1 (0.138) is poor — no contamination makes this a fraud detector (see Part B).

**Score normalization (documented):** `raw = −score_samples` (higher = more anomalous) → `normalized = clip((raw − train_min)/(train_max − train_min), 0, 1)` using **train** min/max only. Flag threshold = (1 − contamination) quantile of train raw scores → normalized operating threshold **0.1585**. Saved: `models/isolation_forest.joblib`, `models/anomaly_metadata.json`.

## Part B — Anomaly evaluation: ANOMALY ≠ FRAUD

| Split | PR-AUC (baseline 0.2215) | ROC-AUC | P / R / F1 @ flag | FP | FN | flagged |
|---|---|---|---|---|---|---|
| val | 0.2173 (**below no-skill**) | 0.5270 | 0.1842 / 0.2569 / 0.2146 | 372 | 243 | 456 |
| test | 0.2214 (≈ baseline) | 0.5447 | 0.2137 / 0.3242 / 0.2576 | 390 | 221 | 496 (33.6%) |

- Mean normalized anomaly score: fraud **0.135** vs legit **0.149** (test) — labeled frauds are on average *less* anomalous than legitimate accounts.
- Fraud among flagged: 106/496 = **0.214, below the 0.2215 base rate**. Flagging "anomalies" anti-selects for fraud.
- Spearman(anomaly score, XGBoost fraud probability): 0.085 val / **0.072 test** — near-independent signals.
- Top-decile overlap: P(both top deciles) = 0.002; P(fraud | top-decile anomaly) = **0.128** (test).

**Interpretation:** on these account-aggregate features, frauds are not statistical outliers — they are short-lived, low-value burner accounts, a dense and common-looking region of feature space. The IF flag instead fires on heavy-tailed legitimate behavior (whales, high-activity accounts). This is precisely why **anomaly ≠ fraud**: "unusual" and "fraudulent" are different concepts, and here they barely overlap. Distributions: `reports/figures/fig_anomaly_distribution.png`; per-record data: `reports/anomaly_analysis.csv`.

## Part C — Blockwell token ablation (data-quality investigation)

Question: does XGBoost depend heavily on ` ERC20_most_rec_token_type_Blockwell say NOTSAFU`? Method: removed exactly that one-hot column (index 43), retrained XGBoost with **identical hyperparameters and the identical train/val/test protocol** (threshold re-selected on validation by argmax F1; test evaluated once). Main model untouched.

| Model | thr | Precision | Recall | F1 | ROC-AUC | PR-AUC | FP | FN |
|---|---|---|---|---|---|---|---|---|
| Full (52f) | 0.55 | 0.9801 | 0.9052 | 0.9412 | 0.9937 | 0.9848 | 6 | 31 |
| No-Blockwell (51f) | 0.40 | 0.9556 | 0.9205 | 0.9377 | 0.9939 | 0.9852 | 14 | 26 |
| Δ | | −0.0245 | +0.0153 | **−0.0035** | +0.0002 | +0.0004 | +8 | −5 |

**Finding:** performance does **not** depend heavily on the suspicious feature. F1 moves −0.0035; ranking metrics (ROC-AUC, PR-AUC) are unchanged-to-slightly-better without it. The feature buys precision (6 vs 14 FP) at some recall cost (31 vs 26 FN) — a useful signal, not a leakage crutch; other features compensate fully in its absence. **Decision: keep the feature in the main model; no silent removal.** Ablated model saved as `models/xgboost_ablated_blockwell.joblib` (experiment artifact); results in `reports/feature_ablation.csv`.

## Part D — Risk scoring engine

**Formula** (`src/risk/scoring.py`, config-driven via `models/risk_config.json`):

```
risk_score = 100 × (w_fraud × fraud_probability + w_anomaly × anomaly_score)
```

Both inputs in [0,1]; weights sum to 1. Weights are a **project-defined operating policy, not universal fraud standards**.

**Weight selection — evidence over prior:** the a priori default was (0.7, 0.3), but validation sensitivity analysis showed monotone degradation as anomaly weight increased:

| w_fraud / w_anomaly | val risk PR-AUC | HIGH P / R / F1 |
|---|---|---|
| 1.0 / 0.0 | **0.9825** | 0.9641 / 0.9021 / **0.9321** |
| 0.8 / 0.2 | 0.9638 | 0.9731 / 0.8838 / 0.9263 |
| 0.7 / 0.3 | 0.9603 | 0.9887 / 0.8043 / 0.8870 |
| 0.6 / 0.4 | 0.9557 | 0.9630 / 0.0795 / 0.1469 |
| 0.5 / 0.5 | 0.9501 | 1.0000 / 0.0459 / 0.0877 |

**Operating policy set to (1.0, 0.0)** — the anomaly input stays plumbed in the formula for future representations (e.g., graph-based anomaly features), but its operating weight is 0 until an anomaly signal that actually tracks fraud is found.

**No additional behavioral signals** were added: raw behaviors (time span, values, counts) are already inside the XGBoost probability — adding them again would double-count. Only data-justified inputs allowed.

## Part E — Risk categories (operational project thresholds, not universal standards)

0–30 → LOW, 31–70 → MEDIUM, 71–100 → HIGH. Configurable in `risk_config.json`. These cutoffs are policy round numbers, **not** data-optimized.

## Part F — Risk-system evaluation (test, once)

Final operating config (1.0, 0.0):

| Bucket | n (% of test) | fraud rate |
|---|---|---|
| LOW | ~1157 (78.4%) | 0.019 |
| MEDIUM | ~24 (1.6%) | 0.583 |
| HIGH | ~295 (20.0%) | **0.986** |

HIGH as fraud-positive: **P=0.9864, R=0.8899, F1=0.9357, FP=4, FN=36**. Risk PR-AUC = 0.9848.

**XGBoost-only vs combined** (test, diagnostic — selection was made on validation):

| Weights | risk PR-AUC | HIGH P / R / F1 | FP / FN | % HIGH |
|---|---|---|---|---|
| (1.0, 0.0) XGB-only | **0.9848** | 0.9864 / 0.8899 / **0.9357** | 4 / 36 | 20.0% |
| (0.7, 0.3) combined | 0.9735 | 1.0000 / 0.8073 / 0.8934 | 0 / 63 | 17.9% |

**Answer to the phase's key question:** anomaly information does **not** add useful signal beyond the supervised fraud probability — it degrades ranking (0.9848 → 0.9735) and HIGH-bucket F1 (0.9357 → 0.8934). Nuance: the (0.7, 0.3) HIGH bucket is perfectly pure (0 FP) — blending creates an ultra-conservative tier — but it misses nearly twice as many frauds (63 vs 36). Per-record data: `reports/risk_analysis.csv`.

## Part G — Output schema (real values)

Highest-risk test record under the operating config:

```json
{"fraud_probability": 0.9996, "anomaly_score": 0.1259, "risk_score": 100, "risk_level": "HIGH"}
```

Note the illustration: risk 100 with anomaly score only 0.126 — the record is a certain fraud that is *not* anomalous. Anomaly ≠ fraud, in one record.

## Part H — Artifacts

- `models/isolation_forest.joblib`, `models/anomaly_metadata.json`, `models/risk_config.json`
- `models/xgboost_ablated_blockwell.joblib` (ablation experiment artifact)
- `reports/anomaly_analysis.csv`, `reports/risk_analysis.csv`, `reports/feature_ablation.csv`
- `reports/risk_weight_sensitivity_val.csv`, `reports/risk_weight_sensitivity_test.csv`, `reports/risk_example.json`
- Figures: `fig_anomaly_distribution.png`, `fig_risk_buckets_test.png`, `fig_risk_weight_sensitivity.png`
- Code: `notebooks/04_anomaly_risk.py`, `src/risk/scoring.py`

## Part I — Documentation notes

- **Thresholds:** anomaly flag threshold from contamination (train quantile, 0.1585 normalized); risk bucket cutoffs 30/70 are policy, not tuned.
- **Limitations:** (1) IF on aggregate features cannot see network structure — the natural next anomaly representation is graph-based. (2) Single validation split; contamination grid coarse. (3) Min/max normalization is sensitive to extreme train points (mitigated by clipping). (4) With w_anomaly=0 the "combined" system is currently XGBoost-only; the anomaly path is retained as infrastructure. (5) FLAG mixes confirmed and suspected fraud — precision figures are lower bounds. (6) The contamination=0.30 selection is criterion-mechanical; it is documented, not endorsed as a fraud operating point.
- **Why anomaly ≠ fraud:** fraud here is a *labeled* minority occupying dense, ordinary-looking regions (burner accounts); anomaly measures *statistical unusualness*, which here points at legitimate heavy-tailed behavior. The two concepts are orthogonal in this feature space (Spearman 0.07).

**STOP.** SHAP, FastAPI, React, and deployment are not started.
