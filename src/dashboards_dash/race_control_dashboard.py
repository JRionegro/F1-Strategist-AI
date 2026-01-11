"""
Race Control Dashboard - Real-time flag status and race control messages.

Shows Safety Car, VSC, flags, penalties, and incidents using OpenF1 race_control API.
Synchronized with simulation time for historical playback.
"""

import logging
from typing import Optional, Tuple
from datetime import datetime, timedelta

import dash_bootstrap_components as dbc
import pandas as pd
from dash import html

from src.utils.logging_config import get_logger, LogCategory

# Use categorized logger for race control
logger = get_logger(LogCategory.RACE_CONTROL)


class RaceControlDashboard:
    """Race Control dashboard using OpenF1 race_control endpoint."""

    def __init__(self, openf1_provider):
        """
        Initialize Race Control Dashboard.

        Args:
            openf1_provider: OpenF1DataProvider instance
        """
        self.provider = openf1_provider
        self._cached_session_key = None
        self._cached_messages = None
        self._cached_drivers = None

    def render(
        self,
        session_key: Optional[int] = None,
        simulation_time: Optional[float] = None,
        session_start_time: Optional[pd.Timestamp] = None,
        focused_driver: Optional[str] = None,
        current_lap: Optional[int] = None
    ):
        """
        Render the Race Control Dashboard with real-time messages.

        Args:
            session_key: OpenF1 session key
            simulation_time: Current simulation time in seconds from session start
            session_start_time: Session start timestamp
            focused_driver: Driver number being tracked (for highlighting)
            current_lap: Current lap number (from simulation or real-time calculation)

        Returns:
            Dash Card component with race control information
        """
        if session_key is None:
            return self._render_no_session()

        try:
            logger.info(
                f"Rendering Race Control for session {session_key} "
                f"at simulation time {simulation_time}s"
            )

            # Fetch/cache data
            if (
                self._cached_session_key != session_key or
                self._cached_messages is None
            ):
                logger.info(f"Fetching race control messages for session {session_key}")
                try:
                    messages = self.provider.get_race_control_messages(
                        session_key=session_key
                    )
                    drivers = self.provider.get_drivers(session_key=session_key)

                    if not messages.empty:
                        self._cached_session_key = session_key
                        self._cached_messages = messages
                        self._cached_drivers = drivers
                        logger.info(f"Cached {len(messages)} race control messages")
                    else:
                        logger.warning("Got empty race control data from API")
                        if self._cached_messages is not None:
                            messages = self._cached_messages
                            drivers = self._cached_drivers
                        else:
                            return self._render_no_data()

                except Exception as e:
                    logger.error(f"Error fetching race control data: {e}")
                    if self._cached_messages is not None:
                        messages = self._cached_messages
                        drivers = self._cached_drivers
                    else:
                        return self._render_error(str(e))
            else:
                messages = self._cached_messages
                drivers = self._cached_drivers

            # Filter by simulation time
            filtered_messages = messages
            if simulation_time is not None and session_start_time is not None:
                try:
                    current_time = session_start_time + timedelta(seconds=simulation_time)
                    filtered_messages = messages[messages['Time'] <= current_time].copy()

                    if filtered_messages.empty:
                        filtered_messages = messages
                        logger.debug("No messages before current time, using all")
                    else:
                        logger.debug(
                            f"Filtered to {len(filtered_messages)}/{len(messages)} messages"
                        )
                except Exception as e:
                    logger.warning(f"Could not filter by simulation time: {e}")
                    filtered_messages = messages

            # Extract current status
            if current_lap is None:
                # Fallback: Calculate lap from available data
                current_lap = self._calculate_current_lap_from_data(
                    session_key,
                    simulation_time,
                    session_start_time,
                    filtered_messages
                )
            current_flag, sc_status = self._extract_current_status(filtered_messages)

            # Build UI components
            status_panel = self._create_status_panel(
                current_flag, sc_status, current_lap
            )
            messages_timeline = self._create_messages_timeline(
                filtered_messages, focused_driver, drivers
            )

            # Return complete Card
            return dbc.Card([
                dbc.CardHeader([
                    html.H5("🚦 Race Control", className="mb-0", style={"fontSize": "1.2rem"})
                ], className="py-1"),
                dbc.CardBody([
                    status_panel,
                    html.Hr(className="my-2"),
                    messages_timeline
                ], className="p-2", style={"backgroundColor": "#1e1e1e"})
            ], className="mb-3 h-100", style={"overflow": "hidden"})

        except Exception as e:
            logger.error(f"Error rendering Race Control Dashboard: {e}", exc_info=True)
            return self._render_error(str(e))

    def _create_status_panel(
        self,
        current_flag: str,
        sc_status: Optional[str],
        current_lap: int
    ):
        """Create current status panel showing flags and SC."""
        # Flag badge
        flag_color = {
            "GREEN": "success",
            "YELLOW": "warning",
            "RED": "danger",
            "SC": "warning",
            "VSC": "warning"
        }.get(current_flag, "secondary")

        flag_icon = {
            "GREEN": "🟢",
            "YELLOW": "🟡",
            "RED": "🔴",
            "SC": "🚗",
            "VSC": "🟡"
        }.get(current_flag, "🏁")

        flag_text = {
            "SC": "SAFETY CAR",
            "VSC": "VIRTUAL SC"
        }.get(current_flag, current_flag)

        return dbc.Card([
            dbc.CardBody([
                html.Div([
                    dbc.Badge(
                        [flag_icon, f" {flag_text}"],
                        color=flag_color,
                        className="me-2",
                        style={"fontSize": "0.9rem"}
                    ),
                    html.Span(
                        f"Lap {current_lap}" if current_lap else "Lap --",
                        className="text-white",
                        style={"fontSize": "0.85rem"}
                    ),
                    html.Span(
                        f" | {sc_status}" if sc_status else "",
                        className="text-warning ms-2",
                        style={"fontSize": "0.75rem"}
                    )
                ], style={"display": "flex", "alignItems": "center"})
            ], className="p-2")
        ], className="mb-2 border border-secondary", style={"backgroundColor": "#2d2d2d"})

    def _create_messages_timeline(
        self,
        messages: pd.DataFrame,
        focused_driver: Optional[str] = None,
        drivers: Optional[pd.DataFrame] = None
    ):
        """Create scrollable timeline of race control messages."""
        
        # Log focused driver to track changes
        if focused_driver:
            logger.info(f"🎯 Creating timeline with focused_driver: {focused_driver} (total messages: {len(messages)})")
        
        if messages.empty:
            return html.Div(
                "No race control messages yet",
                className="text-muted text-center p-3",
                style={"fontSize": "0.85rem"}
            )

        # Limit to last 100 messages and sort by most recent first
        messages_display = messages.tail(100).copy()
        messages_display = messages_display.sort_values(by='Time', ascending=False)

        # Get driver info for focused driver
        driver_number = None
        driver_code = None
        driver_full_name = None
        driver_last_name = None
        
        # Parse focused_driver if it's in format "CODE_YEAR_NUMBER" (e.g., "HAM_2025_44")
        if focused_driver:
            parts = focused_driver.split('_')
            if len(parts) >= 3:
                # Format: CODE_YEAR_NUMBER
                driver_code_from_id = parts[0]
                driver_number_from_id = parts[2]
                logger.info(f"Parsed focused_driver '{focused_driver}': code={driver_code_from_id}, number={driver_number_from_id}")
                
                # Use parsed values
                driver_code = driver_code_from_id
                driver_number = driver_number_from_id
            else:
                # Simple format (just code or number)
                driver_code = focused_driver
        
        # Try to enrich with full driver info from drivers DataFrame
        if drivers is not None and not drivers.empty:
            try:
                # Column names after normalization in openf1_data_provider
                # DriverNumber, Abbreviation, DriverName, TeamName, TeamColor
                
                # Try to find driver by number or code
                driver_match = None
                
                # Check if columns exist
                has_driver_number = 'DriverNumber' in drivers.columns or 'driver_number' in drivers.columns
                has_abbreviation = 'Abbreviation' in drivers.columns or 'name_acronym' in drivers.columns
                
                search_value = driver_code if driver_code else focused_driver
                search_number = driver_number if driver_number else focused_driver
                
                # Validate search values to avoid None errors
                search_value_upper = search_value.upper() if search_value else ""
                search_number_str = str(search_number) if search_number else ""
                
                if has_driver_number and has_abbreviation:
                    number_col = 'DriverNumber' if 'DriverNumber' in drivers.columns else 'driver_number'
                    abbr_col = 'Abbreviation' if 'Abbreviation' in drivers.columns else 'name_acronym'
                    
                    driver_match = drivers[
                        (drivers[number_col].astype(str) == search_number_str) |
                        (drivers[abbr_col] == search_value_upper)
                    ]
                elif has_driver_number:
                    number_col = 'DriverNumber' if 'DriverNumber' in drivers.columns else 'driver_number'
                    driver_match = drivers[drivers[number_col].astype(str) == search_number_str]
                elif has_abbreviation:
                    abbr_col = 'Abbreviation' if 'Abbreviation' in drivers.columns else 'name_acronym'
                    driver_match = drivers[drivers[abbr_col] == search_value_upper]
                
                if driver_match is not None and not driver_match.empty:
                    driver_info = driver_match.iloc[0]
                    
                    # Get driver details with fallbacks (override with DataFrame values if available)
                    driver_number = str(driver_info.get('DriverNumber', driver_info.get('driver_number', driver_number)))
                    driver_code = driver_info.get('Abbreviation', driver_info.get('name_acronym', driver_code))
                    driver_full_name = driver_info.get('DriverName', driver_info.get('full_name', ''))
                    
                    # Extract last name from full name if available
                    if driver_full_name and ' ' in driver_full_name:
                        driver_last_name = driver_full_name.split()[-1]
                    elif 'last_name' in driver_info:
                        driver_last_name = driver_info.get('last_name', '')
                    
                    logger.info(
                        f"Focused driver detected: {driver_code} (#{driver_number}) - {driver_full_name}"
                    )
                else:
                    logger.info(f"Using parsed driver info: {driver_code} (#{driver_number})")
            except Exception as e:
                logger.warning(f"Error processing focused driver info: {e}")
                # Keep parsed values from focused_driver string

        # Classify and format messages
        message_rows = []
        highlighted_count = 0
        
        for idx, (_, row) in enumerate(messages_display.iterrows()):
            msg_type, color = self._classify_message(row)

            # Format time and message
            try:
                time_str = row['Time'].strftime("%H:%M:%S") if pd.notna(row['Time']) else "--:--:--"
            except:
                time_str = "--:--:--"

            message_text = row.get('Message', 'Unknown message')
            category = row.get('Category', '')

            # Check if message mentions focused driver
            is_focused_driver = False
            if focused_driver and message_text:
                import re
                message_upper = message_text.upper()
                
                # === SMART DRIVER DETECTION ===
                # Avoid false positives like "SECTOR 14", "TURN 14", "LAP 14"
                # Also avoid matching "4" in "44" - use strict word boundaries
                # Only match driver numbers in driver-specific contexts
                
                search_patterns = []
                
                if driver_number:
                    num = re.escape(driver_number)
                    # Positive patterns - contexts where number IS a driver reference
                    # Use (?<!\d) and (?!\d) to prevent matching "4" inside "44"
                    search_patterns.extend([
                        rf"\((?<!\d){num}(?!\d)\)",     # (4) but NOT (44)
                        rf"CAR\s*(?<!\d){num}(?!\d)",   # CAR 4 but NOT CAR 44
                        rf"NO\.?\s*(?<!\d){num}(?!\d)", # NO 4 but NOT NO 44
                        rf"#(?<!\d){num}(?!\d)",        # #4 but NOT #44
                        rf"DRIVER\s*(?<!\d){num}(?!\d)", # DRIVER 4 but NOT DRIVER 44
                    ])
                    
                    # Match number only if NOT preceded by false-positive words
                    # Use negative lookbehind for: SECTOR, TURN, LAP, DRS ZONE, CORNER
                    false_positive_prefixes = (
                        r"(?<!SECTOR\s)(?<!SECTOR)"
                        r"(?<!TURN\s)(?<!TURN)"
                        r"(?<!LAP\s)(?<!LAP)"
                        r"(?<!ZONE\s)(?<!ZONE)"
                        r"(?<!DRS\s)(?<!DRS)"
                        r"(?<!CORNER\s)(?<!CORNER)"
                        r"(?<!T)"  # T14 = Turn 14
                        r"(?<!S)"  # S14 = Sector abbreviation
                    )
                    # This pattern matches standalone number NOT after false positives
                    # But regex lookbehind must be fixed width, so we use a different approach
                
                if driver_code:
                    code_upper = driver_code.upper()
                    # Code-based patterns with strict boundaries
                    # Only match if followed by: ), space, -, comma, or end of string
                    # This prevents "COL" from matching "COLLISION"
                    search_patterns.extend([
                        rf"\({re.escape(code_upper)}\)",     # (ALO)
                        rf"\b{re.escape(code_upper)}[\)\s\-,]",  # ALO) or ALO or ALO-
                        rf"\b{re.escape(code_upper)}$"       # ALO at end of message
                    ])
                
                if driver_last_name:
                    last_upper = driver_last_name.upper()
                    search_patterns.append(rf"\b{re.escape(last_upper)}\b")
                
                if driver_full_name:
                    search_patterns.append(rf"\b{re.escape(driver_full_name.upper())}\b")
                
                # Check if any positive pattern matches
                for pattern in search_patterns:
                    if re.search(pattern, message_upper):
                        is_focused_driver = True
                        break
                
                # Secondary check: if number found but might be false positive
                # Check for driver number with additional validation
                if not is_focused_driver and driver_number:
                    num = re.escape(driver_number)
                    # Check if number appears in message as EXACT number
                    # Use (?<!\d) and (?!\d) to prevent matching "4" inside "44"
                    exact_num_pattern = rf"(?<!\d){num}(?!\d)"
                    if re.search(exact_num_pattern, message_upper):
                        # Exclude if preceded by false-positive context words
                        false_positives = [
                            rf"SECTOR\s*(?<!\d){num}(?!\d)",
                            rf"TURN\s*(?<!\d){num}(?!\d)",
                            rf"LAP\s*(?<!\d){num}(?!\d)",
                            rf"T(?<!\d){num}(?!\d)",           # T14 = Turn 14
                            rf"S(?<!\d){num}(?!\d)",           # S14 = Sector 14
                            rf"DRS\s*ZONE\s*(?<!\d){num}(?!\d)",
                            rf"CORNER\s*(?<!\d){num}(?!\d)",
                            rf"ZONE\s*(?<!\d){num}(?!\d)",
                            rf"ROUND\s*(?<!\d){num}(?!\d)",
                            rf"STAGE\s*(?<!\d){num}(?!\d)",
                            rf"SESSION\s*(?<!\d){num}(?!\d)",
                        ]
                        
                        is_false_positive = any(
                            re.search(fp, message_upper) for fp in false_positives
                        )
                        
                        if not is_false_positive:
                            # Additional context: check if message seems driver-related
                            driver_context_words = [
                                'PIT', 'PENALTY', 'TIME', 'WARNING', 'INVESTIGATION',
                                'INCIDENT', 'DELETED', 'TRACK LIMITS', 'OVERTAKE',
                                'COLLISION', 'CONTACT', 'UNSAFE', 'RELEASE', 'JUMP',
                                'START', 'GRID', 'POSITION', 'STOP', 'TYRE', 'TIRE',
                                'STEWARD', 'BLACK', 'WHITE', 'FLAG', 'RETIRED',
                                'STOPPED', 'SLOW', 'MECHANICAL', 'DAMAGE'
                            ]
                            
                            has_driver_context = any(
                                word in message_upper for word in driver_context_words
                            )
                            
                            # Only highlight if message has driver-related context
                            if has_driver_context:
                                is_focused_driver = True

            # Color coding
            text_color = {
                'danger': '#dc3545',
                'warning': '#ffc107',
                'info': '#17a2b8',
                'success': '#28a745',
                'secondary': '#6c757d'
            }.get(color, '#ffffff')

            # Style for focused driver messages
            row_style = {
                "borderLeft": f"3px solid {text_color}",
                "backgroundColor": "#1e1e1e" if idx % 2 == 0 else "#2d2d2d"
            }
            
            if is_focused_driver:
                row_style.update({
                    "backgroundColor": "#ffc107",
                    "borderLeft": "5px solid #ff6b00",
                    "boxShadow": "0 0 10px rgba(255, 193, 7, 0.5)"
                })
                text_color = "#000000"  # Black text for better contrast on yellow
                highlighted_count += 1

            message_rows.append(
                html.Div([
                    html.Span(
                        f"{time_str}",
                        className="me-2",
                        style={"color": "#888", "fontSize": "0.7rem", "fontFamily": "monospace"}
                    ),
                    html.Span(
                        f"{category.upper()}" if category else "",
                        className="me-2",
                        style={"color": text_color, "fontSize": "0.7rem", "fontWeight": "bold"}
                    ),
                    html.Span(
                        message_text,
                        style={
                            "color": text_color,
                            "fontSize": "0.75rem",
                            "fontWeight": "bold" if is_focused_driver else "normal"
                        }
                    )
                ], className="mb-1 p-1", style=row_style)
            )

        return dbc.Card([
            dbc.CardHeader(
                "📋 Race Control Messages",
                className="text-white py-1",
                style={"fontSize": "0.9rem", "backgroundColor": "#1e1e1e"}
            ),
            dbc.CardBody(
                html.Div(
                    message_rows,
                    style={
                        "maxHeight": "350px",
                        "overflowY": "auto",
                        "fontSize": "0.75rem"
                    }
                ),
                className="p-2",
                style={"backgroundColor": "#1e1e1e"}
            )
        ], className="border border-secondary")

    def _classify_message(self, row: pd.Series) -> Tuple[str, str]:
        """
        Classify message type for color-coding.

        Returns:
            Tuple of (message_type, color) where color is Bootstrap contextual color
        """
        category = str(row.get('Category', '')).upper() if pd.notna(row.get('Category')) else ''
        message = str(row.get('Message', '')).upper() if pd.notna(row.get('Message')) else ''
        flag = str(row.get('Flag', '')).upper() if pd.notna(row.get('Flag')) else ''

        # Priority order
        if 'RED FLAG' in message or flag == 'RED':
            return 'red_flag', 'danger'
        elif 'SAFETY CAR DEPLOYED' in message or 'SC DEPLOYED' in message:
            return 'safety_car', 'warning'
        elif 'VIRTUAL SAFETY CAR' in message or 'VSC' in message:
            return 'vsc', 'warning'
        elif 'YELLOW FLAG' in message or 'YELLOW' in flag:
            return 'yellow_flag', 'warning'
        elif 'PENALTY' in message or 'PENALTY' in category:
            return 'penalty', 'info'
        elif 'INVESTIGATION' in message:
            return 'investigation', 'secondary'
        elif 'GREEN FLAG' in message or 'CLEAR' in message or flag == 'GREEN':
            return 'green_flag', 'success'
        else:
            return 'other', 'secondary'

    def _calculate_current_lap_from_data(
        self,
        session_key: Optional[int],
        simulation_time: Optional[float],
        session_start_time: Optional[pd.Timestamp],
        messages: pd.DataFrame
    ) -> int:
        """
        Calculate current lap from available data sources.
        
        Priority order:
        1. From simulation_time + lap timing data (for real-time/live)
        2. From messages (last resort fallback)
        3. Return 0 if no data available
        
        Args:
            session_key: OpenF1 session key
            simulation_time: Simulation time in seconds
            session_start_time: Session start timestamp
            messages: Filtered race control messages
            
        Returns:
            Current lap number
        """
        # Strategy 1: Calculate from timing data (works for both simulation and real-time)
        if session_key and simulation_time is not None and session_start_time:
            try:
                # Get lap timing data from OpenF1
                laps = self.provider.get_laps(session_key=session_key)
                
                if not laps.empty and 'LapStartTime' in laps.columns:
                    # Calculate current timestamp
                    current_time = session_start_time + timedelta(seconds=simulation_time)
                    
                    # Find which lap we're in by comparing timestamps
                    # Use leader's laps (DriverNumber=1) for consistency
                    leader_laps = laps[laps['DriverNumber'] == 1].copy()
                    
                    if not leader_laps.empty:
                        # Sort by lap number
                        leader_laps = leader_laps.sort_values('LapNumber')
                        
                        # Find current lap
                        for idx, row in leader_laps.iterrows():
                            lap_start = row.get('LapStartTime')
                            lap_end = row.get('LapEndTime')
                            lap_num = row.get('LapNumber')
                            
                            if pd.notna(lap_start):
                                # Convert timedelta to absolute time
                                if isinstance(lap_start, timedelta):
                                    lap_start_abs = session_start_time + lap_start
                                else:
                                    lap_start_abs = lap_start
                                
                                # Check if we're in this lap
                                if pd.notna(lap_end):
                                    if isinstance(lap_end, timedelta):
                                        lap_end_abs = session_start_time + lap_end
                                    else:
                                        lap_end_abs = lap_end
                                    
                                    if lap_start_abs <= current_time <= lap_end_abs:
                                        # Convert OpenF1 lap (includes formation) to racing lap
                                        racing_lap = max(1, int(lap_num) - 2) if lap_num > 2 else 1
                                        logger.debug(
                                            f"Calculated lap from timing: OpenF1 lap {lap_num} = "
                                            f"Racing lap {racing_lap}"
                                        )
                                        return racing_lap
                                else:
                                    # Lap not finished yet, check if we've started it
                                    if current_time >= lap_start_abs:
                                        racing_lap = max(1, int(lap_num) - 2) if lap_num > 2 else 1
                                        logger.debug(
                                            f"In progress lap: OpenF1 lap {lap_num} = "
                                            f"Racing lap {racing_lap}"
                                        )
                                        return racing_lap
                        
                        # If no exact match, determine pre-race or post-race
                        first_lap_start = leader_laps.iloc[0].get('LapStartTime')
                        if pd.notna(first_lap_start):
                            if isinstance(first_lap_start, timedelta):
                                first_lap_start_abs = session_start_time + first_lap_start
                            else:
                                first_lap_start_abs = first_lap_start
                            
                            if current_time < first_lap_start_abs:
                                return 0  # Pre-race
                        
                        # Post-race or in last lap
                        last_lap = int(leader_laps.iloc[-1]['LapNumber'])
                        return max(1, last_lap - 2) if last_lap > 2 else 1
                        
            except Exception as e:
                logger.warning(f"Could not calculate lap from timing data: {e}")
        
        # Strategy 2: Extract from messages (old fallback method)
        lap_from_messages = self._extract_current_lap(messages)
        if lap_from_messages > 0:
            logger.debug(f"Using lap from messages: {lap_from_messages}")
            return lap_from_messages
        
        # No data available
        return 0

    def _extract_current_lap(self, messages: pd.DataFrame) -> int:
        """Extract current lap from most recent message mentioning lap number."""
        if messages.empty:
            return 0

        # Look for lap mentions in recent messages
        for idx, row in messages.iloc[::-1].iterrows():
            message = str(row.get('Message', ''))
            if 'LAP' in message.upper():
                # Try to extract lap number
                import re
                match = re.search(r'LAP (\d+)', message.upper())
                if match:
                    return int(match.group(1))

        return 0

    def _extract_current_status(
        self,
        messages: pd.DataFrame
    ) -> Tuple[str, Optional[str]]:
        """
        Extract current flag and SC status from latest messages.

        Returns:
            Tuple of (current_flag, sc_status_text)
        """
        if messages.empty:
            return "GREEN", None

        # Check last 10 messages for current status
        recent_messages = messages.tail(10)

        # Look for SC/VSC
        for idx, row in recent_messages.iloc[::-1].iterrows():
            message = str(row.get('Message', '')).upper()

            if 'SAFETY CAR DEPLOYED' in message:
                return "SC", "SC Active"
            elif 'SAFETY CAR IN THIS LAP' in message or 'SC ENDING' in message:
                return "GREEN", "SC Ending"
            elif 'VIRTUAL SAFETY CAR' in message and 'ENDING' not in message:
                return "VSC", "VSC Active"
            elif 'VSC ENDING' in message:
                return "GREEN", "VSC Ending"
            elif 'RED FLAG' in message:
                return "RED", "Session Suspended"

        # Check for yellow flags
        for idx, row in recent_messages.iloc[::-1].iterrows():
            message = str(row.get('Message', '')).upper()
            if 'YELLOW FLAG' in message:
                return "YELLOW", None

        return "GREEN", None

    def _render_no_session(self):
        """Render placeholder when no session is loaded."""
        return dbc.Card([
            dbc.CardHeader([
                html.H5("🚦 Race Control", className="mb-0", style={"fontSize": "1.2rem"})
            ], className="py-1"),
            dbc.CardBody([
                html.Div([
                    html.I(
                        className="fas fa-flag-checkered fa-3x mb-3",
                        style={"color": "#6c757d"}
                    ),
                    html.H5("No session loaded", className="text-muted"),
                    html.P(
                        "Please select a race session from the sidebar.",
                        className="small text-muted"
                    )
                ], className="text-center p-5")
            ], className="p-2")
        ], className="mb-3", style={"height": "620px"})

    def _render_no_data(self):
        """Render when no race control data available."""
        return dbc.Card([
            dbc.CardHeader([
                html.H5("🚦 Race Control", className="mb-0", style={"fontSize": "1.2rem"})
            ], className="py-1"),
            dbc.CardBody([
                html.Div([
                    html.I(
                        className="fas fa-info-circle fa-3x mb-3",
                        style={"color": "#17a2b8"}
                    ),
                    html.H5("No race control activity", className="text-info"),
                    html.P(
                        "No race control messages available for this session yet.",
                        className="small text-muted"
                    )
                ], className="text-center p-5")
            ], className="p-2")
        ], className="mb-3", style={"height": "620px"})

    def _render_error(self, error_message: str):
        """Render error state."""
        return dbc.Card([
            dbc.CardHeader([
                html.H5("🚦 Race Control", className="mb-0", style={"fontSize": "1.2rem"})
            ], className="py-1"),
            dbc.CardBody([
                html.Div([
                    html.I(
                        className="fas fa-exclamation-triangle fa-3x mb-3",
                        style={"color": "#ffc107"}
                    ),
                    html.H5("Error loading race control data", className="text-warning"),
                    html.P(
                        str(error_message),
                        className="small text-muted"
                    )
                ], className="text-center p-5")
            ], className="p-2")
        ], className="mb-3", style={"height": "620px"})

    def get_status_summary(
        self,
        session_key: int,
        simulation_time: float,
        session_start_time: pd.Timestamp,
        current_lap: int
    ) -> dict:
        """
        Get race control status summary for AI context.
        
        Args:
            session_key: OpenF1 session key
            simulation_time: Current simulation time in seconds
            session_start_time: Session start timestamp
            current_lap: Current lap number
            
        Returns:
            Dict with race control summary:
            {
                'flag': 'GREEN',  # GREEN, YELLOW, RED, SC, VSC
                'safety_car': True/False,
                'virtual_safety_car': True/False,
                'recent_events': ['VSC ENDING', 'PIT LANE OPEN'],
                'penalties': ['HAM - 5s Time Penalty'],
                'incidents': ['Turn 4 - VER off track']
            }
        """
        # Use cached data if available
        if self._cached_session_key != session_key or self._cached_messages is None:
            return {'error': 'No cached data available'}
        
        messages = self._cached_messages
        
        # Determine time column (OpenF1 provider renames 'date' to 'Time')
        time_col = 'Time' if 'Time' in messages.columns else 'Timestamp'
        
        # Filter messages by simulation time
        current_timestamp = session_start_time + pd.Timedelta(seconds=simulation_time)
        try:
            filtered_messages = messages[messages[time_col] <= current_timestamp]
        except Exception as e:
            logger.warning(f"Error filtering messages by time: {e}")
            filtered_messages = messages
        
        if filtered_messages.empty:
            return {
                'flag': 'GREEN',
                'safety_car': False,
                'virtual_safety_car': False,
                'recent_events': [],
                'penalties': [],
                'incidents': []
            }
        
        # Determine current flag status from recent messages
        flag = 'GREEN'
        safety_car = False
        virtual_safety_car = False
        
        # Check last 15 messages for SC/VSC status
        recent_sorted = filtered_messages.sort_values(time_col, ascending=False).head(15)
        
        for _, msg in recent_sorted.iterrows():
            category = str(msg.get('Category', '')).upper()
            message = str(msg.get('Message', '')).upper()
            
            # Check for RED FLAG
            if 'RED FLAG' in message or 'REDFLAG' in category:
                flag = 'RED'
                break
            
            # Check for SAFETY CAR (deployed, not ending)
            sc_patterns = ['SAFETY CAR DEPLOYED', 'SAFETY CAR IN THIS LAP',
                          'SAFETYCAR', 'SC DEPLOYED', 'THE SAFETY CAR']
            sc_ending = ['ENDING', 'IN THIS LAP', 'WITHDRAW']
            
            is_sc_deployed = any(p in message for p in sc_patterns)
            is_sc_ending = any(e in message for e in sc_ending)
            
            if is_sc_deployed and not is_sc_ending:
                flag = 'SC'
                safety_car = True
                break
            elif 'SAFETY CAR' in message and is_sc_ending:
                # SC ending - track is going green
                flag = 'GREEN'
                break
            
            # Check for VIRTUAL SAFETY CAR
            vsc_patterns = ['VIRTUAL SAFETY CAR', 'VSC DEPLOYED', 'VSC ']
            is_vsc = any(p in message for p in vsc_patterns)
            
            if is_vsc and not is_sc_ending:
                flag = 'VSC'
                virtual_safety_car = True
                break
            elif 'VSC' in message and is_sc_ending:
                flag = 'GREEN'
                break
            
            # Check for YELLOW
            if 'YELLOW' in message or category == 'FLAG':
                flag = 'YELLOW'
                # Don't break - keep looking for SC/VSC
        
        # Get recent events (last 5 messages)
        recent_events = []
        for _, msg in recent_sorted.head(5).iterrows():
            msg_text = msg.get('Message', '')
            if msg_text:
                recent_events.append(str(msg_text))
        
        # Get penalties and incidents
        penalties = []
        incidents = []
        for _, msg in filtered_messages.iterrows():
            message = str(msg.get('Message', '')).upper()
            if 'PENALTY' in message or 'TIME PENALTY' in message:
                penalties.append(msg.get('Message', ''))
            elif 'OFF TRACK' in message or 'INCIDENT' in message:
                incidents.append(msg.get('Message', ''))
        
        logger.debug(
            f"Race control status: flag={flag}, SC={safety_car}, "
            f"VSC={virtual_safety_car}, recent_events={len(recent_events)}"
        )
        
        return {
            'flag': flag,
            'safety_car': safety_car,
            'virtual_safety_car': virtual_safety_car,
            'recent_events': recent_events,
            'penalties': penalties[-3:] if penalties else [],
            'incidents': incidents[-3:] if incidents else []
        }
