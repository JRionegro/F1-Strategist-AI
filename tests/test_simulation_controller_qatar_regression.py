"""Regression tests for lap progression in simulation controller."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd

from src.session.simulation_controller import SimulationController


def _build_shifted_lap_data() -> pd.DataFrame:
    """Return lap timing payload with a large absolute offset like Qatar 2025."""
    return pd.DataFrame(
        {
            "LapNumber": [1, 2, 3, 4],
            "DriverNumber": [1, 1, 1, 1],
            "LapStartTime_seconds": [3521.498, 3610.707, 3700.115, 3788.200],
            "LapEndTime_seconds": [3610.707, 3700.115, 3788.200, 3877.300],
        }
    )


def test_controller_rebases_shifted_lap_seconds() -> None:
    """Controller should normalize shifted lap timings so lap detection can progress."""
    start_time = datetime(2025, 11, 30, 16, 0, 0, tzinfo=timezone.utc)
    end_time = start_time + timedelta(seconds=600)

    controller = SimulationController(
        start_time=start_time,
        end_time=end_time,
        lap_data=_build_shifted_lap_data(),
    )

    rebased_start = pd.to_numeric(
        controller.lap_data["LapStartTime_seconds"],
        errors="coerce",
    )
    assert rebased_start.min() == 0.0

    lap_two_start = float(rebased_start.iloc[1])
    assert 80.0 <= lap_two_start <= 100.0


def test_controller_progresses_beyond_lap_one_with_shifted_input() -> None:
    """Lap should move from 1 to 2+ instead of staying frozen at lap 1."""
    start_time = datetime(2025, 11, 30, 16, 0, 0, tzinfo=timezone.utc)
    end_time = start_time + timedelta(seconds=600)

    controller = SimulationController(
        start_time=start_time,
        end_time=end_time,
        lap_data=_build_shifted_lap_data(),
    )

    controller.jump_to_time(start_time + timedelta(seconds=30))
    assert controller.get_current_lap() == 1

    controller.jump_to_time(start_time + timedelta(seconds=95))
    assert controller.get_current_lap() == 2

    controller.jump_to_time(start_time + timedelta(seconds=185))
    assert controller.get_current_lap() == 3
