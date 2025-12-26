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

logger = logging.getLogger(__name__)


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
        focused_driver: Optional[str] = None
    ):
        """
        Render the Race Control Dashboard with real-time messages.

        Args:
            session_key: OpenF1 session key
            simulation_time: Current simulation time in seconds from session start
            session_start_time: Session start timestamp
            focused_driver: Driver number being tracked (for highlighting)

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
            current_lap = self._extract_current_lap(filtered_messages)
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
            ], className="mb-3", style={"height": "620px", "overflow": "auto"})

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
        
        if focused_driver and drivers is not None and not drivers.empty:
            try:
                # Column names after normalization in openf1_data_provider
                # DriverNumber, Abbreviation, DriverName, TeamName, TeamColor
                
                # Try to find driver by number or code
                driver_match = None
                
                # Check if columns exist
                has_driver_number = 'DriverNumber' in drivers.columns or 'driver_number' in drivers.columns
                has_abbreviation = 'Abbreviation' in drivers.columns or 'name_acronym' in drivers.columns
                
                if has_driver_number and has_abbreviation:
                    number_col = 'DriverNumber' if 'DriverNumber' in drivers.columns else 'driver_number'
                    abbr_col = 'Abbreviation' if 'Abbreviation' in drivers.columns else 'name_acronym'
                    
                    driver_match = drivers[
                        (drivers[number_col].astype(str) == str(focused_driver)) |
                        (drivers[abbr_col] == focused_driver.upper())
                    ]
                elif has_driver_number:
                    number_col = 'DriverNumber' if 'DriverNumber' in drivers.columns else 'driver_number'
                    driver_match = drivers[drivers[number_col].astype(str) == str(focused_driver)]
                elif has_abbreviation:
                    abbr_col = 'Abbreviation' if 'Abbreviation' in drivers.columns else 'name_acronym'
                    driver_match = drivers[drivers[abbr_col] == focused_driver.upper()]
                
                if driver_match is not None and not driver_match.empty:
                    driver_info = driver_match.iloc[0]
                    
                    # Get driver details with fallbacks
                    driver_number = str(driver_info.get('DriverNumber', driver_info.get('driver_number', '')))
                    driver_code = driver_info.get('Abbreviation', driver_info.get('name_acronym', ''))
                    driver_full_name = driver_info.get('DriverName', driver_info.get('full_name', ''))
                    
                    # Extract last name from full name if available
                    if driver_full_name and ' ' in driver_full_name:
                        driver_last_name = driver_full_name.split()[-1]
                    elif 'last_name' in driver_info:
                        driver_last_name = driver_info.get('last_name', '')
                    
                    logger.info(
                        f"Focused driver detected: {driver_code} (#{driver_number}) - {driver_full_name}"
                    )
            except Exception as e:
                logger.warning(f"Error processing focused driver info: {e}")

        # Classify and format messages
        message_rows = []
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
                message_upper = message_text.upper()
                
                # Build comprehensive list of search patterns (all uppercase)
                search_patterns = []
                
                if driver_number:
                    search_patterns.extend([
                        f"CAR {driver_number}",
                        f"NO {driver_number}",
                        f"NO. {driver_number}",
                        f"#{driver_number}",
                        f" {driver_number} ",
                        f"({driver_number})"
                    ])
                
                if driver_code:
                    search_patterns.extend([
                        driver_code.upper(),
                        f" {driver_code.upper()} ",
                        f"({driver_code.upper()})"
                    ])
                
                if driver_last_name:
                    search_patterns.extend([
                        driver_last_name.upper(),
                        f" {driver_last_name.upper()} "
                    ])
                
                if driver_full_name:
                    search_patterns.append(driver_full_name.upper())
                
                # Log patterns for debugging
                logger.debug(f"Searching for patterns: {search_patterns} in message: {message_text}")
                
                # Check if any pattern matches
                is_focused_driver = any(
                    pattern in message_upper
                    for pattern in search_patterns
                )
                
                if is_focused_driver:
                    logger.info(f"Message matches focused driver: {message_text}")

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
