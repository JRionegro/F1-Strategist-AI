"""
Test script for live session detection.

Demonstrates the live F1 session detection capabilities.
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.session.live_detector import (
    LiveSessionDetector,
    check_for_live_session,
    get_live_session_detector,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_current_f1_season() -> int:
    """
    Get the current F1 season year.
    
    F1 seasons typically run from March to December.
    If we're in January or early February, the current season
    is still the previous year.
    
    Returns:
        Year of current F1 season
    """
    now = datetime.now()
    current_year = now.year
    current_month = now.month
    
    # If we're in January or February, use previous year's season
    # (new season hasn't started yet)
    if current_month <= 2:
        return current_year - 1
    else:
        return current_year


def test_current_detection():
    """Test if there's a live session right now."""
    logger.info("=== Testing Current Live Session Detection ===")
    
    context = check_for_live_session()
    
    if context:
        logger.info("🔴 LIVE SESSION DETECTED!")
        logger.info(f"  Circuit: {context.circuit_name}")
        logger.info(f"  Session: {context.session_type.value}")
        logger.info(f"  Year: {context.year}")
        logger.info(
            f"  Date: {context.session_date.strftime('%Y-%m-%d %H:%M UTC')}"
        )
        if context.total_laps:
            logger.info(f"  Total Laps: {context.total_laps}")
    else:
        logger.info("No live session detected at this time.")


def test_upcoming_sessions():
    """Test retrieval of upcoming sessions."""
    logger.info("\n=== Testing Upcoming Sessions (Next 7 Days) ===")
    
    detector = get_live_session_detector()
    upcoming = detector.get_upcoming_sessions(days_ahead=7)
    
    if not upcoming:
        logger.info("No sessions in the next 7 days.")
        return
    
    logger.info(f"Found {len(upcoming)} upcoming sessions:")
    
    for i, context in enumerate(upcoming[:5], 1):
        logger.info(f"\n{i}. {context.circuit_name}")
        logger.info(f"   Session: {context.session_type.value}")
        logger.info(
            f"   Date: {context.session_date.strftime('%a %b %d, %H:%M UTC')}"
        )
        
        # Calculate time until
        now = datetime.now()
        session_date = context.session_date
        if session_date.tzinfo:
            session_date = session_date.replace(tzinfo=None)
        
        delta = session_date - now
        if delta.days > 0:
            time_str = f"in {delta.days} days"
        elif delta.seconds > 3600:
            hours = delta.seconds // 3600
            time_str = f"in {hours} hours"
        else:
            minutes = delta.seconds // 60
            time_str = f"in {minutes} minutes"
        
        logger.info(f"   Time: {time_str}")


def test_full_calendar():
    """Display full F1 calendar for current season."""
    season_year = get_current_f1_season()
    system_year = datetime.now().year
    
    logger.info("\n=== Full F1 Calendar ===")
    logger.info(f"System date: {datetime.now().strftime('%B %d, %Y')}")
    logger.info(f"Current F1 season: {season_year}")
    
    if system_year != season_year:
        logger.info(
            f"Note: We're in {datetime.now().strftime('%B')} "
            f"{system_year}, but F1 season {season_year} is still active "
            f"(next season starts in March {system_year})"
        )
    
    try:
        import fastf1
        
        # Get current F1 season schedule
        schedule = fastf1.get_event_schedule(season_year)
        
        logger.info(
            f"\nTotal races in {season_year}: "
            f"{len(schedule)}"
        )
        logger.info("=" * 80)
        
        for race_num, (idx, event) in enumerate(schedule.iterrows(), start=1):
            event_date = event['EventDate']
            event_name = event['EventName']
            country = event.get('Country', 'N/A')
            location = event.get('Location', 'N/A')
            
            # Count sessions
            session_count = 0
            sessions = []
            for i in range(1, 6):
                session_key = f'Session{i}'
                if session_key in event and pd.notna(event[session_key]):
                    session_count += 1
                    session_name = event.get(
                        f'Session{i}Name',
                        f'Session {i}'
                    )
                    session_date = event[session_key]
                    # Handle both datetime and string formats
                    if hasattr(session_date, 'strftime'):
                        date_str = session_date.strftime('%b %d %H:%M')
                    else:
                        date_str = str(session_date)
                    sessions.append(f"{session_name}: {date_str}")
            logger.info(
                f"\n{race_num:2d}. {event_name} "
                f"({country} - {location})"
            )
            logger.info(
                f"    Weekend: {event_date.strftime('%B %d, %Y')}"
            )
            logger.info(
                f"    Sessions ({session_count}):"
            )
            for session in sessions:
                logger.info(f"      - {session}")
        
        logger.info("\n" + "=" * 80)
        logger.info(f"End of {season_year} F1 Season Calendar")
        
    except Exception as e:
        logger.error(f"Error loading calendar: {e}", exc_info=True)


def test_simulated_detection():
    """Test detection with simulated timestamps using real calendar."""
    logger.info("\n=== Testing Simulated Detection ===")
    
    season_year = get_current_f1_season()
    logger.info(f"Testing with {season_year} F1 season")
    
    detector = LiveSessionDetector()
    
    # Get the actual season schedule to find real dates
    try:
        import fastf1
        schedule = fastf1.get_event_schedule(season_year)
        
        # Find last race of the season
        last_event = schedule.iloc[-1]
        
        logger.info(f"\nTesting with last race of {season_year}:")
        logger.info(f"Event: {last_event['EventName']}")
        
        # Test the Race session
        simulated_times = []
        
        # FastF1 uses EventDate + Session times
        # Session5Name is usually "Race"
        event_date = last_event['EventDate']
        session_name = last_event.get('Session5Name', 'Race')
        
        # For testing, use the event_date at a typical race time (2 PM UTC)
        race_datetime = pd.to_datetime(event_date) + pd.Timedelta(hours=14)
        
        # Add 1 hour to be in the middle of the race
        test_time = race_datetime + pd.Timedelta(hours=1)
        simulated_times.append((test_time, session_name))
        
        logger.info(
            f"  Testing {session_name}: "
            f"{race_datetime.strftime('%Y-%m-%d %H:%M UTC')}"
        )
    
    except Exception as e:
        logger.warning(f"Could not load calendar: {e}. Using estimated dates.")
        simulated_times = [
            (datetime(season_year, 12, 7, 13, 0), "Race (estimated)"),
            (datetime(season_year, 12, 6, 14, 0), "Qualifying (estimated)"),
            (datetime(season_year, 12, 6, 10, 0), "FP3 (estimated)"),
        ]
    
    for sim_time, session_label in simulated_times:
        if isinstance(sim_time, datetime):
            time_str = sim_time.strftime('%Y-%m-%d %H:%M UTC')
        else:
            # pandas Timestamp
            time_str = sim_time.strftime('%Y-%m-%d %H:%M UTC')
            sim_time = sim_time.to_pydatetime().replace(tzinfo=None)
        
        logger.info(f"\nSimulating: {time_str} ({session_label})")
        
        context = detector.detect_live_session(current_time=sim_time)
        
        if context:
            logger.info(
                f"  ✅ Would detect: {context.circuit_name} - "
                f"{context.session_type.value}"
            )
        else:
            logger.info("  ❌ No session detected")


def main():
    """Run all tests."""
    try:
        test_current_detection()
        test_upcoming_sessions()
        test_full_calendar()
        test_simulated_detection()
        
    except Exception as e:
        logger.error(f"Error during testing: {e}", exc_info=True)


if __name__ == "__main__":
    main()
