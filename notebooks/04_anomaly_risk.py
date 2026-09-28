"""Phase 4 — unsupervised anomaly detection (Isolation Forest) + risk scoring.

Protocol:
- IsolationForest fitted on TRAIN ONLY, never sees FLAG.
- Validation: operating-configuration selection (contamination etc.).
- Test: evaluated once at the end.
- Part C: controlled ablation of the suspicious Blockwell token feature
  (train/val/test protocol, test evaluated once, main model untouched).
- Parts D-F: transparent 0-100 risk engine, weights chosen on validation,
  final evaluation on test once.
"""
import json
import os
import sys
from datetime import datetime, timezone

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import IsolationForest
from sklearn.metrics import average_precision_score, roc_auc_score
from xgboost import XGBClassifier

ROOT = "/home/hatch/workspace/ai-blockchain-fraud-detection"
sys.path.insert(0, ROOT)
from src.models.training import classification_report_dict, metrics_at_threshold, threshold_sweep
from src.risk.scoring import compute_risk_score, risk_level, score_record

SEED = 42
PROC = f"{ROOT}/data/processed"
FIG = f"{ROOT}/reports/figures"
MODELS = f"{ROOT}/models"

train = np.load(f"{PROC}/train_processed.npz")
val = np.load(f"{PROC}/val_processed.npz")
test = np.load(f"{PROC}/test_processed.npz")
X_train, y_train = train["X"], train["y"]
X_val, y_val = val["X"], val["y"]
X_test, y_test = test["X"], test["y"]
FEATS = json.load(open(f"{PROC}/processed_metadata.json"))["output_features"]
xgb = joblib.load(f"{MODELS}/xgboost.joblib")
p_val_xgb = xgb.predict_proba(X_val)[:, 1]
p_test_xgb = xgb.predict_proba(X_test)[:, 1]

SUSPICIOUS = " ERC20_most_rec_token_type_Blockwell say NOTSAFU"
SUSPICIOUS_IDX = FEATS.index(SUSPICIOUS)
print(f"suspicious feature index: {SUSPICIOUS_IDX}")


# ============================ Part A: Isolation Forest ============================
def norm_scores(iforest, X, lo, hi):
    raw = -iforest.score_samples(X)  # higher = more anomalous
    return np.clip((raw - lo) / (hi - lo + 1e-12), 0, 1), raw


print("\n=== Part A: contamination investigation (n_estimators=200, max_samples=auto) ===")
contam_results = []
for c in [0.05, 0.10, 0.15, 0.22, 0.30]:
    iso = IsolationForest(n_estimators=200, max_samples="auto", contamination=c,
                          random_state=SEED, n_jobs=-1)
    iso.fit(X_train)
    a_tr_raw = -iso.score_samples(X_train)
    lo, hi = a_tr_raw.min(), a_tr_raw.max()
    a_val, _ = norm_scores(iso, X_val, lo, hi)
    thr = np.quantile(a_tr_raw, 1 - c)  # operating threshold: top-c fraction of train
    flag_val = (a_val >= (thr - lo) / (hi - lo + 1e-12)).astype(int)
    pr_auc = average_precision_score(y_val, a_val)
    f1 = metrics_at_threshold(y_val, a_val, float((thr - lo) / (hi - lo + 1e-12)))["f1"]
    n_flag = int(flag_val.sum())
    overlap = float(flag_val[y_val == 1].sum() / max(flag_val.sum(), 1))
    contam_results.append((c, f1, pr_auc, n_flag, overlap))
    print(f"  contamination={c:.2f}: val F1(flag)={f1:.4f} PR-AUC={pr_auc:.4f} "
          f"flagged={n_flag} ({n_flag/len(y_val):.1%}), fraud-among-flagged={overlap:.3f}")

# NOTE: contamination is an *operating assumption* (what fraction of traffic we are
# willing to flag for review), NOT an estimate of fraud prevalence. Selection below.
best_c = max(contam_results, key=lambda r: r[1])[0]
print(f"selected contamination={best_c} (max val F1 of induced flag)")

print("\n=== n_estimators / max_samples check at chosen contamination ===")
param_results = []
for ne, ms in [(100, "auto"), (200, "auto"), (300, "auto"), (200, 0.5)]:
    iso = IsolationForest(n_estimators=ne, max_samples=ms, contamination=best_c,
                          random_state=SEED, n_jobs=-1).fit(X_train)
    lo, hi = (-iso.score_samples(X_train)).min(), (-iso.score_samples(X_train)).max()
    a_val, _ = norm_scores(iso, X_val, lo, hi)
    pr_auc = average_precision_score(y_val, a_val)
    param_results.append((ne, ms, pr_auc))
    print(f"  n_estimators={ne}, max_samples={ms}: val PR-AUC={pr_auc:.4f}")
best_ne, best_ms, _ = max(param_results, key=lambda r: r[2])
print(f"selected: n_estimators={best_ne}, max_samples={best_ms}")

iso = IsolationForest(n_estimators=best_ne, max_samples=best_ms, contamination=best_c,
                      random_state=SEED, n_jobs=-1).fit(X_train)
tr_raw = -iso.score_samples(X_train)
LO, HI = float(tr_raw.min()), float(tr_raw.max())
THR_RAW = float(np.quantile(tr_raw, 1 - best_c))
THR_NORM = (THR_RAW - LO) / (HI - LO + 1e-12)
joblib.dump(iso, f"{MODELS}/isolation_forest.joblib")

a_val, _ = norm_scores(iso, X_val, LO, HI)
a_test, _ = norm_scores(iso, X_test, LO, HI)
flag_val = (a_val >= THR_NORM).astype(int)
flag_test = (a_test >= THR_NORM).astype(int)

# ============================ Part B: anomaly evaluation ============================
print("\n=== Part B: anomaly signal vs FLAG (ANOMALY != FRAUD) ===")
for name, a, y, fl in [("val", a_val, y_val, flag_val), ("test", a_test, y_test, flag_test)]:
    m = metrics_at_threshold(y, a, THR_NORM)
    print(f"  {name}: PR-AUC={m['pr_auc']:.4f} ROC-AUC={m['roc_auc']:.4f} "
          f"P={m['precision']:.4f} R={m['recall']:.4f} F1={m['f1']:.4f} "
          f"FP={m['fp']} FN={m['fn']} flagged={fl.sum()} "
          f"fraud-among-flagged={fl[y==1].sum()}/{fl.sum()}")
    print(f"    mean anomaly score: fraud={a[y==1].mean():.3f} legit={a[y==0].mean():.3f}")

sp_val, _ = spearmanr(a_val, p_val_xgb)
sp_test, _ = spearmanr(a_test, p_test_xgb)
print(f"  Spearman(anomaly, xgb_proba): val={sp_val:.3f} test={sp_test:.3f}")
for name, a, p in [("val", a_val, p_val_xgb), ("test", a_test, p_test_xgb)]:
    top_a = a >= np.quantile(a, 0.9)
    top_p = p >= np.quantile(p, 0.9)
    yy = y_val if name == "val" else y_test
    print(f"  {name} top-decile overlap: P(anom_top & xgb_top)={np.mean(top_a & top_p):.3f}, "
          f"P(fraud|anom_top)={np.mean(yy[top_a]):.3f}")

fig, axes = plt.subplots(1, 2, figsize=(11, 4))
for ax, (name, a, y) in zip(axes, [("validation", a_val, y_val), ("test", a_test, y_test)]):
    ax.hist(a[y == 0], bins=40, alpha=0.6, label="legit (FLAG=0)", density=True)
    ax.hist(a[y == 1], bins=40, alpha=0.6, label="fraud (FLAG=1)", density=True)
    ax.axvline(THR_NORM, color="k", ls="--", label=f"flag threshold ({THR_NORM:.2f})")
    ax.set_xlabel("normalized anomaly score"); ax.set_ylabel("density")
    ax.set_title(f"Anomaly score distribution — {name}\n(anomaly != fraud)")
    ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig(f"{FIG}/fig_anomaly_distribution.png", dpi=110, bbox_inches="tight")
plt.close(fig)

anomaly_df = pd.DataFrame({
    "split": ["val"] * len(y_val) + ["test"] * len(y_test),
    "anomaly_score": np.concatenate([a_val, a_test]).round(4),
    "anomaly_flag": np.concatenate([flag_val, flag_test]),
    "xgb_fraud_probability": np.concatenate([p_val_xgb, p_test_xgb]).round(4),
    "FLAG": np.concatenate([y_val, y_test]),
})
anomaly_df.to_csv(f"{ROOT}/reports/anomaly_analysis.csv", index=False)

anomaly_meta = {
    "phase": 4, "part": "A/B", "created_utc": datetime.now(timezone.utc).isoformat(),
    "seed": SEED,
    "why_isolation_forest": "Unsupervised; no FLAG used in fitting. Random-partition isolation "
        "suits mixed behavioral aggregates with no distributional assumptions, scales to "
        "6889x52, and complements the supervised classifier by flagging records that are "
        "unusual regardless of whether they resemble known fraud.",
    "training": "fitted on train split only (6889 rows, 52 scaled features); FLAG never used.",
    "contamination_grid": [
        {"contamination": c, "val_f1_flag": round(f, 4), "val_pr_auc": round(p, 4)}
        for c, f, p, _, _ in contam_results],
    "selected": {"n_estimators": best_ne, "max_samples": best_ms, "contamination": best_c,
                 "random_state": SEED},
    "why_selected": "contamination chosen by max validation F1 of the induced flag; "
        "n_estimators/max_samples by validation PR-AUC. Contamination is an operating "
        "assumption about review capacity, NOT an estimate of fraud prevalence "
        "(fraud rate is 22.1%; blindly copying it would conflate anomaly with fraud).",
    "score_normalization": "raw = -score_samples (higher = more anomalous); "
        "normalized = clip((raw - train_min)/(train_max - train_min)) using TRAIN min/max only; "
        "flag threshold = (1 - contamination) quantile of train raw scores.",
    "operating_threshold_norm": round(THR_NORM, 4),
    "test_metrics": {k: round(v, 4) if isinstance(v, float) else v
                     for k, v in metrics_at_threshold(y_test, a_test, THR_NORM).items()
                     if k != "per_class"},
    "spearman_anomaly_vs_xgb": {"val": round(float(sp_val), 4), "test": round(float(sp_test), 4)},
}
with open(f"{MODELS}/anomaly_metadata.json", "w") as f:
    json.dump(anomaly_meta, f, indent=2)

# ============================ Part C: Blockwell ablation ============================
print("\n=== Part C: suspicious-token ablation (XGBoost, identical protocol) ===")
keep = [i for i in range(len(FEATS)) if i != SUSPICIOUS_IDX]
Xtr51, Xv51, Xt51 = X_train[:, keep], X_val[:, keep], X_test[:, keep]
neg, pos = int((y_train == 0).sum()), int((y_train == 1).sum())
xgb_ab = XGBClassifier(n_estimators=400, max_depth=6, learning_rate=0.1, subsample=0.8,
                       colsample_bytree=0.8, min_child_weight=1, reg_lambda=1.0,
                       scale_pos_weight=neg / pos, random_state=SEED, n_jobs=-1,
                       tree_method="hist", eval_metric="logloss").fit(Xtr51, y_train)
p_val_ab = xgb_ab.predict_proba(Xv51)[:, 1]
sweep_ab = threshold_sweep(y_val, p_val_ab)
thr_ab = float(sweep_ab.loc[sweep_ab["f1"].idxmax(), "threshold"])
p_test_ab = xgb_ab.predict_proba(Xt51)[:, 1]
full_test = metrics_at_threshold(y_test, p_test_xgb, 0.55)
ab_test = metrics_at_threshold(y_test, p_test_ab, thr_ab)
print(f"  full(52f, thr=0.55): P={full_test['precision']:.4f} R={full_test['recall']:.4f} "
      f"F1={full_test['f1']:.4f} ROC={full_test['roc_auc']:.4f} PR={full_test['pr_auc']:.4f} "
      f"FP={full_test['fp']} FN={full_test['fn']}")
print(f"  ablated(51f, thr={thr_ab}): P={ab_test['precision']:.4f} R={ab_test['recall']:.4f} "
      f"F1={ab_test['f1']:.4f} ROC={ab_test['roc_auc']:.4f} PR={ab_test['pr_auc']:.4f} "
      f"FP={ab_test['fp']} FN={ab_test['fn']}")
joblib.dump(xgb_ab, f"{MODELS}/xgboost_ablated_blockwell.joblib")
ablation_df = pd.DataFrame([
    {"model": "xgboost_full_52f", "n_features": 52, "threshold": 0.55,
     **{k: full_test[k] for k in ["precision", "recall", "f1", "roc_auc", "pr_auc",
                                  "accuracy", "fp", "fn", "tp", "tn"]}},
    {"model": "xgboost_no_blockwell_51f", "n_features": 51, "threshold": thr_ab,
     **{k: ab_test[k] for k in ["precision", "recall", "f1", "roc_auc", "pr_auc",
                                "accuracy", "fp", "fn", "tp", "tn"]}},
])
ablation_df.to_csv(f"{ROOT}/reports/feature_ablation.csv", index=False)

# ============================ Parts D-F: risk engine ============================
print("\n=== Part D: risk weights — sensitivity on validation ===")
risk_config = {
    "formula": "risk_score = 100 * (w_fraud * fraud_probability + w_anomaly * anomaly_score); "
               "both inputs in [0,1]; weights sum to 1",
    "note": "Weights are a project-defined operating policy, NOT universal fraud standards.",
    "weights": {"fraud_probability": 0.7, "anomaly_score": 0.3},
    "why_default_weights": "Supervised fraud probability is the validated signal "
        "(test PR-AUC 0.9848); the anomaly score is a weaker auxiliary signal "
        f"(val PR-AUC {average_precision_score(y_val, a_val):.4f}). 0.7/0.3 lets the "
        "validated signal dominate while giving unusual-but-unseen patterns a voice. "
        "No extra behavioral features: they are already inside the XGBoost probability; "
        "adding them again would double-count.",
    "thresholds": {"low_max": 30, "medium_max": 70},
    "threshold_note": "0-30 LOW, 31-70 MEDIUM, 71-100 HIGH are operational project "
                      "thresholds, NOT universal fraud standards.",
    "levels": {"LOW": [0, 30], "MEDIUM": [31, 70], "HIGH": [71, 100]},
}


def risk_eval(y, p, a, weights, thr_cfg):
    r = 100 * (weights[0] * p + weights[1] * a)
    lvl = np.array([risk_level(s, thr_cfg) for s in r])
    high = (lvl == "HIGH").astype(int)
    m = metrics_at_threshold(y, r / 100.0, 0.71)  # HIGH boundary as score threshold
    return r, lvl, m


sens_rows = []
for wf, wa in [(1.0, 0.0), (0.8, 0.2), (0.7, 0.3), (0.6, 0.4), (0.5, 0.5)]:
    r, lvl, m = risk_eval(y_val, p_val_xgb, a_val, (wf, wa), risk_config["thresholds"])
    sens_rows.append({"w_fraud": wf, "w_anomaly": wa,
                      "val_pr_auc_risk": round(average_precision_score(y_val, r), 4),
                      "HIGH_precision": round(m["precision"], 4),
                      "HIGH_recall": round(m["recall"], 4),
                      "HIGH_f1": round(m["f1"], 4),
                      "pct_HIGH": round(float((lvl == "HIGH").mean()), 4)})
sens_df = pd.DataFrame(sens_rows)
print(sens_df.to_string(index=False))

fig, ax = plt.subplots()
x = [f"{wf:.1f}/{wa:.1f}" for wf, wa in
     [(1.0, 0.0), (0.8, 0.2), (0.7, 0.3), (0.6, 0.4), (0.5, 0.5)]]
ax.plot(x, sens_df["HIGH_f1"], marker="o", label="HIGH F1")
ax.plot(x, sens_df["val_pr_auc_risk"], marker="o", label="risk PR-AUC")
ax.set_xlabel("weights (w_fraud / w_anomaly)"); ax.set_ylabel("score")
ax.set_title("Risk-weight sensitivity — validation")
ax.legend()
fig.savefig(f"{FIG}/fig_risk_weight_sensitivity.png", dpi=110, bbox_inches="tight")
plt.close(fig)

# Final: test evaluation ONCE with default weights
print("\n=== Part F: combined risk evaluation on TEST (once) ===")
W = (risk_config["weights"]["fraud_probability"], risk_config["weights"]["anomaly_score"])
r_test, lvl_test, m_test = risk_eval(y_test, p_test_xgb, a_test, W, risk_config["thresholds"])
risk_config["selected_weights"] = {"fraud_probability": W[0], "anomaly_score": W[1]}
risk_config["sensitivity_validation"] = sens_df.to_dict("records")
with open(f"{MODELS}/risk_config.json", "w") as f:
    json.dump(risk_config, f, indent=2)

bucket_rows = []
for b in ["LOW", "MEDIUM", "HIGH"]:
    mask = lvl_test == b
    n = int(mask.sum())
    fraud_rate = float(y_test[mask].mean()) if n else 0.0
    bucket_rows.append({"bucket": b, "n": n, "pct_of_test": round(n / len(y_test), 4),
                        "fraud_rate": round(fraud_rate, 4)})
    print(f"  {b}: n={n} ({n/len(y_test):.1%}), fraud rate={fraud_rate:.3f}")
print(f"  HIGH as fraud-positive: P={m_test['precision']:.4f} R={m_test['recall']:.4f} "
      f"F1={m_test['f1']:.4f} FP={m_test['fp']} FN={m_test['fn']}")
print(f"  risk PR-AUC (test): {average_precision_score(y_test, r_test):.4f} | "
      f"XGB-only PR-AUC: {average_precision_score(y_test, p_test_xgb):.4f}")

fig, axes = plt.subplots(1, 2, figsize=(11, 4))
axes[0].hist(r_test[y_test == 0], bins=40, alpha=0.6, label="legit", density=True)
axes[0].hist(r_test[y_test == 1], bins=40, alpha=0.6, label="fraud", density=True)
axes[0].axvline(30, color="k", ls="--", alpha=0.5); axes[0].axvline(70, color="k", ls="--", alpha=0.5)
axes[0].set_xlabel("risk score"); axes[0].set_ylabel("density")
axes[0].set_title("Risk score distribution — test"); axes[0].legend(fontsize=8)
bd = pd.DataFrame(bucket_rows)
axes[1].bar(bd["bucket"], bd["fraud_rate"], color=["green", "orange", "red"])
axes[1].set_ylabel("fraud rate"); axes[1].set_title("Fraud rate by risk bucket — test")
for i, v in enumerate(bd["fraud_rate"]):
    axes[1].text(i, v + 0.01, f"{v:.2f}", ha="center", fontsize=9)
fig.tight_layout()
fig.savefig(f"{FIG}/fig_risk_buckets_test.png", dpi=110, bbox_inches="tight")
plt.close(fig)

risk_df = pd.DataFrame({
    "split": ["val"] * len(y_val) + ["test"] * len(y_test),
    "fraud_probability": np.concatenate([p_val_xgb, p_test_xgb]).round(4),
    "anomaly_score": np.concatenate([a_val, a_test]).round(4),
})
r_all = 100 * (W[0] * np.concatenate([p_val_xgb, p_test_xgb]) + W[1] * np.concatenate([a_val, a_test]))
risk_df["risk_score"] = np.round(r_all).astype(int)
risk_df["risk_level"] = [risk_level(s, risk_config["thresholds"]) for s in r_all]
risk_df["FLAG"] = np.concatenate([y_val, y_test])
risk_df.to_csv(f"{ROOT}/reports/risk_analysis.csv", index=False)

# ============================ Part G: example record ============================
ex = risk_df[risk_df["split"] == "test"].sort_values("risk_score", ascending=False).iloc[0]
example = score_record(ex["fraud_probability"], ex["anomaly_score"], risk_config)
print("\n=== Part G: example output (real highest-risk test record) ===")
print(json.dumps(example, indent=2))
with open(f"{ROOT}/reports/risk_example.json", "w") as f:
    json.dump(example, f, indent=2)

print("\nsaved: models/isolation_forest.joblib, anomaly_metadata.json, risk_config.json, "
      "reports/anomaly_analysis.csv, risk_analysis.csv, feature_ablation.csv")
