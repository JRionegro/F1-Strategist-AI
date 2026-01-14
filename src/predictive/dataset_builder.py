"""Dataset builders for predictive AI.

This starter implements an in-memory dataset builder for Option B:
"suggested pit window".

It intentionally does NOT couple to the running app. You can feed it state
snapshots from simulation replay or cached session extracts.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import Any, Optional

import pandas as pd

from .features import compute_stint_lap, rolling_mean
from .labels import make_pit_window_label
from .schemas import PIT_WINDOW_REQUIRED_COLUMNS, PitWindowRow


def build_pit_window_dataset(
    states: Iterable[dict[str, Any]],
    pit_laps_by_driver: dict[str, list[int]],
    *,
    window_half_width: int = 0,
    horizon_laps: Optional[int] = None,
    rolling_window: int = 3,
) -> pd.DataFrame:
    """Build a supervised dataset for pit window prediction.

    Args:
        states: Iterable of state snapshots. Each snapshot must contain:
            - driver_id (str)
            - lap_number (int)
            Optional:
            - compound (str)
            - last_lap_time_s (float)
            - position (int)
            - gap_ahead_s (float)
            - gap_behind_s (float)
            - last_pit_lap (int)
        pit_laps_by_driver: Mapping driver_id -> list of pit laps.
        window_half_width: Label window half-width (0 means start=end=center).
        horizon_laps: Optional max horizon for labeling.
        rolling_window: Window size for rolling lap time.

    Returns:
        DataFrame with the fixed contract columns.

    Raises:
        ValueError: If required fields are missing.
    """
    rows: list[dict[str, Any]] = []

    lap_times_by_driver: dict[str, list[float]] = defaultdict(list)

    for state in states:
        driver_id = str(state.get("driver_id", "")).strip()
        lap_number = state.get("lap_number")

        if not driver_id:
            raise ValueError("state missing driver_id")
        if lap_number is None:
            raise ValueError("state missing lap_number")

        lap_number_int = int(lap_number)

        last_lap_time_s = state.get("last_lap_time_s")
        if last_lap_time_s is not None:
            lap_times_by_driver[driver_id].append(float(last_lap_time_s))

        rolling_lap_time_s = rolling_mean(lap_times_by_driver[driver_id], window=rolling_window)

        label = make_pit_window_label(
            current_lap=lap_number_int,
            pit_laps=pit_laps_by_driver.get(driver_id, []),
            window_half_width=window_half_width,
            horizon_laps=horizon_laps,
        )

        row = {
            "driver_id": driver_id,
            "lap_number": lap_number_int,
            "compound": state.get("compound"),
            "stint_lap": compute_stint_lap(lap_number_int, state.get("last_pit_lap")),
            "last_lap_time_s": float(last_lap_time_s) if last_lap_time_s is not None else None,
            "rolling_lap_time_s": float(rolling_lap_time_s) if rolling_lap_time_s is not None else None,
            "gap_ahead_s": float(state["gap_ahead_s"]) if state.get("gap_ahead_s") is not None else None,
            "gap_behind_s": float(state["gap_behind_s"]) if state.get("gap_behind_s") is not None else None,
            "position": int(state["position"]) if state.get("position") is not None else None,
            "pit_window_start_lap": label.start_lap,
            "pit_window_end_lap": label.end_lap,
            "pit_window_center_lap": label.center_lap,
        }

        validated = PitWindowRow.model_validate(row)
        validated.validate_label_ranges()
        rows.append(validated.model_dump())

    df = pd.DataFrame(rows)

    missing = [col for col in PIT_WINDOW_REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    return df[list(PIT_WINDOW_REQUIRED_COLUMNS)]
