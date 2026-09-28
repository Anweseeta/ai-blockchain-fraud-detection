"""Phase 5 — SHAP explainability for the validated XGBoost model.

- Uses the actual trained XGBoost model + exact training feature representation.
- No retraining. TreeExplainer (exact), model_output="probability".
- Isolation Forest signal is NOT used in explanations (risk weight 0).
- Wording discipline: association, never causation.
"""
import json
import os
import sys
import time

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap

ROOT = "/home/hatch/workspace/ai-blockchain-fraud-detection"
sys.path.insert(0, ROOT)
from src.risk.scoring import score_record

SEED = 42
PROC = f"{ROOT}/data/processed"
SHAP_DIR = f"{ROOT}/reports/shap"
FIGD = f"{ROOT}/reports/figures"
os.makedirs(SHAP_DIR, exist_ok=True)

test = np.load(f"{PROC}/test_processed.npz")
X_test, y_test = test["X"], test["y"]
X_train = np.load(f"{PROC}/train_processed.npz")["X"]
FEATS = json.load(open(f"{PROC}/processed_metadata.json"))["output_features"]
INPUT_FEATS = json.load(open(f"{PROC}/split_metadata.json"))["features"]
raw_test = pd.read_csv(f"{PROC}/test.csv")  # row-aligned with X_test (verified)
xgb = joblib.load(f"{ROOT}/models/xgboost.joblib")
risk_cfg = json.load(open(f"{ROOT}/models/risk_config.json"))
THR = 0.55  # Phase-3 validated operating threshold for this model
p_test = xgb.predict_proba(X_test)[:, 1]

# output feature -> (input column, kind) for human-readable raw values
num_set = [f for f in FEATS if f in INPUT_FEATS]
cat_cols = [c for c in INPUT_FEATS if c not in num_set]


def raw_value_for(out_idx, row):
    name = FEATS[out_idx]
    if name in INPUT_FEATS:
        return name, row[name]
    for c in cat_cols:
        if name.startswith(c + "_"):
            return c, row[c]
    return "", ""


# ============================ Part A: explainer ============================
t0 = time.time()
# tree_path_dependent + raw output is the exact, supported path for this
# XGBoost build (interventional/probability hits a shap/xgboost-3.x
# incompatibility). Values are in log-odds units: sum + base = model margin,
# sigmoid(margin) = fraud probability. Sign = direction of effect.
explainer = shap.TreeExplainer(xgb)
sv = np.asarray(explainer.shap_values(X_test))  # (1476, 52)
base = float(np.atleast_1d(explainer.expected_value)[0])
dt = time.time() - t0
margin = np.log(np.clip(p_test, 1e-12, 1 - 1e-12) / np.clip(1 - p_test, 1e-12, 1 - 1e-12))
print(f"TreeExplainer(raw log-odds): explained {len(X_test)} x {len(FEATS)} in {dt:.1f}s")
print(f"base value={base:.4f}; additivity max err={np.abs(sv.sum(1)+base-margin).max():.2e}")

# ============================ Part B: global ============================
mean_abs = np.abs(sv).mean(0)
mean_sv = sv.mean(0)
order = np.argsort(mean_abs)[::-1]
glob = pd.DataFrame({
    "rank": np.arange(1, len(FEATS) + 1),
    "feature": [FEATS[i] for i in order],
    "mean_abs_shap": mean_abs[order].round(5),
    "mean_shap": mean_sv[order].round(5),
})
glob.to_csv(f"{SHAP_DIR}/global_feature_importance.csv", index=False)
print("\nTop 15 global (mean |SHAP|, probability units):")
print(glob.head(15).to_string(index=False))

Xd = pd.DataFrame(X_test, columns=FEATS)
shap.summary_plot(sv, Xd, max_display=20, show=False)
plt.tight_layout()
plt.savefig(f"{SHAP_DIR}/shap_summary.png", dpi=110, bbox_inches="tight")
plt.savefig(f"{FIGD}/fig_shap_summary.png", dpi=110, bbox_inches="tight")
plt.close()
shap.summary_plot(sv, Xd, plot_type="bar", max_display=20, show=False)
plt.tight_layout()
plt.savefig(f"{SHAP_DIR}/shap_bar.png", dpi=110, bbox_inches="tight")
plt.close()

bw_rank = int(np.where(order == FEATS.index(" ERC20_most_rec_token_type_Blockwell say NOTSAFU"))[0][0]) + 1
print(f"Blockwell feature global SHAP rank: {bw_rank}/52, "
      f"mean|SHAP|={mean_abs[FEATS.index(' ERC20_most_rec_token_type_Blockwell say NOTSAFU')]:.5f}")

# ============================ Part C: local examples ============================
pool_cf = np.where((y_test == 1) & (p_test >= THR))[0]
# medium-risk AND correctly classified at the operating threshold: p in [0.55, 0.70]
pool_med = np.where((y_test == 1) & (p_test >= THR) & (p_test <= 0.70))[0]
pool_cl = np.where((y_test == 0) & (p_test < THR))[0]
pool_fp = np.where((y_test == 0) & (p_test >= THR))[0]
pool_fn = np.where((y_test == 1) & (p_test < THR))[0]
print(f"\npools: correct-fraud={len(pool_cf)} med-fraud={len(pool_med)} "
      f"correct-legit={len(pool_cl)} FP={len(pool_fp)} FN={len(pool_fn)}")

examples = [
    ("high_risk_correct_fraud", pool_cf[np.argmax(p_test[pool_cf])]),
    ("medium_risk_correct_fraud", pool_med[np.argmin(np.abs(p_test[pool_med] - 0.5))]),
    ("low_risk_correct_legit", pool_cl[np.argmin(p_test[pool_cl])]),
    ("high_risk_false_positive", pool_fp[np.argmax(p_test[pool_fp])]),
    ("false_negative", pool_fn[np.argmax(p_test[pool_fn])]),
]

local_rows, local_json = [], {}
for case, idx in examples:
    row = raw_test.iloc[idx]
    rec = score_record(p_test[idx], 0.0, risk_cfg)  # anomaly weight 0 per operating policy
    # rebuild with actual anomaly score for the record but risk per policy weights
    top_idx = np.argsort(np.abs(sv[idx]))[::-1][:10]
    factors = []
    for r, j in enumerate(top_idx, 1):
        v = float(sv[idx, j])
        in_col, raw_v = raw_value_for(j, row)
        factors.append({
            "rank": r, "feature": FEATS[j],
            "transformed_value": round(float(X_test[idx, j]), 4),
            "raw_input_column": in_col, "raw_value": str(raw_v),
            "shap_value": round(v, 5),
            "direction": "increases_risk" if v > 0 else "decreases_risk",
        })
        local_rows.append({"example": case, "test_row": int(idx), "FLAG": int(y_test[idx]),
                           "fraud_probability": round(float(p_test[idx]), 4),
                           "risk_score": rec["risk_score"], "risk_level": rec["risk_level"],
                           **factors[-1]})
    local_json[case] = {"test_row": int(idx), "FLAG": int(y_test[idx]),
                        "fraud_probability": round(float(p_test[idx]), 4),
                        "risk_score": rec["risk_score"], "risk_level": rec["risk_level"],
                        "top_factors": factors}
    pos = [f for f in factors if f["direction"] == "increases_risk"][:3]
    neg = [f for f in factors if f["direction"] == "decreases_risk"][:3]
    print(f"\n[{case}] row={idx} FLAG={y_test[idx]} p={p_test[idx]:.4f} "
          f"risk={rec['risk_score']} {rec['risk_level']}")
    print("  +risk:", [(f["feature"].strip(), f["shap_value"]) for f in pos])
    print("  -risk:", [(f["feature"].strip(), f["shap_value"]) for f in neg])

    exp = shap.Explanation(values=sv[idx], base_values=base, data=X_test[idx],
                           feature_names=[f.strip() for f in FEATS])
    shap.plots.waterfall(exp, max_display=12, show=False)
    plt.tight_layout()
    plt.savefig(f"{SHAP_DIR}/waterfall_{case}.png", dpi=110, bbox_inches="tight")
    plt.savefig(f"{FIGD}/fig_waterfall_{case}.png", dpi=110, bbox_inches="tight")
    plt.close()

pd.DataFrame(local_rows).to_csv(f"{SHAP_DIR}/local_explanations.csv", index=False)
json.dump(local_json, open(f"{SHAP_DIR}/local_examples.json", "w"), indent=2)

# ============================ Part F: error analysis ============================
print("\n=== Part F: error analysis (mean |SHAP| per group) ===")


def group_importance(mask, label):
    m = np.abs(sv[mask]).mean(0)
    o = np.argsort(m)[::-1][:10]
    df = pd.DataFrame({"feature": [FEATS[i] for i in o], "mean_abs_shap": m[o].round(5)})
    df.to_csv(f"{SHAP_DIR}/{label}_explanations.csv", index=False)
    print(f"\n{label} (n={mask.sum()}):")
    print(df.to_string(index=False))
    return set(df["feature"])


fp_mask = (y_test == 0) & (p_test >= THR)
fn_mask = (y_test == 1) & (p_test < THR)
cf_mask = (y_test == 1) & (p_test >= THR)
cl_mask = (y_test == 0) & (p_test < THR)
fp_f = group_importance(fp_mask, "false_positive")
fn_f = group_importance(fn_mask, "false_negative")
cf_f = group_importance(cf_mask, "correct_fraud")
cl_f = group_importance(cl_mask, "correct_legit")
print("\nFP top-10 overlap with correct-fraud top-10:", len(fp_f & cf_f), "/10")
print("FN top-10 overlap with correct-legit top-10:", len(fn_f & cl_f), "/10")
print("FN top-10 overlap with correct-fraud top-10:", len(fn_f & cf_f), "/10")

# ============================ Part H: reusable metadata ============================
meta = {
    "phase": 5, "model": "xgboost (Phase-3 artifact, not retrained)",
    "explainer": "shap.TreeExplainer",
    "explainer_detail": "feature_perturbation='tree_path_dependent', model_output='raw': "
                        "exact Tree SHAP values in log-odds units; values for one record sum "
                        "to margin(x) - base_value with sigmoid(margin) = fraud probability. "
                        "(Interventional/probability-output mode is blocked by a "
                        "shap-0.52/xgboost-3.x incompatibility.)",
    "background_data": "none required (tree-path-dependent exact computation)",
    "n_explained": int(len(X_test)), "n_features": len(FEATS),
    "expected_value_base": round(base, 6),
    "additivity_max_abs_err": float(np.abs(
        sv.sum(1) + base - np.log(np.clip(p_test, 1e-12, 1 - 1e-12)
                                  / np.clip(1 - p_test, 1e-12, 1 - 1e-12))).max()),
    "units": "log-odds (margin); sigmoid(sum + base) = fraud probability",
    "compute_seconds": round(dt, 1),
    "operating_threshold": THR,
    "feature_names": FEATS,
    "note": "SHAP measures association with model output, not causal effect. "
            "Isolation Forest signal excluded from explanations per operating risk policy.",
    "shap_version": shap.__version__,
}
json.dump(meta, open(f"{SHAP_DIR}/shap_metadata.json", "w"), indent=2)
print("\nsaved reports/shap/ artifacts + docs pending")
