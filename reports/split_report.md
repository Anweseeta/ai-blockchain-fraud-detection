# Group-aware split report

- Method: StratifiedGroupKFold(n_splits=20, shuffle=True, random_state=42) — folds 0-2 = test (15%), folds 3-5 = validation (15%), folds 6-19 = train (70%)
- Rows affected by grouping (duplicate addresses): **50 of 9841 (0.51%)** across 25 addresses; labels consistent within every group (mixed-label groups: 0)
- Addresses appearing in more than one split: **0** (verified)

## Class distribution (fraud rate)
- Overall: 22.1%
- Train: 22.1% (n=6889)
- Validation: 22.1% (n=1476)
- Test: 22.1% (n=1476)

Conclusion: distributions are within ~1pp of each other — stratification held despite grouping.

## Files
- `data/processed/train.csv`, `val.csv`, `test.csv` (Address retained as audit metadata only)
- `data/processed/split_metadata.json` — feature list (39 features, excludes Address), removed columns, split config