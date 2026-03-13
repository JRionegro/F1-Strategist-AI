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

from src.data.cache_config import DataType
from src.data.cache_manager import CacheManager

from .features import compute_stint_lap, rolling_mean
from .labels import make_pit_window_label
from .schemas import PIT_WINDOW_REQUIRED_COLUMNS, PitWindowRow


def _normalize_lap_frames_for_dataset(laps: pd.DataFrame) -> pd.DataFrame:
    """Normalize lap frames into the schema expected by the dataset builder."""

    if laps is None or laps.empty:
        raise ValueError("laps data is empty")

    df = laps.copy()

    driver_col = None
    for candidate in ("driver_id", "Driver", "Abbreviation", "DriverNumber"):
        if candidate in df.columns:
            driver_col = candidate
            break
    if driver_col is None:
        raise ValueError("laps missing driver identifier")

    lap_col = "LapNumber" if "LapNumber" in df.columns else "lap_number" if "lap_number" in df.columns else None
    if lap_col is None:
        raise ValueError("laps missing lap number column")

    def _lap_time_seconds(frame: pd.DataFrame) -> pd.Series:
        if "lap_time_s" in frame.columns:
            return frame["lap_time_s"]
        if "LapTime_seconds" in frame.columns:
            return frame["LapTime_seconds"]
        if "LapTime" in frame.columns:
            return pd.to_timedelta(frame["LapTime"]).dt.total_seconds()
        return pd.Series([None] * len(frame))

    normalized = pd.DataFrame(
        {
            "driver_id": df[driver_col].astype(str).str.strip(),
            "lap_number": df[lap_col].astype(int),
            "compound": df.get(
                "Compound",
                df.get("compound")),
            "lap_time_s": _lap_time_seconds(df).astype(
                float,
                errors="ignore"),
            "gap_ahead_s": df.get(
                "GapAhead",
                df.get("gap_ahead_s")),
            "gap_behind_s": df.get(
                "GapBehind",
                df.get("gap_behind_s")),
            "position": df.get(
                "Position",
                df.get(
                    "position",
                    df.get("PositionOrder"))),
        })

    return normalized


def _normalize_pit_events(
        pits: Optional[pd.DataFrame], laps: pd.DataFrame) -> pd.DataFrame:
    """Normalize pit events into driver/lap pairs."""

    if pits is not None and not pits.empty:
        driver_col = None
        for candidate in (
            "driver_id",
            "Driver",
            "Abbreviation",
            "DriverNumber"
        ):
            if candidate in pits.columns:
                driver_col = candidate
                break

        lap_col = None
        for candidate in ("LapNumber", "lap_number"):
            if candidate in pits.columns:
                lap_col = candidate
                break

        if driver_col is not None and lap_col is not None:
            normalized = pits[[driver_col, lap_col]].copy()
            normalized.columns = ["driver_id", "lap_number"]
            normalized["driver_id"] = normalized["driver_id"].astype(
                str).str.strip()
            normalized["lap_number"] = normalized["lap_number"].astype(int)
            return normalized

    if {"PitOutTime", "LapNumber"}.issubset(laps.columns):
        fallback = laps[laps["PitOutTime"].notna()][[
            "LapNumber", "Driver"]].copy()
        fallback.columns = ["lap_number", "driver_id"]
        fallback["driver_id"] = fallback["driver_id"].astype(str).str.strip()
        fallback["lap_number"] = fallback["lap_number"].astype(int)
        return fallback

    return pd.DataFrame(columns=["driver_id", "lap_number"])


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

        rolling_lap_time_s = rolling_mean(
            lap_times_by_driver[driver_id],
            window=rolling_window)

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
            "stint_lap": compute_stint_lap(
                lap_number_int,
                state.get("last_pit_lap")),
            "last_lap_time_s": float(last_lap_time_s) if last_lap_time_s is not None else None,
            "rolling_lap_time_s": float(rolling_lap_time_s) if rolling_lap_time_s is not None else None,
            "gap_ahead_s": float(
                state["gap_ahead_s"]) if state.get("gap_ahead_s") is not None else None,
            "gap_behind_s": float(
                state["gap_behind_s"]) if state.get("gap_behind_s") is not None else None,
            "position": int(
                    state["position"]) if state.get("position") is not None else None,
            "pit_window_start_lap": label.start_lap,
            "pit_window_end_lap": label.end_lap,
            "pit_window_center_lap": label.center_lap,
        }

        validated = PitWindowRow.model_validate(row)
        validated.validate_label_ranges()
        rows.append(validated.model_dump())

    df = pd.DataFrame(rows)

    missing = [
        col for col in PIT_WINDOW_REQUIRED_COLUMNS if col not in df.columns]
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
        # Convert pandas NaN to None so downstream validation accepts missing
        # values.
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
    laps_sorted_df = laps.copy().sort_values(
        by=["driver_id", "lap_number"]).reset_index(drop=True)

    # Track last pit per driver as we iterate laps in order
    last_pit_by_driver: dict[str, Optional[int]] = {
        drv: None for drv in laps_sorted_df["driver_id"].unique()}

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


def build_pit_window_dataset_from_cache(
    cache_manager: CacheManager,
    year: int,
    race_name: str,
    *,
    window_half_width: int = 0,
    horizon_laps: Optional[int] = None,
    rolling_window: int = 3,
    output_path: Optional[str | Path] = None,
    persist: bool = False,
) -> pd.DataFrame:
    """Build a pit-window dataset from cached race data.

    Args:
        cache_manager: Cache manager configured for historical data.
        year: Season year.
        race_name: Race identifier (matches cache naming).
        window_half_width: Label window half-width.
        horizon_laps: Optional prediction horizon.
        rolling_window: Window for rolling lap time feature.
        output_path: Optional path to persist the dataset.
        persist: Persist to disk using output_path or the default processed path.

    Returns:
        DataFrame with the pit-window dataset.

    Raises:
        ValueError: If cached lap data is missing.
    """

    laps_df = cache_manager.get_cached_race_data(
        year, race_name, DataType.LAP_TIMES)
    if laps_df is None or laps_df.empty:
        raise ValueError("cached laps not found for race")

    pits_df = cache_manager.get_cached_race_data(
        year, race_name, DataType.PIT_STOPS)

    normalized_laps = _normalize_lap_frames_for_dataset(laps_df)
    normalized_pits = _normalize_pit_events(pits_df, laps_df)

    dataset = build_pit_window_dataset_from_frames(
        normalized_laps,
        pit_events=normalized_pits if not normalized_pits.empty else None,
        window_half_width=window_half_width,
        horizon_laps=horizon_laps,
        rolling_window=rolling_window,
    )

    resolved_output: Optional[Path] = None
    if persist:
        resolved_output = (
            Path(output_path)
            if output_path is not None
            else cache_manager.config.processed_dir
            / "predictive"
            / f"{year}_{race_name}_pit_window.csv"
        )
    elif output_path is not None:
        resolved_output = Path(output_path)

    if resolved_output is not None:
        persist_dataset(dataset, resolved_output)

    return dataset


def persist_dataset(df: pd.DataFrame, output_path: str | Path) -> Path:
    """Persist dataset deterministically (sorted) to CSV."""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Sort for determinism
    sorted_df = df.sort_values(
        by=["driver_id", "lap_number"]).reset_index(drop=True)
    sorted_df.to_csv(output_path, index=False)
    return output_path
