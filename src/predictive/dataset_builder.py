"""Dataset builders for predictive AI.

Phase 4B adds helpers to build supervised tables from cached lap frames and
persist deterministic datasets for reproducible training/backtests.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
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


def build_states_from_lap_frames(
    laps: pd.DataFrame,
    pit_events: Optional[pd.DataFrame] = None,
) -> tuple[list[dict[str, Any]], dict[str, list[int]]]:
    """Convert lap-level data into state snapshots + pit map.

    Expected lap columns:
    - driver_id (str)
    - lap_number (int)
    Optional: compound, lap_time_s, position, gap_ahead_s, gap_behind_s

    Expected pit_events columns (optional):
    - driver_id (str)
    - lap_number (int)
    """

    def _clean(value: Any) -> Any:
        # Convert pandas NaN to None so downstream validation accepts missing values.
        return None if pd.isna(value) else value

    required = {"driver_id", "lap_number"}
    missing = required - set(laps.columns)
    if missing:
        raise ValueError(f"laps missing required columns: {sorted(missing)}")

    pit_laps_by_driver: dict[str, list[int]] = defaultdict(list)
    if pit_events is not None and not pit_events.empty:
        if not {"driver_id", "lap_number"}.issubset(pit_events.columns):
            raise ValueError("pit_events missing driver_id/lap_number")
        for driver_id, group in pit_events.groupby("driver_id"):
            laps_sorted = sorted(int(x) for x in group["lap_number"].tolist())
            pit_laps_by_driver[str(driver_id)] = laps_sorted

    states: list[dict[str, Any]] = []
    # Sort by driver then lap for deterministic ordering
    laps_sorted_df = laps.copy().sort_values(by=["driver_id", "lap_number"]).reset_index(drop=True)

    # Track last pit per driver as we iterate laps in order
    last_pit_by_driver: dict[str, Optional[int]] = {drv: None for drv in laps_sorted_df["driver_id"].unique()}

    for _, row in laps_sorted_df.iterrows():
        driver_id = str(row["driver_id"])
        lap_number = int(row["lap_number"])

        # Update last pit if current lap is in pit list
        if lap_number in pit_laps_by_driver.get(driver_id, []):
            last_pit_by_driver[driver_id] = lap_number

        states.append(
            {
                "driver_id": driver_id,
                "lap_number": lap_number,
                "compound": _clean(row.get("compound")),
                "last_lap_time_s": _clean(row.get("lap_time_s")),
                "position": _clean(row.get("position")),
                "gap_ahead_s": _clean(row.get("gap_ahead_s")),
                "gap_behind_s": _clean(row.get("gap_behind_s")),
                "last_pit_lap": last_pit_by_driver.get(driver_id),
            }
        )

    return states, pit_laps_by_driver


def build_pit_window_dataset_from_frames(
    laps: pd.DataFrame,
    pit_events: Optional[pd.DataFrame] = None,
    *,
    window_half_width: int = 0,
    horizon_laps: Optional[int] = None,
    rolling_window: int = 3,
) -> pd.DataFrame:
    """End-to-end builder from lap/pit frames to supervised table."""

    states, pit_map = build_states_from_lap_frames(laps, pit_events)
    return build_pit_window_dataset(
        states,
        pit_map,
        window_half_width=window_half_width,
        horizon_laps=horizon_laps,
        rolling_window=rolling_window,
    )


def persist_dataset(df: pd.DataFrame, output_path: str | Path) -> Path:
    """Persist dataset deterministically (sorted) to CSV."""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Sort for determinism
    sorted_df = df.sort_values(by=["driver_id", "lap_number"]).reset_index(drop=True)
    sorted_df.to_csv(output_path, index=False)
    return output_path
