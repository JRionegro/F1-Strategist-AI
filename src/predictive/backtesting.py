"""Backtesting harness for baseline pit-stop models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score

from .modeling import PitStopBaselineModel, _prepare_features


@dataclass
class BacktestResult:
    """Summary of backtest metrics."""

    auc: Optional[float]
    brier: float
    positive_rate: float
    n_train: int
    n_test: int

    def as_dict(self) -> Dict[str, Any]:
        return {
            "auc": self.auc,
            "brier": self.brier,
            "positive_rate": self.positive_rate,
            "n_train": self.n_train,
            "n_test": self.n_test,
        }


def time_order_split(df: pd.DataFrame,
                     test_fraction: float = 0.3) -> tuple[pd.DataFrame,
                                                          pd.DataFrame]:
    """Deterministic time-ordered split to avoid leakage."""

    if not 0 < test_fraction < 1:
        raise ValueError("test_fraction must be between 0 and 1")

    df_sorted = df.sort_values(
        by=["lap_number", "driver_id"]).reset_index(drop=True)
    split_idx = int(len(df_sorted) * (1 - test_fraction))
    if split_idx <= 0 or split_idx >= len(df_sorted):
        raise ValueError("test_fraction results in empty split")

    return df_sorted.iloc[:split_idx].copy(), df_sorted.iloc[split_idx:].copy()


def backtest_pit_baseline(
    df: pd.DataFrame,
    *,
    test_fraction: float = 0.3,
    max_iter: int = 200,
) -> tuple[PitStopBaselineModel, BacktestResult]:
    """Train/test split backtest for the baseline pit model."""

    train_df, test_df = time_order_split(df, test_fraction=test_fraction)

    model = PitStopBaselineModel(max_iter=max_iter)
    model.fit(train_df)

    features_test, labels_test = _prepare_features(test_df)
    proba = model.pipeline.predict_proba(features_test)[:, 1]

    auc: Optional[float]
    try:
        auc = float(roc_auc_score(labels_test, proba))
    except ValueError:
        auc = None

    brier = float(brier_score_loss(labels_test, proba))
    positive_rate = float(np.mean(labels_test)) if len(labels_test) else 0.0

    result = BacktestResult(
        auc=auc,
        brier=brier,
        positive_rate=positive_rate,
        n_train=len(train_df),
        n_test=len(test_df),
    )

    return model, result


__all__ = ["BacktestResult", "time_order_split", "backtest_pit_baseline"]
