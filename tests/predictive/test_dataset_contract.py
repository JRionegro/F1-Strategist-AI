"""Contract tests for predictive datasets.

These tests are designed to be fast and deterministic.
They use synthetic state sequences (no network/API dependencies).
"""

from __future__ import annotations

import pandas as pd

from src.predictive.dataset_builder import build_pit_window_dataset
from src.predictive.schemas import PIT_WINDOW_REQUIRED_COLUMNS


def test_pit_window_dataset_contract_is_stable() -> None:
    """Dataset builder returns stable columns and valid label ranges."""
    states = []
    for lap in range(1, 11):
        states.append(
            {
                "driver_id": "HAM",
                "lap_number": lap,
                "compound": "MEDIUM",
                "last_lap_time_s": 90.0 + (lap * 0.1),
                "position": 3,
                "gap_ahead_s": 1.2,
                "gap_behind_s": 0.9,
                "last_pit_lap": None,
            }
        )

    pit_laps_by_driver = {"HAM": [6]}

    df_1 = build_pit_window_dataset(states, pit_laps_by_driver, window_half_width=1, horizon_laps=10)
    df_2 = build_pit_window_dataset(states, pit_laps_by_driver, window_half_width=1, horizon_laps=10)

    assert tuple(df_1.columns) == PIT_WINDOW_REQUIRED_COLUMNS
    assert df_1.equals(df_2)

    assert df_1["driver_id"].isna().sum() == 0
    assert (df_1["lap_number"] >= 1).all()

    labeled = df_1.dropna(subset=["pit_window_center_lap"]).copy()
    if not labeled.empty:
        center = labeled["pit_window_center_lap"].astype(int)
        start = labeled["pit_window_start_lap"].astype(int)
        end = labeled["pit_window_end_lap"].astype(int)

        assert (start <= center).all()
        assert (center <= end).all()

        assert (center > labeled["lap_number"]).all()
        assert (start > labeled["lap_number"]).all()
        assert (end > labeled["lap_number"]).all()


def test_pit_window_dataset_returns_dataframe() -> None:
    """Smoke test: builder returns a pandas DataFrame."""
    df = build_pit_window_dataset(
        states=[{"driver_id": "VER", "lap_number": 1, "last_lap_time_s": 92.0}],
        pit_laps_by_driver={"VER": [10]},
        window_half_width=0,
        horizon_laps=20,
    )
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
