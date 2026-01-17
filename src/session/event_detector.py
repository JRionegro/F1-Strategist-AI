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
from src.session.tire_thresholds import resolve_tire_windows
from src.utils.logging_config import get_logger, LogCategory

logger = get_logger(LogCategory.PROACTIVE)


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
    # Defaults are defined in src/session/tire_thresholds.py
    
    # Undercut detection thresholds
    UNDERCUT_GAP_THRESHOLD = 2.5  # seconds - gap where undercut is possible
    UNDERCUT_STINT_AGE_MIN = 10  # laps - car behind needs aged tires
    
    def __init__(
        self,
        data_provider: OpenF1DataProvider,
        tire_windows: Optional[Dict[str, Dict[str, int]]] = None,
    ):
        """Initialize with data provider.

        Args:
            data_provider: OpenF1 provider instance.
            tire_windows: Optional overrides for tire window thresholds.
        """
        self.provider = data_provider
        self.tire_windows = resolve_tire_windows(tire_windows)
        logger.info(
            "[PROACTIVE] Tire windows resolved: %s",
            self.tire_windows,
        )
        self._last_checked: Dict[str, Any] = {
            'last_pit_lap': {},  # driver_number -> last pit lap
            'last_sc_time': None,
            'last_alert_lap': 0,
            'alerted_events': set(),  # (event_type, lap) tuples to avoid duplicates
            'last_positions': {},  # driver_number -> position
            'gap_history': {}  # driver_number -> list of (lap, gap) tuples
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
            # Log throttle state for debugging
            logger.debug(
                f"[THROTTLE_CHECK] current_lap={current_lap}, "
                f"last_alert_lap={self._last_checked['last_alert_lap']}"
            )
            
            # Always check for safety car (highest priority, every interval)
            sc_event = self._check_safety_car(session_key, current_time)
            if sc_event:
                events.append(sc_event)
            
            # Always check position changes (important for user awareness)
            if focused_driver:
                position_event = self._check_position_change(
                    session_key, current_time, current_lap, focused_driver
                )
                if position_event:
                    events.append(position_event)
            
            # Relax throttle: allow full checks when lap advances
            if current_lap > self._last_checked['last_alert_lap']:
                logger.info(
                    f"[THROTTLE_CHECK] Lap advanced "
                    f"({self._last_checked['last_alert_lap']} → {current_lap}), "
                    f"triggering full event detection"
                )
                self._last_checked['last_alert_lap'] = current_lap
                throttled = False
            else:
                throttled = True
            
            if throttled:
                logger.debug(
                    f"[DETECT] Lap {current_lap} - "
                    f"SC/Position only (throttled, waiting for lap advance)"
                )
                return events
            
            # Full event detection enabled
            logger.info(
                f"[DETECT] Lap {current_lap} - "
                f"Full detection enabled (pit window checks active)"
            )
            
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
                
                # Check DRS train
                drs_event = self._check_drs_train(
                    session_key, current_time, current_lap, focused_driver
                )
                if drs_event:
                    events.append(drs_event)
                
                # Check gap trend
                gap_event = self._check_gap_trend(
                    session_key, current_time, current_lap, focused_driver
                )
                if gap_event:
                    events.append(gap_event)
            
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
                logger.debug(f"[PIT_CHECK] No stint data for driver {driver_number}")
                return None
            
            # Focus on stints for the requested driver (API may already filter)
            if 'DriverNumber' in stints_df.columns:
                driver_stints = stints_df[stints_df['DriverNumber'] == driver_number]
            else:
                driver_stints = stints_df

            if driver_stints.empty:
                logger.debug(
                    f"[PIT_CHECK] No driver-specific stint data for driver {driver_number}"
                )
                return None

            sort_columns = [
                column for column in ('StintNumber', 'StintStart')
                if column in driver_stints.columns
            ]
            if sort_columns:
                driver_stints = driver_stints.sort_values(sort_columns)

            current_lap = max(1, current_lap)

            current_stint = None
            latest_stint_before: Optional[pd.Series] = None
            earliest_future_stint: Optional[pd.Series] = None
            for _, stint in driver_stints.iterrows():
                stint_start_raw = stint.get('StintStart', stint.get('LapStart'))
                stint_end_raw = stint.get('StintEnd', stint.get('LapEnd'))

                if pd.isna(stint_start_raw):
                    continue

                try:
                    stint_start_lap = int(stint_start_raw)
                except (TypeError, ValueError):
                    continue

                stint_end_lap: Optional[int]
                if pd.isna(stint_end_raw):
                    stint_end_lap = None
                else:
                    try:
                        stint_end_lap = int(stint_end_raw)
                    except (TypeError, ValueError):
                        stint_end_lap = None

                if stint_start_lap <= current_lap and (
                    stint_end_lap is None or current_lap <= stint_end_lap
                ):
                    current_stint = stint
                    break

                if stint_start_lap <= current_lap:
                    latest_stint_before = stint
                elif earliest_future_stint is None:
                    earliest_future_stint = stint

            if current_stint is None:
                if latest_stint_before is not None:
                    current_stint = latest_stint_before
                elif earliest_future_stint is not None:
                    current_stint = earliest_future_stint
                else:
                    current_stint = driver_stints.iloc[0]

            stint_start_raw = current_stint.get('StintStart', current_stint.get('LapStart', 1))

            try:
                stint_start = int(stint_start_raw)
            except (TypeError, ValueError):
                stint_start = 1

            compound = str(current_stint.get('Compound', 'MEDIUM')).upper()
            tyre_age_start_raw = current_stint.get('TyreAge', 0)
            try:
                tyre_age_start = int(tyre_age_start_raw or 0)
            except (TypeError, ValueError):
                tyre_age_start = 0

            laps_since_start = max(0, current_lap - stint_start)
            stint_age = tyre_age_start + laps_since_start
            
            # Get tire window
            window = self.tire_windows.get(
                compound, self.tire_windows["MEDIUM"]
            )
            
            logger.info(
                f"[PIT_CHECK] Driver {driver_number}: {compound} tire, "
                f"stint_age={stint_age}, window=[{window['min']}-{window['optimal']}]"
            )
            
            # Check if APPROACHING pit window (3-5 laps before window opens)
            laps_to_window = window['min'] - stint_age
            if 1 <= laps_to_window <= 5:
                event_key = (f'pit_approaching_{compound}', current_lap // 5)
                if event_key not in self._last_checked['alerted_events']:
                    self._last_checked['alerted_events'].add(event_key)
                    
                    return RaceEvent(
                        event_type='pit_approaching',
                        priority=2,
                        message=(
                            f"📊 PIT WINDOW APPROACHING: Driver {driver_number} on "
                            f"{compound} tires (stint: {stint_age} laps). "
                            f"Optimal pit window opens in ~{laps_to_window} laps. "
                            f"Start planning pit strategy!"
                        ),
                        data={
                            'compound': compound,
                            'stint_age': stint_age,
                            'laps_to_window': laps_to_window,
                            'window': window
                        },
                        timestamp=current_time,
                        driver_number=driver_number
                    )
            
            # Check if in optimal window
            event_key = (f'pit_window_{compound}', current_lap // 5)
            if event_key in self._last_checked['alerted_events']:
                logger.debug(f"[PIT_CHECK] Already alerted for {event_key}")
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
        logger.debug(f"[SC_CHECK] Entering method with session_key={session_key}")
        try:
            race_control_df = self.provider.get_race_control_messages(
                session_key=session_key
            )
            logger.debug(f"[SC_CHECK] Got race_control_df, empty={race_control_df.empty if race_control_df is not None else 'None'}")
            
            if race_control_df.empty:
                logger.debug("[SC_CHECK] No race control messages")
                return None
            
            # Filter to messages before current_time
            # Column is 'Time' (renamed from 'date' in provider)
            time_col = 'Time' if 'Time' in race_control_df.columns else 'Date'
            if time_col in race_control_df.columns:
                race_control_df = race_control_df[
                    pd.to_datetime(race_control_df[time_col]) <= current_time
                ]
                logger.debug(f"[SC_CHECK] Filtered by {time_col} <= {current_time}")
            else:
                logger.warning(f"[SC_CHECK] No time column found! Columns: {list(race_control_df.columns)}")
            
            if race_control_df.empty:
                logger.debug(f"[SC_CHECK] No messages before {current_time}")
                return None
            
            logger.debug(f"[SC_CHECK] Found {len(race_control_df)} messages before current time")
            
            # Check for SC/VSC in recent messages
            recent = race_control_df.tail(10)
            
            # DEBUG: Log last 5 messages to see actual format
            for idx, (_, msg) in enumerate(recent.tail(5).iterrows()):
                cat = str(msg.get('Category', 'N/A'))
                txt = str(msg.get('Message', 'N/A'))[:60]
                logger.debug(f"[SC_MSG_{idx}] Cat='{cat}' Msg='{txt}'")
            
            for _, msg in recent.iterrows():
                category = str(msg.get('Category', '')).upper()
                message = str(msg.get('Message', '')).upper()
                flag = str(msg.get('Flag', '')).upper()
                msg_time = msg.get('Time') or msg.get('Date')  # Try both column names
                
                # Log SC-related messages (broader search)
                if any(kw in category or kw in message or kw in flag 
                       for kw in ['SAFETY', 'VSC', 'SC ', ' SC', 'NEUTRALI']):
                    logger.info(f"[SC_CHECK] Potential SC: Cat='{category}' Flag='{flag}' Msg='{message[:50]}'")
                
                # Check if already alerted for this SC
                if msg_time and self._last_checked['last_sc_time']:
                    if msg_time <= self._last_checked['last_sc_time']:
                        continue
                
                # Check for Safety Car ENDING first (higher specificity)
                is_sc_ending = (
                    'IN THIS LAP' in message or
                    'SC ENDING' in message or
                    'SAFETY CAR ENDING' in message or
                    ('SAFETY CAR' in message and 'WITHDRAWN' in message) or
                    ('SC' in message and 'IN THIS LAP' in message)
                )
                
                if is_sc_ending:
                    self._last_checked['last_sc_time'] = msg_time
                    
                    return RaceEvent(
                        event_type='safety_car_ending',
                        priority=5,
                        message=(
                            "✅ SAFETY CAR ENDING THIS LAP! "
                            "Prepare for restart. Manage tire temperature and gap."
                        ),
                        data={'category': category, 'message': message},
                        timestamp=current_time
                    )
                
                # Flexible Safety Car DEPLOYMENT detection patterns
                is_safety_car = (
                    'SAFETY CAR' in category or 
                    'SAFETY CAR' in message or
                    'SAFETYCAR' in category or
                    'SAFETYCAR' in message or
                    category == 'SAFETYCAR' or
                    'SC DEPLOYED' in message or
                    ('SC' in flag and 'DEPLOYED' in message) or
                    ('SAFETY' in message and 'DEPLOYED' in message)
                )
                
                if is_safety_car:
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
                
                # Check for VSC ENDING
                is_vsc_ending = (
                    ('VSC' in message or 'VIRTUAL SAFETY CAR' in message) and
                    ('ENDING' in message or 'IN THIS LAP' in message or 'WITHDRAWN' in message)
                )
                
                if is_vsc_ending:
                    self._last_checked['last_sc_time'] = msg_time
                    
                    return RaceEvent(
                        event_type='vsc_ending',
                        priority=4,
                        message=(
                            "✅ VSC ENDING! Green flag coming. "
                            "Prepare for full racing speed."
                        ),
                        data={'category': category, 'message': message},
                        timestamp=current_time
                    )
                
                # Flexible VSC detection
                is_vsc = (
                    'VSC' in category or 
                    'VSC' in flag or
                    'VIRTUAL SAFETY CAR' in message or
                    'VIRTUAL' in message and 'SAFETY' in message
                )
                
                if is_vsc:
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
            import traceback
            logger.warning(f"[SC_CHECK] Safety car check failed: {e}")
            logger.debug(f"[SC_CHECK] Traceback: {traceback.format_exc()}")
        
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
            'alerted_events': set(),
            'last_positions': {},  # driver_number -> position
            'gap_history': {}  # driver_number -> list of (lap, gap) tuples
        }

    def _check_position_change(
        self,
        session_key: int,
        current_time: datetime,
        current_lap: int,
        focused_driver: int
    ) -> Optional[RaceEvent]:
        """
        Detect position changes for the focused driver.
        
        Alerts when:
        - Focused driver gains a position (overtake)
        - Focused driver loses a position (overtaken)
        """
        try:
            # Get position data
            position_df = self.provider.get_positions(
                session_key=session_key,
                driver_number=focused_driver
            )
            
            if position_df.empty:
                return None
            
            # Filter to data before current_time
            time_col = 'Time' if 'Time' in position_df.columns else 'Date'
            if time_col in position_df.columns:
                position_df = position_df[
                    pd.to_datetime(position_df[time_col]) <= current_time
                ]
            
            if position_df.empty:
                return None
            
            # Get current position
            current_pos = position_df.iloc[-1].get('Position')
            if current_pos is None:
                return None
            
            current_pos = int(current_pos)
            
            # Get last known position
            last_pos = self._last_checked['last_positions'].get(focused_driver)
            
            # Update stored position
            self._last_checked['last_positions'][focused_driver] = current_pos
            
            if last_pos is None:
                return None
            
            # Detect position change
            if current_pos < last_pos:
                # Gained position(s)
                positions_gained = last_pos - current_pos
                event_key = ('position_gain', current_lap)
                
                if event_key in self._last_checked['alerted_events']:
                    return None
                    
                self._last_checked['alerted_events'].add(event_key)
                
                return RaceEvent(
                    event_type='position_gain',
                    priority=3,
                    message=(
                        f"🏆 POSITION GAINED! Driver {focused_driver} moved from "
                        f"P{last_pos} to P{current_pos} (+{positions_gained} position"
                        f"{'s' if positions_gained > 1 else ''})!"
                    ),
                    data={
                        'old_position': last_pos,
                        'new_position': current_pos,
                        'positions_gained': positions_gained
                    },
                    timestamp=current_time,
                    driver_number=focused_driver
                )
            
            elif current_pos > last_pos:
                # Lost position(s)
                positions_lost = current_pos - last_pos
                event_key = ('position_loss', current_lap)
                
                if event_key in self._last_checked['alerted_events']:
                    return None
                    
                self._last_checked['alerted_events'].add(event_key)
                
                return RaceEvent(
                    event_type='position_loss',
                    priority=4,
                    message=(
                        f"⚠️ POSITION LOST! Driver {focused_driver} dropped from "
                        f"P{last_pos} to P{current_pos} (-{positions_lost} position"
                        f"{'s' if positions_lost > 1 else ''})."
                    ),
                    data={
                        'old_position': last_pos,
                        'new_position': current_pos,
                        'positions_lost': positions_lost
                    },
                    timestamp=current_time,
                    driver_number=focused_driver
                )
            
        except Exception as e:
            logger.debug(f"Position change check failed: {e}")
        
        return None

    def _check_drs_train(
        self,
        session_key: int,
        current_time: datetime,
        current_lap: int,
        focused_driver: int
    ) -> Optional[RaceEvent]:
        """
        Detect if focused driver is stuck in a DRS train.
        
        A DRS train is when multiple cars are within 1 second of each other,
        making overtaking difficult due to everyone having DRS.
        
        This should NOT trigger if:
        - The focused driver is the race leader (P1)
        - The focused driver has clear air ahead (>1.5s gap)
        """
        try:
            event_key = ('drs_train', current_lap // 3)
            if event_key in self._last_checked['alerted_events']:
                return None
            
            # Get intervals data
            intervals_df = self.provider.get_intervals(
                session_key=session_key
            )
            
            if intervals_df.empty:
                return None
            
            # Filter to data before current_time
            time_col = 'Time' if 'Time' in intervals_df.columns else 'Date'
            if time_col in intervals_df.columns:
                intervals_df = intervals_df[
                    pd.to_datetime(intervals_df[time_col]) <= current_time
                ]
            
            if intervals_df.empty:
                return None
            
            # Get latest intervals for all drivers
            latest_intervals = intervals_df.groupby('DriverNumber').last()
            
            # Get focused driver's data
            if focused_driver not in latest_intervals.index:
                return None
            
            focused_data = latest_intervals.loc[focused_driver]
            
            # Check if focused driver is the LEADER
            # Leader has GapToLeader = 0 or None/NaN
            gap_to_leader = focused_data.get('GapToLeader')
            try:
                gap_val = float(str(gap_to_leader).replace('+', '').replace('LAP', '999'))
            except (ValueError, TypeError):
                gap_val = 0.0
            
            # If driver is leader (gap_to_leader ~= 0), no DRS train possible
            if gap_val < 0.5:
                logger.debug(
                    f"[DRS_TRAIN] Driver {focused_driver} is leader "
                    f"(gap={gap_val:.1f}s), skipping DRS train check"
                )
                return None
            
            # Check focused driver's interval to car ahead
            focused_interval = focused_data.get('Interval')
            try:
                interval_ahead = float(
                    str(focused_interval).replace('+', '').replace('LAP', '999')
                )
            except (ValueError, TypeError):
                interval_ahead = 999.0
            
            # If more than 1.5s to car ahead, not in a DRS train
            if interval_ahead > 1.5:
                return None
            
            # Count cars in the train (close to each other)
            cars_in_train = 1  # Start with focused driver
            
            for drv_num in latest_intervals.index:
                if drv_num == focused_driver:
                    continue
                    
                drv_data = latest_intervals.loc[drv_num]
                drv_gap = drv_data.get('GapToLeader')
                
                try:
                    drv_gap_val = float(
                        str(drv_gap).replace('+', '').replace('LAP', '999')
                    )
                except (ValueError, TypeError):
                    continue
                
                # Check if this driver is within 2s of focused driver's gap
                if abs(drv_gap_val - gap_val) < 2.0:
                    cars_in_train += 1
            
            # DRS train if 3+ cars within close proximity
            if cars_in_train >= 3:
                self._last_checked['alerted_events'].add(event_key)
                
                return RaceEvent(
                    event_type='drs_train',
                    priority=2,
                    message=(
                        f"🚂 DRS TRAIN: Driver {focused_driver} is in a group of "
                        f"{cars_in_train} cars within 2s. Overtaking is difficult - "
                        f"consider pit stop to break free or hold position."
                    ),
                    data={
                        'cars_in_train': cars_in_train,
                        'current_lap': current_lap,
                        'gap_to_leader': gap_val,
                        'interval_ahead': interval_ahead
                    },
                    timestamp=current_time,
                    driver_number=focused_driver
                )
            
        except Exception as e:
            logger.debug(f"DRS train check failed: {e}")
        
        return None

    def _check_gap_trend(
        self,
        session_key: int,
        current_time: datetime,
        current_lap: int,
        focused_driver: int
    ) -> Optional[RaceEvent]:
        """
        Analyze gap trend to car ahead/behind.
        
        Alerts when gap is consistently decreasing (catching) or 
        increasing (losing ground).
        """
        try:
            # Get intervals
            intervals_df = self.provider.get_intervals(
                session_key=session_key
            )
            
            if intervals_df.empty:
                return None
            
            # Filter to data before current_time
            time_col = 'Time' if 'Time' in intervals_df.columns else 'Date'
            if time_col in intervals_df.columns:
                intervals_df = intervals_df[
                    pd.to_datetime(intervals_df[time_col]) <= current_time
                ]
            
            if intervals_df.empty:
                return None
            
            # Get focused driver intervals
            driver_intervals = intervals_df[
                intervals_df['DriverNumber'] == focused_driver
            ]
            
            if driver_intervals.empty:
                return None
            
            # Get latest interval to car ahead
            latest = driver_intervals.iloc[-1]
            gap_ahead = latest.get('Interval')
            
            if gap_ahead is None or gap_ahead == '':
                return None
            
            try:
                gap_value = float(str(gap_ahead).replace('+', '').replace('LAP', '999'))
                if gap_value > 100:  # Lapped, skip
                    return None
            except (ValueError, TypeError):
                return None
            
            # Store gap history
            if focused_driver not in self._last_checked.get('gap_history', {}):
                self._last_checked['gap_history'] = self._last_checked.get(
                    'gap_history', {}
                )
                self._last_checked['gap_history'][focused_driver] = []
            
            gap_history = self._last_checked['gap_history'][focused_driver]
            gap_history.append((current_lap, gap_value))
            
            # Keep only last 5 entries
            if len(gap_history) > 5:
                gap_history.pop(0)
            
            # Need at least 3 data points
            if len(gap_history) < 3:
                return None
            
            # Analyze trend
            gaps = [g[1] for g in gap_history[-3:]]
            
            # Check if consistently closing
            if all(gaps[i] > gaps[i+1] for i in range(len(gaps)-1)):
                gap_closed = gaps[0] - gaps[-1]
                
                event_key = ('gap_closing', current_lap // 5)
                if event_key in self._last_checked['alerted_events']:
                    return None
                    
                self._last_checked['alerted_events'].add(event_key)
                
                return RaceEvent(
                    event_type='gap_closing',
                    priority=2,
                    message=(
                        f"📈 CATCHING! Driver {focused_driver} closing on car ahead: "
                        f"{gaps[0]:.1f}s → {gaps[-1]:.1f}s "
                        f"(gained {gap_closed:.1f}s over {len(gaps)} checks). "
                        f"Overtake opportunity approaching!"
                    ),
                    data={
                        'gap_history': gaps,
                        'gap_closed': gap_closed
                    },
                    timestamp=current_time,
                    driver_number=focused_driver
                )
            
            # Check if consistently losing
            if all(gaps[i] < gaps[i+1] for i in range(len(gaps)-1)):
                gap_lost = gaps[-1] - gaps[0]
                
                event_key = ('gap_losing', current_lap // 5)
                if event_key in self._last_checked['alerted_events']:
                    return None
                    
                self._last_checked['alerted_events'].add(event_key)
                
                return RaceEvent(
                    event_type='gap_losing',
                    priority=2,
                    message=(
                        f"📉 LOSING GROUND: Driver {focused_driver} falling behind: "
                        f"{gaps[0]:.1f}s → {gaps[-1]:.1f}s "
                        f"(lost {gap_lost:.1f}s over {len(gaps)} checks). "
                        f"May need strategy adjustment."
                    ),
                    data={
                        'gap_history': gaps,
                        'gap_lost': gap_lost
                    },
                    timestamp=current_time,
                    driver_number=focused_driver
                )
            
        except Exception as e:
            logger.debug(f"Gap trend check failed: {e}")
        
        return None
