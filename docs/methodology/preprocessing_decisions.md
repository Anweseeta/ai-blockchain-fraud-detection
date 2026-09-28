# Preprocessing decisions (Phase 2)

Every transformation is fit **only on the training split** (`notebooks/01_group_split.py`
produced train/val/test). The fitted artifact is `models/preprocessor.joblib`.
Implementation: `src/preprocessing/pipeline.py` (sklearn `ColumnTransformer` + `Pipeline`).

Input: 39 features (37 numeric + 2 categorical). Output: 52 columns
(37 numeric scaled + 15 one-hot). Raw CSVs untouched under `data/raw/`;
processed arrays in `data/processed/{train,val,test}_processed.npz`.

---

## D1 — ERC20 numeric missing values → 0

- **What:** `SimpleImputer(strategy="constant", fill_value=0)` on the 15 ERC20 numeric columns.
- **Why:** Verified on train before applying: the *identical* row set (574 rows, 8.3%) is
  missing across all 15 ERC20 numeric columns, and all 574 also lack token-type info —
  coherent with "this account never touched ERC20 tokens". Additionally, rows with
  *observed* `Total ERC20 tnxs == 0` (3,075 rows) all carry token type `'0'`, confirming the
  source encodes "no token activity" as zero/missing rather than dropping rows.
- **Alternatives:** dropping the 574 rows (rejected — biases the sample against non-token
  users); median imputation (rejected — median of an activity count is not "no activity").
- **Leakage:** none — a constant fill has nothing to fit.

## D2 — token-type categoricals → `none` + one-hot with infrequent grouping

- **What:** `TokenTypeCleaner` maps `'0'`, `' '`, `''`, NaN → `'none'` (fixed mapping, no fitting),
  then `OneHotEncoder(handle_unknown="ignore", min_frequency=0.01)`. Result: 15 columns —
  per token column, the frequent tokens (EOS, Golem, OmiseGO, …), `none`, and one
  `infrequent_sklearn` bucket.
- **Why:** 304/466 raw token names are too high-cardinality for plain one-hot; missingness
  itself is class-informative (NaN 38% in fraud vs 24% in legit on the full data), so it must
  become an explicit category rather than being dropped. `min_frequency=0.01` keeps
  interpretable top tokens while bounding dimensionality.
- **Alternatives:** target encoding (rejected for now — needs careful CV to avoid leakage and
  hurts SHAP readability); plain top-k one-hot (equivalent in practice; infrequent bucket is
  the sklearn-native form).
- **Leakage:** the cleaner is a fixed mapping; the encoder's vocabulary and infrequent
  threshold are fit on train only; `handle_unknown="ignore"` makes unseen inference-time
  tokens safe.

## D3 — other numeric missing values → median (safety net)

- **What:** `SimpleImputer(strategy="median")` on the 22 non-ERC20 numerics.
- **Why:** zero missing observed on train — this is purely defensive so the pipeline never
  crashes on a future row with a missing value.
- **Alternatives:** none serious. **Leakage:** medians are computed on train only.

## D4 — skew-triggered signed log1p (|skew| > 2, fit on train)

- **What:** `SkewLogTransformer` computes per-column skew on the (imputed) train data and
  applies `sign(x)·log1p(|x|)` to the 36 columns exceeding the threshold. `max value received`
  was the only numeric below threshold and stays linear. Signed form keeps the one
  negative-capable column (`total ether balance`) valid.
- **Why:** value/time columns span 6–12 orders of magnitude; raw scales would let linear
  models be dominated by extreme values. Monotonic, so tree models are unaffected — one
  artifact serves both model families.
- **Alternatives:** separate scaled/unscaled artifacts per model family (rejected — doubles
  artifact surface and inference complexity); Box-Cox/Yeo-Johnson (rejected — less
  interpretable, needs positivity handling anyway).
- **Leakage:** skew statistics and the transformed-column list are fit on train only.

## D5 — StandardScaler on all numerics

- **What:** after imputation + log transform.
- **Why:** required for the Logistic Regression baseline and any distance-based steps;
  harmless for trees. Single artifact (see D4).
- **Alternatives:** RobustScaler (considered — IQR outlier fractions reach 31% on some
  columns, but in fraud data extremes may be signal; StandardScaler keeps the transform
  simple and the decision is documented, not hidden).
- **Leakage:** mean/variance fit on train only.

## D6 — no SMOTE in preprocessing

- **What:** imbalance (1:3.5) is left as-is at this stage.
- **Why:** per the brief, class-weighting and threshold tuning are evaluated as modeling
  decisions later; baking resampling into the artifact now would hide that comparison.
- **Alternatives:** SMOTE on train only — kept as an explicit experiment for Phase 5/6.

## D7 — excluded columns

- `Address`: used solely as the grouping variable for the split (see
  `docs/methodology/group_aware_split.md`); **not** a model feature. Retained in the
  processed CSVs as an audit column only.
- `Unnamed: 0`, `Index`: label-order leakage (r = 0.72 / −0.32 with FLAG), removed in Phase 1.
- 7 constant-zero ERC20 columns + 1 unverifiable column: removed in Phase 1.

## D8 — artifact portability

- **What:** the driver imports `src.preprocessing.pipeline`, so the pickled artifact
  references `src.preprocessing.pipeline.*` and loads anywhere with the repo root on
  `sys.path` (verified with a fresh interpreter + inference smoke test).
- **Why:** the backend will load this exact artifact; an unpicklable-by-backend artifact
  would silently break deployment later.
- **Leakage:** n/a (engineering decision).

## D9 — EDA confined to the train split

- **What:** all distributions, correlations, and class comparisons use train only.
- **Why:** test-set statistics must not influence feature or modeling choices; the test set
  stays locked until final evaluation.
