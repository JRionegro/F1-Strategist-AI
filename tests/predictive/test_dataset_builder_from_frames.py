"""Integration-style tests for Phase 4B dataset builder from frames."""

from __future__ import annotations

import pandas as pd

from src.predictive.dataset_builder import (
    build_pit_window_dataset_from_frames,
    persist_dataset,
)
from src.predictive.schemas import PIT_WINDOW_REQUIRED_COLUMNS


def _sample_frames():
    laps = pd.DataFrame(
        [
            {"driver_id": "HAM", "lap_number": 1, "lap_time_s": 91.0, "position": 3, "gap_ahead_s": 1.5},
            {"driver_id": "HAM", "lap_number": 2, "lap_time_s": 90.5, "position": 3, "gap_ahead_s": 1.4},
            {"driver_id": "HAM", "lap_number": 3, "lap_time_s": 90.3, "position": 2, "gap_ahead_s": 0.8},
            {"driver_id": "HAM", "lap_number": 4, "lap_time_s": 90.1, "position": 2, "gap_ahead_s": 0.6},
            {"driver_id": "HAM", "lap_number": 5, "lap_time_s": 89.9, "position": 2, "gap_ahead_s": 0.5},
            {"driver_id": "VER", "lap_number": 1, "lap_time_s": 90.0, "position": 1},
            {"driver_id": "VER", "lap_number": 2, "lap_time_s": 89.8, "position": 1},
            {"driver_id": "VER", "lap_number": 3, "lap_time_s": 89.7, "position": 1},
            {"driver_id": "VER", "lap_number": 4, "lap_time_s": 89.6, "position": 1},
            {"driver_id": "VER", "lap_number": 5, "lap_time_s": 89.5, "position": 1},
        ]
    )

    pit_events = pd.DataFrame(
        [
            {"driver_id": "HAM", "lap_number": 3},
        ]
    )

    return laps, pit_events


def test_build_from_frames_contract_and_determinism(tmp_path) -> None:
    laps, pit_events = _sample_frames()

    df1 = build_pit_window_dataset_from_frames(
        laps,
        pit_events,
        window_half_width=0,
        horizon_laps=10,
        rolling_window=2,
    )
    df2 = build_pit_window_dataset_from_frames(
        laps,
        pit_events,
        window_half_width=0,
        horizon_laps=10,
        rolling_window=2,
    )

    assert tuple(df1.columns) == PIT_WINDOW_REQUIRED_COLUMNS
    assert df1.equals(df2)

    # Persist and ensure file written
    out_path = persist_dataset(df1, tmp_path / "pit_window.csv")
    assert out_path.exists()

    # Core identifiers must be populated
    required_no_na = ["driver_id", "lap_number", "stint_lap"]
    assert df1[required_no_na].isna().sum().sum() == 0


def test_build_from_frames_handles_missing_pits() -> None:
    laps, _ = _sample_frames()

    df = build_pit_window_dataset_from_frames(laps, pit_events=None, window_half_width=0, horizon_laps=10)

    assert len(df) == len(laps)
    assert "pit_window_center_lap" in df.columns
