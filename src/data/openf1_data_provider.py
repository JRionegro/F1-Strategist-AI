"""
OpenF1 Data Provider - Unified source for historical and real-time F1 data.

Uses OpenF1 API (openf1.org) for both historical replay simulations
and live race monitoring, eliminating dual-API complexity.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import pandas as pd
import requests
from time import sleep

logger = logging.getLogger(__name__)


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
    
    def __init__(self, rate_limit_delay: float = 0.5):
        """
        Initialize OpenF1 provider.
        
        Args:
            rate_limit_delay: Seconds to wait between API calls
        """
        self.rate_limit_delay = rate_limit_delay
        self._last_request_time = None
        logger.info("OpenF1DataProvider initialized")

    def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        if self._last_request_time:
            elapsed = (datetime.now() - self._last_request_time).total_seconds()
            if elapsed < self.rate_limit_delay:
                sleep(self.rate_limit_delay - elapsed)
        self._last_request_time = datetime.now()

    def _request(self, endpoint: str, params: Optional[Dict] = None) -> List[Dict]:
        """
        Make API request with rate limiting and error handling.
        
        Args:
            endpoint: API endpoint (e.g., 'sessions', 'laps')
            params: Query parameters
            
        Returns:
            List of JSON objects from API response
        """
        self._rate_limit()
        
        url = f"{self.BASE_URL}/{endpoint}"
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            logger.debug(f"OpenF1 API: GET {endpoint} -> {len(data)} records")
            return data
        except requests.RequestException as e:
            logger.error(f"OpenF1 API error on {endpoint}: {e}")
            return []

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

    def get_laps(
        self, 
        session_key: int,
        driver_number: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Get lap data for a session.
        
        Args:
            session_key: OpenF1 session identifier
            driver_number: Filter by specific driver (optional)
            
        Returns:
            DataFrame with lap times and metadata
        """
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
            df["date_start"] = pd.to_datetime(df["date_start"], format='mixed')
        
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
        driver_number: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Get car telemetry data (speed, RPM, gear, throttle, brake, DRS).
        
        Args:
            session_key: OpenF1 session identifier
            driver_number: Filter by specific driver (optional)
            
        Returns:
            DataFrame with car telemetry data
        """
        params = {"session_key": session_key}
        if driver_number:
            params["driver_number"] = driver_number
            
        car_data = self._request("car_data", params)
        
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
