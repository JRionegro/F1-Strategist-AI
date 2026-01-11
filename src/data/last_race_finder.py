"""
Last Race Finder - OpenF1 Integration.

Automatically finds the most recent completed F1 race session
using the OpenF1 API.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, TYPE_CHECKING

from src.utils.logging_config import get_logger, LogCategory

if TYPE_CHECKING:
    from src.data.openf1_data_provider import OpenF1DataProvider
    from src.session.global_session import RaceContext

# Use categorized logger for data operations
logger = get_logger(LogCategory.DATA)


def get_last_completed_race(
    provider: Optional["OpenF1DataProvider"] = None
) -> Optional["RaceContext"]:
    """
    Find the most recent completed race from OpenF1.

    Args:
        provider: OpenF1DataProvider instance. Creates one if not provided.

    Returns:
        RaceContext with the last completed race, or None if not found.
    """
    # Import here to avoid circular imports
    from src.data.openf1_data_provider import OpenF1DataProvider
    from src.session.global_session import RaceContext, SessionType

    if provider is None:
        provider = OpenF1DataProvider(verify_ssl=False)

    try:
        # Get current date in UTC
        now = datetime.now(timezone.utc)
        current_year = now.year

        logger.info(f"Searching for last completed race (current date: {now})")

        # Try current year first, then previous year if needed
        for year in [current_year, current_year - 1]:
            race_context = _find_last_race_in_year(provider, year, now)
            if race_context:
                return race_context

        logger.warning("No completed races found in current or previous year")
        return None

    except Exception as e:
        logger.error(f"Error finding last completed race: {e}")
        return None


def _find_last_race_in_year(
    provider: "OpenF1DataProvider",
    year: int,
    now: datetime
) -> Optional["RaceContext"]:
    """
    Find the last completed race in a specific year.

    Args:
        provider: OpenF1DataProvider instance.
        year: Year to search.
        now: Current datetime for comparison.

    Returns:
        RaceContext if found, None otherwise.
    """
    from src.session.global_session import RaceContext, SessionType

    try:
        # Get all sessions for the year
        sessions_params = {"year": year}
        all_sessions = provider._request("sessions", sessions_params)

        if not all_sessions:
            logger.info(f"No sessions found for year {year}")
            return None

        # Filter only Race sessions that have ended
        race_sessions = []
        for session in all_sessions:
            session_name = session.get("session_name", "")
            date_end_str = session.get("date_end")

            # Only consider Race sessions (not Practice, Qualifying, Sprint)
            if session_name != "Race":
                continue

            # Parse end date
            if date_end_str:
                try:
                    # OpenF1 returns ISO format dates
                    date_end = datetime.fromisoformat(
                        date_end_str.replace("Z", "+00:00")
                    )

                    # Only include races that have ended
                    if date_end < now:
                        race_sessions.append({
                            "session": session,
                            "date_end": date_end
                        })
                except ValueError as e:
                    logger.warning(
                        f"Could not parse date {date_end_str}: {e}"
                    )
                    continue

        if not race_sessions:
            logger.info(f"No completed races found in {year}")
            return None

        # Sort by end date (most recent first)
        race_sessions.sort(key=lambda x: x["date_end"], reverse=True)

        # Get the most recent race
        last_race = race_sessions[0]["session"]

        logger.info(
            f"Found last completed race: "
            f"{last_race.get('location')} ({last_race.get('country_name')})"
        )

        # Build RaceContext from OpenF1 data
        return _build_race_context(last_race, provider)

    except Exception as e:
        logger.error(f"Error finding races in {year}: {e}")
        return None


def _build_race_context(
    session_data: Dict[str, Any],
    provider: "OpenF1DataProvider"
) -> "RaceContext":
    """
    Build a RaceContext from OpenF1 session data.

    Args:
        session_data: Session data from OpenF1 API.
        provider: OpenF1DataProvider for additional queries.

    Returns:
        RaceContext object.
    """
    from src.session.global_session import RaceContext, SessionType

    # Extract session info
    meeting_key = session_data.get("meeting_key")
    session_key = session_data.get("session_key")
    year = session_data.get("year", datetime.now().year)
    country = session_data.get("country_name", "Unknown")
    location = session_data.get("location", "Unknown")

    # Parse session date
    date_start_str = session_data.get("date_start")
    if date_start_str:
        try:
            session_date = datetime.fromisoformat(
                date_start_str.replace("Z", "+00:00")
            )
            # Remove timezone info for compatibility
            session_date = session_date.replace(tzinfo=None)
        except ValueError:
            session_date = datetime.now()
    else:
        session_date = datetime.now()

    # Get total laps from laps endpoint
    total_laps = 57  # Default
    if session_key:
        total_laps = _get_total_laps(provider, session_key)

    # Determine round number by counting races in the year
    round_number = 1  # Default
    if meeting_key:
        round_number = _get_round_number(provider, year, meeting_key)

    # Build circuit key from location (lowercase, underscores)
    circuit_key = location.lower().replace(" ", "_").replace("-", "_")

    return RaceContext(
        year=year,
        round_number=round_number,
        circuit_name=f"{location} Circuit",
        circuit_key=circuit_key,
        country=country,
        session_type=SessionType.RACE,
        session_date=session_date,
        total_laps=total_laps,
        current_lap=1,
        meeting_key=meeting_key,
        session_key=session_key
    )


def _get_total_laps(
    provider: "OpenF1DataProvider",
    session_key: int
) -> int:
    """
    Get total laps for a session from OpenF1.

    Args:
        provider: OpenF1DataProvider instance.
        session_key: Session key from OpenF1.

    Returns:
        Total number of laps, defaults to 57 if not found.
    """
    try:
        laps_params = {"session_key": session_key}
        laps = provider._request("laps", laps_params)

        if laps:
            # Get max lap number
            max_lap = max(lap.get("lap_number", 0) for lap in laps)
            if max_lap > 0:
                return max_lap

        return 57  # Default F1 race length

    except Exception as e:
        logger.warning(f"Could not get total laps: {e}")
        return 57


def _get_round_number(
    provider: "OpenF1DataProvider",
    year: int,
    meeting_key: int
) -> int:
    """
    Determine the round number for a meeting.

    Args:
        provider: OpenF1DataProvider instance.
        year: Season year.
        meeting_key: Meeting key from OpenF1.

    Returns:
        Round number (1-based).
    """
    try:
        # Get all meetings for the year
        sessions_params = {"year": year}
        all_sessions = provider._request("sessions", sessions_params)

        if not all_sessions:
            return 1

        # Get unique meetings sorted by date
        meetings = {}
        for session in all_sessions:
            mk = session.get("meeting_key")
            if mk and mk not in meetings:
                meetings[mk] = session.get("date_start", "")

        # Sort by date
        sorted_meetings = sorted(meetings.items(), key=lambda x: x[1])

        # Find position of our meeting
        for idx, (mk, _) in enumerate(sorted_meetings, 1):
            if mk == meeting_key:
                return idx

        return 1

    except Exception as e:
        logger.warning(f"Could not determine round number: {e}")
        return 1


def get_last_completed_meeting_key(
    provider: Optional["OpenF1DataProvider"] = None
) -> Optional[int]:
    """
    Get just the meeting_key of the last completed race.

    Useful for dropdown default selection.

    Args:
        provider: OpenF1DataProvider instance.

    Returns:
        Meeting key integer, or None if not found.
    """
    race_context = get_last_completed_race(provider)
    if race_context and hasattr(race_context, 'meeting_key'):
        return race_context.meeting_key
    return None
