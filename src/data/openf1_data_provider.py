"""
OpenF1 Data Provider - Unified source for historical and real-time F1 data.

Uses OpenF1 API (openf1.org) for both historical replay simulations
and live race monitoring, eliminating dual-API complexity.
"""

import logging
import re
import threading
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from time import sleep
from typing import Any, DefaultDict, Dict, List, Optional, Sequence

import pandas as pd
import requests

from src.utils.logging_config import get_logger, LogCategory

from .cache_config import DataType, DEFAULT_CACHE_CONFIG

# Use categorized logger for API/data operations
logger = get_logger(LogCategory.DATA)


def _slugify(value: str) -> str:
    """Return a filesystem-safe slug representation."""
    normalized = re.sub(r"[^a-z0-9]+", "_", value.lower())
    return normalized.strip("_") or "value"


class OpenF1DataProvider:
    """
    Data provider using OpenF1 API for unified historical/live access.
    
    Advantages over FastF1:
    - Same API for historical and real-time data
    - No data structure translation needed
    - Native timestamp format (no Timedelta issues)
    - Designed for streaming scenarios
    - Free for historical data since 2023
    """

    BASE_URL = "https://api.openf1.org/v1"
    
    def __init__(self, rate_limit_delay: float = 0.5, verify_ssl: bool = False):
        """
        Initialize OpenF1 provider.
        
        Args:
            rate_limit_delay: Seconds to wait between API calls
            verify_ssl: Whether to verify SSL certificates (False for corporate proxies)
        """
        self.rate_limit_delay = rate_limit_delay
        self.verify_ssl = verify_ssl
        self._last_request_time = None
        self._session_metadata: Dict[int, Dict[str, Any]] = {}
        self._cached_race_dirs: Dict[int, Path] = {}
        self._api_call_counts: DefaultDict[str, int] = defaultdict(int)
        self._api_call_lock = threading.Lock()
        logger.info("OpenF1DataProvider initialized")
        if not verify_ssl:
            # Suppress InsecureRequestWarning when SSL verification is disabled
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def register_session_metadata(self, session_key: Optional[int], metadata: Dict[str, Any]) -> None:
        """Store session metadata to resolve cache paths for subsequent requests."""
        if session_key is None:
            return
        try:
            key = int(session_key)
        except (TypeError, ValueError):
            return
        self._session_metadata[key] = dict(metadata)

    def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        if self._last_request_time:
            elapsed = (datetime.now() - self._last_request_time).total_seconds()
            if elapsed < self.rate_limit_delay:
                sleep(self.rate_limit_delay - elapsed)
        self._last_request_time = datetime.now()

    def _request(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        max_retries: int = 3,
        base_delay: float = 2.0,
        max_502_retries: int = 5,
        retry_502_delay: float = 3.0
    ) -> List[Dict]:
        """
        Make API request with rate limiting and exponential backoff retry.
        
        Args:
            endpoint: API endpoint (e.g., 'sessions', 'laps')
            params: Query parameters
            max_retries: Maximum number of retry attempts for rate limiting
            base_delay: Base delay in seconds for exponential backoff
            max_502_retries: Maximum retries for 502 Bad Gateway errors
            retry_502_delay: Fixed delay between 502 retries (seconds)
            
        Returns:
            List of JSON objects from API response
        """
        url = f"{self.BASE_URL}/{endpoint}"
        retries_502 = 0
        
        for attempt in range(max_retries + 1):
            self._rate_limit()
            self._increment_api_call_count(endpoint)
            
            try:
                response = requests.get(url, params=params, timeout=30, verify=self.verify_ssl)
                response.raise_for_status()
                data = response.json()
                logger.debug(
                    f"OpenF1 API: GET {endpoint} -> {len(data)} records"
                )
                return data
                
            except requests.HTTPError as e:
                status_code = e.response.status_code if e.response is not None else None
                
                # Handle 502 Bad Gateway with fixed retries
                if status_code == 502:
                    retries_502 += 1
                    if retries_502 <= max_502_retries:
                        logger.warning(
                            f"502 Bad Gateway on {endpoint} "
                            f"(retry {retries_502}/{max_502_retries}). "
                            f"Waiting {retry_502_delay}s..."
                        )
                        sleep(retry_502_delay)
                        continue
                    else:
                        logger.error(
                            f"502 Bad Gateway on {endpoint} "
                            f"after {max_502_retries} retries. Giving up."
                        )
                        raise
                
                # Handle 429 Rate Limit with exponential backoff
                elif status_code == 429:
                    if attempt < max_retries:
                        wait_time = base_delay * (2 ** attempt)
                        logger.warning(
                            f"Rate limit hit on {endpoint} "
                            f"(attempt {attempt + 1}/{max_retries + 1}). "
                            f"Waiting {wait_time}s before retry..."
                        )
                        sleep(wait_time)
                        continue
                    else:
                        logger.error(
                            f"Rate limit exceeded on {endpoint} "
                            f"after {max_retries} retries"
                        )
                        raise
                else:
                    logger.error(f"OpenF1 API HTTP error on {endpoint}: {e}")
                    raise
                    
            except requests.RequestException as e:
                logger.error(f"OpenF1 API error on {endpoint}: {e}")
                if attempt < max_retries:
                    wait_time = base_delay * (2 ** attempt)
                    logger.info(
                        f"Retrying {endpoint} "
                        f"(attempt {attempt + 1}/{max_retries + 1}) "
                        f"after {wait_time}s..."
                    )
                    sleep(wait_time)
                    continue
                else:
                    raise
        
        return []

    def _increment_api_call_count(self, endpoint: str) -> None:
        """Increment API call counter for diagnostics."""
        normalized = endpoint.strip("/") or "unknown"
        with self._api_call_lock:
            self._api_call_counts[normalized] += 1

    def reset_api_call_counts(self) -> None:
        """Reset accumulated API call counters."""
        with self._api_call_lock:
            self._api_call_counts.clear()

    def get_api_call_counts(self) -> Dict[str, int]:
        """Return a snapshot of API call counters."""
        with self._api_call_lock:
            return dict(self._api_call_counts)

    def log_api_call_summary(
        self,
        context: str,
        reset: bool = False,
        level: int = logging.INFO,
    ) -> None:
        """Log the current API call counters for the given context."""
        counts = self.get_api_call_counts()
        if not counts:
            logger.log(level, "%s: no OpenF1 API calls recorded", context)
        else:
            total = sum(counts.values())
            details = ", ".join(
                f"{endpoint}={count}" for endpoint, count in sorted(counts.items())
            )
            logger.log(
                level,
                "%s: %d OpenF1 API call(s) (%s)",
                context,
                total,
                details,
            )
        if reset:
            self.reset_api_call_counts()

    def get_session(
        self, 
        year: int, 
        round_number: Optional[int] = None,
        session_name: Optional[str] = None,
        country_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get session information.
        
        Args:
            year: Season year
            round_number: Round number (optional, can use country_name instead)
            session_name: Session type ('Race', 'Qualifying', etc.)
            country_name: Country name for the race
            
        Returns:
            Session metadata dict or None if not found
        """
        params: Dict[str, Any] = {"year": year}
        
        if session_name:
            params["session_name"] = session_name
        if country_name:
            params["country_name"] = country_name
            
        sessions = self._request("sessions", params)
        
        if not sessions:
            logger.warning(f"No sessions found for {year} round {round_number}")
            return None
            
        # If round_number specified, filter by it
        if round_number:
            sessions = [s for s in sessions if s.get("round_number") == round_number]
            
        if not sessions:
            return None
            
        # Return most recent matching session
        sessions.sort(key=lambda x: x.get("date_start", ""), reverse=True)
        return sessions[0]

    def get_drivers(
        self, 
        session_key: int
    ) -> pd.DataFrame:
        """
        Get drivers participating in a session.
        
        Args:
            session_key: OpenF1 session identifier
            
        Returns:
            DataFrame with driver information
        """
        cached_df = self._load_cached_race_dataframe(session_key, DataType.DRIVER_INFO)
        if cached_df is not None and not cached_df.empty:
            logger.info(
                "Loaded %s drivers from cache for session %s",
                len(cached_df),
                session_key,
            )
            return cached_df

        params = {"session_key": session_key}
        drivers = self._request("drivers", params)

        if not drivers:
            logger.warning(f"No drivers found for session {session_key}")
            return pd.DataFrame()

        df = pd.DataFrame(drivers)
        
        # Normalize column names for compatibility
        column_mapping = {
            "driver_number": "DriverNumber",
            "name_acronym": "Abbreviation",
            "full_name": "DriverName",
            "team_name": "TeamName",
            "team_colour": "TeamColor"
        }
        
        df = df.rename(columns=column_mapping)
        logger.info(f"Loaded {len(df)} drivers for session {session_key}")
        
        return df

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    def _load_cached_race_dataframe(
        self,
        session_key: int,
        data_type: DataType,
    ) -> Optional[pd.DataFrame]:
        """Return cached race-level dataframe for the session when available."""
        metadata = self._session_metadata.get(int(session_key))
        if metadata is None:
            return None

        race_dir = self._find_cached_race_directory(int(session_key), metadata)
        if race_dir is None:
            return None

        extension = DEFAULT_CACHE_CONFIG.get_file_extension()
        cache_file = race_dir / f"{data_type.value}{extension}"
        if not cache_file.exists():
            return None

        cached_frame = self._read_cache_file(cache_file)
        if cached_frame is None or cached_frame.empty:
            return None

        # Ensure meeting/session keys propagate from cache when missing
        if "meeting_key" not in cached_frame.columns and metadata.get("meeting_key") is not None:
            cached_frame = cached_frame.assign(meeting_key=metadata.get("meeting_key"))
        if "session_key" not in cached_frame.columns:
            cached_frame = cached_frame.assign(session_key=int(session_key))
        return cached_frame

    def _find_cached_race_directory(
        self,
        session_key: int,
        metadata: Dict[str, Any],
    ) -> Optional[Path]:
        """Resolve the cache directory matching the session metadata."""
        cached = self._cached_race_dirs.get(session_key)
        if cached is not None and cached.exists():
            return cached

        year = self._extract_session_year(metadata)
        date_str = self._extract_session_date(metadata)
        if year is None or date_str is None:
            return None

        year_dir = DEFAULT_CACHE_CONFIG.races_dir / str(year)
        if not year_dir.exists():
            return None

        slug_candidates = self._collect_slug_candidates(metadata, date_str)
        for slug in slug_candidates:
            race_dir = year_dir / slug
            if race_dir.exists():
                self._cached_race_dirs[session_key] = race_dir
                return race_dir

        date_matches = sorted(path for path in year_dir.glob(f"{date_str}_*") if path.is_dir())
        if len(date_matches) == 1:
            self._cached_race_dirs[session_key] = date_matches[0]
            return date_matches[0]

        if date_matches:
            meeting_key = str(metadata.get("meeting_key") or metadata.get("MeetingKey") or "").lower()
            circuit_key = str(metadata.get("circuit_key") or metadata.get("CircuitKey") or "").lower()
            identifiers = {value for value in (meeting_key, circuit_key) if value}
            for candidate in date_matches:
                lowered = candidate.name.lower()
                if any(identifier in lowered for identifier in identifiers):
                    self._cached_race_dirs[session_key] = candidate
                    return candidate
            selected = date_matches[0]
            self._cached_race_dirs[session_key] = selected
            return selected

        return None

    @staticmethod
    def _extract_session_year(metadata: Dict[str, Any]) -> Optional[int]:
        """Try to coerce the session year from metadata fields."""
        year_candidates = [metadata.get("year"), metadata.get("Year")]
        for candidate in year_candidates:
            if candidate is None:
                continue
            try:
                return int(candidate)
            except (TypeError, ValueError):
                continue

        date_text = metadata.get("date_start") or metadata.get("session_start") or metadata.get("meeting_start")
        if date_text:
            parsed = pd.to_datetime(date_text, format="mixed", errors="coerce")
            if pd.notna(parsed):
                return int(parsed.year)
        return None

    @staticmethod
    def _extract_session_date(metadata: Dict[str, Any]) -> Optional[str]:
        """Return ISO date string for the session start."""
        date_text = metadata.get("date_start") or metadata.get("session_start") or metadata.get("meeting_start")
        if not date_text:
            year_value = metadata.get("year") or metadata.get("Year")
            if year_value is None:
                return None
            try:
                return str(int(year_value))
            except (TypeError, ValueError):
                return None

        parsed = pd.to_datetime(date_text, format="mixed", errors="coerce")
        if pd.isna(parsed):
            return None
        return parsed.date().isoformat()

    def _collect_slug_candidates(self, metadata: Dict[str, Any], date_str: str) -> List[str]:
        """Build possible cache directory slugs for the session."""
        candidate_slugs: List[str] = []

        raw_cache_slug = metadata.get("cache_slug") or metadata.get("CacheSlug")
        if isinstance(raw_cache_slug, str) and raw_cache_slug.strip():
            normalized_slug = raw_cache_slug.strip()
            if normalized_slug.startswith(date_str):
                candidate_slugs.append(normalized_slug)
            else:
                candidate_slugs.append(f"{date_str}_{_slugify(normalized_slug)}")

        name_keys = [
            ("meeting_name", "MeetingName"),
            ("official_name", "OfficialName"),
            ("event_name", "EventName"),
            ("location", "Location"),
            ("circuit_short_name", "CircuitShortName"),
            ("country_name", "CountryName", "Country"),
        ]
        seen_slugs: set[str] = set(candidate_slugs)
        for aliases in name_keys:
            value = self._first_metadata_value(metadata, aliases)
            if not value:
                continue
            slug = f"{date_str}_{_slugify(value)}"
            if slug not in seen_slugs:
                candidate_slugs.append(slug)
                seen_slugs.add(slug)

        meeting_key = metadata.get("meeting_key") or metadata.get("MeetingKey")
        if meeting_key is not None:
            slug = f"{date_str}_{_slugify(str(meeting_key))}"
            if slug not in seen_slugs:
                candidate_slugs.append(slug)

        return candidate_slugs

    @staticmethod
    def _first_metadata_value(metadata: Dict[str, Any], keys: tuple[str, ...]) -> Optional[str]:
        """Return the first non-empty metadata value for the provided keys."""
        for key in keys:
            value = metadata.get(key)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return None

    @staticmethod
    def _read_cache_file(file_path: Path) -> Optional[pd.DataFrame]:
        """Read cached dataframe from disk handling parquet/csv formats."""
        try:
            if file_path.suffix == ".parquet":
                return pd.read_parquet(file_path)
            if file_path.suffix == ".csv":
                return pd.read_csv(file_path)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to read cache file %s: %s", file_path, exc)
        return None

    @staticmethod
    def _filter_by_driver(
        data_frame: pd.DataFrame,
        driver_number: Optional[int],
    ) -> pd.DataFrame:
        """Return dataframe filtered by driver when driver data is requested."""
        if driver_number is None:
            return data_frame
        if "DriverNumber" not in data_frame.columns:
            return data_frame
        mask = data_frame["DriverNumber"] == driver_number
        return data_frame.loc[mask].copy()

    @staticmethod
    def _coerce_datetime_columns(
        data_frame: pd.DataFrame,
        columns: Sequence[str],
    ) -> pd.DataFrame:
        """Ensure the provided columns are timezone-aware datetimes when present."""
        if not columns:
            return data_frame
        coerced = data_frame.copy()
        for column in columns:
            if column in coerced.columns:
                coerced[column] = pd.to_datetime(
                    coerced[column],
                    format="mixed",
                    errors="coerce",
                )
        return coerced

    @staticmethod
    def _filter_by_time_range(
        data_frame: pd.DataFrame,
        column: str,
        start: Optional[str],
        end: Optional[str],
    ) -> pd.DataFrame:
        """Filter dataframe rows by ISO datetime range if both parameters are provided."""
        if column not in data_frame.columns:
            return data_frame

        filtered = data_frame.copy()
        if start:
            start_dt = pd.to_datetime(start, format="mixed", errors="coerce")
            if pd.notna(start_dt):
                filtered = filtered.loc[filtered[column] >= start_dt]
        if end:
            end_dt = pd.to_datetime(end, format="mixed", errors="coerce")
            if pd.notna(end_dt):
                filtered = filtered.loc[filtered[column] <= end_dt]
        return filtered

    def get_laps(
        self,
        session_key: int,
        driver_number: Optional[int] = None,
    ) -> pd.DataFrame:
        """Return lap data for a session optionally filtered by driver."""
        cached_df = self._load_cached_race_dataframe(
            session_key,
            DataType.LAP_TIMES,
        )
        if cached_df is not None:
            df = cached_df.copy()
            df = self._filter_by_driver(df, driver_number)
            df = self._coerce_datetime_columns(df, ["LapStartTime", "LapEndTime"])
            logger.info(
                "Loaded %s laps for session %s from cache",
                len(df),
                session_key,
            )
            return df.reset_index(drop=True)

        params = {"session_key": session_key}
        if driver_number:
            params["driver_number"] = driver_number

        laps = self._request("laps", params)

        if not laps:
            logger.warning(f"No laps found for session {session_key}")
            return pd.DataFrame()

        df = pd.DataFrame(laps)

        # Convert timestamps to datetime
        if "date_start" in df.columns:
            df["date_start"] = pd.to_datetime(df["date_start"], format="mixed")

        # Calculate lap duration in seconds
        if "lap_duration" in df.columns:
            df["lap_duration_seconds"] = df["lap_duration"]

        # Normalize column names
        column_mapping = {
            "driver_number": "DriverNumber",
            "lap_number": "LapNumber",
            "lap_duration": "LapTime_seconds",
            "date_start": "LapStartTime",
            "is_pit_out_lap": "PitOutTime",
            "is_pit_in_lap": "PitInTime"
        }
        
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

        # Add LapEndTime calculation
        if "LapStartTime" in df.columns and "LapTime_seconds" in df.columns:
            df["LapEndTime"] = df["LapStartTime"] + pd.to_timedelta(df["LapTime_seconds"], unit="s")

        logger.info(f"Loaded {len(df)} laps for session {session_key}")

        return df

    def get_positions(
        self,
        session_key: int,
        driver_number: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Get position/interval data during session.
        
        Args:
            session_key: OpenF1 session identifier
            driver_number: Filter by specific driver (optional)
            
        Returns:
            DataFrame with position updates
        """
        cached_df = self._load_cached_race_dataframe(session_key, DataType.POSITIONS)
        if cached_df is not None:
            df = cached_df.copy()
            df = self._filter_by_driver(df, driver_number)
            df = self._coerce_datetime_columns(df, ["Timestamp"])
            logger.info(
                "Loaded %s position updates for session %s from cache",
                len(df),
                session_key,
            )
            return df.reset_index(drop=True)

        params = {"session_key": session_key}
        if driver_number:
            params["driver_number"] = driver_number
            
        positions = self._request("position", params)
        
        if not positions:
            logger.warning(f"No position data for session {session_key}")
            return pd.DataFrame()
            
        df = pd.DataFrame(positions)
        
        # Convert timestamp
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], format='mixed')
            
        column_mapping = {
            "driver_number": "DriverNumber",
            "position": "Position",
            "date": "Timestamp"
        }
        
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
        
        logger.info(f"Loaded {len(df)} position updates for session {session_key}")
        
        return df

    def get_stints(
        self,
        session_key: int,
        driver_number: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Get tire stint information.
        
        Args:
            session_key: OpenF1 session identifier
            driver_number: Filter by specific driver (optional)
            
        Returns:
            DataFrame with stint/tire data
        """
        cached_df = self._load_cached_race_dataframe(session_key, DataType.TIRE_STRATEGY)
        if cached_df is not None:
            df = cached_df.copy()
            df = self._filter_by_driver(df, driver_number)
            logger.info(
                "Loaded %s stints for session %s from cache",
                len(df),
                session_key,
            )
            return df.reset_index(drop=True)

        params = {"session_key": session_key}
        if driver_number:
            params["driver_number"] = driver_number
            
        stints = self._request("stints", params)
        
        if not stints:
            logger.warning(f"No stint data for session {session_key}")
            return pd.DataFrame()
            
        df = pd.DataFrame(stints)
        
        column_mapping = {
            "driver_number": "DriverNumber",
            "stint_number": "StintNumber",
            "lap_start": "StintStart",
            "lap_end": "StintEnd",
            "compound": "Compound",
            "tyre_age_at_start": "TyreAge"
        }
        
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
        
        logger.info(f"Loaded {len(df)} stints for session {session_key}")
        
        return df

    def get_race_control_messages(
        self,
        session_key: int
    ) -> pd.DataFrame:
        """
        Get race control messages (flags, SC, VSC, etc.).
        
        Args:
            session_key: OpenF1 session identifier
            
        Returns:
            DataFrame with race control events
        """
        cached_df = self._load_cached_race_dataframe(session_key, DataType.RACE_CONTROL)
        if cached_df is not None:
            df = cached_df.copy()
            df = self._coerce_datetime_columns(df, ["Time"])
            logger.info(
                "Loaded %s race control messages for session %s from cache",
                len(df),
                session_key,
            )
            return df.reset_index(drop=True)

        params = {"session_key": session_key}
        messages = self._request("race_control", params)
        
        if not messages:
            logger.warning(f"No race control messages for session {session_key}")
            return pd.DataFrame()
            
        df = pd.DataFrame(messages)
        
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], format='mixed')
            
        column_mapping = {
            "date": "Time",
            "category": "Category",
            "message": "Message",
            "flag": "Flag"
        }
        
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
        
        logger.info(f"Loaded {len(df)} race control messages for session {session_key}")
        
        return df

    def get_pit_stops(
        self,
        session_key: int,
        driver_number: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Get pit stop data.
        
        Args:
            session_key: OpenF1 session identifier
            driver_number: Filter by specific driver (optional)
            
        Returns:
            DataFrame with pit stop information
        """
        cached_df = self._load_cached_race_dataframe(session_key, DataType.PIT_STOPS)
        if cached_df is not None:
            df = cached_df.copy()
            df = self._filter_by_driver(df, driver_number)
            df = self._coerce_datetime_columns(df, ["Time"])
            logger.info(
                "Loaded %s pit stops for session %s from cache",
                len(df),
                session_key,
            )
            return df.reset_index(drop=True)

        params = {"session_key": session_key}
        if driver_number:
            params["driver_number"] = driver_number
            
        pit_stops = self._request("pit", params)
        
        if not pit_stops:
            logger.warning(f"No pit stop data for session {session_key}")
            return pd.DataFrame()
            
        df = pd.DataFrame(pit_stops)
        
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], format='mixed')
            
        column_mapping = {
            "driver_number": "DriverNumber",
            "lap_number": "Lap",
            "pit_duration": "PitDuration",
            "date": "Time"
        }
        
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
        
        logger.info(f"Loaded {len(df)} pit stops for session {session_key}")
        
        return df

    def get_weather(
        self,
        session_key: int
    ) -> pd.DataFrame:
        """
        Get weather data for session.
        
        Args:
            session_key: OpenF1 session identifier
            
        Returns:
            DataFrame with weather conditions
        """
        cached_df = self._load_cached_race_dataframe(session_key, DataType.WEATHER)
        if cached_df is not None:
            df = cached_df.copy()
            df = self._coerce_datetime_columns(df, ["Time"])
            logger.info(
                "Loaded %s weather records for session %s from cache",
                len(df),
                session_key,
            )
            return df.reset_index(drop=True)

        params = {"session_key": session_key}
        weather = self._request("weather", params)
        
        if not weather:
            logger.warning(f"No weather data for session {session_key}")
            return pd.DataFrame()
            
        df = pd.DataFrame(weather)
        
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], format='mixed')
            
        column_mapping = {
            "date": "Time",
            "air_temperature": "AirTemp",
            "track_temperature": "TrackTemp",
            "humidity": "Humidity",
            "pressure": "Pressure",
            "wind_speed": "WindSpeed",
            "wind_direction": "WindDirection",
            "rainfall": "Rainfall"
        }
        
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
        
        logger.info(f"Loaded {len(df)} weather records for session {session_key}")
        
        return df

    def get_intervals(
        self,
        session_key: int,
        driver_number: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Get interval/gap data (time gaps between drivers).
        
        Args:
            session_key: OpenF1 session identifier
            driver_number: Filter by specific driver (optional)
            
        Returns:
            DataFrame with interval data
        """
        cached_df = self._load_cached_race_dataframe(session_key, DataType.INTERVALS)
        if cached_df is not None:
            df = cached_df.copy()
            df = self._filter_by_driver(df, driver_number)
            df = self._coerce_datetime_columns(df, ["Timestamp"])
            logger.info(
                "Loaded %s interval records for session %s from cache",
                len(df),
                session_key,
            )
            return df.reset_index(drop=True)

        params = {"session_key": session_key}
        if driver_number:
            params["driver_number"] = driver_number
            
        intervals = self._request("intervals", params)
        
        if not intervals:
            logger.warning(f"No interval data for session {session_key}")
            return pd.DataFrame()
            
        df = pd.DataFrame(intervals)
        
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], format='mixed')
            
        column_mapping = {
            "driver_number": "DriverNumber",
            "gap_to_leader": "GapToLeader",
            "interval": "Interval",
            "date": "Timestamp"
        }
        
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
        
        logger.info(f"Loaded {len(df)} interval records for session {session_key}")
        
        return df

    def get_car_data(
        self,
        session_key: int,
        driver_number: Optional[int] = None,
        date_start: Optional[str] = None,
        date_end: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Get car telemetry data (speed, RPM, gear, throttle, brake, DRS).
        
        Args:
            session_key: OpenF1 session identifier
            driver_number: Filter by specific driver (optional)
            date_start: ISO format timestamp for start filter (optional)
                       Example: "2025-11-30T16:10:00"
            date_end: ISO format timestamp for end filter (optional)
                     Example: "2025-11-30T16:12:00"
            
        Returns:
            DataFrame with car telemetry data
        """
        cached_df = self._load_cached_race_dataframe(session_key, DataType.CAR_DATA)
        if cached_df is not None:
            df = cached_df.copy()
            df = self._filter_by_driver(df, driver_number)
            df = self._coerce_datetime_columns(df, ["Timestamp"])
            df = self._filter_by_time_range(df, "Timestamp", date_start, date_end)
            logger.info(
                "Loaded %s car data records for session %s from cache",
                len(df),
                session_key,
            )
            return df.reset_index(drop=True)

        params: Dict[str, Any] = {"session_key": session_key}
        if driver_number:
            params["driver_number"] = driver_number
        if date_start:
            params["date>"] = date_start  # OpenF1 uses date> not date>=
        if date_end:
            params["date<"] = date_end
            
        try:
            car_data = self._request("car_data", params)
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            if status_code == 422:
                logger.warning(
                    f"Car telemetry not available for session {session_key} (HTTP 422)"
                )
                return pd.DataFrame()
            raise
        
        if not car_data:
            logger.warning(f"No car data for session {session_key}")
            return pd.DataFrame()
            
        df = pd.DataFrame(car_data)
        
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], format='mixed')
            
        column_mapping = {
            "driver_number": "DriverNumber",
            "date": "Timestamp",
            "speed": "Speed",
            "rpm": "RPM",
            "n_gear": "Gear",
            "throttle": "Throttle",
            "brake": "Brake",
            "drs": "DRS"
        }
        
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
        
        logger.info(f"Loaded {len(df)} car data records for session {session_key}")
        
        return df

    def get_location(
        self,
        session_key: int,
        driver_number: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Get GPS location data for drivers on track.
        
        Args:
            session_key: OpenF1 session identifier
            driver_number: Filter by specific driver (optional)
            
        Returns:
            DataFrame with GPS coordinates
        """
        params = {"session_key": session_key}
        if driver_number:
            params["driver_number"] = driver_number
            
        location = self._request("location", params)
        
        if not location:
            logger.warning(f"No location data for session {session_key}")
            return pd.DataFrame()
            
        df = pd.DataFrame(location)
        
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], format='mixed')
            
        column_mapping = {
            "driver_number": "DriverNumber",
            "date": "Timestamp",
            "x": "X",
            "y": "Y",
            "z": "Z"
        }
        
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
        
        logger.info(f"Loaded {len(df)} location records for session {session_key}")
        
        return df

    def get_team_radio(
        self,
        session_key: int,
        driver_number: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Get team radio messages.
        
        Args:
            session_key: OpenF1 session identifier
            driver_number: Filter by specific driver (optional)
            
        Returns:
            DataFrame with team radio messages and audio URLs
        """
        params = {"session_key": session_key}
        if driver_number:
            params["driver_number"] = driver_number
            
        radio = self._request("team_radio", params)
        
        if not radio:
            logger.warning(f"No team radio data for session {session_key}")
            return pd.DataFrame()
            
        df = pd.DataFrame(radio)
        
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], format='mixed')
            
        column_mapping = {
            "driver_number": "DriverNumber",
            "date": "Timestamp",
            "recording_url": "AudioURL"
        }
        
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
        
        logger.info(f"Loaded {len(df)} team radio messages for session {session_key}")
        
        return df

    def get_meetings(
        self,
        session_key: Optional[int] = None,
        year: Optional[int] = None,
        country_name: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Get meeting (race weekend) information.
        
        Args:
            session_key: OpenF1 session identifier (optional)
            year: Filter by year (optional)
            country_name: Filter by country (optional)
            
        Returns:
            DataFrame with meeting/event information
        """
        params = {}
        if session_key:
            params["session_key"] = session_key
        if year:
            params["year"] = year
        if country_name:
            params["country_name"] = country_name
            
        meetings = self._request("meetings", params)
        
        if not meetings:
            logger.warning("No meetings found")
            return pd.DataFrame()
            
        df = pd.DataFrame(meetings)
        
        if "date_start" in df.columns:
            df["date_start"] = pd.to_datetime(df["date_start"], format='mixed')
            
        column_mapping = {
            "meeting_key": "MeetingKey",
            "meeting_name": "MeetingName",
            "meeting_official_name": "OfficialName",
            "location": "Location",
            "country_name": "Country",
            "circuit_short_name": "Circuit",
            "date_start": "StartDate",
            "year": "Year"
        }
        
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
        
        logger.info(f"Loaded {len(df)} meetings")
        
        return df

    def get_overtakes(
        self,
        session_key: int,
        driver_number: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Get overtaking maneuvers during a session.
        
        Args:
            session_key: OpenF1 session identifier
            driver_number: Optional filter for specific driver
            
        Returns:
            DataFrame with columns: DriverNumber, OvertakingDriverNumber, 
            Timestamp, LapNumber
        """
        logger.info(
            f"Getting overtakes for session {session_key}"
            + (f", driver {driver_number}" if driver_number else "")
        )
        
        params = {"session_key": session_key}
        if driver_number:
            params["driver_number"] = driver_number
        
        overtakes = self._request("overtakes", params)
        
        if not overtakes:
            logger.warning("No overtakes found")
            return pd.DataFrame()
        
        df = pd.DataFrame(overtakes)
        
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], format='mixed')
        
        column_mapping = {
            "driver_number": "DriverNumber",
            "overtaking_driver_number": "OvertakingDriverNumber",
            "date": "Timestamp",
            "lap_number": "LapNumber"
        }
        
        df = df.rename(
            columns={k: v for k, v in column_mapping.items() if k in df.columns}
        )
        
        logger.info(f"Loaded {len(df)} overtakes for session {session_key}")
        
        return df

    def stream_live_data(
        self,
        session_key: int,
        data_type: str = "position",
        callback=None,
        poll_interval: float = 2.0
    ):
        """
        Stream live data during an ongoing session (for future real-time feature).
        
        Args:
            session_key: OpenF1 session identifier
            data_type: Type of data to stream ('position', 'laps', etc.)
            callback: Function to call with new data
            poll_interval: Seconds between polls
        """
        logger.info(f"Starting live stream for session {session_key}, type: {data_type}")
        
        last_timestamp = None
        
        while True:
            try:
                params = {"session_key": session_key}
                
                # Only get new data since last poll
                if last_timestamp:
                    params["date>"] = last_timestamp.isoformat()
                
                data = self._request(data_type, params)
                
                if data and callback:
                    callback(data)
                    
                    # Update last timestamp
                    if "date" in data[-1]:
                        last_timestamp = pd.to_datetime(data[-1]["date"], format='mixed')
                
                sleep(poll_interval)
                
            except KeyboardInterrupt:
                logger.info("Live stream stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in live stream: {e}")
                sleep(poll_interval)
