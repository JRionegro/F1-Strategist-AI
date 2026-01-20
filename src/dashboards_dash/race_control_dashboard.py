"""
Race Control Dashboard - Real-time flag status and race control messages.

Shows Safety Car, VSC, flags, penalties, and incidents using OpenF1 race_control API.
Synchronized with simulation time for historical playback.
"""

from typing import Any, Optional, Tuple
from datetime import datetime, timedelta
import re

import dash_bootstrap_components as dbc
import pandas as pd
from dash import html

from src.utils.logging_config import get_logger, LogCategory

# Use categorized logger for race control
logger = get_logger(LogCategory.RACE_CONTROL)


class RaceControlDashboard:
    """Race Control dashboard using OpenF1 race_control endpoint."""

    def __init__(self, openf1_provider):
        """Initialize Race Control Dashboard."""
        self.provider = openf1_provider
        self._cached_session_key = None
        self._cached_messages = None
        self._cached_drivers = None

    def _get_messages_and_drivers(
        self,
        session_key: int
    ) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
        """Fetch race control messages and drivers with caching.

        Returns cached data when available for the same session_key.
        """
        if self._cached_session_key == session_key and self._cached_messages is not None:
            return self._cached_messages, self._cached_drivers

        logger.info(f"Fetching race control messages for session {session_key}")
        try:
            messages = self.provider.get_race_control_messages(session_key=session_key)
            drivers = self.provider.get_drivers(session_key=session_key)

            if messages.empty:
                logger.warning("Got empty race control data from API")
                return self._cached_messages, self._cached_drivers

            self._cached_session_key = session_key
            self._cached_messages = messages
            self._cached_drivers = drivers
            logger.info(f"Cached {len(messages)} race control messages")
            return messages, drivers
        except Exception as exc:
            logger.error(f"Error fetching race control data: {exc}")
            return self._cached_messages, self._cached_drivers

    def _filter_messages_by_time(
        self,
        messages: pd.DataFrame,
        simulation_time: Optional[float],
        session_start_time: Optional[pd.Timestamp]
    ) -> pd.DataFrame:
        """Filter messages to those occurring before the current simulation time."""
        filtered_messages = messages
        if simulation_time is None or session_start_time is None:
            return filtered_messages

        try:
            current_time = session_start_time + timedelta(seconds=simulation_time)
            current_time = pd.Timestamp(current_time)

            # Normalize timeline to UTC to match OpenF1 timestamps and avoid tz comparison errors
            if current_time.tzinfo is None:
                current_time = current_time.tz_localize("UTC")
            else:
                current_time = current_time.tz_convert("UTC")

            time_series = pd.to_datetime(messages.get('Time'), utc=True, errors='coerce')
            if time_series.isna().all():
                logger.debug("Race control messages missing valid timestamps; skipping filter")
                return messages

            filtered_messages = messages[time_series <= current_time].copy()

            if filtered_messages.empty:
                filtered_messages = messages
                logger.debug("No messages before current time, using all")
            else:
                logger.debug(
                    f"Filtered to {len(filtered_messages)}/{len(messages)} messages"
                )
        except Exception as exc:
            logger.warning(f"Could not filter by simulation time: {exc}")
            filtered_messages = messages

        return filtered_messages

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
            "VSC": "warning",
            "CHEQUERED": "secondary",
        }.get(current_flag, "secondary")

        flag_icon = {
            "GREEN": "🟢",
            "YELLOW": "🟡",
            "RED": "🔴",
            "SC": "🚗",
            "VSC": "🟡",
            "CHEQUERED": "🏁",
        }.get(current_flag, "🏁")

        flag_text = {
            "SC": "SAFETY CAR",
            "VSC": "VIRTUAL SC",
            "CHEQUERED": "SESSION ENDED",
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

            # Check if message references the focused driver in canonical format
            is_focused_driver = False
            if (
                focused_driver
                and message_text
                and driver_number
                and driver_code
            ):
                message_upper = message_text.upper()
                canonical_pattern = (
                    rf"\bCAR\s+{re.escape(driver_number)}\s*"
                    rf"\(\s*{re.escape(driver_code.upper())}\s*\)"
                )
                if re.search(canonical_pattern, message_upper):
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

    def _create_summary_panel(self, status_summary: dict[str, Any]) -> dbc.Card:
        """Create compact summary card for recent race control activity."""

        flag_value = str(status_summary.get('flag', 'GREEN')).upper()
        flag_color = {
            "GREEN": "success",
            "YELLOW": "warning",
            "RED": "danger",
            "SC": "warning",
            "VSC": "info",
            "CHEQUERED": "secondary",
        }.get(flag_value, "secondary")

        status_badges = [
            dbc.Badge(flag_value, color=flag_color, className="me-1")
        ]
        if status_summary.get('safety_car'):
            status_badges.append(dbc.Badge("SC", color="warning", className="me-1"))
        if status_summary.get('virtual_safety_car'):
            status_badges.append(dbc.Badge("VSC", color="info", className="me-1"))

        recent_events = [
            str(item) for item in status_summary.get('recent_events') or []
        ]
        penalties = [
            str(item) for item in status_summary.get('penalties') or []
        ]
        incidents = [
            str(item) for item in status_summary.get('incidents') or []
        ]

        def render_section(
            title: str,
            items: list[str],
            empty_text: str
        ) -> html.Div:
            header = html.Div(title, className="text-white small fw-bold mb-1")
            if not items:
                content = html.Div(empty_text, className="text-muted small")
            else:
                content = html.Ul(
                    [
                        html.Li(str(item), className="small mb-1")
                        for item in items
                    ],
                    className="ps-3 mb-0"
                )
            return html.Div([header, content], className="mb-3")

        sections = [
            html.Div(status_badges, className="mb-2"),
            render_section("Recent", recent_events, "No recent events."),
            render_section("Penalties", penalties, "No penalties."),
            render_section("Incidents", incidents, "No incidents."),
        ]

        return dbc.Card(
            dbc.CardBody(
                sections,
                className="p-2",
                style={"backgroundColor": "#1e1e1e"}
            ),
            className="border border-secondary",
            style={"minHeight": "350px"}
        )

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
                            try:
                                lap_num_int = int(lap_num)
                            except (TypeError, ValueError):
                                continue
                            
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
                                        current_lap = max(1, lap_num_int)
                                        logger.debug(
                                            "Calculated lap from timing: OpenF1 lap %s",
                                            lap_num_int
                                        )
                                        return current_lap
                                else:
                                    # Lap not finished yet, check if we've started it
                                    if current_time >= lap_start_abs:
                                        current_lap = max(1, lap_num_int)
                                        logger.debug(
                                            "In progress lap: OpenF1 lap %s",
                                            lap_num_int
                                        )
                                        return current_lap
                        
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
                        try:
                            last_lap = int(leader_laps.iloc[-1]['LapNumber'])
                        except (TypeError, ValueError):
                            return 1
                        return max(1, last_lap)
                        
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
        messages: pd.DataFrame,
        current_lap: Optional[int] = None,
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

        status_flag = "GREEN"
        status_detail: Optional[str] = None
        sc_end_lap_hint: Optional[int] = None

        # Look for SC/VSC and session end/flags
        for idx, row in recent_messages.iloc[::-1].iterrows():
            message = str(row.get('Message', '')).upper()

            end_tokens = (
                'CHEQUERED FLAG',
                'CHEQUEREDFLAG',
                'SESSION FINISH',
                'SESSION FINISHED',
                'SESSION END',
                'SESSION ENDED',
                'END OF SESSION',
                'SESSION COMPLETE',
                'RACE FINISH',
                'RACE FINISHED',
                'QUALIFYING FINISH',
                'QUALIFYING ENDED',
                'PRACTICE FINISH',
                'PRACTICE FINISHED',
                'FINISH FLAG'
            )

            lap_hint = None
            lap_match = re.search(r"LAP\s*(\d+)", message)
            if lap_match:
                try:
                    lap_hint = int(lap_match.group(1))
                except ValueError:
                    lap_hint = None

            if any(token in message for token in end_tokens):
                return "CHEQUERED", "Session Ended"

            if 'SAFETY CAR DEPLOYED' in message:
                status_flag, status_detail = "SC", "SC Active"
                break
            if 'SAFETY CAR IN THIS LAP' in message or 'SC ENDING' in message:
                status_flag, status_detail = "GREEN", "SC Ending"
                sc_end_lap_hint = lap_hint if lap_hint is not None else current_lap
                break
            if 'VIRTUAL SAFETY CAR' in message and 'ENDING' not in message:
                status_flag, status_detail = "VSC", "VSC Active"
                break
            if 'VSC ENDING' in message:
                status_flag, status_detail = "GREEN", "VSC Ending"
                sc_end_lap_hint = lap_hint if lap_hint is not None else current_lap
                break
            if 'RED FLAG' in message:
                status_flag, status_detail = "RED", "Session Suspended"
                break

        # Check for yellow flags if nothing else matched
        if status_flag == "GREEN" and status_detail is None:
            for idx, row in recent_messages.iloc[::-1].iterrows():
                message = str(row.get('Message', '')).upper()
                if 'YELLOW FLAG' in message and 'INFRINGEMENT' not in message:
                    status_flag, status_detail = "YELLOW", None
                    break

        # Clear "SC/VSC Ending" indicator once the lap has advanced
        if (
            status_flag == "GREEN"
            and status_detail in {"SC Ending", "VSC Ending"}
            and current_lap is not None
        ):
            # If we have a lap hint for the ending message, hide after the next lap
            if sc_end_lap_hint is not None and current_lap > sc_end_lap_hint:
                return "GREEN", None
            # If no lap hint, assume it should clear after current lap advances by 1
            # (current_lap passed in reflects the active lap)
            if sc_end_lap_hint is None:
                return "GREEN", None

        return status_flag, status_detail

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

    def get_signature(
        self,
        session_key: Optional[int],
        simulation_time: Optional[float],
        session_start_time: Optional[pd.Timestamp],
        focused_driver: Optional[str] = None,
        current_lap: Optional[int] = None,
    ) -> Optional[Tuple[int, int, Optional[str], Optional[str], Optional[str], Optional[int]]]:
        """Build immutable signature describing the rendered state."""

        if session_key is None:
            return None

        messages, _ = self._get_messages_and_drivers(session_key)
        if messages is None or messages.empty:
            return (
                session_key,
                0,
                None,
                None,
                (focused_driver or "").upper() or None,
                current_lap,
            )

        filtered_messages = self._filter_messages_by_time(
            messages,
            simulation_time,
            session_start_time
        )

        if filtered_messages.empty:
            filtered_messages = messages.tail(1)

        time_col = 'Time' if 'Time' in filtered_messages.columns else None
        ordered_messages = filtered_messages
        if time_col:
            try:
                ordered_messages = filtered_messages.sort_values(time_col)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Could not sort messages for signature: %s", exc)

        latest_row = ordered_messages.iloc[-1]
        latest_time_str: Optional[str] = None
        if time_col and pd.notna(latest_row.get(time_col)):
            try:
                latest_time = pd.to_datetime(latest_row[time_col], utc=True)
                latest_time_str = latest_time.isoformat()
            except Exception as exc:  # noqa: BLE001
                logger.debug("Could not normalize latest message time: %s", exc)
                latest_time_str = str(latest_row.get(time_col))

        latest_message = latest_row.get('Message')
        latest_message_str = str(latest_message) if pd.notna(latest_message) else None

        focused_key = (focused_driver or "").upper() or None

        return (
            session_key,
            int(len(filtered_messages)),
            latest_time_str,
            latest_message_str,
            focused_key,
            current_lap,
        )

    def render(
        self,
        session_key: Optional[int],
        simulation_time: Optional[float],
        session_start_time: Optional[pd.Timestamp],
        focused_driver: Optional[str] = None,
        current_lap: Optional[int] = None
    ):
        """Render the Race Control dashboard card."""

        if session_key is None:
            return self._render_no_session()

        messages, drivers = self._get_messages_and_drivers(session_key)
        if messages is None or messages.empty:
            return self._render_no_data()

        filtered_messages = self._filter_messages_by_time(
            messages,
            simulation_time,
            session_start_time
        )
        if filtered_messages.empty:
            filtered_messages = messages.tail(50)

        lap_value = current_lap
        if lap_value is None:
            lap_value = self._calculate_current_lap_from_data(
                session_key,
                simulation_time,
                session_start_time,
                filtered_messages
            )
            if lap_value <= 0:
                lap_value = 0

        display_lap = lap_value or 0

        flag_state, sc_detail = self._extract_current_status(
            filtered_messages,
            current_lap=display_lap if display_lap > 0 else None
        )

        status_card = self._create_status_panel(
            flag_state,
            sc_detail,
            display_lap
        )
        timeline_component = self._create_messages_timeline(
            filtered_messages,
            focused_driver=focused_driver,
            drivers=drivers
        )

        def build_summary_placeholder(message: str) -> dbc.Card:
            return dbc.Card(
                dbc.CardBody(
                    html.Div(
                        message,
                        className="text-muted small text-center py-4"
                    ),
                    className="p-2",
                    style={"backgroundColor": "#1e1e1e"}
                ),
                className="border border-secondary",
                style={"minHeight": "350px"}
            )

        summary_card: Any
        if (
            simulation_time is not None
            and session_start_time is not None
        ):
            summary_data = self.get_status_summary(
                session_key=session_key,
                simulation_time=simulation_time,
                session_start_time=session_start_time,
                current_lap=display_lap
            )
            if isinstance(summary_data, dict) and not summary_data.get('error'):
                summary_card = self._create_summary_panel(summary_data)
            else:
                summary_card = build_summary_placeholder("Summary unavailable.")
        else:
            summary_card = build_summary_placeholder("Waiting for timing data.")

        hidden_summary = html.Div(
            summary_card,
            style={"display": "none"},
            id="race-control-summary-hidden"
        )

        content_layout = html.Div(
            [
                status_card,
                dbc.Row(
                    [
                        dbc.Col(timeline_component, md=12)
                    ],
                    className="g-2"
                ),
                hidden_summary,
            ],
            className="d-flex flex-column gap-2"
        )

        return dbc.Card(
            [
                dbc.CardHeader(
                    html.H5(
                        "🚦 Race Control",
                        className="mb-0",
                        style={"fontSize": "1.2rem"}
                    ),
                    className="py-1",
                    style={"backgroundColor": "#1e1e1e"}
                ),
                dbc.CardBody(
                    content_layout,
                    className="p-2",
                    style={"backgroundColor": "#121212"}
                )
            ],
            className="mb-3 border border-secondary",
            style={"minHeight": "620px", "backgroundColor": "#121212"}
        )
