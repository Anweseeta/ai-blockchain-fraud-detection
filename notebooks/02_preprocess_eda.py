"""Phase 2 — preprocessing (train-fit only) + EDA (train split primarily).

1. Verifies the ERC20-missing assumption against actual data.
2. Builds/fits the preprocessing pipeline on TRAIN only; transforms val/test.
3. Saves the fitted artifact + processed arrays + feature metadata.
4. Runs EDA on the training split: distributions, categoricals, missingness,
   target, outliers, correlations, feature-vs-target, blockchain behavior.
No model training happens here.
"""
import json
import os
import sys

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = "/home/hatch/workspace/ai-blockchain-fraud-detection"
sys.path.insert(0, ROOT)  # so the artifact pickles as src.preprocessing.pipeline (importable)
from src.preprocessing.pipeline import build_preprocessor, split_feature_groups

PROC = f"{ROOT}/data/processed"
FIG = f"{ROOT}/reports/figures"
os.makedirs(FIG, exist_ok=True)

train = pd.read_csv(f"{PROC}/train.csv")
val = pd.read_csv(f"{PROC}/val.csv")
test = pd.read_csv(f"{PROC}/test.csv")
with open(f"{PROC}/split_metadata.json") as f:
    META = json.load(f)
FEATURES = META["features"]

print("=" * 70)
print("STEP 1 — verify the ERC20-missing assumption on TRAIN")
print("=" * 70)
erc20_num, other_num, cat_cols = split_feature_groups(FEATURES, train)
print(f"feature groups: erc20_numeric={len(erc20_num)}, other_numeric={len(other_num)}, categorical={cat_cols}")

# (a) coherence: is the SAME row set missing across all ERC20 numeric columns?
miss_masks = {c: set(train.index[train[c].isna()]) for c in erc20_num}
mask_sets = list(miss_masks.values())
coherent = all(m == mask_sets[0] for m in mask_sets)
print(f"(a) identical missing-row set across all {len(erc20_num)} ERC20 numeric cols: {coherent} "
      f"(n={len(mask_sets[0])})")

# (b) do those rows also lack token-type info (missing or none-like)?
tok = cat_cols[0]
no_tok_rows = set(train.index[train[tok].isna() | train[tok].astype(str).str.strip().isin({"0", ""})])
overlap = len(mask_sets[0] & no_tok_rows)
print(f"(b) ERC20-missing rows that also have no token type: {overlap}/{len(mask_sets[0])}")

# (c) rows with Total ERC20 tnxs == 0 (observed, not missing): what is their token type?
t = train[" Total ERC20 tnxs"]
zero_tok = train[t.fillna(-1) == 0][tok].astype(str).str.strip()
print(f"(c) rows with observed Total ERC20 tnxs==0: token type value counts -> "
      f"{zero_tok.value_counts(dropna=False).head(4).to_dict()}")

# (d) non-ERC20 numerics: any missing on train? (pipeline uses median as safety net)
other_missing = train[other_num].isna().sum().sum()
print(f"(d) missing values in non-ERC20 numerics (train): {other_missing}")

assumption_ok = coherent and overlap == len(mask_sets[0])
print(f"ASSUMPTION 'missing ERC20 = no token activity' verified: {assumption_ok}")
assert assumption_ok, "ERC20 missingness is not coherent — do not blindly impute 0"

print()
print("=" * 70)
print("STEP 2 — fit preprocessing on TRAIN only, transform val/test")
print("=" * 70)
pre = build_preprocessor(erc20_num, other_num, cat_cols)
X_train = pre.fit_transform(train[FEATURES])
X_val = pre.transform(val[FEATURES])
X_test = pre.transform(test[FEATURES])
y_train, y_val, y_test = (d["FLAG"].to_numpy() for d in (train, val, test))
feat_names = list(pre.get_feature_names_out())
print(f"transformed shapes: train {X_train.shape}, val {X_val.shape}, test {X_test.shape}")
print(f"output features: {len(feat_names)} (numeric {len(erc20_num)+len(other_num)} + "
      f"one-hot {len(feat_names)-(len(erc20_num)+len(other_num))})")
assert not np.isnan(X_train).any() and not np.isnan(X_val).any() and not np.isnan(X_test).any()
print("no NaNs remain in any split")

# which columns got the log transform (from the fitted transformers)?
log_erc20 = pre.named_transformers_["erc20_num"].named_steps["skew_log"].log_cols_
log_other = pre.named_transformers_["num"].named_steps["skew_log"].log_cols_
print(f"log1p applied to {len(log_erc20)+len(log_other)} numeric cols: {sorted(set(log_erc20+log_other))}")

joblib.dump(pre, f"{ROOT}/models/preprocessor.joblib")
np.savez(f"{PROC}/train_processed.npz", X=X_train, y=y_train)
np.savez(f"{PROC}/val_processed.npz", X=X_val, y=y_val)
np.savez(f"{PROC}/test_processed.npz", X=X_test, y=y_test)
with open(f"{PROC}/processed_metadata.json", "w") as f:
    json.dump(
        {
            "input_features": FEATURES,
            "output_features": feat_names,
            "n_output": len(feat_names),
            "log_transformed": sorted(set(log_erc20 + log_other)),
            "onehot_prefixes": cat_cols,
            "fitted_on": "train split only",
            "address_used": False,
        },
        f,
        indent=2,
    )
print("saved: models/preprocessor.joblib, data/processed/{train,val,test}_processed.npz")

print()
print("=" * 70)
print("STEP 3 — EDA on the TRAIN split (raw values)")
print("=" * 70)

# --- target distribution
fig, ax = plt.subplots()
vc = train["FLAG"].value_counts().sort_index()
ax.bar(["legit (0)", "fraud (1)"], vc.values)
ax.set_title("Target distribution — train split (n=6,889)")
for i, v in enumerate(vc.values):
    ax.text(i, v, f"{v}\n({v/len(train):.1%})", ha="center", va="bottom")
fig.savefig(f"{FIG}/fig_target_dist.png", dpi=110, bbox_inches="tight")
plt.close(fig)

# --- missingness
miss = train[FEATURES].isna().sum()
miss = miss[miss > 0].sort_values(ascending=False)
fig, ax = plt.subplots(figsize=(10, 4))
ax.barh(miss.index.str.strip(), miss.values)
ax.set_title("Missing values by column — train split (all in ERC20 block)")
fig.savefig(f"{FIG}/fig_missingness.png", dpi=110, bbox_inches="tight")
plt.close(fig)

# --- numeric distributions by class (key features, log-ish view)
key = ["Sent tnx", "Received Tnx", "Time Diff between first and last (Mins)",
       "total Ether sent", "total ether received", "total ether balance",
       "avg val sent", "avg val received", " Total ERC20 tnxs",
       "Unique Sent To Addresses", "Unique Received From Addresses",
       "Number of Created Contracts"]
fig, axes = plt.subplots(3, 4, figsize=(16, 10))
for ax, c in zip(axes.ravel(), key):
    a = train.loc[train["FLAG"] == 0, c].dropna()
    b = train.loc[train["FLAG"] == 1, c].dropna()
    bins = np.histogram_bin_edges(np.log1p(np.abs(pd.concat([a, b]))), bins=40)
    ax.hist(np.log1p(np.abs(a)), bins=bins, alpha=0.6, label="legit")
    ax.hist(np.log1p(np.abs(b)), bins=bins, alpha=0.6, label="fraud")
    ax.set_title(c.strip()[:34]); ax.set_xlabel("log1p(|x|)")
axes.ravel()[0].legend()
fig.suptitle("Feature distributions by class — train (log1p scale)")
fig.savefig(f"{FIG}/fig_dist_by_class.png", dpi=110, bbox_inches="tight")
plt.close(fig)

# --- categorical distributions
for c in cat_cols:
    cleaned = train[c].apply(lambda v: "none" if (pd.isna(v) or str(v).strip() in {"0", ""}) else str(v).strip())
    top = cleaned.value_counts().head(10)
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.barh(top.index, top.values)
    ax.set_title(f"Top token types — {c.strip()} (cleaned, train)")
    fig.savefig(f"{FIG}/fig_cat_{c.strip().replace(' ', '_')[:20]}.png", dpi=110, bbox_inches="tight")
    plt.close(fig)

# --- correlation with target + heatmap of top features
num_all = erc20_num + other_num
corr_flag = train[num_all + ["FLAG"]].corr(numeric_only=True)["FLAG"].drop("FLAG")
corr_flag = corr_flag.reindex(corr_flag.abs().sort_values(ascending=False).index)
corr_flag.to_csv(f"{ROOT}/reports/eda_corr_with_flag.csv", header=["pearson_r_with_FLAG"])
top15 = corr_flag.head(15).index.tolist()
fig, ax = plt.subplots(figsize=(10, 8))
m = train[top15 + ["FLAG"]].corr(numeric_only=True)
im = ax.imshow(m.values, vmin=-1, vmax=1, cmap="coolwarm")
ax.set_xticks(range(len(m.columns))); ax.set_yticks(range(len(m.columns)))
ax.set_xticklabels([c.strip()[:22] for c in m.columns], rotation=45, ha="right", fontsize=8)
ax.set_yticklabels([c.strip()[:22] for c in m.columns], fontsize=8)
ax.set_title("Correlation heatmap — top-15 |r| with FLAG + FLAG (train)")
fig.colorbar(im, ax=ax)
fig.savefig(f"{FIG}/fig_corr_heatmap.png", dpi=110, bbox_inches="tight")
plt.close(fig)
print("top 10 |pearson r| with FLAG (train):")
print(corr_flag.head(10).round(3).to_string())

# --- class-wise medians table
med = train.groupby("FLAG")[num_all].median().T
med.columns = ["median_legit", "median_fraud"]
med["ratio_fraud_over_legit"] = med["median_fraud"] / med["median_legit"].replace(0, np.nan)
med.to_csv(f"{ROOT}/reports/eda_class_medians.csv")

# --- outlier analysis: IQR fraction overall + by class
out = {}
for c in num_all:
    s = train[c].dropna()
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = q3 - q1
    out[c] = float(((s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)).mean()) if iqr > 0 else 0.0
out = dict(sorted(out.items(), key=lambda kv: -kv[1]))
print("top IQR-outlier fractions (train):", {k: round(v, 3) for k, v in list(out.items())[:8]})

# --- blockchain behavioral patterns: class-wise comparison
t = train
pat = {
    "median_activity_span_mins": (t.groupby("FLAG")["Time Diff between first and last (Mins)"].median().to_dict()),
    "median_sent_tnx": t.groupby("FLAG")["Sent tnx"].median().to_dict(),
    "median_received_tnx": t.groupby("FLAG")["Received Tnx"].median().to_dict(),
    "frac_created_contract": (t.groupby("FLAG")["Number of Created Contracts"].apply(lambda s: (s > 0).mean()).to_dict()),
    "frac_erc20_active": (t.groupby("FLAG")[" Total ERC20 tnxs"].apply(lambda s: s.fillna(0).gt(0).mean()).to_dict()),
    "median_total_eth_sent": t.groupby("FLAG")["total Ether sent"].median().to_dict(),
    "median_total_eth_received": t.groupby("FLAG")["total ether received"].median().to_dict(),
    "median_unique_sent_to": t.groupby("FLAG")["Unique Sent To Addresses"].median().to_dict(),
    "median_avg_min_between_sent": t.groupby("FLAG")["Avg min between sent tnx"].median().to_dict(),
}
with open(f"{ROOT}/reports/eda_blockchain_patterns.json", "w") as f:
    json.dump({k: {str(kk): float(vv) for kk, vv in v.items()} for k, v in pat.items()}, f, indent=2)
print("blockchain patterns (0=legit, 1=fraud):")
for k, v in pat.items():
    print(f"  {k}: legit={v[0]:.4g} fraud={v[1]:.4g}")

print()
print("EDA artifacts saved to reports/ + reports/figures/")
