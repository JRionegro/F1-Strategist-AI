"""Baseline predictive models for pit decisions.

Implements a simple logistic regression baseline for pit-stop probability.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Tuple

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline


FEATURE_COLUMNS: Tuple[str, ...] = (
    "stint_lap",
    "last_lap_time_s",
    "rolling_lap_time_s",
    "gap_ahead_s",
    "gap_behind_s",
    "position",
)


def _prepare_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    """Prepare features and labels from pit-window dataset."""

    required = set(FEATURE_COLUMNS) | {"lap_number", "pit_window_center_lap"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"dataset missing required columns: {
                sorted(missing)}")

    label = df["pit_window_center_lap"].notna().astype(int)

    features = df.loc[:, list(FEATURE_COLUMNS)].copy()
    features = features.infer_objects(copy=False)
    features = features.fillna(0.0)

    return features, label


@dataclass
class PitStopBaselineModel:
    """Logistic regression baseline for pit-stop probability."""

    max_iter: int = 200
    solver: Literal["lbfgs", "liblinear", "newton-cg",
                    "newton-cholesky", "sag", "saga"] = "lbfgs"

    def __post_init__(self) -> None:
        self.pipeline = Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "clf",
                    LogisticRegression(
                        max_iter=self.max_iter,
                        solver=self.solver,
                    ),
                ),
            ]
        )
        self._is_fitted = False

    def fit(self, df: pd.DataFrame) -> "PitStopBaselineModel":
        """Fit the baseline model."""

        features, label = _prepare_features(df)
        if label.nunique() < 2:
            raise ValueError(
                "label must contain at least one positive and one negative example")

        self.pipeline.fit(features, label)
        self._is_fitted = True
        return self

    def predict_proba(self, df: pd.DataFrame) -> np.ndarray:
        """Predict pit-stop probability."""

        if not self._is_fitted:
            raise RuntimeError("model is not fitted")

        features, _ = _prepare_features(df)
        return self.pipeline.predict_proba(features)[:, 1]

    def predict(self, df: pd.DataFrame, threshold: float = 0.5) -> np.ndarray:
        """Predict binary pit-stop decisions using a probability threshold."""

        proba = self.predict_proba(df)
        return (proba >= threshold).astype(int)


__all__ = ["FEATURE_COLUMNS", "PitStopBaselineModel"]
