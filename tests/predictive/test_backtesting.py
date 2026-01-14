"""Backtesting harness tests."""

from __future__ import annotations

import pandas as pd

from src.predictive.backtesting import backtest_pit_baseline, time_order_split
from src.predictive.dataset_builder import build_pit_window_dataset
from src.predictive.real_backtest import METRICS_DIR, backtest_race


def _make_dataset() -> pd.DataFrame:
    states = []
    for lap in range(1, 11):
        states.append(
            {
                "driver_id": "VER" if lap % 2 == 0 else "HAM",
                "lap_number": lap,
                "compound": "MEDIUM",
                "last_lap_time_s": 90.0 + lap * 0.2,
                "position": 1 if lap % 2 == 0 else 2,
                "gap_ahead_s": 0.5,
                "gap_behind_s": 1.0,
                "last_pit_lap": None,
            }
        )
    pit_laps = {"VER": [12], "HAM": [12]}
    return build_pit_window_dataset(states, pit_laps, window_half_width=0, horizon_laps=10)


def test_time_order_split_is_deterministic() -> None:
    df = _make_dataset()
    train_a, test_a = time_order_split(df, test_fraction=0.4)
    train_b, test_b = time_order_split(df, test_fraction=0.4)

    assert train_a.equals(train_b)
    assert test_a.equals(test_b)
    assert len(train_a) + len(test_a) == len(df)


def test_backtest_runs_and_returns_metrics() -> None:
    df = _make_dataset()
    model, result = backtest_pit_baseline(df, test_fraction=0.3, max_iter=50)

    assert result.n_train > 0 and result.n_test > 0
    assert 0 <= result.brier <= 1
    assert result.positive_rate > 0

    proba = model.predict_proba(df)
    assert len(proba) == len(df)


def test_real_backtest_saves_metrics_and_artifact(tmp_path, monkeypatch) -> None:
    # Use synthetic cache data via monkeypatching CacheManager to avoid IO
    from src.predictive import real_backtest
    from src.predictive import dataset_builder

    class _FakeCacheManager:
        def __init__(self, *args, **kwargs):
            self.config = type("Cfg", (), {"processed_dir": tmp_path / "processed"})

        def get_cached_race_data(self, year, race_name, data_type):
            # Simple 4-lap dataset with a pit on lap 3 for one driver
            laps = pd.DataFrame(
                [
                    {"Driver": "HAM", "LapNumber": 1, "LapTime_seconds": 90.1, "Compound": "MEDIUM", "Position": 1},
                    {"Driver": "HAM", "LapNumber": 2, "LapTime_seconds": 90.0, "Compound": "MEDIUM", "Position": 1},
                    {"Driver": "HAM", "LapNumber": 3, "LapTime_seconds": 89.9, "Compound": "HARD", "Position": 2},
                    {"Driver": "HAM", "LapNumber": 4, "LapTime_seconds": 89.8, "Compound": "HARD", "Position": 2},
                    {"Driver": "VER", "LapNumber": 1, "LapTime_seconds": 89.9, "Compound": "SOFT", "Position": 2},
                    {"Driver": "VER", "LapNumber": 2, "LapTime_seconds": 89.8, "Compound": "SOFT", "Position": 2},
                    {"Driver": "VER", "LapNumber": 3, "LapTime_seconds": 89.7, "Compound": "SOFT", "Position": 2},
                    {"Driver": "VER", "LapNumber": 4, "LapTime_seconds": 89.6, "Compound": "SOFT", "Position": 2},
                ]
            )

            pits = pd.DataFrame([{"Driver": "HAM", "LapNumber": 3}])

            if data_type.name == "LAP_TIMES":
                return laps
            return pits

    monkeypatch.setattr(real_backtest, "CacheManager", _FakeCacheManager)
    monkeypatch.setattr(dataset_builder, "CacheManager", _FakeCacheManager)

    metrics_path = backtest_race(year=2024, race_name="demo", cache_config=None, test_fraction=0.3, max_iter=50)

    assert metrics_path.exists()
    assert METRICS_DIR.exists()
