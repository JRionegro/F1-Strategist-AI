"""
OpenF1 Adapter - Compatibility layer to replace FastF1 with OpenF1.

Provides FastF1-like interface using OpenF1 as backend, allowing
gradual migration without breaking existing code.
"""

import logging
from typing import Optional, List
from datetime import datetime
import pandas as pd
import numpy as np

from .openf1_data_provider import OpenF1DataProvider

logger = logging.getLogger(__name__)


class SessionAdapter:
    """
    Adapter that mimics fastf1.core.Session using OpenF1 data.
    
    Provides same properties and methods as FastF1 Session objects
    to maintain compatibility with existing dashboard code.
    """
    
    def __init__(
        self,
        provider: OpenF1DataProvider,
        session_info: dict,
        session_key: int
    ):
        """
        Initialize session adapter.
        
        Args:
            provider: OpenF1 data provider instance
            session_info: Session metadata from OpenF1
            session_key: OpenF1 session identifier
        """
        self.provider = provider
        self.session_info = session_info
        self.session_key = session_key
        
        # Cache loaded data
        self._laps = None
        self._results = None
        self._drivers = None
        self._weather = None
        self._race_control_messages = None
        
        # Session metadata (FastF1-compatible properties)
        self.name = session_info.get("session_name", "Unknown")
        date_start = session_info.get("date_start")
        self.date = pd.to_datetime(date_start) if date_start else pd.Timestamp.now()
        self.event_name = session_info.get("meeting_name", "")
        self.location = session_info.get("location", "")
        self.country_name = session_info.get("country_name", "")
        
        logger.info(f"SessionAdapter created for {self.event_name} - {self.name}")
    
    @property
    def laps(self) -> pd.DataFrame:
        """Get lap data (lazy loaded)."""
        if self._laps is None:
            self.load_laps()
        # Type guard: after load_laps, _laps is always a DataFrame (possibly empty)
        assert self._laps is not None, "Laps should be loaded"
        return self._laps
    
    @property
    def results(self) -> pd.DataFrame:
        """Get race results (lazy loaded)."""
        if self._results is None:
            self.load_results()
        # Type guard: after load_results, _results is always a DataFrame (possibly empty)
        assert self._results is not None, "Results should be loaded"
        return self._results
    
    @property
    def drivers(self) -> List[str]:
        """Get list of driver abbreviations."""
        if self._drivers is None:
            driver_df = self.provider.get_drivers(self.session_key)
            self._drivers = driver_df["Abbreviation"].unique().tolist()
        return self._drivers
    
    @property
    def weather_data(self) -> pd.DataFrame:
        """Get weather data."""
        if self._weather is None:
            self._weather = self.provider.get_weather(self.session_key)
        return self._weather
    
    @property
    def race_control_messages(self) -> pd.DataFrame:
        """Get race control messages."""
        if self._race_control_messages is None:
            self._race_control_messages = self.provider.get_race_control_messages(
                self.session_key
            )
        return self._race_control_messages
    
    def load(self, laps: bool = True, telemetry: bool = False, weather: bool = False,
             messages: bool = False) -> None:
        """
        Load session data (FastF1-compatible method).
        
        Args:
            laps: Load lap data
            telemetry: Load telemetry (not implemented for OpenF1)
            weather: Load weather data
            messages: Load race control messages
        """
        logger.info(f"Loading session data for {self.event_name} - {self.name}")
        
        if laps:
            self.load_laps()
        if weather:
            self._weather = self.provider.get_weather(self.session_key)
        if messages:
            self._race_control_messages = self.provider.get_race_control_messages(
                self.session_key
            )
            
        logger.info("Session data loaded successfully")
    
    def load_laps(self) -> None:
        """Load and process lap data from OpenF1."""
        logger.info("Loading laps from OpenF1...")
        
        # Get laps from OpenF1
        laps_df = self.provider.get_laps(self.session_key)
        
        if laps_df.empty:
            logger.warning("No lap data available")
            self._laps = pd.DataFrame()
            return
        
        # Get stints for tire information
        stints_df = self.provider.get_stints(self.session_key)
        
        # Merge tire compound information
        if not stints_df.empty:
            # Create a mapping of lap number to compound for each driver
            for _, stint in stints_df.iterrows():
                driver_num = stint["DriverNumber"]
                start_lap = stint.get("StintStart", 1)
                end_lap = stint.get("StintEnd", 999)
                compound = stint.get("Compound", "UNKNOWN")
                
                mask = (
                    (laps_df["DriverNumber"] == driver_num) &
                    (laps_df["LapNumber"] >= start_lap) &
                    (laps_df["LapNumber"] <= end_lap)
                )
                laps_df.loc[mask, "Compound"] = compound
        
        # Add default compound if missing
        if "Compound" not in laps_df.columns:
            laps_df["Compound"] = "UNKNOWN"
        
        # Convert LapTime_seconds to timedelta for compatibility
        if "LapTime_seconds" in laps_df.columns:
            laps_df["LapTime"] = pd.to_timedelta(laps_df["LapTime_seconds"], unit="s")
        
        # Calculate LapStartTime and LapEndTime as timedelta from session start
        if "LapStartTime" in laps_df.columns and not laps_df.empty:
            session_start = self.date
            
            # Convert absolute timestamps to timedelta from start
            laps_df["LapStartTime_abs"] = laps_df["LapStartTime"]
            laps_df["LapStartTime"] = laps_df["LapStartTime"] - session_start
            
            # Calculate end time
            if "LapTime" in laps_df.columns:
                laps_df["LapEndTime"] = laps_df["LapStartTime"] + laps_df["LapTime"]
                
                # Create seconds versions for simulation
                # Ensure timedelta type before accessing dt accessor
                laps_df["LapStartTime_seconds"] = pd.to_timedelta(
                    laps_df["LapStartTime"]
                ).dt.total_seconds()
                laps_df["LapEndTime_seconds"] = pd.to_timedelta(
                    laps_df["LapEndTime"]
                ).dt.total_seconds()
        
        # Add PitInTime and PitOutTime flags
        if "PitOutTime" not in laps_df.columns:
            laps_df["PitOutTime"] = pd.NaT
        if "PitInTime" not in laps_df.columns:
            laps_df["PitInTime"] = pd.NaT
        
        # Add Driver info (merge from drivers endpoint)
        drivers_df = self.provider.get_drivers(self.session_key)
        if not drivers_df.empty:
            laps_df = laps_df.merge(
                drivers_df[["DriverNumber", "Abbreviation", "DriverName", "TeamName"]],
                on="DriverNumber",
                how="left"
            )
        
        self._laps = laps_df
        logger.info(f"Loaded {len(laps_df)} laps")
    
    def load_results(self) -> None:
        """Load race results by analyzing final lap positions."""
        logger.info("Loading results from OpenF1...")
        
        if self._laps is None:
            self.load_laps()
        
        # Type guard after load_laps
        assert self._laps is not None, "Laps should be loaded"
        
        if self._laps.empty:
            logger.warning("Cannot load results without lap data")
            self._results = pd.DataFrame()
            return
        
        # Get last lap for each driver
        last_laps = (
            self._laps.sort_values("LapNumber")
            .groupby("DriverNumber")
            .last()
            .reset_index()
        )
        
        # Get positions from positions endpoint (more accurate)
        positions_df = self.provider.get_positions(self.session_key)
        
        if not positions_df.empty:
            # Get final position for each driver
            final_positions = (
                positions_df.sort_values("Timestamp")
                .groupby("DriverNumber")
                .last()
                .reset_index()
            )
            
            # Merge with last lap data
            results = last_laps.merge(
                final_positions[["DriverNumber", "Position"]],
                on="DriverNumber",
                how="left"
            )
        else:
            # Fallback: use lap count as proxy for position
            results = last_laps.copy()
            results["Position"] = range(1, len(results) + 1)
        
        # Rename columns for FastF1 compatibility
        results = results.rename(columns={
            "Position": "ClassifiedPosition",
            "Abbreviation": "Abbreviation",
            "DriverName": "FullName",
            "TeamName": "TeamName",
            "DriverNumber": "DriverNumber"
        })
        
        # Add missing columns with defaults
        if "Points" not in results.columns:
            results["Points"] = 0
        if "Status" not in results.columns:
            results["Status"] = "Finished"
        if "GridPosition" not in results.columns:
            results["GridPosition"] = np.nan
        
        # Sort by final position
        results = results.sort_values("ClassifiedPosition")
        
        self._results = results
        logger.info(f"Loaded results for {len(results)} drivers")


def get_session(
    year: int,
    round_number: int,
    session_type: str,
    provider: Optional[OpenF1DataProvider] = None
) -> Optional[SessionAdapter]:
    """
    Get session adapter (FastF1-like interface).
    
    Args:
        year: Season year
        round_number: Round number
        session_type: Session type ('R', 'Q', 'FP1', etc.)
        provider: OpenF1 provider instance (creates new if None)
        
    Returns:
        SessionAdapter instance or None if not found
    """
    if provider is None:
        provider = OpenF1DataProvider()
    
    # Map FastF1 session codes to OpenF1 session names
    session_mapping = {
        "R": "Race",
        "Q": "Qualifying",
        "SQ": "Sprint Qualifying",
        "S": "Sprint",
        "FP1": "Practice 1",
        "FP2": "Practice 2",
        "FP3": "Practice 3"
    }
    
    session_name = session_mapping.get(session_type, session_type)
    
    logger.info(f"Fetching session: {year} Round {round_number} {session_name}")
    
    # Get session info from OpenF1
    session_info = provider.get_session(
        year=year,
        round_number=round_number,
        session_name=session_name
    )
    
    if not session_info:
        logger.error(f"Session not found: {year} Round {round_number} {session_name}")
        return None
    
    session_key = session_info.get("session_key")
    if not session_key:
        logger.error("Session key not found in session info")
        return None
    
    return SessionAdapter(provider, session_info, session_key)
