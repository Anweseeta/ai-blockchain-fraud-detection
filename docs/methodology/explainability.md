# Explainability Methodology (SHAP)

## Why SHAP was selected

The primary model is a gradient-boosted tree ensemble (XGBoost). SHAP (SHapley Additive
exPlanations) was selected because:

1. **Exact for trees.** Tree SHAP computes exact Shapley values for tree ensembles in
   polynomial time — no sampling approximation, no surrogate model.
2. **Additive (local accuracy).** For each record, the SHAP values plus a base value sum
   exactly to the model's output. The explanation always accounts for the full prediction.
3. **One method, two levels.** The same values aggregate into global feature importance
   (mean |SHAP|) and decompose into per-record local explanations.
4. **Consistent.** If the model changes so a feature contributes more, its SHAP value
   cannot decrease — a guarantee most importance heuristics lack.

## How SHAP works (high level)

A prediction is treated as a payout in a cooperative game played by the features. Each
feature's SHAP value is its average marginal contribution to the payout across all
possible coalitions of features — i.e., how much the model's output moves when that
feature joins the set of known features, averaged over every ordering. Positive values
push the output toward fraud; negative values push it away. The base value is the
model's average output; the sum of a record's SHAP values plus the base equals that
record's model output exactly (up to floating-point error).

## Configuration used in this project

- Explainer: `shap.TreeExplainer` (tree_path_dependent, model_output="raw").
- Model: the validated Phase-3 XGBoost artifact — **not retrained**.
- Values are in **log-odds units**: sum + base = model margin, sigmoid(margin) = fraud
  probability. (Probability-output mode was blocked by a shap-0.52 / xgboost-3.x
  incompatibility; log-odds is the exact, supported path.)
- Background data: none required. Explained: full test set (1,476 records × 52 features)
  in ~1.1 s. Additivity verified: max abs error 0.037 log-odds units.
- Isolation Forest signal excluded from explanations per the operating risk policy
  (anomaly weight 0).

## Global vs local explanation

- **Global:** "What features generally influence the model?" — mean |SHAP| over the test
  set ranks features by average impact magnitude. Direction comes from the beeswarm plot
  / value–SHAP correlation.
- **Local:** "Why did this particular record receive this prediction?" — the record's own
  SHAP vector, shown as top positive/negative contributors and waterfall plots.

## Reading the wording

- "Higher X is **associated with** higher model output (toward fraud)" — an observed
  regularity in what the model learned.
- "This feature **contributed positively to the model's fraud prediction**" — a statement
  about this record's explanation.
- Never: "this feature proves/causes fraud." SHAP explains the **model**, not the world.
  If the model learned a spurious pattern, SHAP will faithfully report that pattern.

## Limitations

1. **Not causal inference.** SHAP values are attributions of a fitted function. They say
   nothing about what would happen under intervention.
2. **Correlated features share credit.** The transaction-count / ERC20-value blocks are
   mutually correlated; SHAP splits their joint contribution across them. Small rank
   differences between correlated features should not be over-interpreted.
3. **Feature-independence assumption.** The tree-path-dependent computation approximates
   conditional expectations assuming independence; with heavy correlation, some attribution
   can leak between correlated features.
4. **Explains the model, including its mistakes.** A high SHAP value on a false positive
   means the model found the record fraud-like — it does not make the record fraudulent.
5. **Units.** Log-odds contributions are comparable across features but are not
   probabilities; sign gives direction, magnitude gives relative strength.
6. **Background choice matters in general** (not applicable here — no background used).

## Computational considerations

Tree SHAP is exact and fast: 1,476 × 52 explanations in ~1.1 s on CPU, memory-trivial.
Per-record explanation at serve time is milliseconds — suitable for the future API's
explain endpoint. Reusable metadata (base value, feature names, explainer config) is
stored in `reports/shap/shap_metadata.json`.
