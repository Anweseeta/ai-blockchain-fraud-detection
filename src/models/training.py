"""Shared supervised-training utilities: metrics, threshold sweeps, plots.

All metrics are computed with sklearn on actual model outputs — nothing is estimated.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)


def metrics_at_threshold(y_true: np.ndarray, y_proba: np.ndarray, threshold: float) -> dict:
    """Full metric set at one decision threshold."""
    y_pred = (y_proba >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {
        "threshold": round(float(threshold), 4),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, y_proba)),
        "pr_auc": float(average_precision_score(y_true, y_proba)),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
        "support_0": int((y_true == 0).sum()),
        "support_1": int((y_true == 1).sum()),
    }


def threshold_sweep(
    y_true: np.ndarray, y_proba: np.ndarray, thresholds: np.ndarray | None = None
) -> pd.DataFrame:
    """Precision/recall/F1 across thresholds (for validation-set threshold selection)."""
    if thresholds is None:
        thresholds = np.arange(0.05, 0.96, 0.05)
    rows = []
    for t in thresholds:
        m = metrics_at_threshold(y_true, y_proba, float(t))
        rows.append(
            {"threshold": m["threshold"], "precision": m["precision"],
             "recall": m["recall"], "f1": m["f1"], "fp": m["fp"], "fn": m["fn"]}
        )
    return pd.DataFrame(rows)


def classification_report_dict(y_true: np.ndarray, y_proba: np.ndarray, threshold: float) -> dict:
    """Per-class precision/recall/F1 at a threshold."""
    from sklearn.metrics import precision_recall_fscore_support

    y_pred = (y_proba >= threshold).astype(int)
    p, r, f, s = precision_recall_fscore_support(y_true, y_pred, labels=[0, 1], zero_division=0)
    return {
        "legit": {"precision": float(p[0]), "recall": float(r[0]), "f1": float(f[0]), "support": int(s[0])},
        "fraud": {"precision": float(p[1]), "recall": float(r[1]), "f1": float(f[1]), "support": int(s[1])},
    }


def roc_points(y_true, y_proba):
    fpr, tpr, _ = roc_curve(y_true, y_proba)
    return fpr, tpr


def pr_points(y_true, y_proba):
    precision, recall, _ = precision_recall_curve(y_true, y_proba)
    return precision, recall
