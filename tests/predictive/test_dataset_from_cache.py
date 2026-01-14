"""Integration-style test building dataset from cached race data."""

from __future__ import annotations

import pandas as pd

from src.data.cache_config import CacheConfig, DataType
from src.data.cache_manager import CacheManager
from src.predictive.dataset_builder import build_pit_window_dataset_from_cache
from src.predictive.schemas import PIT_WINDOW_REQUIRED_COLUMNS


def test_build_dataset_from_cache(tmp_path) -> None:
    """End-to-end build using CacheManager cached laps/pit data."""

    config = CacheConfig(
        base_dir=tmp_path / "data",
        cache_dir=tmp_path / "cache",
        races_dir=tmp_path / "races",
        telemetry_dir=tmp_path / "telemetry",
        processed_dir=tmp_path / "processed",
        use_parquet=False,
    )

    cache_manager = CacheManager(config=config)

    laps_df = pd.DataFrame(
        [
            {"Driver": "HAM", "LapNumber": 1, "LapTime_seconds": 90.1, "Compound": "MEDIUM", "Position": 1},
            {"Driver": "HAM", "LapNumber": 2, "LapTime_seconds": 90.0, "Compound": "MEDIUM", "Position": 1},
            {"Driver": "HAM", "LapNumber": 3, "LapTime_seconds": 89.9, "Compound": "HARD", "Position": 2},
            {"Driver": "VER", "LapNumber": 1, "LapTime_seconds": 89.5, "Compound": "SOFT", "Position": 2},
            {"Driver": "VER", "LapNumber": 2, "LapTime_seconds": 89.4, "Compound": "SOFT", "Position": 1},
            {"Driver": "VER", "LapNumber": 3, "LapTime_seconds": 89.6, "Compound": "MEDIUM", "Position": 1},
        ]
    )

    pits_df = pd.DataFrame(
        [
            {"Driver": "HAM", "LapNumber": 3},
            {"Driver": "VER", "LapNumber": 3},
        ]
    )

    cache_manager.save_race_data(2024, "demo", DataType.LAP_TIMES, laps_df)
    cache_manager.save_race_data(2024, "demo", DataType.PIT_STOPS, pits_df)

    dataset = build_pit_window_dataset_from_cache(
        cache_manager,
        2024,
        "demo",
        window_half_width=0,
        horizon_laps=5,
        rolling_window=2,
        persist=True,
    )

    expected_path = config.processed_dir / "predictive" / "2024_demo_pit_window.csv"

    assert expected_path.exists()
    assert not dataset.empty
    assert tuple(dataset.columns) == PIT_WINDOW_REQUIRED_COLUMNS
    assert dataset["driver_id"].nunique() == 2
    assert dataset["lap_number"].max() == 3
    assert dataset["pit_window_center_lap"].notna().any()
