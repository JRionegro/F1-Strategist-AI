"""Fetch OpenF1 race data and persist lap/pit caches for predictive training."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

import pandas as pd

from src.data.cache_config import CacheConfig, DataType
from src.data.cache_manager import CacheManager
from src.data.openf1_data_provider import OpenF1DataProvider

logger = logging.getLogger(__name__)


def _parse_race_date(race_name: str) -> Optional[datetime]:
    """Extract YYYY-MM-DD prefix from race_name if present."""

    prefix = race_name.split("_")[0]
    try:
        return datetime.strptime(prefix, "%Y-%m-%d")
    except ValueError:
        return None


def _resolve_session_key(
    provider: OpenF1DataProvider,
    *,
    year: int,
    race_name: str,
    session_key: Optional[int] = None,
) -> Tuple[int, Dict]:
    """Resolve the OpenF1 session_key for the race session."""

    if session_key is not None:
        session = provider.get_session(
            year=year, round_number=None, session_name="Race")
        return int(session_key), session or {}

    target_date = _parse_race_date(race_name)
    sessions = provider._request(
        "sessions", {
            "year": year, "session_name": "Race"})
    if not sessions:
        raise ValueError(f"No race sessions found for year {year}")

    def _matches_date(session: Dict) -> bool:
        if target_date is None:
            return False
        raw_date = session.get("date_start")
        if not raw_date:
            return False
        try:
            session_date = pd.to_datetime(raw_date, format="mixed").date()
        except Exception:
            return False
        return session_date == target_date.date()

    filtered = [s for s in sessions if _matches_date(s)] or sessions
    filtered.sort(key=lambda s: s.get("date_start", ""), reverse=True)

    chosen = filtered[0]
    key = chosen.get("session_key")
    if key is None:
        raise ValueError("Race session found but missing session_key")

    return int(key), chosen


def _build_driver_map(drivers_df: pd.DataFrame) -> Dict[str, str]:
    """Map driver numbers to abbreviations (fallback to number as string)."""

    if drivers_df is None or drivers_df.empty:
        return {}

    mapping: Dict[str, str] = {}
    for _, row in drivers_df.iterrows():
        number = str(row.get("DriverNumber"))
        abbr = str(row.get("Abbreviation")) if row.get(
            "Abbreviation") else number
        mapping[number] = abbr
    return mapping


def _apply_stints(
        laps_df: pd.DataFrame,
        stints_df: pd.DataFrame) -> pd.DataFrame:
    """Attach compound info to laps using stint ranges."""

    if stints_df is None or stints_df.empty:
        if "Compound" not in laps_df.columns:
            laps_df["Compound"] = None
        return laps_df

    enriched = laps_df.copy()
    if "Compound" not in enriched.columns:
        enriched["Compound"] = None

    for _, stint in stints_df.iterrows():
        driver_num = stint.get("DriverNumber")
        start = stint.get("StintStart", 1)
        end = stint.get("StintEnd", 10**6)
        compound = stint.get("Compound")
        if driver_num is None or compound is None:
            continue
        mask = (
            (enriched.get("DriverNumber") == driver_num)
            & (enriched.get("LapNumber") >= start)
            & (enriched.get("LapNumber") <= end)
        )
        enriched.loc[mask, "Compound"] = compound

    return enriched


def _normalize_laps(
    laps_df: pd.DataFrame,
    driver_map: Dict[str, str],
    stints_df: pd.DataFrame,
) -> pd.DataFrame:
    """Produce lap frame aligned with dataset builder expectations."""

    if laps_df is None or laps_df.empty:
        raise ValueError("OpenF1 laps are empty")

    enriched = _apply_stints(laps_df, stints_df)
    frame = enriched.copy()

    frame["driver_id"] = frame["DriverNumber"].astype(
        str).map(lambda x: driver_map.get(str(x), str(x)))
    frame["lap_number"] = frame["LapNumber"].astype(int)

    if "LapTime_seconds" in frame.columns:
        frame["lap_time_s"] = frame["LapTime_seconds"].astype(float)

    if "Compound" in frame.columns:
        frame["compound"] = frame["Compound"]

    if "Position" in frame.columns:
        frame["position"] = frame["Position"]

    return frame


def _normalize_pits(pit_df: pd.DataFrame,
                    driver_map: Dict[str, str]) -> pd.DataFrame:
    """Normalize pit events to driver_id/lap_number pairs."""

    if pit_df is None or pit_df.empty:
        return pd.DataFrame(columns=["driver_id", "lap_number"])

    frame = pit_df.copy()
    lap_col = "Lap" if "Lap" in frame.columns else "LapNumber"
    frame["lap_number"] = frame[lap_col].astype(int)
    frame["driver_id"] = frame["DriverNumber"].astype(
        str).map(lambda x: driver_map.get(str(x), str(x)))

    return frame[["driver_id", "lap_number"]]


def fetch_and_cache_openf1_race(
    *,
    year: int,
    race_name: str,
    cache_config: Optional[CacheConfig] = None,
    session_key: Optional[int] = None,
) -> Tuple[Path, Path]:
    """Fetch OpenF1 race data and persist lap/pit caches using CacheManager.

    Args:
        year: Season year.
        race_name: Race identifier used as cache folder name.
        cache_config: Optional cache configuration override.
        session_key: Optional explicit OpenF1 session key; resolved by date if omitted.

    Returns:
        Tuple of paths to saved lap_times and pit_stops files.
    """

    provider = OpenF1DataProvider()
    resolved_session_key, _ = _resolve_session_key(
        provider, year=year, race_name=race_name, session_key=session_key)

    drivers_df = provider.get_drivers(resolved_session_key)
    driver_map = _build_driver_map(drivers_df)

    laps_df = provider.get_laps(resolved_session_key)
    stints_df = provider.get_stints(resolved_session_key)
    pit_df = provider.get_pit_stops(resolved_session_key)

    normalized_laps = _normalize_laps(laps_df, driver_map, stints_df)
    normalized_pits = _normalize_pits(pit_df, driver_map)

    cache_manager = CacheManager(config=cache_config or CacheConfig())

    lap_saved = cache_manager.save_race_data(
        year, race_name, DataType.LAP_TIMES, normalized_laps)
    pit_saved = cache_manager.save_race_data(
        year, race_name, DataType.PIT_STOPS, normalized_pits)

    if not lap_saved:
        raise RuntimeError("Failed to persist lap_times to cache")
    if not pit_saved:
        raise RuntimeError("Failed to persist pit_stops to cache")

    lap_path = cache_manager._get_cache_file_path(
        year, race_name, DataType.LAP_TIMES)
    pit_path = cache_manager._get_cache_file_path(
        year, race_name, DataType.PIT_STOPS)

    logger.info("Cached OpenF1 race data for %s (%s)", race_name, year)

    return lap_path, pit_path


__all__ = ["fetch_and_cache_openf1_race"]
