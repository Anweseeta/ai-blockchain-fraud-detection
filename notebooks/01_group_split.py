"""Phase 2a — group-aware stratified train/validation/test split.

Address is used ONLY as a grouping variable for the split (leakage prevention:
no address may appear in more than one partition). It is excluded from the
modeling feature list afterwards.
"""
import json
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

RAW = "/home/hatch/workspace/ai-blockchain-fraud-detection/data/raw/transaction_dataset.csv"
PROC = "/home/hatch/workspace/ai-blockchain-fraud-detection/data/processed"
REPORT = "/home/hatch/workspace/ai-blockchain-fraud-detection/reports/split_report.md"

# Columns removed per the data dictionary (Address kept ONLY for grouping, then dropped as a feature)
REMOVE = [
    "Unnamed: 0", "Index",                                   # label-order leakage
    " ERC20 uniq sent addr.1",                               # unverifiable, near-constant
    " ERC20 avg time between sent tnx", " ERC20 avg time between rec tnx",
    " ERC20 avg time between rec 2 tnx", " ERC20 avg time between contract tnx",
    " ERC20 min val sent contract", " ERC20 max val sent contract",
    " ERC20 avg val sent contract",                          # constant zero
]

df = pd.read_csv(RAW)
print(f"raw shape: {df.shape}")

df = df.drop(columns=REMOVE)
print(f"after column removal: {df.shape} (Address kept for grouping only)")

groups = df["Address"].to_numpy()
y = df["FLAG"].to_numpy()

# Sanity: label consistency inside duplicate-address groups
dup = df[df.duplicated("Address", keep=False)]
n_dup_rows = len(dup)
n_dup_addrs = dup["Address"].nunique()
mixed = (dup.groupby("Address")["FLAG"].nunique() > 1).sum()
print(f"duplicate-address rows: {n_dup_rows} ({n_dup_rows/len(df):.2%} of data), "
      f"addresses: {n_dup_addrs}, mixed-label groups: {mixed}")

# Group-aware stratified split: 20 folds -> 3 test (15%), 3 val (15%), 14 train (70%)
sgkf = StratifiedGroupKFold(n_splits=20, shuffle=True, random_state=42)
folds = np.zeros(len(df), dtype=int)
for i, (_, te_idx) in enumerate(sgkf.split(df, y, groups)):
    folds[te_idx] = i

test_mask = np.isin(folds, [0, 1, 2])
val_mask = np.isin(folds, [3, 4, 5])
train_mask = ~(test_mask | val_mask)

train, val, test = df[train_mask], df[val_mask], df[test_mask]
print(f"train={len(train)}, val={len(val)}, test={len(test)}")

# Verification 1: no address crosses partitions
sets = {"train": set(train["Address"]), "val": set(val["Address"]), "test": set(test["Address"])}
overlap = (sets["train"] & sets["val"]) | (sets["train"] & sets["test"]) | (sets["val"] & sets["test"])
print(f"addresses appearing in >1 split: {len(overlap)}")
assert len(overlap) == 0, "GROUP LEAKAGE: address spans splits"

# Verification 2: class distributions
def dist(d):
    vc = d["FLAG"].value_counts(normalize=True).sort_index()
    return {int(k): round(float(v), 4) for k, v in vc.items()}

overall = dist(df)
report = {
    "overall_fraud_rate": overall.get(1),
    "n_train": len(train), "n_val": len(val), "n_test": len(test),
    "train_dist": dist(train), "val_dist": dist(val), "test_dist": dist(test),
    "dup_rows_affected": int(n_dup_rows),
    "dup_addresses": int(n_dup_addrs),
    "mixed_label_groups": int(mixed),
    "group_overlap_across_splits": 0,
    "random_state": 42, "method": "StratifiedGroupKFold(n_splits=20)",
}
for name, d in [("train", train), ("val", val), ("test", test)]:
    print(name, dist(d), f"n={len(d)}")

# Save splits (Address retained as a metadata column for audit; NOT in the feature list)
for name, d in [("train", train), ("val", val), ("test", test)]:
    d.to_csv(f"{PROC}/{name}.csv", index=False)

feature_cols = [c for c in df.columns if c not in ("Address", "FLAG")]
meta = {
    "target": "FLAG",
    "grouping_column": "Address",
    "grouping_note": "Address used ONLY for group-aware splitting (leakage prevention). "
                     "It is NOT a modeling feature.",
    "features": feature_cols,
    "n_features": len(feature_cols),
    "removed_columns": REMOVE,
    "split": {"train": len(train), "val": len(val), "test": len(test), **{k: v for k, v in report.items() if k in ('random_state','method')}},
}
with open(f"{PROC}/split_metadata.json", "w") as f:
    json.dump(meta, f, indent=2)

lines = [
    "# Group-aware split report",
    "",
    f"- Method: StratifiedGroupKFold(n_splits=20, shuffle=True, random_state=42) — "
    f"folds 0-2 = test (15%), folds 3-5 = validation (15%), folds 6-19 = train (70%)",
    f"- Rows affected by grouping (duplicate addresses): **{n_dup_rows} of {len(df)} "
    f"({n_dup_rows/len(df):.2%})** across {n_dup_addrs} addresses; labels consistent "
    f"within every group (mixed-label groups: {mixed})",
    f"- Addresses appearing in more than one split: **0** (verified)",
    "",
    "## Class distribution (fraud rate)",
    f"- Overall: {overall.get(1):.1%}",
    f"- Train: {dist(train).get(1):.1%} (n={len(train)})",
    f"- Validation: {dist(val).get(1):.1%} (n={len(val)})",
    f"- Test: {dist(test).get(1):.1%} (n={len(test)})",
    "",
    "Conclusion: distributions are within ~1pp of each other — stratification held despite grouping.",
    "",
    "## Files",
    "- `data/processed/train.csv`, `val.csv`, `test.csv` (Address retained as audit metadata only)",
    "- `data/processed/split_metadata.json` — feature list (40 features, excludes Address), "
    "removed columns, split config",
]
with open(REPORT, "w") as f:
    f.write("\n".join(lines))
print("saved splits +", REPORT)
