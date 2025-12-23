"""
Live Leaderboard Dashboard - Real-time Race Position Tracking.

Uses OpenF1 APIs for live position updates, intervals, tire strategy,
and overtaking information.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

import pandas as pd
import dash_bootstrap_components as dbc
from dash import html, dcc, callback, Input, Output, State
from dash.exceptions import PreventUpdate

from src.data.openf1_data_provider import OpenF1DataProvider

logger = logging.getLogger(__name__)

# Team colors for visual styling (official F1 2024 colors)
TEAM_COLORS = {
    "Red Bull Racing": "#3671C6",
    "Ferrari": "#E8002D",
    "Mercedes": "#27F4D2",
    "McLaren": "#FF8000",
    "Aston Martin": "#229971",
    "Alpine": "#FF87BC",
    "Williams": "#64C4FF",
    "RB": "#6692FF",
    "Kick Sauber": "#52E252",
    "Haas F1 Team": "#B6BABD",
}

# Tire compound colors
TIRE_COLORS = {
    "SOFT": "#FF0000",
    "MEDIUM": "#FFF200",
    "HARD": "#FFFFFF",
    "INTERMEDIATE": "#00FF00",
    "WET": "#0000FF",
}


class LiveLeaderboardDashboard:
    """
    Live leaderboard dashboard with real-time position tracking.
    """

    def __init__(self, provider: OpenF1DataProvider):
        """
        Initialize live leaderboard dashboard.

        Args:
            provider: OpenF1 data provider for API calls
        """
        self.provider = provider
        self.current_session_key: Optional[int] = None

    def create_layout(self) -> dbc.Container:
        """
        Create dashboard layout with auto-refresh capability.

        Returns:
            Dashboard layout container
        """
        return dbc.Container([
            # Header section
            dbc.Row([
                dbc.Col([
                    html.H2(
                        "🏁 Live Leaderboard",
                        className="text-center mb-3"
                    ),
                    html.P(
                        "Real-time race positions and intervals",
                        className="text-center text-muted mb-4"
                    ),
                ], width=12)
            ]),

            # Session selector
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("Session Selection"),
                            dbc.Row([
                                dbc.Col([
                                    dbc.Label("Year"),
                                    dcc.Dropdown(
                                        id="leaderboard-year",
                                        options=[
                                            {"label": "2024", "value": 2024},
                                            {"label": "2023", "value": 2023}
                                        ],
                                        value=2024,
                                        clearable=False
                                    )
                                ], width=3),
                                dbc.Col([
                                    dbc.Label("Meeting"),
                                    dcc.Dropdown(
                                        id="leaderboard-meeting",
                                        placeholder="Select meeting...",
                                    )
                                ], width=6),
                                dbc.Col([
                                    dbc.Label("Session"),
                                    dcc.Dropdown(
                                        id="leaderboard-session",
                                        placeholder="Select session...",
                                    )
                                ], width=3),
                            ]),
                            dbc.Row([
                                dbc.Col([
                                    dbc.Button(
                                        "Load Session",
                                        id="load-session-btn",
                                        color="primary",
                                        className="mt-3"
                                    )
                                ])
                            ])
                        ])
                    ], className="mb-4")
                ], width=12)
            ]),

            # Auto-refresh control
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    html.Span("🔄 Auto-refresh: ", className="me-2"),
                                    dbc.Switch(
                                        id="auto-refresh-switch",
                                        value=False,
                                        label="Enabled"
                                    ),
                                ], width=3),
                                dbc.Col([
                                    html.Span("Refresh every: ", className="me-2"),
                                    dcc.Slider(
                                        id="refresh-interval-slider",
                                        min=1,
                                        max=10,
                                        step=1,
                                        value=2,
                                        marks={i: f"{i}s" for i in range(1, 11)},
                                    )
                                ], width=6),
                                dbc.Col([
                                    html.Div(
                                        id="last-update-time",
                                        className="text-muted text-end"
                                    )
                                ], width=3)
                            ])
                        ])
                    ], className="mb-4")
                ], width=12)
            ]),

            # Interval component for auto-refresh
            dcc.Interval(
                id='leaderboard-interval',
                interval=2000,  # 2 seconds default
                n_intervals=0,
                disabled=True
            ),

            # Session info banner
            dbc.Row([
                dbc.Col([
                    html.Div(id="session-info-banner")
                ], width=12)
            ]),

            # Main leaderboard table
            dbc.Row([
                dbc.Col([
                    html.Div(id="leaderboard-table")
                ], width=12)
            ], className="mb-4"),

            # Additional info cards
            dbc.Row([
                dbc.Col([
                    html.Div(id="recent-overtakes-card")
                ], width=6),
                dbc.Col([
                    html.Div(id="race-control-alerts-card")
                ], width=6)
            ])

        ], fluid=True)

    def setup_callbacks(self, app):
        """
        Set up dashboard callbacks.

        Args:
            app: Dash app instance
        """

        @callback(
            Output("leaderboard-meeting", "options"),
            Input("leaderboard-year", "value")
        )
        def update_meetings(year: int):
            """Load meetings for selected year."""
            if not year:
                return []

            try:
                meetings = self.provider.get_meetings(year=year)
                if meetings.empty:
                    return []

                options = []
                for _, meeting in meetings.iterrows():
                    label = f"{meeting.get('Country', 'Unknown')} - {meeting.get('Location', 'Unknown')}"
                    value = int(meeting.get('MeetingKey', 0))
                    options.append({"label": label, "value": value})

                return options
            except Exception as e:
                logger.error(f"Error loading meetings: {e}")
                return []

        @callback(
            Output("leaderboard-session", "options"),
            Input("leaderboard-meeting", "value")
        )
        def update_sessions(meeting_key: int):
            """Load sessions for selected meeting."""
            if not meeting_key:
                return []

            try:
                # Use _request directly to query by meeting_key
                sessions_data = self.provider._request(
                    "sessions", {"meeting_key": meeting_key}
                )
                if not sessions_data:
                    return []

                options = []
                for session in sessions_data:
                    label = session.get('session_name', 'Unknown')
                    value = int(session.get('session_key', 0))
                    options.append({"label": label, "value": value})

                return options
            except Exception as e:
                logger.error(f"Error loading sessions: {e}")
                return []

        @callback(
            Output("leaderboard-interval", "interval"),
            Output("leaderboard-interval", "disabled"),
            Input("auto-refresh-switch", "value"),
            Input("refresh-interval-slider", "value")
        )
        def control_auto_refresh(enabled: bool, interval_seconds: int):
            """Control auto-refresh interval."""
            interval_ms = interval_seconds * 1000
            disabled = not enabled
            return interval_ms, disabled

        @callback(
            Output("session-info-banner", "children"),
            Output("leaderboard-table", "children"),
            Output("recent-overtakes-card", "children"),
            Output("race-control-alerts-card", "children"),
            Output("last-update-time", "children"),
            Input("load-session-btn", "n_clicks"),
            Input("leaderboard-interval", "n_intervals"),
            State("leaderboard-session", "value"),
            prevent_initial_call=True
        )
        def update_leaderboard(n_clicks, n_intervals, session_key: int):
            """Update all leaderboard components."""
            if not session_key:
                raise PreventUpdate

            # Store session key
            self.current_session_key = session_key

            try:
                # Get latest data
                positions = self._get_latest_positions(session_key)
                intervals = self._get_latest_intervals(session_key)
                stints = self._get_current_stints(session_key)
                overtakes = self._get_recent_overtakes(session_key)
                race_control = self._get_race_control_messages(session_key)

                # Build components
                session_banner = self._build_session_banner(session_key)
                leaderboard = self._build_leaderboard_table(
                    positions, intervals, stints
                )
                overtakes_card = self._build_overtakes_card(overtakes)
                race_control_card = self._build_race_control_card(race_control)

                # Update timestamp
                update_time = f"Last updated: {datetime.now().strftime('%H:%M:%S')}"

                return session_banner, leaderboard, overtakes_card, race_control_card, update_time

            except Exception as e:
                logger.error(f"Error updating leaderboard: {e}")
                error_msg = html.Div(
                    f"Error loading data: {str(e)}",
                    className="alert alert-danger"
                )
                return error_msg, None, None, None, ""

    def _get_latest_positions(self, session_key: int) -> pd.DataFrame:
        """Get latest position data."""
        # Get most recent positions
        positions = self.provider.get_positions(session_key=session_key)
        if positions.empty:
            return positions

        # Get latest date
        latest_date = positions['Timestamp'].max()
        return positions[positions['Timestamp'] == latest_date].sort_values('Position')

    def _get_latest_intervals(self, session_key: int) -> pd.DataFrame:
        """Get latest interval data."""
        intervals = self.provider.get_intervals(session_key=session_key)
        if intervals.empty:
            return intervals

        latest_date = intervals['Timestamp'].max()
        return intervals[intervals['Timestamp'] == latest_date]

    def _get_current_stints(self, session_key: int) -> pd.DataFrame:
        """Get current tire stint information."""
        stints = self.provider.get_stints(session_key=session_key)
        if stints.empty:
            return stints

        # Get most recent stint for each driver
        return stints.sort_values('StintNumber').groupby('DriverNumber').tail(1)

    def _get_recent_overtakes(self, session_key: int, limit: int = 10) -> pd.DataFrame:
        """Get recent overtaking moves."""
        overtakes = self.provider.get_overtakes(session_key=session_key)
        if overtakes.empty:
            return overtakes

        return overtakes.sort_values('Timestamp', ascending=False).head(limit)

    def _get_race_control_messages(
        self, session_key: int, limit: int = 10
    ) -> pd.DataFrame:
        """Get recent race control messages."""
        messages = self.provider.get_race_control_messages(session_key=session_key)
        if messages.empty:
            return messages

        return messages.sort_values('Time', ascending=False).head(limit)

    def _build_session_banner(self, session_key: int) -> dbc.Alert:
        """Build session information banner."""
        try:
            # Use _request directly to query by session_key
            sessions_data = self.provider._request(
                "sessions", {"session_key": session_key}
            )
            if not sessions_data or len(sessions_data) == 0:
                return dbc.Alert("Session information unavailable", color="warning")

            session = sessions_data[0]
            banner_text = (
                f"📍 {session.get('circuit_short_name', 'Unknown')} | "
                f"🏁 {session.get('session_name', 'Unknown')} | "
                f"📅 {session.get('StartDate', 'Unknown')}"
            )

            return dbc.Alert(banner_text, color="info", className="mb-3")
        except Exception as e:
            logger.error(f"Error building session banner: {e}")
            return dbc.Alert("Session info error", color="warning")

    def _build_leaderboard_table(
        self,
        positions: pd.DataFrame,
        intervals: pd.DataFrame,
        stints: pd.DataFrame
    ) -> dbc.Card:
        """Build main leaderboard table."""
        if positions.empty:
            return dbc.Card([
                dbc.CardBody([
                    html.P("No position data available", className="text-center text-muted")
                ])
            ])

        # Merge data
        leaderboard = positions.copy()

        # Add intervals
        if not intervals.empty:
            intervals_dict = intervals.set_index('DriverNumber')['GapToLeader'].to_dict()
            leaderboard['GapToLeader'] = leaderboard['DriverNumber'].map(
                intervals_dict
            ).fillna("-")

        # Add tire info
        if not stints.empty:
            tire_dict = stints.set_index('DriverNumber')['Compound'].to_dict()
            stint_lap_dict = stints.set_index('DriverNumber')['TyreAge'].to_dict()
            leaderboard['TireCompound'] = leaderboard['DriverNumber'].map(tire_dict).fillna("UNKNOWN")
            leaderboard['StintLaps'] = leaderboard['DriverNumber'].map(stint_lap_dict).fillna(0)

        # Build table rows
        table_rows = []
        for _, row in leaderboard.iterrows():
            position = int(row.get('Position', 0))
            driver_number = int(row.get('DriverNumber', 0))
            
            # Get driver name (from driver info if available)
            driver_name = f"#{driver_number}"
            
            gap = row.get('GapToLeader', '-')
            if isinstance(gap, (int, float)):
                gap = f"+{gap:.3f}s"
            
            tire = row.get('TireCompound', 'UNKNOWN')
            stint_laps = int(row.get('StintLaps', 0))
            
            # Position change indicator (placeholder)
            position_change = ""  # Could calculate from previous data
            
            # Tire badge
            tire_color = TIRE_COLORS.get(tire, "#999999")
            tire_badge = html.Span(
                tire[0] if tire else "?",
                style={
                    "backgroundColor": tire_color,
                    "color": "black" if tire in ["MEDIUM", "HARD"] else "white",
                    "padding": "2px 8px",
                    "borderRadius": "4px",
                    "fontWeight": "bold",
                    "fontSize": "12px"
                }
            )
            
            table_rows.append(
                html.Tr([
                    html.Td(position, style={"fontWeight": "bold", "width": "50px"}),
                    html.Td(position_change, style={"width": "30px"}),
                    html.Td(driver_name, style={"fontWeight": "bold"}),
                    html.Td(gap, style={"fontFamily": "monospace"}),
                    html.Td([tire_badge, f" {stint_laps} laps"]),
                ])
            )

        table = dbc.Table(
            [
                html.Thead(
                    html.Tr([
                        html.Th("Pos"),
                        html.Th(""),
                        html.Th("Driver"),
                        html.Th("Gap"),
                        html.Th("Tire"),
                    ])
                ),
                html.Tbody(table_rows)
            ],
            bordered=True,
            hover=True,
            responsive=True,
            striped=True,
            className="leaderboard-table"
        )

        return dbc.Card([
            dbc.CardHeader(html.H4("Race Positions")),
            dbc.CardBody(table)
        ])

    def _build_overtakes_card(self, overtakes: pd.DataFrame) -> dbc.Card:
        """Build recent overtakes card."""
        if overtakes.empty:
            return dbc.Card([
                dbc.CardHeader(html.H5("🏎️ Recent Overtakes")),
                dbc.CardBody([
                    html.P("No overtakes data available", className="text-muted")
                ])
            ])

        overtake_items = []
        for _, overtake in overtakes.iterrows():
            overtaking = overtake.get('OvertakingDriverNumber', '?')
            overtaken = overtake.get('OvertakenDriverNumber', '?')
            
            overtake_items.append(
                dbc.ListGroupItem([
                    html.Span(f"#{overtaking}", style={"fontWeight": "bold", "color": "#00FF00"}),
                    html.Span(" overtook ", className="text-muted"),
                    html.Span(f"#{overtaken}", style={"fontWeight": "bold", "color": "#FF0000"}),
                ])
            )

        return dbc.Card([
            dbc.CardHeader(html.H5("🏎️ Recent Overtakes")),
            dbc.CardBody([
                dbc.ListGroup(overtake_items, flush=True)
            ])
        ])

    def _build_race_control_card(self, messages: pd.DataFrame) -> dbc.Card:
        """Build race control messages card."""
        if messages.empty:
            return dbc.Card([
                dbc.CardHeader(html.H5("🚩 Race Control")),
                dbc.CardBody([
                    html.P("No race control messages", className="text-muted")
                ])
            ])

        message_items = []
        for _, msg in messages.iterrows():
            category = msg.get('Category', 'Other')
            message = msg.get('Message', 'No message')
            flag = msg.get('Flag', '')
            
            # Color code by category
            badge_color = {
                'Flag': 'warning',
                'SafetyCar': 'danger',
                'CarEvent': 'info',
                'Drs': 'success'
            }.get(category, 'secondary')
            
            message_items.append(
                dbc.ListGroupItem([
                    dbc.Badge(category, color=badge_color, className="me-2"),
                    html.Span(message, className="small"),
                    html.Span(f" {flag}", className="ms-2") if flag else ""
                ])
            )

        return dbc.Card([
            dbc.CardHeader(html.H5("🚩 Race Control")),
            dbc.CardBody([
                dbc.ListGroup(message_items, flush=True)
            ])
        ])
