"""
F1 Strategist AI - Main Dash Application.

Multi-dashboard F1 strategy platform with live and simulation modes.
Migrated from Streamlit to Dash for better layout control.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from dash import Dash, html, dcc, Input, Output, State, callback, ctx, Patch
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd

# OpenF1 data provider (replaces FastF1)
from src.data.openf1_adapter import get_session as get_openf1_session, SessionAdapter
from src.data.openf1_data_provider import OpenF1DataProvider

# Core infrastructure (reused from Streamlit version)
from src.agents.orchestrator import AgentOrchestrator
from src.session.global_session import (
    GlobalSession,
    RaceContext,
    SessionMode,
    SessionType,
)
from src.session.simulation_controller import SimulationController
from src.session.live_detector import check_for_live_session

# Dash dashboards
from src.dashboards_dash.ai_assistant_dashboard import AIAssistantDashboard
from src.dashboards_dash.race_overview_dashboard import RaceOverviewDashboard
from src.dashboards_dash.live_leaderboard_dashboard import (
    LiveLeaderboardDashboard
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize OpenF1 provider (replaces FastF1)
openf1_provider = OpenF1DataProvider()

# Initialize Live Leaderboard Dashboard
leaderboard_dashboard = LiveLeaderboardDashboard(openf1_provider)

# Initialize Dash app with F1 theme
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG],
    suppress_callback_exceptions=True,
    title="F1 Strategist AI",
    # Development settings to avoid asset loading issues
    compress=False,
    serve_locally=True
)

server = app.server
server.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable caching
server.config['TEMPLATES_AUTO_RELOAD'] = True

# Global session (singleton pattern maintained)
session = GlobalSession()

# Simulation controller (initialized with dummy times, will be updated)
simulation_controller: Optional[SimulationController] = None

# Current loaded session object (for circuit map and other dashboards)
current_session_obj = None


def get_last_completed_race() -> RaceContext:
    """
    Get the most recent completed race.
    Returns Abu Dhabi GP 2025 (last race of season).
    """
    return RaceContext(
        year=2025,
        round_number=24,
        circuit_name="Yas Marina Circuit",
        circuit_key="abu_dhabi",
        country="United Arab Emirates",
        session_type=SessionType.RACE,
        session_date=datetime(2025, 12, 8, 15, 0),
        total_laps=57,
        current_lap=1
    )


def load_f1_calendar(year: int) -> pd.DataFrame:
    """
    Load F1 calendar for specified year using OpenF1 data.
    Note: OpenF1 provides data from 2023 onwards.
    """
    # OpenF1 doesn't have a calendar endpoint, so we'll build from sessions
    # For now, return a simple structure for 2025 season
    if year < 2023:
        logger.warning(f"OpenF1 data not available for year {year}. Use 2023-2025.")
        return pd.DataFrame()
    
    try:
        # Get all sessions for the year to build calendar
        sessions_params = {"year": year}
        all_sessions = openf1_provider._request("sessions", sessions_params)
        
        if not all_sessions:
            logger.warning(f"No sessions found for year {year}")
            return pd.DataFrame()
        
        # Group by race (meeting_key or location)
        df = pd.DataFrame(all_sessions)
        
        # Use meeting_key to group races (each meeting has multiple sessions)
        calendar = df.groupby("meeting_key").agg({
            "country_name": "first",
            "location": "first",
            "date_start": "first",
            "year": "first",
            "circuit_short_name": "first"
        }).reset_index()
        
        # Add round number based on date order
        calendar = calendar.sort_values("date_start")
        calendar["RoundNumber"] = range(1, len(calendar) + 1)
        
        # Create event name from country and location
        calendar["EventName"] = calendar["country_name"].astype(str) + " Grand Prix"
        
        calendar = calendar.rename(columns={
            "country_name": "Country",
            "location": "Location",
            "date_start": "EventDate",
            "meeting_key": "MeetingKey",
            "circuit_short_name": "CircuitShortName"
        })
        
        logger.info(f"Loaded {len(calendar)} races for {year}")
        return calendar
        
    except Exception as e:
        logger.error(f"Error loading calendar for {year}: {e}")
        return pd.DataFrame()


def get_available_sessions(
    schedule: pd.DataFrame,
    round_number: int
) -> list[tuple[str, SessionType]]:
    """Get available sessions for a specific race."""
    event = schedule[schedule['RoundNumber'] == round_number].iloc[0]
    
    sessions = []
    
    # Check each session column in the event
    for i in range(1, 6):
        col = f'Session{i}'
        session_value = event.get(col)
        
        if pd.notna(session_value):
            session_str = str(session_value)
            
            # Determine session name and type based on content
            if 'Practice 1' in session_str or session_str == 'Practice 1':
                sessions.append(('FP1', SessionType.FP1))
            elif 'Practice 2' in session_str or session_str == 'Practice 2':
                sessions.append(('FP2', SessionType.FP2))
            elif 'Practice 3' in session_str or session_str == 'Practice 3':
                sessions.append(('FP3', SessionType.FP3))
            elif 'Sprint Shootout' in session_str or 'Sprint Qualifying' in session_str:
                sessions.append(('Sprint Qualifying', SessionType.SPRINT_QUALIFYING))
            elif 'Sprint' in session_str and 'Qualifying' not in session_str and 'Shootout' not in session_str:
                sessions.append(('Sprint', SessionType.SPRINT))
            elif 'Qualifying' in session_str:
                sessions.append(('Qualifying', SessionType.QUALIFYING))
            elif 'Race' in session_str:
                sessions.append(('Race', SessionType.RACE))
    
    return sessions


# ============================================================================
# SIDEBAR COMPONENT
# ============================================================================

def create_sidebar():
    """Create sidebar with all controls."""
    return dbc.Col([
        html.Div([
            html.H4("🏎️ F1 Strategist", className="text-center mb-3"),
            
            html.Hr(),
            
            # Mode selector
            html.H6("🎮 Mode", className="mb-2"),
            dbc.RadioItems(
                id="mode-selector",
                options=[
                    {"label": " 🏁 Live", "value": "live"},
                    {"label": " ⏯️ Simulation", "value": "sim"}
                ],
                value="sim",
                className="mb-3"
            ),
            
            html.Hr(),
            
            # Context selector (collapsed)
            dbc.Accordion([
                dbc.AccordionItem([
                    dbc.Label("**Year**", className="fw-bold"),
                    dcc.Dropdown(
                        id='year-selector',
                        options=[
                            {'label': str(y), 'value': y} 
                            for y in range(2025, 2017, -1)
                        ],
                        value=2025,
                        className="mb-3",
                        clearable=False
                    ),
                    
                    dbc.Label("**Circuit**", className="fw-bold"),
                    dcc.Dropdown(
                        id='circuit-selector',
                        options=[],  # Will be populated by callback
                        value=None,
                        className="mb-3",
                        clearable=False
                    ),
                    
                    dbc.Label("**Session**", className="fw-bold"),
                    dcc.Dropdown(
                        id='session-selector',
                        options=[],  # Will be populated by callback
                        value=None,
                        className="mb-3",
                        clearable=False
                    ),
                    
                    dbc.Label("**Driver**", className="fw-bold"),
                    html.Div(id='driver-dropdown-container', children=[
                        dcc.Loading(
                            dcc.Dropdown(
                                id='driver-selector',
                                options=[],
                                value=None,
                                placeholder="Loading drivers...",
                                className="mb-2",
                                clearable=True
                            ),
                            type="circle",
                            color="#e10600"
                        )
                    ])
                ], title="📍 Context", className="mb-3")
            ], start_collapsed=True),
            
            html.Hr(),
            
            # Dashboard selector
            html.H6("📊 Dashboards", className="mb-2"),
            dbc.Checklist(
                id="dashboard-selector",
                options=[
                    {"label": " Race Overview", "value": "race_overview"},
                    {"label": " Live Leaderboard", "value": "live_leaderboard"},
                    {"label": " Telemetry", "value": "telemetry"},
                    {"label": " Tire Strategy", "value": "tires"},
                    {"label": " Weather", "value": "weather"},
                    {"label": " Lap Analysis", "value": "laps"},
                    {"label": " Race Control", "value": "control"},
                    {"label": " Qualifying", "value": "qualifying"},
                    {"label": " AI Assistant", "value": "ai"}
                ],
                value=["race_overview", "ai"],
                className="mb-3"
            ),
            
            html.Hr(),
            
            # Simulation controls (collapsed)
            dbc.Accordion([
                dbc.AccordionItem([
                    dbc.Row([
                        dbc.Col([
                            dbc.Button(
                                "▶️",
                                id="play-btn",
                                color="success",
                                className="w-100 mb-2"
                            ),
                            dbc.Tooltip(
                                "Play simulation",
                                target="play-btn",
                                placement="top",
                                id="play-btn-tooltip"
                            )
                        ], width=6),
                        dbc.Col([
                            dbc.Button(
                                "⏮️",
                                id="restart-btn",
                                color="secondary",
                                className="w-100 mb-2"
                            ),
                            dbc.Tooltip("Restart simulation", target="restart-btn", placement="top")
                        ], width=6)
                    ]),
                    
                    dbc.Label("Speed", className="mt-2"),
                    dcc.Slider(
                        id='speed-slider',
                        min=1.0,
                        max=5.0,
                        step=0.25,
                        value=1.0,
                        marks={
                            1.0: '1x',
                            2.0: '2x',
                            3.0: '3x',
                            4.0: '4x',
                            5.0: '5x'
                        },
                        className="mb-3"
                    ),
                    
                    dbc.Row([
                        dbc.Col([
                            dbc.Button(
                                "⏪",
                                id="back-btn",
                                color="secondary",
                                className="w-100"
                            ),
                            dbc.Tooltip("Previous lap", target="back-btn", placement="bottom")
                        ], width=6),
                        dbc.Col([
                            dbc.Button(
                                "⏩",
                                id="forward-btn",
                                color="secondary",
                                className="w-100"
                            ),
                            dbc.Tooltip("Next lap", target="forward-btn", placement="bottom")
                        ], width=6)
                    ]),
                    
                    html.Div(
                        id="simulation-progress",
                        children="⏱️ Not started",
                        className="text-center mt-3 small text-muted"
                    ),
                    
                    # Interval for updating simulation progress (3 seconds)
                    dcc.Interval(
                        id='simulation-interval',
                        interval=3000,  # milliseconds (every 3 seconds)
                        n_intervals=0,
                        disabled=True  # Start disabled, enable when playing
                    )
                ], title="⏯️ Playback", className="mb-3", id="playback-accordion-item")
            ], start_collapsed=True, id="playback-accordion"),
            
            html.Hr(),
            
            # Menu (collapsed)
            dbc.Accordion([
                dbc.AccordionItem([
                    # Config option
                    html.Div([
                        html.H6("⚙️ Configuration", className="mb-3"),
                        
                        # API Keys
                        html.Div([
                            html.P("🔑 API Keys", className="fw-bold mb-2"),
                            dbc.Label("Claude API Key", className="small"),
                            dbc.Input(
                                id='claude-api-key-input',
                                type="password",
                                placeholder="Enter Anthropic Claude API Key",
                                value=os.getenv("ANTHROPIC_API_KEY", ""),
                                className="mb-2",
                                style={'fontSize': '0.85rem'}
                            ),
                            dbc.Label("Gemini API Key", className="small"),
                            dbc.Input(
                                id='gemini-api-key-input',
                                type="password",
                                placeholder="Enter Google Gemini API Key",
                                value=os.getenv("GOOGLE_API_KEY", ""),
                                className="mb-2",
                                style={'fontSize': '0.85rem'}
                            ),
                            dbc.Label("OpenF1 API Key", className="small"),
                            dbc.Input(
                                id='openf1-api-key-input',
                                type="password",
                                placeholder="Enter OpenF1 API Key",
                                value=os.getenv("OPENF1_API_KEY", ""),
                                className="mb-2",
                                style={'fontSize': '0.85rem'}
                            ),
                            dbc.Button(
                                "💾 Save Keys",
                                id="save-api-keys-btn",
                                color="primary",
                                size="sm",
                                className="w-100 mb-2"
                            ),
                            html.Div(id="api-keys-save-status", className="small text-muted")
                        ], className="mb-3"),
                        
                        # LLM Settings
                        html.Div([
                            html.P("🤖 LLM Settings", className="fw-bold mb-2"),
                            dbc.Label("Provider", className="small"),
                            dcc.Dropdown(
                                id='llm-provider-selector',
                                options=[
                                    {'label': 'Hybrid (Auto)', 'value': 'hybrid'},
                                    {'label': 'Claude Only', 'value': 'claude'},
                                    {'label': 'Gemini Only', 'value': 'gemini'}
                                ],
                                value='hybrid',
                                className="mb-2",
                                clearable=False,
                                style={'fontSize': '0.85rem'}
                            )
                        ], className="mb-3"),
                        
                        # Data Sources
                        html.Div([
                            html.P("📂 Data Sources", className="fw-bold mb-2"),
                            html.Small(f"Cache: ./cache", className="text-muted d-block"),
                            html.Small(f"Vector Store: ChromaDB", className="text-muted d-block")
                        ])
                    ])
                ], title="⚙️ Menu", className="mb-2")
            ], start_collapsed=True),
            
            # Help button
            dbc.Button(
                [html.I(className="bi bi-question-circle me-1"), "Help"],
                id="help-btn",
                color="info",
                outline=True,
                size="sm",
                className="w-100 mb-2"
            ),
            
            dbc.Button(
                [html.I(className="bi bi-trash me-1"), "Clear History"],
                id="clear-history-btn",
                color="danger",
                outline=True,
                size="sm",
                className="w-100"
            )
            
        ], className="p-3", style={
            'height': '100vh',
            'overflow-y': 'auto',
            'background-color': '#1a1a1a'
        })
    ], width=2, id='sidebar-column', className="border-end border-secondary")


# ============================================================================
# MAIN CONTENT AREA
# ============================================================================

def create_main_content():
    """Create main content area with dashboard placeholders."""
    return dbc.Col([
        # Toggle sidebar button
        html.Div([
            dbc.Button(
                "<<",
                id='sidebar-toggle-btn',
                color="dark",
                size="sm",
                className="mb-2",
                style={'position': 'fixed', 'top': '10px', 'left': '10px', 'zIndex': '1000', 'fontSize': '0.7rem', 'fontWeight': 'bold', 'padding': '2px 6px'}
            ),
            dbc.Tooltip(
                "Hide sidebar",
                target="sidebar-toggle-btn",
                placement="right"
            )
        ]),
        html.Div([
            # Dashboard container - will be populated dynamically
            html.Div(id='dashboard-container', children=[
                html.Div([
                    html.H3(
                        "🏎️ F1 Strategist AI",
                        className="text-center mt-5"
                    ),
                    html.P(
                        "Select dashboards from the sidebar to begin",
                        className="text-center text-muted"
                    )
                ], className="text-center")
            ])
        ], className="p-3")
    ], width=10, id='main-content-column')


# ============================================================================
# APP LAYOUT
# ============================================================================

app.layout = dbc.Container([
    # Store components for state management
    dcc.Store(id='session-store', data={}),
    dcc.Store(id='user-prefs-store', data={
        'focused_driver': 'VER',
        'visible_dashboards': ['circuit', 'ai']
    }),
    dcc.Store(id='cache-buster-store', data={'timestamp': 0}),
    dcc.Store(id='sidebar-visible-store', data=True),
    
    # Help Modal
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("❓ Help & Documentation")),
        dbc.ModalBody([
            html.H5("🚀 Quick Start", className="mb-2"),
            html.Ul([
                html.Li("Select Mode: Live or Simulation"),
                html.Li("Set Context: Year, circuit, session, driver"),
                html.Li("Choose Dashboards: Pick which views to display"),
                html.Li("Start Analyzing: Use AI Assistant or explore data")
            ], className="mb-3"),
            
            html.H5("🤖 AI Agents", className="mb-2"),
            html.Ul([
                html.Li("🎯 Strategy Agent: Race/qualifying strategy"),
                html.Li("🌤️ Weather Agent: Meteorological analysis"),
                html.Li("⚡ Performance Agent: Lap times & telemetry"),
                html.Li("🚦 Race Control Agent: Flags & incidents"),
                html.Li("🏁 Position Agent: Gaps & overtakes")
            ], className="mb-3"),
            
            html.H5("ℹ️ About", className="mb-2"),
            html.P([
                html.Strong("F1 Strategist AI v1.0.0"), html.Br(),
                "Multi-agent F1 strategy assistant with real-time analysis.", html.Br(),
                html.Small("Tech: Dash, Claude/Gemini, FastF1, ChromaDB", className="text-muted")
            ])
        ]),
        dbc.ModalFooter(
            dbc.Button("Close", id="close-help-modal", className="ms-auto", n_clicks=0)
        )
    ], id="help-modal", is_open=False, size="lg"),
    
    # Main layout
    dbc.Row([
        create_sidebar(),
        create_main_content()
    ], className="g-0", style={'height': '100vh'})
], fluid=True, className="vh-100 p-0")


# ============================================================================
# CALLBACKS
# ============================================================================

@callback(
    Output('circuit-selector', 'options'),
    Output('circuit-selector', 'value'),
    Input('year-selector', 'value'),
    State('circuit-selector', 'value'),
    prevent_initial_call=False
)
def update_circuits(year, current_circuit):
    """Update circuit dropdown based on selected year."""
    if year is None:
        return [], None
    
    schedule = load_f1_calendar(year)
    if schedule.empty:
        return [], None
    
    circuit_options = []
    circuit_keys = []
    circuit_short_names = {
        'United Arab Emirates': 'Abu Dhabi',
        'United States': 'USA',
        'United Kingdom': 'Britain',
        'Saudi Arabia': 'Saudi',
    }
    
    for _, event in schedule.iterrows():
        country = event['Country']
        location = event['Location']
        round_num = event['RoundNumber']
        meeting_key = event['MeetingKey']
        
        if country == 'United States':
            if 'Miami' in location:
                display_name = "Miami"
            elif 'Austin' in location:
                display_name = "USA (Austin)"
            elif 'Las Vegas' in location:
                display_name = "Las Vegas"
            else:
                display_name = circuit_short_names.get(country, country)
        else:
            display_name = circuit_short_names.get(country, country)
        
        # Use meeting_key as value for OpenF1 API calls
        circuit_keys.append(meeting_key)
        
        circuit_options.append({
            'label': f"R{round_num} - {display_name}",
            'value': meeting_key
        })
    
    # Keep current selection if it exists in new options, otherwise select last race (2025) or first
    if current_circuit and current_circuit in circuit_keys:
        default_value = current_circuit
    else:
        default_value = circuit_options[-1]['value'] if year == 2025 else circuit_options[0]['value']
    
    return circuit_options, default_value


@callback(
    Output('session-selector', 'options'),
    Output('session-selector', 'value'),
    Input('circuit-selector', 'value'),
    Input('year-selector', 'value'),
    State('session-selector', 'value'),
    prevent_initial_call=False
)
def update_sessions(circuit_key, year, current_session):
    """Update session dropdown based on selected circuit (meeting_key from OpenF1)."""
    if not circuit_key or not year:
        return [], None
    
    try:
        # meeting_key is now the circuit_key value from dropdown
        meeting_key = circuit_key
        
        # Get sessions for this meeting from OpenF1
        sessions_params = {"year": year, "meeting_key": meeting_key}
        sessions = openf1_provider._request("sessions", sessions_params)
        
        if not sessions:
            logger.warning(f"No sessions found for meeting_key={meeting_key}, year={year}")
            return [], None
        
        # Create session options from OpenF1 data
        session_map = {
            'Practice 1': 'P1',
            'Practice 2': 'P2',
            'Practice 3': 'P3',
            'Qualifying': 'Q',
            'Sprint': 'S',
            'Sprint Qualifying': 'SQ',
            'Sprint Shootout': 'SS',
            'Race': 'R'
        }
        
        session_options = []
        for session in sessions:
            session_name = session.get('session_name', '')
            session_type = session_map.get(session_name, session_name)
            session_options.append({
                'label': session_name,
                'value': session_type
            })
        
        # Keep current selection if valid, otherwise select last session (Race)
        session_values = [opt['value'] for opt in session_options]
        if current_session and current_session in session_values:
            default_value = current_session
        else:
            default_value = session_options[-1]['value'] if session_options else None
        
        logger.info(f"Found {len(session_options)} sessions for meeting_key={meeting_key}")
        return session_options, default_value
    
    except Exception as e:
        logger.error(f"Error updating sessions: {e}")
        return [], None


import time

@callback(
    Output('driver-dropdown-container', 'children'),
    Input('year-selector', 'value'),
    Input('circuit-selector', 'value'),
    Input('session-selector', 'value'),
    prevent_initial_call=True
)
def clear_driver_dropdown_immediately(year, circuit, session):
    """Clear dropdown immediately when parameters change."""
    return dcc.Loading(
        dcc.Dropdown(
            id='driver-selector',
            options=[],
            value=None,
            placeholder="Loading drivers...",
            className="mb-2",
            clearable=True
        ),
        type="circle",
        color="#e10600"
    )

@callback(
    Output('driver-dropdown-container', 'children', allow_duplicate=True),
    Output('session-store', 'data', allow_duplicate=True),
    Input('session-selector', 'value'),
    Input('circuit-selector', 'value'),
    Input('year-selector', 'value'),
    prevent_initial_call=True
)
def update_drivers(session, circuit_key, year):
    """Recreate driver dropdown with fresh data using OpenF1."""
    if not session or not circuit_key or not year:
        logger.warning(f"Missing parameters: session={session}, circuit_key={circuit_key}, year={year}")
        # Return empty dropdown
        return dcc.Loading(
            dcc.Dropdown(
                id='driver-selector',
                options=[],
                value=None,
                placeholder="Select year, circuit and session...",
                className="mb-2",
                clearable=True
            ),
            type="circle",
            color="#e10600"
        ), {'loaded': False}
    
    # circuit_key is now the meeting_key from OpenF1
    meeting_key = circuit_key
    
    try:
        logger.info(f"Loading drivers for year={year}, meeting_key={meeting_key}, session={session}")
        
        # Get session_key from OpenF1 using meeting_key and session type
        session_map_reverse = {
            'P1': 'Practice 1',
            'P2': 'Practice 2',
            'P3': 'Practice 3',
            'Q': 'Qualifying',
            'S': 'Sprint',
            'SQ': 'Sprint Qualifying',
            'SS': 'Sprint Shootout',
            'R': 'Race'
        }
        
        session_name = session_map_reverse.get(session.upper(), session)
        
        # Get session info from OpenF1
        sessions_params = {"year": year, "meeting_key": meeting_key, "session_name": session_name}
        sessions = openf1_provider._request("sessions", sessions_params)
        
        if not sessions:
            logger.error(f"No session found for meeting_key={meeting_key}, session={session_name}")
            return dcc.Loading(
                dcc.Dropdown(
                    id='driver-selector',
                    options=[],
                    value=None,
                    placeholder="Session not available",
                    className="mb-2",
                    clearable=True
                ),
                type="circle",
                color="#e10600"
            ), {'loaded': False}
        
        session_key = sessions[0].get('session_key')
        
        if not session_key:
            logger.error(f"No session_key found for meeting_key={meeting_key}, session={session_name}")
            return dcc.Loading(
                dcc.Dropdown(
                    id='driver-selector',
                    options=[],
                    value=None,
                    placeholder="Session not available",
                    className="mb-2",
                    clearable=True
                ),
                type="circle",
                color="#e10600"
            ), {'loaded': False}
        
        # Get full session_info
        session_info = sessions[0]
        
        # Load session using SessionAdapter
        logger.info(f"Loading session with session_key={session_key}")
        session_obj = SessionAdapter(
            provider=openf1_provider,
            session_info=session_info,
            session_key=session_key
        )
        
        try:
            session_obj.load()
        except Exception as e:
            logger.error(f"Failed to load session data: {e}")
            return dcc.Loading(
                dcc.Dropdown(
                    id='driver-selector',
                    options=[],
                    value=None,
                    placeholder="Error loading session",
                    className="mb-2",
                    clearable=True
                ),
                type="circle",
                color="#e10600"
            ), {'loaded': False}
        
        # Store session_obj globally for use in dashboards
        global current_session_obj
        current_session_obj = session_obj
        
        # Initialize simulation controller with session times
        global simulation_controller
        try:
            # Get session date/time information
            session_date = session_obj.date  # This is the event date
            
            # Get lap times to determine session duration
            laps = session_obj.laps
            if not laps.empty and 'LapEndTime_seconds' in laps.columns:
                # Get first and last lap end times
                first_lap_end = laps['LapEndTime_seconds'].min()
                last_lap_end = laps['LapEndTime_seconds'].max()
                
                # Convert seconds to timedelta and add to session date
                if pd.notna(first_lap_end) and pd.notna(last_lap_end):
                    # Start simulation FROM first lap completion time
                    start_time = session_date + timedelta(seconds=float(first_lap_end))
                    end_time = session_date + timedelta(seconds=float(last_lap_end))
                    
                    # Create controller - simulation starts at first lap
                    simulation_controller = SimulationController(start_time, end_time)
                    simulation_controller.pause()  # Start paused
                    
                    logger.info(
                        f"SimulationController initialized: {start_time} -> {end_time} "
                        f"(first lap at {first_lap_end:.1f}s, last lap at {last_lap_end:.1f}s)"
                    )
                else:
                    logger.warning("Could not extract lap times for simulation")
            else:
                logger.warning("No lap data available for simulation controller")
        except Exception as e:
            logger.error(f"Failed to initialize SimulationController: {e}")
        
        drivers = session_obj.drivers
        results = session_obj.results
        
        logger.info(f"Loaded {len(drivers)} drivers from session")
        
        driver_options = []
        
        # Iterate over results DataFrame to get driver info
        for _, driver_data in results.iterrows():
            try:
                driver_num = driver_data['DriverNumber']
                abbr = driver_data['Abbreviation']
                full_name = driver_data['FullName']
                # Format with fixed-width columns for better alignment
                # #NN AAA - First LASTNAME
                label = f"#{str(driver_num).rjust(2)} {abbr.ljust(3)} - {full_name}"
                driver_options.append({
                    'label': label,
                    'value': f"{abbr}_{year}_{driver_num}"
                })
            except Exception as e:
                logger.error(f"Error loading driver: {e}")
                continue
        
        logger.info(f"Created {len(driver_options)} driver options")
        
        # Log first few drivers for debugging
        driver_names = [opt['label'] for opt in driver_options[:5]]
        logger.info(f"Sample drivers: {', '.join(driver_names)}")
        
        # Reset to None to clear selection
        default_value = None
        
        logger.info(f"Returning {len(driver_options)} options, forcing reset to: {default_value}")
        
        # Return dropdown with consistent ID and signal session loaded
        return dcc.Loading(
            dcc.Dropdown(
                id='driver-selector',
                options=driver_options,
                value=None,
                placeholder="Select a driver...",
                className="mb-2",
                clearable=True,
                style={
                    'fontSize': '12px',
                    'fontFamily': 'monospace',
                    'lineHeight': '1.2'
                }
            ),
            type="circle",
            color="#e10600"
        ), {'loaded': True, 'year': year, 'meeting_key': meeting_key, 'session': session}
    
    except Exception as e:
        logger.error(f"Error loading drivers for {year} meeting_key={meeting_key} {session}: {e}")
        # Return empty dropdown on error
        return dcc.Loading(
            dcc.Dropdown(
                id='driver-selector',
                options=[],
                value=None,
                placeholder="Error loading drivers",
                className="mb-2",
                clearable=True
            ),
            type="circle",
            color="#e10600"
        ), {'loaded': False}, {'loaded': False}


@callback(
    Output('dashboard-container', 'children'),
    Input('dashboard-selector', 'value'),
    Input('session-store', 'data'),
    State('driver-selector', 'value'),
    prevent_initial_call=False
)
def update_dashboards(selected_dashboards, session_data, focused_driver):
    """Update visible dashboards based on selection."""
    if not selected_dashboards:
        return html.Div([
            html.H4("No dashboards selected", className="text-center mt-5"),
            html.P(
                "Select one or more dashboards from the sidebar",
                className="text-center text-muted"
            )
        ])
    
    # Check if session is loaded (for dashboards that require it)
    session_loaded = session_data and session_data.get('loaded', False)
    
    # Create dashboards based on selection
    dashboards = []
    
    for dashboard_id in selected_dashboards:
        if dashboard_id == "ai":
            # AI Assistant Dashboard
            dashboards.append(
                AIAssistantDashboard.create_layout(
                    focused_driver=focused_driver if focused_driver != 'none' else None
                )
            )
        
        elif dashboard_id == "race_overview":
            # Race Overview Dashboard (Leaderboard + Circuit Map)
            if not session_loaded:
                logger.info("Race overview requested but session not yet loaded, showing placeholder")
                dashboards.append(
                    dbc.Card([
                        dbc.CardHeader(html.H5("🏁 Race Overview - Leaderboard & Circuit Map")),
                        dbc.CardBody([
                            dcc.Loading(
                                html.Div([
                                    html.P("Loading session data...", className="text-center p-5 text-muted"),
                                    html.P("Please wait while we load the race information.", 
                                           className="text-center text-muted small")
                                ]),
                                type="circle",
                                color="#e10600"
                            )
                        ])
                    ], className="mb-3")
                )
                continue
                
            try:
                # Use globally stored session object
                global current_session_obj
                
                if current_session_obj is None:
                    logger.warning("Race overview requested but no session loaded")
                    dashboards.append(
                        dbc.Card([
                            dbc.CardHeader(html.H5("🏁 Race Overview - Leaderboard & Circuit Map")),
                            dbc.CardBody([
                                html.P("No session loaded. Please select a race session from the sidebar.", 
                                       className="text-muted text-center p-5")
                            ])
                        ], className="mb-3")
                    )
                else:
                    logger.info("Rendering race overview dashboard...")
                    overview_content = RaceOverviewDashboard.render(
                        session_obj=current_session_obj,
                        focused_driver=focused_driver if focused_driver != 'none' else None
                    )
                    dashboards.append(
                        dbc.Card([
                            dbc.CardHeader(html.H5("🏁 Race Overview - Leaderboard & Circuit Map")),
                            dbc.CardBody([overview_content])
                        ], className="mb-3")
                    )
                    logger.info("Race overview dashboard rendered successfully")
                    
            except Exception as e:
                logger.error(f"Error creating race overview dashboard: {e}", exc_info=True)
                dashboards.append(
                    dbc.Card([
                        dbc.CardHeader(html.H5("🏁 Race Overview - Leaderboard & Circuit Map")),
                        dbc.CardBody([
                            html.P(f"Error loading race overview: {str(e)}", className="text-danger")
                        ])
                    ], className="mb-3")
                )
        
        elif dashboard_id == "live_leaderboard":
            # Live Leaderboard Dashboard (OpenF1 real-time data)
            try:
                logger.info("Rendering live leaderboard dashboard...")
                leaderboard_content = leaderboard_dashboard.create_layout()
                dashboards.append(leaderboard_content)
                logger.info("Live leaderboard dashboard rendered successfully")
            except Exception as e:
                logger.error(f"Error creating live leaderboard dashboard: {e}", exc_info=True)
                dashboards.append(
                    dbc.Card([
                        dbc.CardHeader(html.H5("🏎️ Live Leaderboard")),
                        dbc.CardBody([
                            html.P(
                                f"Error loading live leaderboard: {str(e)}",
                                className="text-danger"
                            )
                        ])
                    ], className="mb-3")
                )
        
        elif dashboard_id == "telemetry":
            # Telemetry placeholder
            dashboards.append(
                dbc.Card([
                    dbc.CardHeader(html.H5("📊 Telemetry")),
                    dbc.CardBody([
                        html.P(f"Showing telemetry for: {focused_driver}", className="text-muted"),
                        html.Div(
                            "Speed, throttle, brake, and gear data will be rendered here",
                            className="text-center p-5 bg-dark rounded"
                        )
                    ])
                ], className="mb-3")
            )
        
        else:
            # Generic placeholder for other dashboards
            dashboards.append(
                dbc.Card([
                    dbc.CardHeader(html.H5(f"📊 {dashboard_id.title()}")),
                    dbc.CardBody([
                        html.P(f"Dashboard: {dashboard_id}", className="text-muted"),
                        html.Div(
                            f"{dashboard_id.title()} dashboard content coming soon",
                            className="text-center p-5 bg-dark rounded"
                        )
                    ])
                ], className="mb-3")
            )
    
    return dashboards


# Callback: Hide/Show Playback based on Mode
@callback(
    Output('playback-accordion', 'style'),
    Input('mode-selector', 'value'),
    prevent_initial_call=False
)
def toggle_playback_visibility(mode):
    """Hide playback controls when in Live mode."""
    if mode == 'live':
        return {'display': 'none'}
    return {'display': 'block'}


# Callback: Save API Keys to .env file
@callback(
    Output('api-keys-save-status', 'children'),
    Input('save-api-keys-btn', 'n_clicks'),
    State('claude-api-key-input', 'value'),
    State('gemini-api-key-input', 'value'),
    State('openf1-api-key-input', 'value'),
    prevent_initial_call=True
)
def save_api_keys(n_clicks, claude_key, gemini_key, openf1_key):
    """Save API keys to .env file."""
    if not n_clicks:
        raise PreventUpdate
    
    try:
        env_path = '.env'
        lines = []
        
        # Read existing .env file if it exists
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                lines = f.readlines()
        
        # Update or add keys
        claude_found = False
        gemini_found = False
        openf1_found = False
        
        for i, line in enumerate(lines):
            if line.startswith('ANTHROPIC_API_KEY='):
                lines[i] = f'ANTHROPIC_API_KEY={claude_key}\n'
                claude_found = True
            elif line.startswith('GOOGLE_API_KEY='):
                lines[i] = f'GOOGLE_API_KEY={gemini_key}\n'
                gemini_found = True
            elif line.startswith('OPENF1_API_KEY='):
                lines[i] = f'OPENF1_API_KEY={openf1_key}\n'
                openf1_found = True
        
        # Add keys if not found
        if not claude_found:
            lines.append(f'ANTHROPIC_API_KEY={claude_key}\n')
        if not gemini_found:
            lines.append(f'GOOGLE_API_KEY={gemini_key}\n')
        if not openf1_found:
            lines.append(f'OPENF1_API_KEY={openf1_key}\n')
        
        # Write back to .env
        with open(env_path, 'w') as f:
            f.writelines(lines)
        
        # Update environment variables in current session
        os.environ['ANTHROPIC_API_KEY'] = claude_key
        os.environ['GOOGLE_API_KEY'] = gemini_key
        os.environ['OPENF1_API_KEY'] = openf1_key
        
        return dbc.Alert("✅ API keys saved successfully!", color="success", dismissable=True, duration=3000, className="small py-1 mb-0 mt-2")
    
    except Exception as e:
        logger.error(f"Error saving API keys: {e}")
        return dbc.Alert(f"❌ Error: {str(e)}", color="danger", dismissable=True, duration=3000, className="small py-1 mb-0 mt-2")


# Callback: Play/Pause simulation
@callback(
    Output('play-btn', 'children'),
    Output('play-btn', 'color'),
    Output('simulation-interval', 'disabled'),
    Output('play-btn-tooltip', 'children'),
    Input('play-btn', 'n_clicks'),
    prevent_initial_call=True
)
def toggle_play_pause(n_clicks):
    """Toggle play/pause for simulation."""
    global simulation_controller, current_session_obj
    
    if simulation_controller is None:
        return "▶️", "success", True, "Play simulation"
    
    # If starting to play for the first time, calculate offset from laps data
    if not simulation_controller.is_playing and current_session_obj is not None:
        laps = current_session_obj.laps
        if 'LapStartTime' in laps.columns and not laps.empty:
            # Get minimum LapStartTime to use as offset
            laps_with_time = laps[pd.notna(laps['LapStartTime'])]
            if not laps_with_time.empty:
                min_lap_start = laps_with_time['LapStartTime'].min().total_seconds()
                simulation_controller.play(start_from_seconds=min_lap_start)
                is_playing = True
            else:
                is_playing = simulation_controller.toggle_play_pause()
        else:
            is_playing = simulation_controller.toggle_play_pause()
    else:
        is_playing = simulation_controller.toggle_play_pause()
    
    if is_playing:
        return "⏸️", "warning", False, "Pause simulation"  # Enable interval, change tooltip
    else:
        return "▶️", "success", True, "Play simulation"  # Disable interval, change tooltip


# Callback: Restart simulation
@callback(
    Output('play-btn', 'children', allow_duplicate=True),
    Output('play-btn', 'color', allow_duplicate=True),
    Output('simulation-interval', 'disabled', allow_duplicate=True),
    Output('play-btn-tooltip', 'children', allow_duplicate=True),
    Input('restart-btn', 'n_clicks'),
    prevent_initial_call=True
)
def restart_simulation(n_clicks):
    """Restart simulation from beginning."""
    global simulation_controller
    
    if simulation_controller:
        simulation_controller.restart()
    
    return "▶️", "success", True, "Play simulation"  # Stop, reset, and reset tooltip


# Callback: Change simulation speed
@callback(
    Output('speed-slider', 'value'),
    Output('simulation-progress', 'children', allow_duplicate=True),
    Input('speed-slider', 'value'),
    prevent_initial_call=True
)
def change_speed(speed):
    """Change simulation playback speed."""
    global simulation_controller
    
    if simulation_controller:
        try:
            simulation_controller.set_speed(float(speed))
            logger.info(f"Simulation speed changed to {speed}x")
            
            # Show immediate feedback in progress display
            progress = simulation_controller.get_progress()
            remaining = simulation_controller.get_remaining_time()
            elapsed = simulation_controller.get_elapsed_time()
            elapsed_seconds = elapsed.total_seconds()
            current_lap = min(int(elapsed_seconds / 90) + 1, 57)
            remaining_minutes = int(remaining.total_seconds() // 60)
            remaining_seconds = int(remaining.total_seconds() % 60)
            
            return speed, f"⏱️ Lap {current_lap}/57 | ⏳ {remaining_minutes}m {remaining_seconds}s left | 🚀 {speed}x"
        except ValueError as e:
            logger.error(f"Invalid speed value: {e}")
            return 1.0, "⚠️ Invalid speed"
    
    return speed, "⏱️ Not started"


# Callback: Jump backward (previous lap)
@callback(
    Output('simulation-progress', 'children', allow_duplicate=True),
    Input('back-btn', 'n_clicks'),
    prevent_initial_call=True
)
def jump_backward(n_clicks):
    """Jump to previous lap."""
    global simulation_controller
    
    if simulation_controller:
        simulation_controller.jump_backward(90)  # ~90 seconds per lap
        logger.info("Jumped to previous lap")
        
        # Return updated progress
        progress = simulation_controller.get_progress()
        remaining = simulation_controller.get_remaining_time()
        current_lap = int(progress * 57)  # Approximate lap count
        return f"⏱️ Lap {current_lap}/57 | ⏳ {int(remaining.total_seconds() // 60)}m left"
    
    return "⏱️ Not started"


# Callback: Jump forward (next lap)
@callback(
    Output('simulation-progress', 'children', allow_duplicate=True),
    Input('forward-btn', 'n_clicks'),
    prevent_initial_call=True
)
def jump_forward(n_clicks):
    """Jump to next lap."""
    global simulation_controller
    
    if simulation_controller:
        simulation_controller.jump_forward(90)  # ~90 seconds per lap
        logger.info("Jumped to next lap")
        
        # Return updated progress
        progress = simulation_controller.get_progress()
        remaining = simulation_controller.get_remaining_time()
        current_lap = int(progress * 57)  # Approximate lap count
        return f"⏱️ Lap {current_lap}/57 | ⏳ {int(remaining.total_seconds() // 60)}m left"
    
    return "⏱️ Not started"


# Callback: Update simulation progress display every second
@callback(
    Output('simulation-progress', 'children', allow_duplicate=True),
    Input('simulation-interval', 'n_intervals'),
    prevent_initial_call=True
)
def update_simulation_progress(n_intervals):
    """Update the simulation progress display in real-time."""
    global simulation_controller
    
    if simulation_controller is None:
        return "⏱️ Not started"
    
    # Update simulation time
    simulation_controller.update()
    
    # Get progress information
    progress = simulation_controller.get_progress()
    remaining = simulation_controller.get_remaining_time()
    elapsed = simulation_controller.get_elapsed_time()
    
    # Calculate current lap (assuming ~90s per lap, 57 laps total)
    elapsed_seconds = elapsed.total_seconds()
    current_lap = min(int(elapsed_seconds / 90) + 1, 57)
    
    # Format remaining time
    remaining_minutes = int(remaining.total_seconds() // 60)
    remaining_seconds = int(remaining.total_seconds() % 60)
    
    # Get current speed multiplier
    speed = simulation_controller.speed_multiplier
    
    return f"⏱️ Lap {current_lap}/57 | ⏳ {remaining_minutes}m {remaining_seconds}s left | 🚀 {speed}x"


# NOTE: Circuit map real-time updates disabled
# The circuit map shows static driver positions at race start
# Real-time position tracking proved too computationally expensive for smooth UI
# Future optimization: Consider WebGL-based rendering or server-side position streaming
#
# Previous attempts:
# 1. Full figure regeneration every second -> UI blocking
# 2. Patch() with 3-second updates -> Still causes blocking
# 
# The static display is functional and doesn't interfere with simulation playback


@callback(
    Output('leaderboard-container', 'children'),
    Input('simulation-interval', 'n_intervals'),
    State('dashboard-selector', 'value'),
    prevent_initial_call=True
)
def update_leaderboard_realtime(n_intervals, selected_dashboards):
    """Update leaderboard table with current simulation time."""
    global simulation_controller, current_session_obj
    
    # Only update if race_overview dashboard is selected
    if not selected_dashboards or 'race_overview' not in selected_dashboards:
        raise PreventUpdate
    
    # Check if simulation is running and session loaded
    if simulation_controller is None or current_session_obj is None:
        raise PreventUpdate
    
    # Only update if simulation is actively playing
    if not simulation_controller.is_playing:
        raise PreventUpdate
    
    try:
        # Get elapsed simulation seconds
        elapsed_seconds = simulation_controller.get_elapsed_seconds()
        
        # Get session data
        laps = current_session_obj.laps
        results = current_session_obj.results
        
        # Generate updated leaderboard with elapsed time
        leaderboard_table = RaceOverviewDashboard._build_leaderboard(
            current_session_obj, laps, results, elapsed_seconds
        )
        
        return leaderboard_table
        
    except Exception as e:
        logger.error(f"Error updating real-time leaderboard: {e}", exc_info=True)
        raise PreventUpdate


# Callback: Update circuit map driver positions in real-time
@callback(
    Output('circuit-map-graph', 'figure'),
    Input('simulation-interval', 'n_intervals'),
    State('dashboard-selector', 'value'),
    State('circuit-map-graph', 'figure'),
    prevent_initial_call=True
)
def update_circuit_map_realtime(n_intervals, selected_dashboards, current_figure):
    """Update driver positions on circuit map using Patch for efficiency."""
    global simulation_controller, current_session_obj
    
    # Only update if race_overview dashboard is selected
    if not selected_dashboards or 'race_overview' not in selected_dashboards:
        raise PreventUpdate
    
    # Check if simulation is running and session loaded
    if simulation_controller is None or current_session_obj is None:
        raise PreventUpdate
    
    try:
        # Get current simulation time
        current_time = simulation_controller.current_time
        
        # Get session data
        laps = current_session_obj.laps
        results = current_session_obj.results
        drivers = current_session_obj.drivers
        
        # Use Patch to update only driver positions (Traces 2+)
        patched_figure = Patch()
        
        driver_idx = 0
        for driver_num in drivers:
            try:
                driver_info = results[results['DriverNumber'] == str(driver_num)].iloc[0]
                
                # Get driver's laps
                driver_laps = laps[laps['DriverNumber'] == driver_num]
                if driver_laps.empty:
                    continue
                
                # Find appropriate lap based on current_time
                if 'Time' in driver_laps.columns:
                    valid_laps = driver_laps[
                        pd.notna(driver_laps['Time']) & 
                        (driver_laps['Time'] <= current_time)
                    ]
                    if not valid_laps.empty:
                        current_lap = valid_laps.iloc[-1]
                    else:
                        current_lap = driver_laps.iloc[0]
                else:
                    current_lap = driver_laps.iloc[0]
                
                telemetry = current_lap.get_telemetry()
                
                if not telemetry.empty and 'X' in telemetry.columns and 'Y' in telemetry.columns:
                    if 'Time' in telemetry.columns:
                        valid_telem = telemetry[pd.notna(telemetry['Time'])]
                        if not valid_telem.empty:
                            # Find closest telemetry point by time
                            time_diffs = (valid_telem['Time'] - current_time).abs()
                            closest_idx = time_diffs.idxmin()
                            x_pos = telemetry.loc[closest_idx, 'X']
                            y_pos = telemetry.loc[closest_idx, 'Y']
                        else:
                            x_pos = telemetry['X'].iloc[0]
                            y_pos = telemetry['Y'].iloc[0]
                    else:
                        x_pos = telemetry['X'].iloc[0]
                        y_pos = telemetry['Y'].iloc[0]
                    
                    # Update driver position (trace index = 2 + driver_idx)
                    # Trace 0 = circuit outline, Trace 1 = START marker, Traces 2+ = drivers
                    trace_idx = 2 + driver_idx
                    patched_figure['data'][trace_idx]['x'] = [x_pos]
                    patched_figure['data'][trace_idx]['y'] = [y_pos]
                    
                    driver_idx += 1
                    
            except Exception as e:
                logger.debug(f"Error updating position for driver {driver_num}: {e}")
                continue
        
        return patched_figure
        
    except Exception as e:
        logger.error(f"Error updating circuit map: {e}")
        raise PreventUpdate


# Callback: Toggle help modal
@callback(
    Output('help-modal', 'is_open'),
    [Input('help-btn', 'n_clicks'),
     Input('close-help-modal', 'n_clicks')],
    State('help-modal', 'is_open'),
    prevent_initial_call=True
)
def toggle_help_modal(help_clicks, close_clicks, is_open):
    """Toggle help modal visibility."""
    if help_clicks or close_clicks:
        return not is_open
    return is_open


# Callback: Toggle sidebar visibility
@callback(
    [Output('sidebar-column', 'style'),
     Output('main-content-column', 'width'),
     Output('sidebar-visible-store', 'data'),
     Output('sidebar-toggle-btn', 'children'),
     Output('sidebar-toggle-btn', 'title')],
    Input('sidebar-toggle-btn', 'n_clicks'),
    State('sidebar-visible-store', 'data'),
    prevent_initial_call=True
)
def toggle_sidebar(n_clicks, is_visible):
    """Toggle sidebar visibility."""
    if n_clicks is None:
        raise PreventUpdate
    
    # Toggle visibility
    new_visibility = not is_visible
    
    if new_visibility:
        # Show sidebar
        return {'display': 'block'}, 10, True, '<<', 'Hide sidebar'
    else:
        # Hide sidebar
        return {'display': 'none'}, 12, False, '>>', 'Show sidebar'


if __name__ == '__main__':
    logger.info("="*60)
    logger.info("F1 STRATEGIST AI - DASH VERSION")
    logger.info("="*60)
    logger.info("Starting application...")
    logger.info("Open: http://localhost:8501")
    logger.info("="*60)
    
    # Register leaderboard callbacks
    logger.info("Registering live leaderboard callbacks...")
    leaderboard_dashboard.setup_callbacks(app)
    
    # Initialize session with last completed race
    last_race = get_last_completed_race()
    session.race_context = last_race
    logger.info(f"Initialized with {last_race.country} GP (Round {last_race.round_number}, {last_race.year})")
    
    app.run(debug=True, port=8501)
