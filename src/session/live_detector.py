"""
Live session detection for F1 Strategist AI.

Automatically detects active F1 sessions and provides session information.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

import fastf1

from src.session.global_session import RaceContext, SessionType

logger = logging.getLogger(__name__)


class LiveSessionDetector:
    """
    Detects active F1 sessions based on current time.

    Features:
    - Queries F1 calendar
    - Checks for sessions within time window (-3h buffer)
    - Provides session details
    """

    # Session type mapping from FastF1 to our enum
    SESSION_TYPE_MAP = {
        "Practice 1": SessionType.FP1,
        "Practice 2": SessionType.FP2,
        "Practice 3": SessionType.FP3,
        "Qualifying": SessionType.QUALIFYING,
        "Sprint Qualifying": SessionType.SPRINT_QUALIFYING,
        "Sprint": SessionType.SPRINT,
        "Race": SessionType.RACE,
    }

    def __init__(self, buffer_hours: int = 3):
        """
        Initialize live session detector.

        Args:
            buffer_hours: Hours before session start to consider "live"
        """
        self.buffer_hours = buffer_hours
        self.cache_timeout = timedelta(minutes=5)
        self._last_check: Optional[datetime] = None
        self._cached_result: Optional[RaceContext] = None

    def detect_live_session(
        self,
        current_time: Optional[datetime] = None
    ) -> Optional[RaceContext]:
        """
        Detect if there's a live F1 session happening now.

        Checks if current time is within buffer window of any session:
        - Session start time - buffer_hours <= now <= session end time

        Args:
            current_time: Time to check against (defaults to now)

        Returns:
            RaceContext if live session detected, None otherwise
        """
        if current_time is None:
            current_time = datetime.now()

        # Use cache if recent
        if self._last_check and self._cached_result:
            if current_time - self._last_check < self.cache_timeout:
                logger.debug("Using cached live session result")
                return self._cached_result

        logger.info(f"Checking for live sessions at {current_time}")

        try:
            # Get current year
            year = current_time.year

            # Load F1 schedule
            schedule = fastf1.get_event_schedule(year)

            # Find active session
            for _, event in schedule.iterrows():
                session_context = self._check_event_for_live_session(
                    event,
                    current_time
                )

                if session_context:
                    logger.info(
                        f"Live session detected: "
                        f"{session_context.circuit_name} - "
                        f"{session_context.session_type.value}"
                    )

                    # Cache result
                    self._last_check = current_time
                    self._cached_result = session_context

                    return session_context

            logger.info("No live sessions detected")
            self._last_check = current_time
            self._cached_result = None
            return None

        except Exception as e:
            logger.error(f"Error detecting live session: {e}")
            return None

    def _check_event_for_live_session(
        self,
        event,
        current_time: datetime
    ) -> Optional[RaceContext]:
        """
        Check if an event has an active session.

        Args:
            event: FastF1 event row
            current_time: Current timestamp

        Returns:
            RaceContext if session is active, None otherwise
        """
        # Define session columns in order of importance
        session_columns = [
            ("Session5", "Session5Date"),  # Usually Race
            ("Session4", "Session4Date"),  # Usually Qualifying
            ("Session3", "Session3Date"),  # Usually FP3 or Sprint
            ("Session2", "Session2Date"),  # Usually FP2
            ("Session1", "Session1Date"),  # Usually FP1
        ]

        for session_name_col, session_date_col in session_columns:
            if session_name_col not in event or session_date_col not in event:
                continue

            session_name = event[session_name_col]
            session_date = event[session_date_col]

            if session_name is None or session_date is None:
                continue

            # Convert to datetime if needed
            if not isinstance(session_date, datetime):
                session_date = session_date.to_pydatetime()

            # Make timezone-naive for comparison
            if session_date.tzinfo:
                session_date = session_date.replace(tzinfo=None)

            # Check if within time window
            buffer_start = session_date - timedelta(hours=self.buffer_hours)

            # Estimate session duration
            session_duration = self._estimate_session_duration(session_name)
            session_end = session_date + session_duration

            if buffer_start <= current_time <= session_end:
                # Found active session
                return self._create_race_context(
                    event,
                    session_name,
                    session_date
                )

        return None

    def _estimate_session_duration(self, session_name: str) -> timedelta:
        """
        Estimate session duration based on session type.

        Args:
            session_name: Name of session

        Returns:
            Estimated duration
        """
        session_name_lower = session_name.lower()

        if "race" in session_name_lower:
            return timedelta(hours=2, minutes=30)
        elif "qualifying" in session_name_lower:
            return timedelta(hours=1, minutes=30)
        elif "sprint" in session_name_lower:
            return timedelta(hours=1, minutes=0)
        elif "practice" in session_name_lower:
            return timedelta(hours=1, minutes=30)
        else:
            return timedelta(hours=2, minutes=0)

    def _create_race_context(
        self,
        event,
        session_name: str,
        session_date: datetime
    ) -> RaceContext:
        """
        Create RaceContext from event data.

        Args:
            event: FastF1 event row
            session_name: Session name
            session_date: Session start time

        Returns:
            RaceContext with session details
        """
        # Map session type
        session_type = self.SESSION_TYPE_MAP.get(
            session_name,
            SessionType.RACE
        )

        # Get circuit information
        circuit_name = event.get("EventName", "Unknown Circuit")
        country = event.get("Country", "Unknown")
        round_number = event.get("RoundNumber", 0)

        # Try to get circuit key (simplified)
        circuit_key = circuit_name.lower().replace(" ", "_")

        # Estimate total laps (circuit-specific, simplified)
        total_laps = self._estimate_total_laps(circuit_name, session_type)

        return RaceContext(
            year=session_date.year,
            round_number=int(round_number) if round_number else 0,
            circuit_name=circuit_name,
            circuit_key=circuit_key,
            country=country,
            session_type=session_type,
            session_date=session_date,
            total_laps=total_laps,
            current_lap=1,
            focused_driver=None,
            focused_team=None,
            track_status="Unknown"
        )

    def _estimate_total_laps(
        self,
        circuit_name: str,
        session_type: SessionType
    ) -> int:
        """
        Estimate total laps for a circuit.

        Args:
            circuit_name: Name of circuit
            session_type: Type of session

        Returns:
            Estimated lap count
        """
        # For non-race sessions, return 0
        if session_type != SessionType.RACE:
            return 0

        # Circuit-specific lap counts (simplified)
        circuit_laps = {
            "bahrain": 57,
            "saudi": 50,
            "jeddah": 50,
            "australia": 58,
            "japan": 53,
            "suzuka": 53,
            "china": 56,
            "shanghai": 56,
            "miami": 57,
            "monaco": 78,
            "spain": 66,
            "barcelona": 66,
            "canada": 70,
            "montreal": 70,
            "austria": 71,
            "spielberg": 71,
            "britain": 52,
            "silverstone": 52,
            "hungary": 70,
            "hungaroring": 70,
            "belgium": 44,
            "spa": 44,
            "netherlands": 72,
            "zandvoort": 72,
            "italy": 53,
            "monza": 53,
            "singapore": 62,
            "marina bay": 62,
            "qatar": 57,
            "lusail": 57,
            "usa": 56,
            "austin": 56,
            "cota": 56,
            "las vegas": 50,
            "vegas": 50,
            "mexico": 71,
            "brazil": 71,
            "interlagos": 71,
            "sao paulo": 71,
            "abu dhabi": 58,
            "yas marina": 58,
            "azerbaijan": 51,
            "baku": 51,
            "imola": 63,
            "emilia": 63,
        }

        # Try to find match
        circuit_lower = circuit_name.lower()
        for key, laps in circuit_laps.items():
            if key in circuit_lower:
                return laps

        # Default
        return 60

    def get_upcoming_sessions(
        self,
        days_ahead: int = 7
    ) -> List[RaceContext]:
        """
        Get upcoming F1 sessions.

        Args:
            days_ahead: Number of days to look ahead

        Returns:
            List of upcoming session contexts
        """
        current_time = datetime.now()
        end_time = current_time + timedelta(days=days_ahead)

        try:
            year = current_time.year
            schedule = fastf1.get_event_schedule(year)

            upcoming_sessions = []

            for _, event in schedule.iterrows():
                # Check all sessions in this event
                session_columns = [
                    ("Session1", "Session1Date"),
                    ("Session2", "Session2Date"),
                    ("Session3", "Session3Date"),
                    ("Session4", "Session4Date"),
                    ("Session5", "Session5Date"),
                ]

                for session_name_col, session_date_col in session_columns:
                    if (
                        session_name_col not in event
                        or session_date_col not in event
                    ):
                        continue

                    session_name = event[session_name_col]
                    session_date = event[session_date_col]

                    if session_name is None or session_date is None:
                        continue

                    # Convert to datetime
                    if not isinstance(session_date, datetime):
                        session_date = session_date.to_pydatetime()

                    if session_date.tzinfo:
                        session_date = session_date.replace(tzinfo=None)

                    # Check if within range
                    if current_time <= session_date <= end_time:
                        context = self._create_race_context(
                            event,
                            session_name,
                            session_date
                        )
                        upcoming_sessions.append(context)

            # Sort by date
            upcoming_sessions.sort(key=lambda x: x.session_date)

            return upcoming_sessions

        except Exception as e:
            logger.error(f"Error getting upcoming sessions: {e}")
            return []


# Global detector instance
_detector: Optional[LiveSessionDetector] = None


def get_live_session_detector() -> LiveSessionDetector:
    """
    Get singleton detector instance.

    Returns:
        LiveSessionDetector instance
    """
    global _detector

    if _detector is None:
        _detector = LiveSessionDetector(buffer_hours=3)

    return _detector


def check_for_live_session() -> Optional[RaceContext]:
    """
    Quick check for live session.

    Returns:
        RaceContext if live, None otherwise
    """
    detector = get_live_session_detector()
    return detector.detect_live_session()
