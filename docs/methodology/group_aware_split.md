# Methodology decision — group-aware split on `Address` (leakage prevention)

**Date:** 2026-09-25
**Status:** implemented in `notebooks/01_group_split.py`

## What was chosen
`Address` is used **only as a grouping variable** for dataset splitting, never as a model feature.

- Split method: `StratifiedGroupKFold(n_splits=20, shuffle=True, random_state=42)` —
  folds 0–2 → test (15%, n=1,476), folds 3–5 → validation (15%, n=1,476), folds 6–19 → train (70%, n=6,889).
- `Address` is retained in the processed CSVs as an audit/metadata column, but is **excluded
  from the modeling feature list** (`data/processed/split_metadata.json`: 40 features, no Address).

## Why
25 addresses (50 rows, 0.51% of the data) appear twice in the dataset with mutually consistent
labels. A plain random split could place the two rows of the same account in different partitions,
letting the model memorize an account seen in training and be "tested" on the same account —
a small but real train/test leakage path. Grouping guarantees each address lives in exactly
one partition (verified: 0 addresses span splits).

## Alternatives considered
- Plain stratified random split — simpler, but allows the 50 duplicated rows to straddle
  partitions. Rejected: leakage, however small, is unacceptable in a fraud-detection study.
- Dropping the 50 duplicate rows — loses valid data for no modeling benefit since labels are
  consistent. Rejected.
- Using Address as a feature — rejected outright: it is a unique identifier with no
  generalization value; a model would memorize it.

## Evidence
- Duplicate-address rows: 50 (0.51%); mixed-label groups: 0
- Post-split fraud rates: train 22.14%, validation 22.15%, test 22.15% — stratification held
  despite grouping (see `reports/split_report.md`)

## Limitations
- Only 25 duplicated addresses, so the practical effect is tiny — this is a correctness measure,
  not a performance one. Documented as such to avoid overstating its impact.
