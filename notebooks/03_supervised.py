"""Phase 3 — supervised modeling: Logistic Regression -> Random Forest -> XGBoost.

Protocol (per brief):
- Train on train split, hyperparameter selection + threshold tuning on validation.
- Test set evaluated ONCE per final model configuration, at the very end.
- No SMOTE. Class weighting where supported. Seeds fixed (42).
- Main comparison uses the Phase-2 transformed features (log + scaled) for a
  controlled comparison. A separate ablation checks trees on raw features.
"""
import itertools
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
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBClassifier

ROOT = "/home/hatch/workspace/ai-blockchain-fraud-detection"
sys.path.insert(0, ROOT)
from src.models.training import (
    classification_report_dict,
    metrics_at_threshold,
    pr_points,
    roc_points,
    threshold_sweep,
)
from src.preprocessing.pipeline import TokenTypeCleaner, split_feature_groups

SEED = 42
PROC = f"{ROOT}/data/processed"
FIG = f"{ROOT}/reports/figures"
MODELS = f"{ROOT}/models"
os.makedirs(FIG, exist_ok=True)

train = np.load(f"{PROC}/train_processed.npz")
val = np.load(f"{PROC}/val_processed.npz")
test = np.load(f"{PROC}/test_processed.npz")
X_train, y_train = train["X"], train["y"]
X_val, y_val = val["X"], val["y"]
X_test, y_test = test["X"], test["y"]
with open(f"{PROC}/processed_metadata.json") as f:
    FEAT_NAMES = json.load(f)["output_features"]
with open(f"{PROC}/split_metadata.json") as f:
    INPUT_FEATS = json.load(f)["features"]
print(f"data: train {X_train.shape}, val {X_val.shape}, test {X_test.shape}, features={len(FEAT_NAMES)}")

neg, pos = int((y_train == 0).sum()), int((y_train == 1).sum())
print(f"train class balance: neg={neg}, pos={pos}, scale_pos_weight={neg/pos:.3f}")

results = {}   # per-model: params, val metrics, threshold, test metrics
curves = {}    # roc/pr points on test for comparison plots


def plot_confusion(m, name, split):
    fig, ax = plt.subplots()
    cm = np.array([[m["tn"], m["fp"]], [m["fn"], m["tp"]]])
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks([0, 1]); ax.set_yticks([0, 1])
    ax.set_xticklabels(["pred legit", "pred fraud"]); ax.set_yticklabels(["true legit", "true fraud"])
    for i in range(2):
        for j in range(2):
            ax.text(j, i, cm[i, j], ha="center", va="center", fontsize=14)
    ax.set_title(f"Confusion matrix — {name} ({split}, thr={m['threshold']})")
    fig.colorbar(im, ax=ax)
    fig.savefig(f"{FIG}/fig_cm_{name}_{split}.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


def plot_threshold_sweep(sweep: pd.DataFrame, name: str):
    fig, ax = plt.subplots()
    ax.plot(sweep["threshold"], sweep["precision"], marker="o", label="precision")
    ax.plot(sweep["threshold"], sweep["recall"], marker="o", label="recall")
    ax.plot(sweep["threshold"], sweep["f1"], marker="o", label="F1")
    best = sweep.loc[sweep["f1"].idxmax()]
    ax.axvline(best["threshold"], ls="--", color="k", alpha=0.5)
    ax.set_xlabel("threshold"); ax.set_ylabel("score")
    ax.set_title(f"Threshold trade-off — {name} (validation; best F1 @ {best['threshold']:.2f})")
    ax.legend()
    fig.savefig(f"{FIG}/fig_threshold_{name}_val.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


def run_model(name, estimator_fn, param_grid):
    """Grid-search on validation F1@0.5, threshold-tune on validation, test once."""
    print(f"\n{'='*70}\n{name}: hyperparameter search on validation (F1 @ 0.5)\n{'='*70}")
    keys = list(param_grid)
    best = None
    for vals in itertools.product(*[param_grid[k] for k in keys]):
        params = dict(zip(keys, vals))
        est = estimator_fn(params)
        est.fit(X_train, y_train)
        p = est.predict_proba(X_val)[:, 1]
        f1 = metrics_at_threshold(y_val, p, 0.5)["f1"]
        tag = ", ".join(f"{k}={v}" for k, v in params.items())
        print(f"  F1={f1:.4f}  [{tag}]")
        if best is None or f1 > best[0]:
            best = (f1, params, est)
    f1v, params, est = best
    print(f"selected: {params} (val F1@0.5={f1v:.4f})")

    # threshold tuning on validation
    p_val = est.predict_proba(X_val)[:, 1]
    sweep = threshold_sweep(y_val, p_val)
    sweep.to_csv(f"{ROOT}/reports/threshold_sweep_{name}.csv", index=False)
    plot_threshold_sweep(sweep, name)
    thr = float(sweep.loc[sweep["f1"].idxmax(), "threshold"])
    val_m = metrics_at_threshold(y_val, p_val, thr)
    print(f"threshold: {thr} -> val precision={val_m['precision']:.4f} recall={val_m['recall']:.4f} "
          f"F1={val_m['f1']:.4f} (FP={val_m['fp']}, FN={val_m['fn']})")

    # FINAL: test set, evaluated once
    p_test = est.predict_proba(X_test)[:, 1]
    test_m = metrics_at_threshold(y_test, p_test, thr)
    test_m["per_class"] = classification_report_dict(y_test, p_test, thr)
    plot_confusion(test_m, name, "test")
    curves[name] = {"roc": roc_points(y_test, p_test), "pr": pr_points(y_test, p_test),
                    "roc_auc": test_m["roc_auc"], "pr_auc": test_m["pr_auc"]}
    print(f"TEST (once): precision={test_m['precision']:.4f} recall={test_m['recall']:.4f} "
          f"F1={test_m['f1']:.4f} ROC-AUC={test_m['roc_auc']:.4f} PR-AUC={test_m['pr_auc']:.4f} "
          f"acc={test_m['accuracy']:.4f} FP={test_m['fp']} FN={test_m['fn']}")

    joblib.dump(est, f"{MODELS}/{name}.joblib")
    results[name] = {
        "params": params, "val_f1_at_0.5": round(f1v, 4),
        "threshold": thr, "val_metrics": val_m, "test_metrics": test_m,
    }
    return est


# ---------------- 1. Logistic Regression (baseline) ----------------
run_model(
    "logistic_regression",
    lambda p: LogisticRegression(class_weight="balanced", max_iter=5000,
                                random_state=SEED, **p),
    {"C": [0.01, 0.1, 1.0, 10.0], "solver": ["lbfgs"]},
)

# ---------------- 2. Random Forest ----------------
run_model(
    "random_forest",
    lambda p: RandomForestClassifier(random_state=SEED, n_jobs=-1, **p),
    {
        "n_estimators": [300],
        "max_depth": [None, 15],
        "min_samples_split": [2, 5],
        "min_samples_leaf": [1, 2],
        "max_features": ["sqrt", 0.5],
        "class_weight": ["balanced", "balanced_subsample"],
    },
)

# ---------------- 3. XGBoost ----------------
run_model(
    "xgboost",
    lambda p: XGBClassifier(scale_pos_weight=neg / pos, random_state=SEED,
                            n_jobs=-1, tree_method="hist", eval_metric="logloss", **p),
    {
        "n_estimators": [400],
        "max_depth": [4, 6],
        "learning_rate": [0.05, 0.1],
        "subsample": [0.8],
        "colsample_bytree": [0.8],
        "min_child_weight": [1],
        "reg_lambda": [1.0],
    },
)

# ---------------- comparison ROC / PR plots (test) ----------------
fig, ax = plt.subplots()
for name, c in curves.items():
    fpr, tpr = c["roc"]
    ax.plot(fpr, tpr, label=f"{name} (AUC={c['roc_auc']:.3f})")
ax.plot([0, 1], [0, 1], "k--", alpha=0.4)
ax.set_xlabel("FPR"); ax.set_ylabel("TPR"); ax.set_title("ROC curves — test set")
ax.legend(fontsize=8)
fig.savefig(f"{FIG}/fig_roc_comparison_test.png", dpi=110, bbox_inches="tight")
plt.close(fig)

fig, ax = plt.subplots()
base = (y_test == 1).mean()
for name, c in curves.items():
    prec, rec = c["pr"]
    ax.plot(rec, prec, label=f"{name} (AP={c['pr_auc']:.3f})")
ax.axhline(base, ls="--", color="k", alpha=0.4, label=f"baseline ({base:.2f})")
ax.set_xlabel("recall"); ax.set_ylabel("precision"); ax.set_title("Precision-Recall curves — test set")
ax.legend(fontsize=8)
fig.savefig(f"{FIG}/fig_pr_comparison_test.png", dpi=110, bbox_inches="tight")
plt.close(fig)

# ---------------- ablation: do trees need the log/scale transform? ----------------
print(f"\n{'='*70}\nAblation: RandomForest on RAW (imputed+onehot, no log/scale) vs transformed\n{'='*70}")
raw_df = pd.read_csv(f"{PROC}/train.csv")
raw_val = pd.read_csv(f"{PROC}/val.csv")
erc20_num, other_num, cat_cols = split_feature_groups(INPUT_FEATS, raw_df)
raw_pre = ColumnTransformer([
    ("erc20", SimpleImputer(strategy="constant", fill_value=0), erc20_num),
    ("num", SimpleImputer(strategy="median"), other_num),
    ("cat", Pipeline([("clean", TokenTypeCleaner()),
                      ("oh", OneHotEncoder(handle_unknown="ignore", sparse_output=False,
                                           min_frequency=0.01))]), cat_cols),
], verbose_feature_names_out=False)
Xr_train = raw_pre.fit_transform(raw_df[INPUT_FEATS])
Xr_val = raw_pre.transform(raw_val[INPUT_FEATS])
yr_train, yr_val = raw_df["FLAG"].to_numpy(), raw_val["FLAG"].to_numpy()
rf_raw = RandomForestClassifier(n_estimators=300, class_weight="balanced_subsample",
                                random_state=SEED, n_jobs=-1).fit(Xr_train, yr_train)
rf_t = RandomForestClassifier(n_estimators=300, class_weight="balanced_subsample",
                              random_state=SEED, n_jobs=-1).fit(X_train, y_train)
for label, est, Xv in [("raw", rf_raw, Xr_val), ("transformed", rf_t, X_val)]:
    m = metrics_at_threshold(yr_val, est.predict_proba(Xv)[:, 1], 0.5)
    print(f"  {label}: val F1@0.5={m['f1']:.4f} PR-AUC={m['pr_auc']:.4f} ROC-AUC={m['roc_auc']:.4f}")
ablation = {
    "note": "validation-only comparison; not used for model selection",
    "raw": metrics_at_threshold(yr_val, rf_raw.predict_proba(Xr_val)[:, 1], 0.5),
    "transformed": metrics_at_threshold(yr_val, rf_t.predict_proba(X_val)[:, 1], 0.5),
}

# ---------------- save metadata ----------------
meta = {
    "phase": 3,
    "created_utc": datetime.now(timezone.utc).isoformat(),
    "seed": SEED,
    "data": {"train": list(X_train.shape), "val": list(X_val.shape), "test": list(X_test.shape),
             "n_features": len(FEAT_NAMES), "train_pos_rate": round(float(y_train.mean()), 4)},
    "preprocessing": "phase-2 pipeline (log1p on 36/37 numerics + StandardScaler + one-hot); "
                     "fitted on train only",
    "class_imbalance": "class_weight='balanced'/'balanced_subsample' (LR/RF); "
                       f"scale_pos_weight={neg/pos:.3f} (XGB); no SMOTE",
    "hyperparam_selection": "grid search maximizing validation F1 @ threshold 0.5",
    "threshold_criterion": "argmax F1 on validation sweep (0.05..0.95 step 0.05)",
    "test_protocol": "each final model evaluated on the test set exactly once",
    "models": {k: {"params": v["params"], "threshold": v["threshold"],
                   "val_metrics": v["val_metrics"], "test_metrics": v["test_metrics"]}
               for k, v in results.items()},
    "ablation_raw_vs_transformed_rf": ablation,
    "versions": {"sklearn": __import__("sklearn").__version__,
                 "xgboost": __import__("xgboost").__version__},
}
with open(f"{MODELS}/model_metadata.json", "w") as f:
    json.dump(meta, f, indent=2)
with open(f"{MODELS}/threshold_config.json", "w") as f:
    json.dump({k: {"threshold": v["threshold"],
                   "criterion": "argmax F1 on validation",
                   "val_precision": v["val_metrics"]["precision"],
                   "val_recall": v["val_metrics"]["recall"],
                   "val_f1": v["val_metrics"]["f1"]}
               for k, v in results.items()}, f, indent=2)

comp = pd.DataFrame([
    {"model": k, **{mkey: v["test_metrics"][mkey]
                    for mkey in ["precision", "recall", "f1", "roc_auc", "pr_auc",
                                 "accuracy", "fp", "fn", "tp", "tn"]},
     "threshold": v["threshold"]}
    for k, v in results.items()
])
comp.to_csv(f"{ROOT}/reports/model_comparison.csv", index=False)
print("\n" + comp.to_string(index=False))
print("\nsaved models/, model_metadata.json, threshold_config.json, reports/model_comparison.csv")
