"""Preprocessing pipeline for the blockchain fraud detection project.

Design rules (see docs/methodology/preprocessing_decisions.md):
- Fit ONLY on the training split; transform validation/test without refitting.
- ERC20 numeric columns: NaN means "no token activity" -> impute 0.
- Other numeric columns: median imputation (safety net; no missing observed),
  skew-triggered log transform, then standard scaling.
- Token-type categoricals: clean '0'/' '/NaN -> 'none', one-hot with infrequent grouping.
- Address / Unnamed: 0 / Index are never model features (handled before this module).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

# Raw values in the token-type columns that all mean "no token / unknown".
NONE_LIKE = {"0", ""}


class TokenTypeCleaner(BaseEstimator, TransformerMixin):
    """Map every 'none-like' token-type value ('0', ' ', '', NaN) to 'none'.

    Fixed mapping — no fitting, so no leakage. Applied before one-hot encoding.
    """

    def fit(self, X, y=None):
        self.input_features_ = list(pd.DataFrame(X).columns)
        return self

    def transform(self, X):
        X = pd.DataFrame(X).copy()
        for c in X.columns:
            X[c] = X[c].apply(
                lambda v: "none" if (pd.isna(v) or str(v).strip() in NONE_LIKE) else str(v).strip()
            )
        return X

    def get_feature_names_out(self, input_features=None):
        return np.asarray(input_features if input_features is not None else self.input_features_)


class SkewLogTransformer(BaseEstimator, TransformerMixin):
    """Apply signed log1p to columns whose |skew| exceeds a threshold (fit on train).

    Signed log1p (sign(x) * log1p(|x|)) handles heavy right tails and is safe for
    the one column with negative values (total ether balance). Monotonic, so tree
    models are unaffected while linear/distance models get stabilized scales.
    """

    def __init__(self, skew_threshold: float = 2.0):
        self.skew_threshold = skew_threshold

    def fit(self, X, y=None):
        X = pd.DataFrame(X)
        self.input_features_ = list(X.columns)
        skew = X.skew(numeric_only=True).abs()
        self.log_cols_ = skew[skew > self.skew_threshold].index.tolist()
        return self

    def transform(self, X):
        X = pd.DataFrame(X).copy()
        for c in self.log_cols_:
            v = X[c].to_numpy(dtype=float)
            X[c] = np.sign(v) * np.log1p(np.abs(v))
        return X

    def get_feature_names_out(self, input_features=None):
        return np.asarray(input_features if input_features is not None else self.input_features_)


def build_preprocessor(
    erc20_numeric: list[str],
    other_numeric: list[str],
    categorical: list[str],
    skew_threshold: float = 2.0,
    min_token_frequency: float = 0.01,
) -> ColumnTransformer:
    """Build the full (unfitted) preprocessing ColumnTransformer."""
    erc20_pipe = Pipeline(
        [
            ("impute_zero", SimpleImputer(strategy="constant", fill_value=0)),
            ("skew_log", SkewLogTransformer(skew_threshold=skew_threshold)),
            ("scale", StandardScaler()),
        ]
    )
    numeric_pipe = Pipeline(
        [
            ("impute_median", SimpleImputer(strategy="median")),
            ("skew_log", SkewLogTransformer(skew_threshold=skew_threshold)),
            ("scale", StandardScaler()),
        ]
    )
    cat_pipe = Pipeline(
        [
            ("clean", TokenTypeCleaner()),
            (
                "onehot",
                OneHotEncoder(
                    handle_unknown="ignore",
                    sparse_output=False,
                    min_frequency=min_token_frequency,
                ),
            ),
        ]
    )
    # pandas output through the numeric branches so SkewLogTransformer sees
    # real column names (needed for the logged-column record in metadata)
    erc20_pipe.set_output(transform="pandas")
    numeric_pipe.set_output(transform="pandas")
    return ColumnTransformer(
        [
            ("erc20_num", erc20_pipe, erc20_numeric),
            ("num", numeric_pipe, other_numeric),
            ("cat", cat_pipe, categorical),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )


def _is_categorical(dtype) -> bool:
    # pandas 3.x infers `str` (StringDtype), not `object`, for string columns
    return dtype == object or isinstance(dtype, pd.StringDtype)


def split_feature_groups(feature_cols: list[str], df: pd.DataFrame):
    """Partition feature columns into (erc20_numeric, other_numeric, categorical)."""
    categorical = [c for c in feature_cols if _is_categorical(df[c].dtype)]
    numeric = [c for c in feature_cols if c not in categorical]
    erc20_numeric = [c for c in numeric if "erc20" in c.lower()]
    other_numeric = [c for c in numeric if c not in erc20_numeric]
    return erc20_numeric, other_numeric, categorical
