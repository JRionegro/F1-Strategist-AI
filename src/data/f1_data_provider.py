"""
Unified F1 Data Provider - Wrapper for FastF1 and OpenF1.

Provides unified interface to access Formula 1 data from multiple
sources (FastF1 for historical analysis and OpenF1 for real-time).
"""

import logging
import os
from typing import Optional
from abc import ABC, abstractmethod

import pandas as pd
import fastf1

logger = logging.getLogger(__name__)


class F1DataProvider(ABC):
    """Base interface for F1 data providers."""

    @abstractmethod
    def get_race_results(
        self, year: int, round_number: int
    ) -> pd.DataFrame:
        """Get race results."""
        pass

    @abstractmethod
    def get_telemetry(
        self, year: int, round_number: int, driver: str
    ) -> pd.DataFrame:
        """Get telemetry data."""
        pass

    @abstractmethod
    def get_qualifying_results(
        self, year: int, round_number: int
    ) -> pd.DataFrame:
        """Get qualifying results."""
        pass


class FastF1Provider(F1DataProvider):
    """Data provider using FastF1 (historical analysis)."""

    def __init__(self, cache_dir: str = "./cache") -> None:
        """Initialize FastF1 provider."""
        os.makedirs(cache_dir, exist_ok=True)
        fastf1.Cache.enable_cache(cache_dir=cache_dir)
        logger.info("FastF1Provider initialized with cache")

    def get_race_results(
        self, year: int, round_number: int
    ) -> pd.DataFrame:
        """Get race results from FastF1."""
        try:
            session = fastf1.get_session(year, round_number, "R")
            session.load()

            results = session.results[
                [
                    "DriverNumber",
                    "Abbreviation",
                    "TeamName",
                    "ClassifiedPosition",
                    "Points",
                    "Status"
                ]
            ].copy()

            results.rename(
                columns={
                    "Abbreviation": "Driver",
                    "ClassifiedPosition": "Position"
                },
                inplace=True
            )

            logger.info(f"Race results: {year} R{round_number}")
            return results
        except Exception as e:
            msg = f"Error getting race results: {str(e)}"
            logger.error(msg)
            raise

    def get_telemetry(
        self, year: int, round_number: int, driver: str
    ) -> pd.DataFrame:
        """Get detailed telemetry data."""
        try:
            session = fastf1.get_session(year, round_number, "R")
            session.load()

            laps = session.laps.pick_drivers(driver)

            if laps.empty:
                logger.warning(
                    f"No telemetry for {driver} "
                    f"in {year} R{round_number}"
                )
                return pd.DataFrame()

            telemetry = (
                laps.iloc[-1]
                .get_telemetry()
                .reset_index(drop=True)
            )

            logger.info(
                f"Telemetry: {driver} in {year} R{round_number}"
            )
            return telemetry
        except Exception as e:
            logger.error(f"Error getting telemetry: {str(e)}")
            raise

    def get_qualifying_results(
        self, year: int, round_number: int
    ) -> pd.DataFrame:
        """Get qualifying results."""
        try:
            session = fastf1.get_session(year, round_number, "Q")
            session.load()

            results = session.results[
                [
                    "DriverNumber",
                    "Abbreviation",
                    "TeamName",
                    "Q1",
                    "Q2",
                    "Q3",
                    "GridPosition"
                ]
            ].copy()

            results.rename(
                columns={"Abbreviation": "Driver"},
                inplace=True
            )

            logger.info(f"Qualifying: {year} R{round_number}")
            return results
        except Exception as e:
            logger.error(f"Error getting qualifying: {str(e)}")
            raise

    def get_lap_times(
        self, year: int, round_number: int, session_type: str = "R"
    ) -> pd.DataFrame:
        """Get lap times for all drivers."""
        try:
            session = fastf1.get_session(
                year, round_number, session_type
            )
            session.load()

            laps = session.laps[[
                "Driver",
                "LapNumber",
                "LapTime",
                "Sector1Time",
                "Sector2Time",
                "Sector3Time",
                "Compound",
                "TyreLife",
                "IsPersonalBest"
            ]].copy()

            logger.info(f"Lap times: {year} R{round_number}")
            return laps
        except Exception as e:
            logger.error(f"Error getting lap times: {str(e)}")
            raise

    def get_pit_stops(
        self, year: int, round_number: int
    ) -> pd.DataFrame:
        """Get pit stop data."""
        try:
            session = fastf1.get_session(year, round_number, "R")
            session.load()

            laps = session.laps
            pit_stops = laps[laps["PitOutTime"].notna()][[
                "Driver",
                "LapNumber",
                "PitInTime",
                "PitOutTime",
                "Compound",
                "TyreLife"
            ]].copy()

            logger.info(f"Pit stops: {year} R{round_number}")
            return pit_stops
        except Exception as e:
            logger.error(f"Error getting pit stops: {str(e)}")
            raise

    def get_weather(
        self, year: int, round_number: int
    ) -> pd.DataFrame:
        """Get weather data."""
        try:
            session = fastf1.get_session(year, round_number, "R")
            session.load()

            if session.weather_data is None:
                logger.warning(
                    f"No weather data: {year} R{round_number}"
                )
                return pd.DataFrame()

            weather = session.weather_data[[
                "Time",
                "AirTemp",
                "TrackTemp",
                "Humidity",
                "Pressure",
                "WindSpeed",
                "WindDirection",
                "Rainfall"
            ]].copy()

            logger.info(f"Weather data: {year} R{round_number}")
            return weather
        except Exception as e:
            logger.error(f"Error getting weather: {str(e)}")
            raise

    def get_tire_strategy(
        self, year: int, round_number: int
    ) -> pd.DataFrame:
        """Get tire strategy data."""
        try:
            session = fastf1.get_session(year, round_number, "R")
            session.load()

            laps = session.laps[[
                "Driver",
                "LapNumber",
                "Compound",
                "TyreLife",
                "FreshTyre",
                "Stint"
            ]].copy()

            logger.info(f"Tire strategy: {year} R{round_number}")
            return laps
        except Exception as e:
            logger.error(
                f"Error getting tire strategy: {str(e)}"
            )
            raise

    def get_practice_results(
        self, year: int, round_number: int, session_type: str
    ) -> pd.DataFrame:
        """Get practice session results (FP1/FP2/FP3)."""
        try:
            session = fastf1.get_session(
                year, round_number, session_type
            )
            session.load()

            results = session.results[[
                "DriverNumber",
                "Abbreviation",
                "TeamName",
                "Position"
            ]].copy()

            results.rename(
                columns={"Abbreviation": "Driver"},
                inplace=True
            )

            logger.info(
                f"Practice results: "
                f"{year} R{round_number} {session_type}"
            )
            return results
        except Exception as e:
            logger.error(
                f"Error getting practice results: {str(e)}"
            )
            raise

    def get_sprint_results(
        self, year: int, round_number: int
    ) -> pd.DataFrame:
        """Get sprint race results."""
        try:
            session = fastf1.get_session(year, round_number, "S")
            session.load()

            results = session.results[[
                "DriverNumber",
                "Abbreviation",
                "TeamName",
                "ClassifiedPosition",
                "Points",
                "Status"
            ]].copy()

            results.rename(
                columns={
                    "Abbreviation": "Driver",
                    "ClassifiedPosition": "Position"
                },
                inplace=True
            )

            logger.info(f"Sprint results: {year} R{round_number}")
            return results
        except Exception as e:
            logger.error(
                f"Error getting sprint results: {str(e)}"
            )
            raise

    def get_driver_info(
        self, year: int, round_number: int
    ) -> pd.DataFrame:
        """Get driver information."""
        try:
            session = fastf1.get_session(year, round_number, "R")
            session.load()

            drivers = session.results[[
                "DriverNumber",
                "BroadcastName",
                "Abbreviation",
                "TeamName",
                "TeamColor",
                "FirstName",
                "LastName",
                "CountryCode"
            ]].copy()

            logger.info(f"Driver info: {year} R{round_number}")
            return drivers
        except Exception as e:
            logger.error(f"Error getting driver info: {str(e)}")
            raise

    def get_track_status(
        self, year: int, round_number: int
    ) -> pd.DataFrame:
        """Get track status (flags, safety car)."""
        try:
            session = fastf1.get_session(year, round_number, "R")
            session.load()

            if session.track_status is None:
                logger.warning(
                    f"No track status data: {year} R{round_number}"
                )
                return pd.DataFrame()

            track_status = session.track_status[[
                "Time",
                "Status",
                "Message"
            ]].copy()

            logger.info(f"Track status: {year} R{round_number}")
            return track_status
        except Exception as e:
            logger.error(f"Error getting track status: {str(e)}")
            raise

    def get_race_control_messages(
        self, year: int, round_number: int
    ) -> pd.DataFrame:
        """Get race control messages (penalties, etc)."""
        try:
            session = fastf1.get_session(year, round_number, "R")
            session.load()

            if session.race_control_messages is None:
                logger.warning(
                    f"No race control messages: {year} R{round_number}"
                )
                return pd.DataFrame()

            messages = session.race_control_messages[[
                "Time",
                "Category",
                "Message",
                "Status",
                "Flag"
            ]].copy()

            logger.info(
                f"Race control messages: {year} R{round_number}"
            )
            return messages
        except Exception as e:
            logger.error(
                f"Error getting race control: {str(e)}"
            )
            raise


class OpenF1Provider(F1DataProvider):
    """Data provider using OpenF1 (real-time)."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        """Initialize OpenF1 provider."""
        self.api_key = api_key
        self.base_url = "https://api.openf1.org/v1"
        logger.info("OpenF1Provider initialized")

    def get_race_results(
        self, year: int, round_number: int
    ) -> pd.DataFrame:
        """Get race results from OpenF1 (real-time)."""
        logger.info(f"Real-time results: {year} R{round_number}")
        return pd.DataFrame()

    def get_telemetry(
        self, year: int, round_number: int, driver: str
    ) -> pd.DataFrame:
        """Get real-time telemetry."""
        logger.info(
            f"Real-time telemetry: "
            f"{driver} in {year} R{round_number}"
        )
        return pd.DataFrame()

    def get_qualifying_results(
        self, year: int, round_number: int
    ) -> pd.DataFrame:
        """Get real-time qualifying results."""
        logger.info(
            f"Real-time qualifying: {year} R{round_number}"
        )
        return pd.DataFrame()


class UnifiedF1DataProvider:
    """
    Unified provider combining FastF1 and OpenF1.

    Uses FastF1 for historical analysis and OpenF1 for real-time.
    """

    def __init__(
        self,
        use_cache: bool = True,
        cache_dir: str = "./cache",
        openf1_api_key: Optional[str] = None
    ) -> None:
        """Initialize unified provider."""
        self.fastf1_provider = FastF1Provider(cache_dir=cache_dir)
        self.openf1_provider = OpenF1Provider(
            api_key=openf1_api_key
        )
        logger.info("UnifiedF1DataProvider initialized")

    def get_race_results(
        self,
        year: int,
        round_number: int,
        use_realtime: bool = False
    ) -> pd.DataFrame:
        """Get race results."""
        provider = (
            self.openf1_provider if use_realtime
            else self.fastf1_provider
        )
        return provider.get_race_results(year, round_number)

    def get_telemetry(
        self,
        year: int,
        round_number: int,
        driver: str,
        use_realtime: bool = False
    ) -> pd.DataFrame:
        """Get telemetry data."""
        provider = (
            self.openf1_provider if use_realtime
            else self.fastf1_provider
        )
        return provider.get_telemetry(year, round_number, driver)

    def get_qualifying_results(
        self,
        year: int,
        round_number: int,
        use_realtime: bool = False
    ) -> pd.DataFrame:
        """Get qualifying results."""
        provider = (
            self.openf1_provider if use_realtime
            else self.fastf1_provider
        )
        return provider.get_qualifying_results(year, round_number)

    def get_lap_times(
        self,
        year: int,
        round_number: int,
        session_type: str = "R",
        use_realtime: bool = False
    ) -> pd.DataFrame:
        """Get lap times."""
        return self.fastf1_provider.get_lap_times(
            year, round_number, session_type
        )

    def get_pit_stops(
        self,
        year: int,
        round_number: int,
        use_realtime: bool = False
    ) -> pd.DataFrame:
        """Get pit stop data."""
        return self.fastf1_provider.get_pit_stops(
            year, round_number
        )

    def get_weather(
        self,
        year: int,
        round_number: int,
        use_realtime: bool = False
    ) -> pd.DataFrame:
        """Get weather data."""
        return self.fastf1_provider.get_weather(
            year, round_number
        )

    def get_tire_strategy(
        self,
        year: int,
        round_number: int,
        use_realtime: bool = False
    ) -> pd.DataFrame:
        """Get tire strategy."""
        return self.fastf1_provider.get_tire_strategy(
            year, round_number
        )

    def get_practice_results(
        self,
        year: int,
        round_number: int,
        session_type: str
    ) -> pd.DataFrame:
        """Get practice results (FP1/FP2/FP3)."""
        return self.fastf1_provider.get_practice_results(
            year, round_number, session_type
        )

    def get_sprint_results(
        self, year: int, round_number: int
    ) -> pd.DataFrame:
        """Get sprint race results."""
        return self.fastf1_provider.get_sprint_results(
            year, round_number
        )

    def get_driver_info(
        self, year: int, round_number: int
    ) -> pd.DataFrame:
        """Get driver information."""
        return self.fastf1_provider.get_driver_info(
            year, round_number
        )

    def get_track_status(
        self, year: int, round_number: int
    ) -> pd.DataFrame:
        """Get track status."""
        return self.fastf1_provider.get_track_status(
            year, round_number
        )

    def get_race_control_messages(
        self, year: int, round_number: int
    ) -> pd.DataFrame:
        """Get race control messages."""
        return self.fastf1_provider.get_race_control_messages(
            year, round_number
        )

    def get_season_schedule(self, year: int) -> pd.DataFrame:
        """Get complete season calendar."""
        try:
            schedule = fastf1.get_event_schedule(year)
            logger.info(f"Schedule obtained: {year}")
            return schedule
        except Exception as e:
            msg = f"Error getting schedule {year}: {str(e)}"
            logger.error(msg)
            raise
