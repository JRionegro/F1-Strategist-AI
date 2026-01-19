"""FastF1 powered position provider used by the track map dashboard."""
from __future__ import annotations

import logging
import math
import pickle
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, cast
from numbers import Real

FloatDict = Dict[str, float]
DriverPosition = Dict[str, Union[float, FloatDict]]

import fastf1
from fastf1.core import Session
import numpy as np
import pandas as pd

from src.utils.logging_config import LogCategory, get_logger

logger = get_logger(LogCategory.DATA)


class FastF1PositionProvider:
    """Expose driver position samples derived from FastF1 telemetry."""

    SESSION_TYPE_MAPPING: Dict[str, str] = {
        "Race": "R",
        "Qualifying": "Q",
        "Sprint": "S",
        "Practice 1": "FP1",
        "Practice 2": "FP2",
        "Practice 3": "FP3",
        "Sprint Shootout": "SQ",
        "Sprint Qualifying": "SQ",
    }

    CACHE_SCHEMA_VERSION: int = 4

    def __init__(self, cache_dir: str = "./cache") -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        fastf1.Cache.enable_cache(str(self.cache_dir))

        self.session: Optional[Session] = None
        self.session_params: Optional[Tuple[int, str, str]] = None
        self._driver_mapping: Dict[int, str] = {}
        self._telemetry_cache: Dict[Tuple[str, int], pd.DataFrame] = {}
        self.positions_df: Optional[pd.DataFrame] = None
        self._current_session_key: Optional[Tuple[int, str, str]] = None
        self._session_time_offset: float = 0.0
        self._time_bounds: Tuple[float, float] = (0.0, 0.0)
        self._circuit_outline_cache: Optional[Dict[str, pd.DataFrame]] = None
        self._loading_lock: bool = False

        logger.info("FastF1PositionProvider ready (cache dir: %s)", self.cache_dir)

    def _get_positions_cache_path(self, year: int, country: str, session_type: str) -> Path:
        safe_country = country.replace(" ", "_").replace("/", "_")
        session_dir = self.cache_dir / str(year)
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir / f"{safe_country}_{session_type}_positions.pkl"

    @staticmethod
    def translate_openf1_session(openf1_session: Dict[str, str]) -> Dict[str, str | int]:
        """Translate an OpenF1 session payload into FastF1 parameters."""
        date_start = openf1_session.get("date_start")
        if date_start:
            year = datetime.fromisoformat(date_start.replace("Z", "+00:00")).year
        else:
            year = datetime.utcnow().year

        country = openf1_session.get("country_name")
        if not country:
            meeting_name = openf1_session.get("meeting_name", "")
            country = meeting_name.replace(" Grand Prix", "").strip()

        session_name = openf1_session.get("session_name", "Race")
        identifier = FastF1PositionProvider.SESSION_TYPE_MAPPING.get(session_name, "R")

        return {"year": year, "round": country, "identifier": identifier}

    def load_session(self, year: int, country: str, session_type: str = "R") -> bool:
        """Load telemetry for the requested session."""
        session_key = (year, country, session_type)
        if self._current_session_key == session_key and self.positions_df is not None:
            logger.info("Session already loaded: %s", session_key)
            return True

        if self._loading_lock:
            logger.warning("Session load already running; skipping duplicate request")
            return False

        self._loading_lock = True
        self.session_params = session_key
        cache_path = self._get_positions_cache_path(year, country, session_type)

        try:
            if cache_path.exists():
                logger.info("Loading positions from cache: %s", cache_path.name)
                with cache_path.open("rb") as handle:
                    cache_data = pickle.load(handle)

                if cache_data.get("schema_version") != self.CACHE_SCHEMA_VERSION:
                    raise ValueError("Cache schema mismatch")

                positions = cache_data.get("positions")
                if not isinstance(positions, pd.DataFrame) or positions.empty:
                    raise ValueError("Cached positions invalid")

                self.positions_df = positions
                self._driver_mapping = cache_data.get("driver_mapping", {})
                self.session = cache_data.get("session")
                self._session_time_offset = float(cache_data.get("time_offset", 0.0))
                time_bounds = cache_data.get("time_bounds")
                if isinstance(time_bounds, tuple) and len(time_bounds) == 2:
                    self._time_bounds = (float(time_bounds[0]), float(time_bounds[1]))
                else:
                    self._calculate_time_bounds()

                self._current_session_key = session_key
                logger.info("Loaded %d cached samples", len(self.positions_df))
                return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("Cache load failed: %s", exc)
            self.positions_df = None

        try:
            logger.info("Loading session from FastF1...")
            session_obj = fastf1.get_session(year, country, session_type)
            session_obj.load(telemetry=True, laps=True, weather=False, messages=False)
            self.session = session_obj
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to load FastF1 session: %s", exc)
            self.session = None
            self._loading_lock = False
            return False

        if not hasattr(self.session, "pos_data"):
            logger.error("Session has no pos_data attribute")
            self.session = None
            self._loading_lock = False
            return False

        pos_data = self.session.pos_data  # type: ignore[attr-defined]
        if not isinstance(pos_data, dict) or len(pos_data) == 0:
            logger.error("Position data unavailable for session")
            self.session = None
            self._loading_lock = False
            return False

        if hasattr(self.session, "results") and self.session.results is not None:
            for _, row in self.session.results.iterrows():
                self._driver_mapping[int(row["DriverNumber"])] = row["Abbreviation"]

        self._preload_all_positions()
        self._save_positions_cache(cache_path)
        self._current_session_key = session_key
        self._loading_lock = False
        return True

    def _preload_all_positions(self) -> None:
        """Sample driver telemetry and build a DataFrame ready for interpolation."""
        if self.session is None:
            raise ValueError("Session not loaded")

        pos_data = getattr(self.session, "pos_data", None)
        if not isinstance(pos_data, dict) or len(pos_data) == 0:
            raise ValueError("Position telemetry unavailable")

        position_frames: List[pd.DataFrame] = []
        processed_drivers: List[str] = []
        target_samples = 100_000

        for driver_code, driver_df in pos_data.items():
            driver_id = str(driver_code)
            if driver_df is None or driver_df.empty:
                continue

            if not {"X", "Y", "SessionTime"}.issubset(driver_df.columns):
                continue

            filtered = driver_df.dropna(subset=["X", "Y", "SessionTime"])
            filtered = filtered.loc[(filtered["X"] != 0) | (filtered["Y"] != 0)]
            if filtered.empty:
                continue

            filtered = filtered.copy()
            filtered.loc[:, "time"] = filtered["SessionTime"].dt.total_seconds().astype(float)
            filtered.loc[:, "x"] = filtered["X"].astype(float)
            filtered.loc[:, "y"] = filtered["Y"].astype(float)
            filtered.loc[:, "z"] = filtered.get("Z", pd.Series(0.0, index=filtered.index)).fillna(0.0).astype(float)

            driver_laps = self.session.laps.pick_drivers(driver_id)
            lap_info = driver_laps[["LapNumber", "LapStartTime"]].dropna().copy()
            lap_info.loc[:, "LapStartTime"] = pd.to_timedelta(lap_info["LapStartTime"])
            lap_info.sort_values("LapStartTime", inplace=True)

            if not lap_info.empty:
                lap_numbers = lap_info["LapNumber"].astype(int).to_numpy()
                lap_start_seconds = lap_info["LapStartTime"].apply(lambda td: float(td.total_seconds())).to_numpy()
            else:
                lap_numbers = np.array([1])
                lap_start_seconds = np.array([0.0])

            step = max(1, len(filtered) // target_samples)
            sampled = filtered.iloc[::step].copy()
            idx = np.searchsorted(lap_start_seconds, sampled["time"].to_numpy(), side="right") - 1
            idx = np.clip(idx, 0, len(lap_numbers) - 1)
            sampled.loc[:, "lap_number"] = lap_numbers[idx]
            sampled.loc[:, "driver_number"] = driver_id
            dx = sampled["x"].diff().fillna(0.0)
            dy = sampled["y"].diff().fillna(0.0)
            sampled.loc[:, "distance"] = np.hypot(dx, dy).cumsum()

            position_frames.append(sampled[[
                "driver_number",
                "x",
                "y",
                "z",
                "distance",
                "time",
                "lap_number",
            ]].copy())
            processed_drivers.append(driver_id)

        if not position_frames:
            raise ValueError("No driver telemetry samples were collected")

        combined = pd.concat(position_frames, ignore_index=True)
        combined.sort_values(["time", "driver_number"], inplace=True)
        combined.reset_index(drop=True, inplace=True)
        self.positions_df = combined
        self._calculate_time_bounds()
        self._session_time_offset = self._determine_session_time_offset()
        logger.info(
            "Preloaded %d samples across %d drivers (offset %.3fs)",
            len(self.positions_df),
            len(processed_drivers),
            self._session_time_offset,
        )

    def _calculate_time_bounds(self) -> Tuple[float, float]:
        if self.positions_df is None or self.positions_df.empty:
            self._time_bounds = (0.0, 0.0)
        else:
            min_time = float(self.positions_df["time"].min())
            max_time = float(self.positions_df["time"].max())
            self._time_bounds = (min_time, max_time)
        return self._time_bounds

    def _determine_session_time_offset(self) -> float:
        if self.session is not None and hasattr(self.session, "laps"):
            lap_data = self.session.laps
            if isinstance(lap_data, pd.DataFrame) and "LapStartTime" in lap_data.columns:
                valid = pd.to_timedelta(lap_data["LapStartTime"].dropna(), errors="coerce").dropna()
                if not valid.empty:
                    return max(float(valid.min().total_seconds()), 0.0)

        if self.positions_df is not None and not self.positions_df.empty:
            return float(self.positions_df["time"].min())
        return 0.0

    def _save_positions_cache(self, cache_path: Path) -> None:
        if self.positions_df is None or self.positions_df.empty:
            return

        data = {
            "positions": self.positions_df,
            "driver_mapping": self._driver_mapping,
            "session": None,
            "schema_version": self.CACHE_SCHEMA_VERSION,
            "time_offset": self._session_time_offset,
            "time_bounds": self._time_bounds,
        }
        with cache_path.open("wb") as handle:
            pickle.dump(data, handle)
        size_mb = cache_path.stat().st_size / (1024 * 1024)
        logger.info("Saved position cache (%.2f MB): %s", size_mb, cache_path.name)

    def get_session_time_offset(self) -> float:
        """Return the cached session time offset in seconds."""
        return float(self._session_time_offset)

    def get_time_bounds(self) -> Tuple[float, float]:
        """Return the minimum and maximum cached session timestamps."""
        if self._time_bounds == (0.0, 0.0):
            return self._calculate_time_bounds()
        return self._time_bounds

    def clamp_session_time(self, elapsed_time: float) -> float:
        """Clamp an elapsed simulation time to the cached session timeline."""
        min_time, max_time = self.get_time_bounds()
        adjusted_time = float(elapsed_time) + self._session_time_offset
        return float(np.clip(adjusted_time, min_time, max_time))

    def get_lap_trajectories(
        self,
        lap_number: int,
        driver_numbers: Optional[List[int]] = None,
    ) -> Dict[str, Dict[str, List[float]]]:
        """Return raw lap trajectories for the provided drivers."""
        if self.positions_df is None or self.positions_df.empty:
            return {}

        lap_df = self.positions_df
        if "lap_number" in lap_df.columns:
            try:
                lap_mask = lap_df["lap_number"].astype(int) == int(lap_number)
            except Exception:  # noqa: BLE001
                lap_mask = lap_df["lap_number"] == lap_number
            lap_df = lap_df.loc[lap_mask]

        if lap_df.empty:
            return {}

        allowed_drivers: Optional[set[str]]
        if driver_numbers is None:
            allowed_drivers = None
        else:
            allowed_drivers = {str(number) for number in driver_numbers}

        trajectories: Dict[str, Dict[str, List[float]]] = {}
        grouped = lap_df.groupby("driver_number")
        for driver_id, driver_df in grouped:
            driver_key = str(driver_id)
            if allowed_drivers is not None and driver_key not in allowed_drivers:
                continue

            sorted_df = driver_df.sort_values("time")
            time_values = sorted_df["time"].astype(float).tolist()
            x_values = sorted_df["x"].astype(float).tolist()
            y_values = sorted_df["y"].astype(float).tolist()
            if not time_values:
                continue

            lap_values = sorted_df["lap_number"].astype(float).tolist()
            lap_value = lap_values[-1] if lap_values else float(lap_number)
            trajectories[driver_key] = {
                "time": time_values,
                "x": x_values,
                "y": y_values,
                "lap": [float(lap_value)],
            }

        return trajectories

    def get_driver_abbreviation(self, driver_number: int) -> Optional[str]:
        return self._driver_mapping.get(driver_number)

    def get_driver_position(self, driver_number: int, lap_number: int) -> Optional[Dict[str, float]]:
        if self.session is None:
            return None

        abbreviation = self.get_driver_abbreviation(driver_number)
        if not abbreviation:
            return None

        cache_key = (abbreviation, lap_number)
        telemetry = self._telemetry_cache.get(cache_key)
        if telemetry is None:
            laps = self.session.laps.pick_drivers(abbreviation)
            lap_row = laps[laps["LapNumber"] == lap_number]
            if lap_row.empty:
                return None
            telemetry = lap_row.iloc[0].get_telemetry()
            self._telemetry_cache[cache_key] = telemetry

        if telemetry.empty:
            return None

        last_point = telemetry.iloc[-1]
        return {
            "x": float(last_point.get("X", 0.0)),
            "y": float(last_point.get("Y", 0.0)),
            "z": float(last_point.get("Z", 0.0)),
        }

    def get_all_driver_positions(
        self,
        lap_number: Optional[int],
        driver_numbers: Optional[List[int]] = None,
        elapsed_time: Optional[float] = None,
    ) -> Dict[int, DriverPosition]:
        if self.positions_df is None or self.positions_df.empty:
            logger.warning("No preloaded position data available")
            return {}

        if driver_numbers is None:
            driver_numbers = list(self._driver_mapping.keys())

        if elapsed_time is None:
            logger.warning("Elapsed time not provided; unable to map positions")
            return {}

        adjusted_time = self.clamp_session_time(float(elapsed_time))

        positions: Dict[int, DriverPosition] = {}
        for driver_number in driver_numbers:
            driver_id = str(driver_number)
            driver_data = self.positions_df[self.positions_df["driver_number"] == driver_id]
            if driver_data.empty:
                continue

            driver_data = driver_data.sort_values("time").reset_index(drop=True)

            filtered_data = driver_data
            if lap_number is not None and "lap_number" in driver_data.columns:
                try:
                    lap_mask = driver_data["lap_number"].astype(int) == int(lap_number)
                except Exception:  # noqa: BLE001
                    lap_mask = driver_data["lap_number"] == lap_number
                if lap_mask.any():
                    filtered_data = driver_data.loc[lap_mask].reset_index(drop=True)
                    if filtered_data.empty:
                        filtered_data = driver_data
                else:
                    filtered_data = driver_data

            time_values = filtered_data["time"].to_numpy(dtype=float)
            if time_values.size == 0:
                continue
            insert_idx = int(np.searchsorted(time_values, adjusted_time, side="left"))
            prev_idx = max(insert_idx - 1, 0)
            next_idx = min(insert_idx, len(filtered_data) - 1)
            prev_row = filtered_data.iloc[prev_idx]
            next_row = filtered_data.iloc[next_idx]
            prev_time = float(prev_row["time"])
            next_time = float(next_row["time"])

            if next_time <= prev_time:
                ratio = 0.0
            else:
                ratio = (adjusted_time - prev_time) / (next_time - prev_time)
                ratio = float(np.clip(ratio, 0.0, 1.0))

            prev_x = float(prev_row["x"])
            prev_y = float(prev_row["y"])
            prev_z = float(prev_row["z"])
            next_x = float(next_row["x"])
            next_y = float(next_row["y"])
            next_z = float(next_row["z"])

            x_val = prev_x + (next_x - prev_x) * ratio
            y_val = prev_y + (next_y - prev_y) * ratio
            z_val = prev_z + (next_z - prev_z) * ratio
            time_val = prev_time + (next_time - prev_time) * ratio

            current_lap_val = next_row.get("lap_number")
            if isinstance(current_lap_val, Real) and math.isfinite(float(current_lap_val)):
                lap_number_value = int(round(float(current_lap_val)))
            else:
                lap_number_value = int(lap_number) if lap_number is not None else -1

            positions[driver_number] = {
                "x": x_val,
                "y": y_val,
                "z": z_val,
                "time": time_val,
                "query_time": adjusted_time,
                "lap_number": lap_number_value,
                "previous_sample": {
                    "time": prev_time,
                    "x": prev_x,
                    "y": prev_y,
                    "z": prev_z,
                },
                "next_sample": {
                    "time": next_time,
                    "x": next_x,
                    "y": next_y,
                    "z": next_z,
                },
            }

        return positions

    def get_circuit_outline(
        self,
        sample_driver_number: Optional[int] = None,
        track_width: float = 200.0,
    ) -> Optional[Dict[str, pd.DataFrame]]:
        if self._circuit_outline_cache is not None:
            return self._circuit_outline_cache

        if self.session is None and self.session_params is not None:
            year, country, session_type = self.session_params
            try:
                reload_session = fastf1.get_session(year, country, session_type)
                reload_session.load(telemetry=True, laps=True, weather=False, messages=False)
                self.session = reload_session
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to reload session for outline: %s", exc)
                return None

        if self.session is None:
            return None

        if sample_driver_number is None:
            sample_driver_number = int(self.session.drivers[0])

        driver_laps = self.session.laps.pick_drivers(sample_driver_number)
        first_lap = driver_laps.iloc[0] if not driver_laps.empty else None
        if first_lap is None:
            return None

        telemetry = first_lap.get_telemetry()
        if telemetry is None or telemetry.empty:
            return None

        x_center = telemetry["X"].astype(float).to_numpy()
        y_center = telemetry["Y"].astype(float).to_numpy()
        z_center = telemetry.get("Z", pd.Series(0.0, index=telemetry.index)).fillna(0.0).astype(float).to_numpy()
        distance = telemetry["Distance"].astype(float).to_numpy()

        dx = np.gradient(x_center)
        dy = np.gradient(y_center)
        norm = np.sqrt(dx**2 + dy**2)
        norm[norm == 0] = 1.0
        dx /= norm
        dy /= norm
        nx = -dy
        ny = dx
        half_width = track_width / 2.0
        x_outer = x_center + nx * half_width
        y_outer = y_center + ny * half_width
        x_inner = x_center - nx * half_width
        y_inner = y_center - ny * half_width

        center_df = pd.DataFrame({"X": x_center, "Y": y_center, "Z": z_center, "Distance": distance})
        inner_df = pd.DataFrame({"X": x_inner, "Y": y_inner, "Z": z_center, "Distance": distance})
        outer_df = pd.DataFrame({"X": x_outer, "Y": y_outer, "Z": z_center, "Distance": distance})

        if not center_df.empty:
            center_df = pd.concat([center_df, center_df.iloc[[0]]], ignore_index=True)
            inner_df = pd.concat([inner_df, inner_df.iloc[[0]]], ignore_index=True)
            outer_df = pd.concat([outer_df, outer_df.iloc[[0]]], ignore_index=True)

        outline = {"center": center_df, "inner": inner_df, "outer": outer_df}
        self._circuit_outline_cache = outline
        return outline

    def clear_cache(self) -> None:
        self._telemetry_cache.clear()
        self.positions_df = None
        self._circuit_outline_cache = None
        self._current_session_key = None
        logger.info("Position provider caches cleared")

    def get_session_info(self) -> Optional[Dict[str, Union[int, str, List[int]]]]:
        if self.session_params is None:
            return None

        year, country, session_type = self.session_params
        info: Dict[str, Union[int, str, List[int]]] = {
            "year": year,
            "country": country,
            "session_type": session_type,
            "drivers": list(self._driver_mapping.keys()),
            "driver_count": len(self._driver_mapping),
        }

        if self.session is not None and hasattr(self.session, "event"):
            event = cast(Dict[str, str], getattr(self.session, "event", {}))
            info["event_name"] = event.get("EventName", "")
            info["circuit_name"] = event.get("Location", "")
        return info
