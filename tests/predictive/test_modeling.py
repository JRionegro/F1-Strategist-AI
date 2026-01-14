"""Tests for baseline pit-stop model."""

from __future__ import annotations

import pandas as pd
import pytest

from src.predictive.dataset_builder import build_pit_window_dataset
from src.predictive.modeling import FEATURE_COLUMNS, PitStopBaselineModel


@pytest.fixture
def sample_dataset() -> pd.DataFrame:
    states = []
    for lap in range(1, 7):
        states.append(
            {
                "driver_id": "HAM",
                "lap_number": lap,
                "compound": "MEDIUM",
                "last_lap_time_s": 90.0 + lap * 0.1,
                "position": 2,
                "gap_ahead_s": 1.0,
                "gap_behind_s": 0.5,
                "last_pit_lap": None if lap < 4 else 3,
            }
        )
    pit_laps = {"HAM": [4]}
    return build_pit_window_dataset(states, pit_laps, window_half_width=0, horizon_laps=10)


def test_feature_columns_present(sample_dataset: pd.DataFrame) -> None:
    missing = set(FEATURE_COLUMNS) - set(sample_dataset.columns)
    assert not missing


def test_model_trains_and_predicts(sample_dataset: pd.DataFrame) -> None:
    model = PitStopBaselineModel(max_iter=50)
    model.fit(sample_dataset)

    proba = model.predict_proba(sample_dataset)
    assert proba.shape[0] == len(sample_dataset)
    assert (proba >= 0).all() and (proba <= 1).all()

    preds = model.predict(sample_dataset, threshold=0.4)
    assert set(preds).issubset({0, 1})


def test_model_requires_positive_and_negative(sample_dataset: pd.DataFrame) -> None:
    positive_only = sample_dataset.copy()
    positive_only["pit_window_center_lap"] = 5

    model = PitStopBaselineModel()
    with pytest.raises(ValueError):
        model.fit(positive_only)
