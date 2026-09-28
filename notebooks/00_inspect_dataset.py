"""Phase 1 dataset inspection — no assumptions about structure.
Reads the raw CSV and produces a full profile to stdout + reports/dataset_profile.md."""
import json
import pandas as pd
import numpy as np

RAW = "/home/hatch/workspace/ai-blockchain-fraud-detection/data/raw/transaction_dataset.csv"
OUT = "/home/hatch/workspace/ai-blockchain-fraud-detection/reports/dataset_profile.md"

df = pd.read_csv(RAW)
lines = []

def add(s=""):
    lines.append(s)

add("# Dataset Profile — transaction_dataset.csv")
add("")
add(f"- Rows: {df.shape[0]} (excl. header), Columns: {df.shape[1]}")
add(f"- Memory: {df.memory_usage(deep=True).sum()/1e6:.2f} MB")
add("")

add("## Column names (in order)")
for i, c in enumerate(df.columns):
    add(f"{i}. {c}")
add("")

add("## Dtypes")
add(df.dtypes.astype(str).to_string())
add("")

add("## Missing values")
miss = df.isna().sum()
miss = miss[miss > 0]
if len(miss):
    add(miss.to_string())
else:
    add("None — zero missing values in every column.")
add("")

add("## Duplicate rows")
add(f"Fully duplicated rows: {df.duplicated().sum()}")
add(f"Unique addresses: {df['Address'].nunique()} of {len(df)} rows")
add("")

add("## Unique-value counts per column")
uniq = df.nunique(dropna=False).sort_values()
add(uniq.to_string())
add("")

obj = [c for c in df.columns if df[c].dtype == object]
add("## Object (categorical-ish) columns")
for c in obj:
    vals = df[c].value_counts(dropna=False)
    add(f"- {c}: {df[c].nunique()} unique, top: {vals.index[:3].tolist()} counts={vals.iloc[:3].tolist()}")
add("")

add("## Numeric summary (describe)")
with pd.option_context("display.width", 200, "display.max_columns", 60):
    add(df.describe(include=[np.number]).T.to_string())
add("")

# Target
if "FLAG" in df.columns:
    add("## Target: FLAG")
    vc = df["FLAG"].value_counts(dropna=False)
    add(vc.to_string())
    n0 = int(vc.get(0, 0)); n1 = int(vc.get(1, 0))
    add(f"legit(0)={n0} ({n0/len(df):.1%}), fraud(1)={n1} ({n1/len(df):.1%}), imbalance ratio 1:{n0/max(n1,1):.1f}")
    # check FLAG is strictly binary
    add(f"Unique FLAG values: {sorted(df['FLAG'].dropna().unique().tolist())}")
    add(f"FLAG dtype: {df['FLAG'].dtype}")
add("")

# Correlation with FLAG (numeric)
num = df.select_dtypes(include=[np.number]).columns.tolist()
corr = df[num].corr(numeric_only=True)["FLAG"].drop("FLAG").sort_values(ascending=False)
add("## Pearson correlation with FLAG (top 10 abs)")
top = corr.reindex(corr.abs().sort_values(ascending=False).index)[:10]
add(top.to_string())
add("")

# Impossible/invalid checks
add("## Sanity checks")
checks = []
for c in num:
    s = df[c]
    if (s < 0).any():
        checks.append(f"{c}: has negatives (min={s.min()})")
    if np.isinf(s).any():
        checks.append(f"{c}: has inf")
if "total transactions (including tnx to create contract" in df.columns or True:
    c = [x for x in df.columns if x.startswith("total transactions")][0]
    checks.append(f"{c}: zeros={int((df[c]==0).sum())}, min={df[c].min()}, max={df[c].max()}")
add("\n".join("- " + x for x in checks))
add("")

# Outliers: IQR
add("## Outliers (IQR method, % beyond 1.5*IQR)")
out = {}
for c in num:
    s = df[c].dropna()
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = q3 - q1
    if iqr > 0:
        frac = ((s < q1 - 1.5*iqr) | (s > q3 + 1.5*iqr)).mean()
        out[c] = round(float(frac), 4)
out = dict(sorted(out.items(), key=lambda x: -x[1]))
add(json.dumps(dict(list(out.items())[:15]), indent=1))
add("")

# Address reuse / identifier leakage probe: are duplicate addresses consistent in FLAG?
dups = df[df.duplicated("Address", keep=False)]
add(f"## Address duplication: {len(dups)} rows share an Address with another row")
if len(dups):
    grp = dups.groupby("Address")["FLAG"].nunique()
    add(f"Addresses with mixed FLAG values: {(grp > 1).sum()}")

report = "\n".join(lines)
with open(OUT, "w") as f:
    f.write(report)
print(report[:12000])
