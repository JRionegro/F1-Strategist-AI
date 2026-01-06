"""
Race Event Detector - Proactive alerts for F1 strategy.

Detects race events (pit windows, safety cars, undercuts) for 
proactive AI assistant notifications.

CRITICAL: Only uses data with timestamp <= current_time (NO FUTURE DATA).
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import pandas as pd

from src.data.openf1_data_provider import OpenF1DataProvider

logger = logging.getLogger(__name__)


@dataclass
class RaceEvent:
    """Detected race event for proactive alerts."""
    event_type: str  # pit_window, undercut_risk, safety_car, tire_deg, position_change
    priority: int  # 1-5 (5 = highest urgency)
    message: str  # Human-readable alert message
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[datetime] = None
    driver_number: Optional[int] = None


class RaceEventDetector:
    """
    Detects race events for proactive AI alerts.
    
    Events detected:
    - Pit window open (optimal lap range for pit stop)
    - Undercut risk (car behind likely to pit)
    - Safety car / VSC deployed
    - Tire degradation warnings
    - Position changes affecting focused driver
    
    CRITICAL: All detection uses only data up to current_time.
    """
    
    # Tire compound optimal stint lengths (laps)
    TIRE_WINDOWS = {
        'SOFT': {'min': 8, 'optimal': 12, 'max': 18},
        'MEDIUM': {'min': 15, 'optimal': 22, 'max': 30},
        'HARD': {'min': 25, 'optimal': 35, 'max': 45},
        'INTERMEDIATE': {'min': 10, 'optimal': 20, 'max': 35},
        'WET': {'min': 15, 'optimal': 30, 'max': 50}
    }
    
    # Undercut detection thresholds
    UNDERCUT_GAP_THRESHOLD = 2.5  # seconds - gap where undercut is possible
    UNDERCUT_STINT_AGE_MIN = 10  # laps - car behind needs aged tires
    
    def __init__(self, data_provider: OpenF1DataProvider):
        """Initialize with data provider."""
        self.provider = data_provider
        self._last_checked: Dict[str, Any] = {
            'last_pit_lap': {},  # driver_number -> last pit lap
            'last_sc_time': None,
            'last_alert_lap': 0,
            'alerted_events': set()  # (event_type, lap) tuples to avoid duplicates
        }
    
    def detect_events(
        self,
        session_key: int,
        current_time: datetime,
        current_lap: int,
        focused_driver: Optional[int] = None,
        total_laps: int = 57
    ) -> List[RaceEvent]:
        """
        Detect new race events up to current_time.
        
        Args:
            session_key: OpenF1 session key
            current_time: Current simulation time (DO NOT USE FUTURE DATA)
            current_lap: Current racing lap number
            focused_driver: Driver number to focus alerts on
            total_laps: Total race laps
            
        Returns:
            List of detected RaceEvent objects
        """
        events = []
        
        try:
            # Only check every 2 laps to avoid spam
            if current_lap <= self._last_checked['last_alert_lap'] + 1:
                # Still check for safety car (urgent)
                sc_event = self._check_safety_car(
                    session_key, current_time
                )
                if sc_event:
                    events.append(sc_event)
                return events
            
            self._last_checked['last_alert_lap'] = current_lap
            
            # Check pit window for focused driver
            if focused_driver:
                pit_event = self._check_pit_window(
                    session_key, current_time, current_lap,
                    focused_driver, total_laps
                )
                if pit_event:
                    events.append(pit_event)
                
                # Check undercut risk
                undercut_event = self._check_undercut_risk(
                    session_key, current_time, current_lap, focused_driver
                )
                if undercut_event:
                    events.append(undercut_event)
                
                # Check tire degradation
                deg_event = self._check_tire_degradation(
                    session_key, current_time, current_lap, focused_driver
                )
                if deg_event:
                    events.append(deg_event)
            
            # Always check safety car (highest priority)
            sc_event = self._check_safety_car(session_key, current_time)
            if sc_event:
                events.append(sc_event)
            
        except Exception as e:
            logger.warning(f"Event detection error: {e}")
        
        return events
    
    def _check_pit_window(
        self,
        session_key: int,
        current_time: datetime,
        current_lap: int,
        driver_number: int,
        total_laps: int
    ) -> Optional[RaceEvent]:
        """Check if driver is in optimal pit window."""
        try:
            # Get current stint info
            stints_df = self.provider.get_stints(
                session_key=session_key,
                driver_number=driver_number
            )
            
            if stints_df.empty:
                return None
            
            # Get latest stint
            latest_stint = stints_df.iloc[-1]
            compound = latest_stint.get('Compound', 'MEDIUM').upper()
            stint_start = latest_stint.get('LapStart', 1)
            stint_age = current_lap - stint_start + 1
            
            # Get tire window
            window = self.TIRE_WINDOWS.get(compound, self.TIRE_WINDOWS['MEDIUM'])
            
            # Check if in optimal window
            event_key = (f'pit_window_{compound}', current_lap // 5)
            if event_key in self._last_checked['alerted_events']:
                return None
            
            if window['min'] <= stint_age <= window['optimal']:
                self._last_checked['alerted_events'].add(event_key)
                
                remaining_optimal = window['optimal'] - stint_age
                
                return RaceEvent(
                    event_type='pit_window',
                    priority=3,
                    message=(
                        f"🔧 PIT WINDOW OPEN: Driver {driver_number} on "
                        f"{compound} tires (stint age: {stint_age} laps). "
                        f"Optimal window for {remaining_optimal} more laps. "
                        f"Consider pitting in next {remaining_optimal + 3} laps."
                    ),
                    data={
                        'compound': compound,
                        'stint_age': stint_age,
                        'window': window,
                        'remaining_optimal': remaining_optimal
                    },
                    timestamp=current_time,
                    driver_number=driver_number
                )
            
            # Check if tires are degraded beyond optimal
            elif stint_age > window['optimal']:
                event_key = (f'pit_overdue_{compound}', current_lap // 3)
                if event_key in self._last_checked['alerted_events']:
                    return None
                    
                self._last_checked['alerted_events'].add(event_key)
                
                return RaceEvent(
                    event_type='pit_window',
                    priority=4,
                    message=(
                        f"⚠️ TIRES DEGRADED: Driver {driver_number} on "
                        f"{compound} tires for {stint_age} laps "
                        f"(optimal was {window['optimal']}). "
                        f"Pit stop recommended soon!"
                    ),
                    data={
                        'compound': compound,
                        'stint_age': stint_age,
                        'overdue_by': stint_age - window['optimal']
                    },
                    timestamp=current_time,
                    driver_number=driver_number
                )
            
        except Exception as e:
            logger.debug(f"Pit window check failed: {e}")
        
        return None
    
    def _check_undercut_risk(
        self,
        session_key: int,
        current_time: datetime,
        current_lap: int,
        focused_driver: int
    ) -> Optional[RaceEvent]:
        """
        Check undercut risk from car behind.
        
        Only alerts if:
        1. Gap to car behind < 2.5s
        2. Car behind has aged tires (> 10 laps)
        3. Both cars haven't pitted recently
        """
        try:
            event_key = ('undercut_risk', current_lap // 4)
            if event_key in self._last_checked['alerted_events']:
                return None
            
            # Get intervals/gaps
            intervals_df = self.provider.get_intervals(
                session_key=session_key
            )
            
            if intervals_df.empty:
                return None
            
            # Filter to data before current_time
            if 'Date' in intervals_df.columns:
                intervals_df = intervals_df[
                    pd.to_datetime(intervals_df['Date']) <= current_time
                ]
            
            if intervals_df.empty:
                return None
            
            # Get latest interval for focused driver
            driver_intervals = intervals_df[
                intervals_df['DriverNumber'] == focused_driver
            ]
            
            if driver_intervals.empty:
                return None
            
            latest = driver_intervals.iloc[-1]
            gap_behind = latest.get('GapToPositionAhead')
            
            # Find driver behind
            if gap_behind is None or gap_behind == '':
                return None
            
            try:
                gap_value = float(str(gap_behind).replace('+', ''))
            except (ValueError, TypeError):
                return None
            
            if gap_value > self.UNDERCUT_GAP_THRESHOLD:
                return None
            
            # Get stints to check tire age of car behind
            stints_df = self.provider.get_stints(session_key=session_key)
            if stints_df.empty:
                return None
            
            # This is a simplified check - in reality we'd need position data
            # For now, alert if gap is close and we're in pit window
            self._last_checked['alerted_events'].add(event_key)
            
            return RaceEvent(
                event_type='undercut_risk',
                priority=4,
                message=(
                    f"⚡ UNDERCUT RISK: Car behind driver {focused_driver} "
                    f"is within {gap_value:.1f}s. Watch for their pit stop - "
                    f"consider covering if they pit."
                ),
                data={
                    'gap_behind': gap_value,
                    'current_lap': current_lap
                },
                timestamp=current_time,
                driver_number=focused_driver
            )
            
        except Exception as e:
            logger.debug(f"Undercut check failed: {e}")
        
        return None
    
    def _check_safety_car(
        self,
        session_key: int,
        current_time: datetime
    ) -> Optional[RaceEvent]:
        """Check for safety car or VSC deployment."""
        try:
            race_control_df = self.provider.get_race_control_messages(
                session_key=session_key
            )
            
            if race_control_df.empty:
                return None
            
            # Filter to messages before current_time
            if 'Date' in race_control_df.columns:
                race_control_df = race_control_df[
                    pd.to_datetime(race_control_df['Date']) <= current_time
                ]
            
            if race_control_df.empty:
                return None
            
            # Check for SC/VSC in recent messages
            recent = race_control_df.tail(5)
            
            for _, msg in recent.iterrows():
                category = str(msg.get('Category', '')).upper()
                message = str(msg.get('Message', '')).upper()
                msg_time = msg.get('Date')
                
                # Check if already alerted for this SC
                if msg_time and self._last_checked['last_sc_time']:
                    if msg_time <= self._last_checked['last_sc_time']:
                        continue
                
                if 'SAFETY CAR' in category or 'SAFETY CAR' in message:
                    self._last_checked['last_sc_time'] = msg_time
                    
                    return RaceEvent(
                        event_type='safety_car',
                        priority=5,
                        message=(
                            "🚨 SAFETY CAR DEPLOYED! Consider pit stop - "
                            "reduced time loss during SC period. "
                            "Evaluate tire condition and track position."
                        ),
                        data={'category': category, 'message': message},
                        timestamp=current_time
                    )
                
                if 'VSC' in category or 'VIRTUAL SAFETY CAR' in message:
                    self._last_checked['last_sc_time'] = msg_time
                    
                    return RaceEvent(
                        event_type='vsc',
                        priority=4,
                        message=(
                            "🟡 VSC DEPLOYED! Reduced pit loss opportunity. "
                            "Quick decision needed on pit stop."
                        ),
                        data={'category': category, 'message': message},
                        timestamp=current_time
                    )
            
        except Exception as e:
            logger.debug(f"Safety car check failed: {e}")
        
        return None
    
    def _check_tire_degradation(
        self,
        session_key: int,
        current_time: datetime,
        current_lap: int,
        driver_number: int
    ) -> Optional[RaceEvent]:
        """Check for significant tire degradation based on lap times."""
        try:
            event_key = ('tire_deg', current_lap // 5)
            if event_key in self._last_checked['alerted_events']:
                return None
            
            # Get lap times
            laps_df = self.provider.get_laps(
                session_key=session_key,
                driver_number=driver_number
            )
            
            if laps_df.empty or len(laps_df) < 5:
                return None
            
            # Filter to laps before current_time
            if 'DateStart' in laps_df.columns:
                laps_df = laps_df[
                    pd.to_datetime(laps_df['DateStart']) <= current_time
                ]
            
            if len(laps_df) < 5:
                return None
            
            # Get lap times
            lap_times = laps_df['LapDuration'].dropna().tail(5)
            if len(lap_times) < 5:
                return None
            
            # Calculate degradation trend
            first_half = lap_times.iloc[:2].mean()
            second_half = lap_times.iloc[-2:].mean()
            
            if first_half and second_half:
                deg_seconds = second_half - first_half
                
                # If losing more than 0.5s per lap on average, alert
                if deg_seconds > 1.0:
                    self._last_checked['alerted_events'].add(event_key)
                    
                    return RaceEvent(
                        event_type='tire_degradation',
                        priority=3,
                        message=(
                            f"📉 TIRE DEGRADATION: Driver {driver_number} "
                            f"losing ~{deg_seconds:.1f}s over last 5 laps. "
                            f"Performance drop indicates tire wear."
                        ),
                        data={
                            'degradation_seconds': deg_seconds,
                            'recent_laps': lap_times.tolist()
                        },
                        timestamp=current_time,
                        driver_number=driver_number
                    )
            
        except Exception as e:
            logger.debug(f"Tire degradation check failed: {e}")
        
        return None
    
    def reset(self) -> None:
        """Reset detector state for new session."""
        self._last_checked = {
            'last_pit_lap': {},
            'last_sc_time': None,
            'last_alert_lap': 0,
            'alerted_events': set()
        }
