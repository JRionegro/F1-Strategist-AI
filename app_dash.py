"""
F1 Strategist AI - Main Dash Application.

Multi-dashboard F1 strategy platform with live and simulation modes.
Migrated from Streamlit to Dash for better layout control.
"""

import logging
import os
import sys
import importlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import dash
from dash import Dash, html, dcc, Input, Output, State, callback, ctx, Patch, ALL
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd

# OpenF1 data provider (replaces FastF1)
from src.data.openf1_adapter import get_session as get_openf1_session, SessionAdapter
from src.data.openf1_data_provider import OpenF1DataProvider
from src.data.last_race_finder import (
    get_last_completed_race,
    get_last_completed_meeting_key
)

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

# FORCE RELOAD: Remove modules from cache BEFORE importing
modules_to_reload = [
    'src.dashboards_dash.weather_dashboard',
    'src.dashboards_dash.ai_assistant_dashboard', 
    'src.dashboards_dash.race_overview_dashboard'
]
for module_name in modules_to_reload:
    if module_name in sys.modules:
        del sys.modules[module_name]

# Clear Python's import cache
importlib.invalidate_caches()

# Remove compiled Python files
import os
import glob
project_root = os.path.dirname(os.path.abspath(__file__))
for pattern in ['**/*.pyc', '**/__pycache__']:
    for item in glob.glob(os.path.join(project_root, 'src', 'dashboards_dash', pattern), recursive=True):
        try:
            if os.path.isfile(item):
                os.remove(item)
            elif os.path.isdir(item):
                import shutil
                shutil.rmtree(item)
        except:
            pass

# NOW import dashboards (fresh, no cache)
from src.dashboards_dash.ai_assistant_dashboard import AIAssistantDashboard
from src.dashboards_dash.race_overview_dashboard import RaceOverviewDashboard
from src.dashboards_dash.race_control_dashboard import RaceControlDashboard
from src.dashboards_dash import weather_dashboard

# RAG Manager for document loading
from src.rag.rag_manager import get_rag_manager, reset_rag_manager
from src.rag.template_generator import get_template_generator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize OpenF1 provider with SSL verification disabled for corporate proxies
openf1_provider = OpenF1DataProvider(verify_ssl=False)

# Initialize Race Overview Dashboard
race_overview_dashboard = RaceOverviewDashboard(openf1_provider)

# Initialize Race Control Dashboard
race_control_dashboard = RaceControlDashboard(openf1_provider)

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
server.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable Flask caching
server.config['TEMPLATES_AUTO_RELOAD'] = True

# Global session (singleton pattern maintained)
session = GlobalSession()

# Simulation controller (initialized with dummy times, will be updated)
simulation_controller: Optional[SimulationController] = None

# Current loaded session object (for circuit map and other dashboards)
current_session_obj = None


def get_last_completed_race_context() -> RaceContext:
    """
    Get the most recent completed race from OpenF1.

    Falls back to a default if OpenF1 is unavailable.

    Returns:
        RaceContext with the last completed race information.
    """
    # Try to get from OpenF1
    race_context = get_last_completed_race(openf1_provider)

    if race_context:
        logger.info(
            f"Found last completed race: {race_context.country} GP "
            f"(Round {race_context.round_number}, {race_context.year})"
        )
        return race_context

    # Fallback: return a sensible default (last known race)
    logger.warning(
        "Could not find last race from OpenF1, using fallback"
    )
    return RaceContext(
        year=datetime.now().year,
        round_number=1,
        circuit_name="Unknown Circuit",
        circuit_key="unknown",
        country="Unknown",
        session_type=SessionType.RACE,
        session_date=datetime.now(),
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
            html.H4([
                html.Span("🏎️", style={'fontSize': '3rem'}),
                " F1 Strategist"
            ], className="text-center mb-3"),
            
            html.Hr(),
            
            # Mode selector (collapsed)
            dbc.Accordion([
                dbc.AccordionItem([
                    dbc.RadioItems(
                        id="mode-selector",
                        options=[
                            {"label": " 🏁 Live", "value": "live"},
                            {"label": " ⏯️ Simulation", "value": "sim"}
                        ],
                        value="sim",
                        className="mb-2"
                    )
                ], title="🎮 Mode", className="mb-3")
            ], start_collapsed=True),
            
            html.Hr(),
            
            # Context selector (expanded by default)
            dbc.Accordion([
                dbc.AccordionItem([
                    dbc.Label("Year", className="fw-bold"),
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
                    
                    dbc.Label("Circuit", className="fw-bold"),
                    dcc.Dropdown(
                        id='circuit-selector',
                        options=[],  # Will be populated by callback
                        value=None,
                        className="mb-3",
                        clearable=False
                    ),
                    
                    dbc.Label("Session", className="fw-bold"),
                    dcc.Dropdown(
                        id='session-selector',
                        options=[],  # Will be populated by callback
                        value=None,
                        className="mb-3",
                        clearable=False
                    ),
                    
                    dbc.Label("Driver", className="fw-bold"),
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
                ], title="🗺️ Context", className="mb-3")
            ], start_collapsed=False),
            
            html.Hr(),
            
            # Dashboard selector (collapsed)
            dbc.Accordion([
                dbc.AccordionItem([
                    dbc.Checklist(
                        id="dashboard-selector",
                        options=[
                            {"label": " AI Assistant", "value": "ai"},
                            {"label": " Race Overview", "value": "race_overview"},
                            {"label": " Race Control", "value": "race_control"},
                            {"label": " Weather", "value": "weather"},
                            {"label": " Telemetry", "value": "telemetry"},
                            # Phase 2 Dashboards (Coming Soon)
                            # {"label": " Tire Strategy", "value": "tires"},
                            # {"label": " Lap Analysis", "value": "laps"},
                            # {"label": " Qualifying", "value": "qualifying"},
                        ],
                        value=["ai", "race_overview", "race_control", "weather"],
                        className="mb-2"
                    )
                ], title="📊 Dashboards", className="mb-3")
            ], start_collapsed=True),
            
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
            
            # RAG Documents Section
            dbc.Accordion([
                dbc.AccordionItem([
                    # RAG Status indicator
                    html.Div([
                        html.Span(id="rag-status", children="⚪ Not loaded"),
                        html.Small(
                            id="rag-doc-count",
                            className="text-muted ms-2"
                        )
                    ], className="mb-3"),
                    
                    # Document list by category
                    html.Div([
                        # Global Documents
                        html.Div([
                            html.H6(
                                "🌐 Global",
                                className="text-info mb-1",
                                style={'fontSize': '0.85rem'}
                            ),
                            html.Div(
                                id="rag-global-docs",
                                className="ps-2 small text-muted"
                            )
                        ], className="mb-2"),
                        
                        # Strategy Documents
                        html.Div([
                            html.H6(
                                "📋 Strategy",
                                className="text-info mb-1",
                                style={'fontSize': '0.85rem'}
                            ),
                            html.Div(
                                id="rag-strategy-docs",
                                className="ps-2 small text-muted"
                            )
                        ], className="mb-2"),
                        
                        # Weather Documents
                        html.Div([
                            html.H6(
                                "🌦️ Weather",
                                className="text-info mb-1",
                                style={'fontSize': '0.85rem'}
                            ),
                            html.Div(
                                id="rag-weather-docs",
                                className="ps-2 small text-muted"
                            )
                        ], className="mb-2"),
                        
                        # Performance Documents
                        html.Div([
                            html.H6(
                                "📊 Performance",
                                className="text-info mb-1",
                                style={'fontSize': '0.85rem'}
                            ),
                            html.Div(
                                id="rag-performance-docs",
                                className="ps-2 small text-muted"
                            )
                        ], className="mb-2"),
                        
                        # Race Control Documents
                        html.Div([
                            html.H6(
                                "🚦 Race Control",
                                className="text-info mb-1",
                                style={'fontSize': '0.85rem'}
                            ),
                            html.Div(
                                id="rag-race-control-docs",
                                className="ps-2 small text-muted"
                            )
                        ], className="mb-2"),
                        
                        # Race Position Documents
                        html.Div([
                            html.H6(
                                "🏁 Positions",
                                className="text-info mb-1",
                                style={'fontSize': '0.85rem'}
                            ),
                            html.Div(
                                id="rag-race-position-docs",
                                className="ps-2 small text-muted"
                            )
                        ], className="mb-2"),
                        
                        # FIA Regulations
                        html.Div([
                            html.H6(
                                "📖 FIA Regs",
                                className="text-info mb-1",
                                style={'fontSize': '0.85rem'}
                            ),
                            html.Div(
                                id="rag-fia-docs",
                                className="ps-2 small text-muted"
                            )
                        ], className="mb-2"),
                    ]),
                    
                    # Action buttons
                    html.Div([
                        dbc.Button(
                            "🔄 Reload",
                            id="rag-reload-btn",
                            size="sm",
                            color="secondary",
                            outline=True,
                            className="me-2"
                        ),
                        dbc.Button(
                            "📝 Generate",
                            id="rag-generate-btn",
                            size="sm",
                            color="info",
                            outline=True,
                            title="Generate circuit templates from historical data"
                        ),
                    ], className="mt-3 d-flex"),
                    
                    # RAG reload status message
                    html.Div(
                        id="rag-reload-status",
                        className="small text-muted mt-2"
                    )
                ], title="📚 RAG Documents", className="mb-3")
            ], start_collapsed=True, id="rag-accordion"),
            
            html.Hr(),
            
            # Menu (collapsed)
            dbc.Accordion([
                dbc.AccordionItem([
                    # Config option
                    html.Div([
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
                ], title="⚙️ Configuration", className="mb-2")
            ], start_collapsed=True),
            
            # Help button
            dbc.Button(
                [html.I(className="bi bi-question-circle me-1"), "Help"],
                id="help-btn",
                color="info",
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
    dcc.Store(id='simulation-time-store', data={'time': 0.0, 'timestamp': 0}),
    dcc.Store(id='weather-last-update-store', data={'timestamp': 0, 'state': None}),
    
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
    
    # Document Editor Modal (for RAG documents)
    dbc.Modal([
        dbc.ModalHeader([
            dbc.ModalTitle(id="doc-editor-title", children="📝 Edit Document"),
        ]),
        dbc.ModalBody([
            # Document path info
            html.Div([
                html.Small(id="doc-editor-path", className="text-muted")
            ], className="mb-2"),
            # Textarea for editing
            dcc.Textarea(
                id="doc-editor-textarea",
                style={
                    "width": "100%",
                    "height": "450px",
                    "fontFamily": "'Consolas', 'Monaco', monospace",
                    "fontSize": "13px",
                    "lineHeight": "1.5",
                    "padding": "10px",
                    "border": "1px solid #444",
                    "borderRadius": "4px",
                    "backgroundColor": "#1e1e1e",
                    "color": "#d4d4d4"
                },
                placeholder="Document content will appear here..."
            ),
            # Status message
            html.Div(id="doc-editor-status", className="mt-2 small")
        ]),
        dbc.ModalFooter([
            html.Div([
                dbc.Button(
                    "💾 Save",
                    id="doc-editor-save-btn",
                    color="primary",
                    className="me-2"
                ),
                dbc.Button(
                    "Cancel",
                    id="doc-editor-cancel-btn",
                    color="secondary",
                    outline=True
                )
            ])
        ])
    ], id="doc-editor-modal", is_open=False, size="xl", centered=True),
    
    # Hidden store for current document being edited
    dcc.Store(id="doc-editor-store", data={"filepath": None, "category": None}),
    
    # Template Generation Confirmation Modal
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("⚠️ Confirm Template Generation")),
        dbc.ModalBody([
            html.P(id="rag-generate-confirm-message"),
            html.Div(id="rag-generate-existing-files", className="small text-warning")
        ]),
        dbc.ModalFooter([
            dbc.Button(
                "Cancel",
                id="rag-generate-cancel-btn",
                color="secondary",
                className="me-2"
            ),
            dbc.Button(
                "Generate & Overwrite",
                id="rag-generate-confirm-btn",
                color="danger"
            ),
        ])
    ], id="rag-generate-confirm-modal", is_open=False, centered=True),
    
    # Store for tracking template generation state
    dcc.Store(id="rag-generate-store", data={"year": None, "circuit": None}),
    
    # Main layout
    dbc.Row([
        create_sidebar(),
        create_main_content()
    ], className="g-0", style={'height': '100vh'})
], fluid=True, className="vh-100 p-0")


# ============================================================================
# CALLBACKS
# ============================================================================

# Callback to enable/disable Live mode based on live session availability
@callback(
    Output('mode-selector', 'options'),
    Input('mode-selector', 'value'),  # Dummy input to trigger on load
    prevent_initial_call=False
)
def update_live_mode_availability(_):
    """Check if live session is available and enable/disable Live mode."""
    live_session = check_for_live_session()
    
    if live_session:
        # Live session available - enable both modes
        return [
            {"label": " 🏁 Live", "value": "live", "disabled": False},
            {"label": " ⏯️ Simulation", "value": "sim", "disabled": False}
        ]
    else:
        # No live session - disable Live mode
        return [
            {"label": " 🏁 Live (No race now)", "value": "live", "disabled": True},
            {"label": " ⏯️ Simulation", "value": "sim", "disabled": False}
        ]


# Callback to lock/unlock Context controls based on mode
@callback(
    Output('year-selector', 'disabled'),
    Output('circuit-selector', 'disabled'),
    Output('session-selector', 'disabled'),
    Output('year-selector', 'value', allow_duplicate=True),
    Output('circuit-selector', 'value', allow_duplicate=True),
    Output('session-selector', 'value', allow_duplicate=True),
    Input('mode-selector', 'value'),
    prevent_initial_call=True
)
def handle_mode_change(mode):
    """Lock Context controls in Live mode and auto-load live session data."""
    if mode == "live":
        # Get live session information
        live_session = check_for_live_session()
        
        if live_session:
            # Lock controls and set values from live session
            year = live_session.year
            circuit_key = live_session.circuit_key
            
            # Map SessionType enum to dropdown value
            session_type_map = {
                'Practice 1': 'P1',
                'Practice 2': 'P2',
                'Practice 3': 'P3',
                'Qualifying': 'Q',
                'Sprint': 'S',
                'Sprint Qualifying': 'SQ',
                'Race': 'R'
            }
            session_value = session_type_map.get(live_session.session_type.value, 'R')
            
            logger.info(f"Live mode activated: year={year}, circuit={circuit_key}, session={session_value}")
            
            return True, True, True, year, circuit_key, session_value
        else:
            # No live session, keep simulation mode
            logger.warning("Live mode selected but no live session available")
            return False, False, False, 2025, None, None
    else:
        # Simulation mode - unlock controls
        return False, False, False, 2025, None, None


@callback(
    Output('circuit-selector', 'options'),
    Output('circuit-selector', 'value'),
    Output('session-selector', 'options', allow_duplicate=True),
    Output('session-selector', 'value', allow_duplicate=True),
    Input('year-selector', 'value'),
    State('circuit-selector', 'value'),
    prevent_initial_call='initial_duplicate'
)
def update_circuits(year, current_circuit):
    """Update circuit dropdown based on selected year. Clears session when year changes."""
    if year is None:
        return [], None, [], None
    
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
    
    # When year changes, always clear circuit selection to force user to choose
    # This also triggers session dropdown to clear
    from dash import ctx
    triggered_id = ctx.triggered_id if ctx.triggered else None
    
    if triggered_id == 'year-selector':
        # Year changed - clear circuit and session, let user select
        logger.info(f"Year changed to {year}, clearing circuit and session selections")
        return circuit_options, None, [], None
    
    # Keep current selection if it exists in new options
    if current_circuit and current_circuit in circuit_keys:
        default_value = current_circuit
    else:
        # Try to get last completed race from OpenF1
        last_meeting_key = get_last_completed_meeting_key(openf1_provider)

        if last_meeting_key and last_meeting_key in circuit_keys:
            default_value = last_meeting_key
            logger.info(
                f"Auto-selected last completed race: meeting_key={last_meeting_key}"
            )
        elif circuit_options:
            # Fallback: select last race in list for current year, first otherwise
            default_value = circuit_options[-1]['value']
            logger.info("Using last circuit in calendar as default")
        else:
            default_value = None

    # Return empty session options - will be populated by update_sessions callback
    return circuit_options, default_value, [], None


@callback(
    Output('session-selector', 'options', allow_duplicate=True),
    Output('session-selector', 'value', allow_duplicate=True),
    Input('circuit-selector', 'value'),
    Input('year-selector', 'value'),
    State('session-selector', 'value'),
    prevent_initial_call=True
)
def update_sessions(circuit_key, year, current_session):
    """Update session dropdown based on selected circuit (meeting_key from OpenF1)."""
    from dash import ctx
    
    if not circuit_key or not year:
        return [], None
    
    # When circuit changes, always clear session selection
    triggered_id = ctx.triggered_id if ctx.triggered else None
    force_clear = triggered_id == 'circuit-selector'
    
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
        
        # When circuit changes, clear session and let user select
        session_values = [opt['value'] for opt in session_options]
        if force_clear:
            logger.info(f"Circuit changed, clearing session selection. Found {len(session_options)} sessions for meeting_key={meeting_key}")
            default_value = None
        elif current_session and current_session in session_values:
            default_value = current_session
        else:
            default_value = None  # Don't auto-select, let user choose
        
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
                    
                    # Prepare lap data with absolute timestamps for accurate lap tracking
                    lap_timing_data = None
                    if 'LapStartTime' in laps.columns and 'LapNumber' in laps.columns and 'DriverNumber' in laps.columns:
                        # Use LEADER's laps (DriverNumber=1) for race lap count
                        leader_laps = laps[laps['DriverNumber'] == 1].copy()
                        if not leader_laps.empty:
                            # Convert LapStartTime (timedelta from session start) to absolute datetime
                            lap_timing_data = leader_laps[['LapNumber', 'LapStartTime', 'DriverNumber']].copy()
                            # Drop rows with NaT LapStartTime
                            lap_timing_data = lap_timing_data.dropna(subset=['LapStartTime'])
                            # LapStartTime is a timedelta from session start, convert to absolute datetime
                            lap_timing_data['LapStartTime'] = session_date + lap_timing_data['LapStartTime']
                            logger.info(f"Prepared lap timing data from LEADER: {len(lap_timing_data)} laps with absolute timestamps")
                            logger.info(f"First lap timestamp: {lap_timing_data['LapStartTime'].min()}")
                            logger.info(f"Last lap timestamp: {lap_timing_data['LapStartTime'].max()}")
                        else:
                            logger.warning("No laps found for leader (DriverNumber=1)")
                    
                    # Create controller with lap data for EXACT lap calculation
                    simulation_controller = SimulationController(
                        start_time,
                        end_time,
                        lap_data=lap_timing_data
                    )
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


# ============================================================================
# RAG DOCUMENT CALLBACKS
# ============================================================================

def _format_doc_list(docs: list, category: str = "unknown") -> list:
    """
    Format document list for display in sidebar with edit buttons.
    
    Args:
        docs: List of document dicts or strings
        category: Document category (global, strategy, weather, tire, fia)
    
    Returns:
        List of html components with clickable document names
    """
    if not docs:
        return [html.Small("No documents", className="text-muted fst-italic")]
    
    items = []
    for idx, doc in enumerate(docs):
        if isinstance(doc, dict):
            filename = doc.get('filename', 'Unknown')
            filepath = doc.get('filepath', '')
        else:
            filename = str(doc)
            filepath = ""
        
        # Use Button with filepath encoded in the index
        # Format: category|idx|filepath (base64 encoded to avoid special chars)
        import base64
        encoded_path = base64.b64encode(filepath.encode()).decode() if filepath else ""
        btn_index = f"{category}|{idx}|{encoded_path}"
        
        items.append(
            html.Div([
                html.I(className="bi bi-file-earmark-text me-1"),
                dbc.Button(
                    filename,
                    id={"type": "doc-edit-btn", "index": btn_index},
                    color="link",
                    size="sm",
                    className="p-0 text-start",
                    style={
                        "textDecoration": "underline dotted",
                        "color": "#6ea8fe",
                        "fontSize": "inherit"
                    }
                ),
            ], className="small d-flex align-items-center mb-1")
        )
    return items


def _get_circuit_name_for_rag(meeting_key: int, year: int) -> str:
    """
    Convert meeting_key to circuit name for RAG folder lookup.
    
    Args:
        meeting_key: OpenF1 meeting key
        year: Season year
        
    Returns:
        Circuit name in snake_case (e.g., 'abu_dhabi')
    """
    try:
        # Get meeting info from OpenF1
        meetings = openf1_provider._request(
            "meetings",
            {"year": year, "meeting_key": meeting_key}
        )
        if meetings:
            # Extract circuit name and convert to folder format
            meeting_name = meetings[0].get('meeting_name', '')
            # Remove "Grand Prix" and convert to snake_case
            circuit = meeting_name.lower()
            circuit = circuit.replace(' grand prix', '')
            circuit = circuit.replace(' ', '_')
            circuit = circuit.replace('-', '_')
            return circuit
    except Exception as e:
        logger.warning(f"Could not get circuit name for meeting_key={meeting_key}: {e}")
    return ""


@callback(
    Output('rag-status', 'children'),
    Output('rag-doc-count', 'children'),
    Output('rag-global-docs', 'children'),
    Output('rag-strategy-docs', 'children'),
    Output('rag-weather-docs', 'children'),
    Output('rag-performance-docs', 'children'),
    Output('rag-race-control-docs', 'children'),
    Output('rag-race-position-docs', 'children'),
    Output('rag-fia-docs', 'children'),
    Input('year-selector', 'value'),
    Input('circuit-selector', 'value'),
    prevent_initial_call=False
)
def update_rag_on_context_change(year, meeting_key):
    """
    Load RAG documents when year/circuit context changes.
    
    This callback:
    1. Loads global documents (always)
    2. Loads year-level documents
    3. Loads circuit-specific documents if available
    4. Updates the sidebar display with document lists
    """
    if not year:
        return (
            "⚪ Not loaded",
            "",
            [html.Small("Select year first", className="text-muted fst-italic")],
            [], [], [], [], [], [], []
        )
    
    try:
        rag_manager = get_rag_manager()
        
        # Convert meeting_key to circuit name
        circuit = None
        if meeting_key:
            circuit = _get_circuit_name_for_rag(meeting_key, year)
        
        # Load context into ChromaDB
        chunk_count = rag_manager.load_context(year=year, circuit=circuit)
        
        # Get document lists by category
        docs = rag_manager.list_documents()
        
        # Debug: Log what documents are found per category
        logger.info(f"RAG docs by category: {[(k, len(v)) for k, v in docs.items()]}")
        
        # Determine status icon
        if chunk_count > 0:
            status = "🟢 Loaded"
        else:
            status = "🟡 No docs"
        
        doc_count_text = f"({chunk_count} chunks)"
        
        # Format lists for display (with category for clickable editing)
        global_list = _format_doc_list(docs.get("global", []), "global")
        strategy_list = _format_doc_list(docs.get("strategy", []), "strategy")
        weather_list = _format_doc_list(docs.get("weather", []), "weather")
        performance_list = _format_doc_list(
            docs.get("performance", []), "performance"
        )
        race_control_list = _format_doc_list(
            docs.get("race_control", []), "race_control"
        )
        race_position_list = _format_doc_list(
            docs.get("race_position", []), "race_position"
        )
        fia_list = _format_doc_list(docs.get("fia", []), "fia")
        
        return (
            status,
            doc_count_text,
            global_list,
            strategy_list,
            weather_list,
            performance_list,
            race_control_list,
            race_position_list,
            fia_list
        )
        
    except Exception as e:
        logger.error(f"Error loading RAG context: {e}")
        return (
            "🔴 Error",
            "",
            [html.Small(f"Error: {str(e)[:50]}", className="text-danger")],
            [], [], [], [], [], [], []
        )


@callback(
    Output('rag-reload-status', 'children'),
    Output('rag-status', 'children', allow_duplicate=True),
    Output('rag-doc-count', 'children', allow_duplicate=True),
    Input('rag-reload-btn', 'n_clicks'),
    State('year-selector', 'value'),
    State('circuit-selector', 'value'),
    prevent_initial_call=True
)
def reload_rag_documents(n_clicks, year, meeting_key):
    """Manually reload RAG documents."""
    if not n_clicks:
        raise PreventUpdate
    
    try:
        rag_manager = get_rag_manager()
        
        # Convert meeting_key to circuit name
        circuit = None
        if meeting_key and year:
            circuit = _get_circuit_name_for_rag(meeting_key, year)
        
        # Force reload
        chunk_count = rag_manager.reload()
        
        status_msg = f"✅ Reloaded {chunk_count} chunks"
        return (
            status_msg,
            "🟢 Loaded" if chunk_count > 0 else "🟡 No docs",
            f"({chunk_count} chunks)"
        )
        
    except Exception as e:
        logger.error(f"Error reloading RAG: {e}")
        return f"❌ Error: {str(e)[:50]}", "🔴 Error", ""


# ============================================================================
# TEMPLATE GENERATION CALLBACKS
# ============================================================================

@callback(
    Output('rag-generate-confirm-modal', 'is_open'),
    Output('rag-generate-confirm-message', 'children'),
    Output('rag-generate-existing-files', 'children'),
    Output('rag-generate-store', 'data'),
    Output('rag-reload-status', 'children', allow_duplicate=True),
    Output('rag-status', 'children', allow_duplicate=True),
    Output('rag-doc-count', 'children', allow_duplicate=True),
    Output('rag-global-docs', 'children', allow_duplicate=True),
    Output('rag-strategy-docs', 'children', allow_duplicate=True),
    Output('rag-weather-docs', 'children', allow_duplicate=True),
    Output('rag-performance-docs', 'children', allow_duplicate=True),
    Output('rag-race-control-docs', 'children', allow_duplicate=True),
    Output('rag-race-position-docs', 'children', allow_duplicate=True),
    Output('rag-fia-docs', 'children', allow_duplicate=True),
    Input('rag-generate-btn', 'n_clicks'),
    Input('rag-generate-cancel-btn', 'n_clicks'),
    Input('rag-generate-confirm-btn', 'n_clicks'),
    State('year-selector', 'value'),
    State('circuit-selector', 'value'),
    State('rag-generate-store', 'data'),
    prevent_initial_call=True
)
def handle_template_generation(
    gen_clicks, cancel_clicks, confirm_clicks,
    year, meeting_key, store_data
):
    """Handle template generation with confirmation for overwrites."""
    from pathlib import Path
    from dash.exceptions import PreventUpdate
    
    triggered_id = ctx.triggered_id
    
    # Default empty doc lists for early returns (7 categories)
    no_update_lists = (
        dash.no_update, dash.no_update, dash.no_update, dash.no_update,
        dash.no_update, dash.no_update, dash.no_update
    )
    
    # Cancel button - close modal
    if triggered_id == 'rag-generate-cancel-btn':
        return (
            False, "", "", {"year": None, "circuit": None}, "",
            dash.no_update, dash.no_update,
            *no_update_lists
        )
    
    # Generate button clicked - check for existing files
    if triggered_id == 'rag-generate-btn':
        if not year or not meeting_key:
            return (
                False, "", "", store_data, "⚠️ Select year and circuit first",
                dash.no_update, dash.no_update,
                *no_update_lists
            )
        
        # Get circuit name
        circuit = _get_circuit_name_for_rag(meeting_key, year)
        if not circuit:
            return (
                False, "", "", store_data, "⚠️ Could not determine circuit",
                dash.no_update, dash.no_update,
                *no_update_lists
            )
        
        # Check for existing files
        rag_path = Path("data/rag") / str(year) / "circuits" / circuit
        existing_files = []
        if rag_path.exists():
            existing_files = [f.name for f in rag_path.glob("*.md")]
        
        circuit_display = circuit.replace('_', ' ').title()
        
        if existing_files:
            # Show confirmation modal
            message = f"Generate templates for {circuit_display} ({year})?"
            files_msg = f"⚠️ Will overwrite: {', '.join(existing_files)}"
            return (
                True,
                message,
                files_msg,
                {"year": year, "circuit": circuit},
                "",
                dash.no_update, dash.no_update,
                *no_update_lists
            )
        else:
            # No existing files - generate directly
            return _do_generate_templates(year, circuit, circuit_display)
    
    # Confirm button - actually generate
    if triggered_id == 'rag-generate-confirm-btn':
        if store_data and store_data.get('year') and store_data.get('circuit'):
            circuit_display = store_data['circuit'].replace('_', ' ').title()
            return _do_generate_templates(
                store_data['year'],
                store_data['circuit'],
                circuit_display
            )
    
    raise PreventUpdate


def _do_generate_templates(year: int, circuit: str, circuit_display: str):
    """
    Execute template generation and return callback outputs.
    
    Args:
        year: Target year
        circuit: Circuit name in snake_case
        circuit_display: Circuit name for display
    
    Returns:
        Tuple of callback outputs (15 values for new category structure)
    """
    try:
        generator = get_template_generator()
        
        # Generate with save_to_disk=True
        logger.info(f"Generating templates for {circuit} ({year})...")
        docs = generator.generate_for_circuit(
            year=year,
            circuit=circuit,
            use_historical=True,
            save_to_disk=True
        )
        
        # Reload RAG context to include new docs
        rag_manager = get_rag_manager()
        chunk_count = rag_manager.reload()
        
        # Get updated document lists
        all_docs = rag_manager.list_documents()
        
        # Format lists for display
        global_list = _format_doc_list(all_docs.get("global", []), "global")
        strategy_list = _format_doc_list(
            all_docs.get("strategy", []), "strategy"
        )
        weather_list = _format_doc_list(all_docs.get("weather", []), "weather")
        performance_list = _format_doc_list(
            all_docs.get("performance", []), "performance"
        )
        race_control_list = _format_doc_list(
            all_docs.get("race_control", []), "race_control"
        )
        race_position_list = _format_doc_list(
            all_docs.get("race_position", []), "race_position"
        )
        fia_list = _format_doc_list(all_docs.get("fia", []), "fia")
        
        files_generated = list(docs.keys())
        status_msg = (
            f"✅ Generated {len(files_generated)} templates for "
            f"{circuit_display}: {', '.join(files_generated)}"
        )
        logger.info(status_msg)
        
        return (
            False,  # Close modal
            "",
            "",
            {"year": None, "circuit": None},
            status_msg,
            "🟢 Loaded",
            f"({chunk_count} chunks)",
            global_list,
            strategy_list,
            weather_list,
            performance_list,
            race_control_list,
            race_position_list,
            fia_list
        )
        
    except Exception as e:
        logger.error(f"Error generating templates: {e}")
        return (
            False,
            "",
            "",
            {"year": None, "circuit": None},
            f"❌ Error: {str(e)[:80]}",
            dash.no_update, dash.no_update,
            dash.no_update, dash.no_update, dash.no_update,
            dash.no_update, dash.no_update, dash.no_update,
            dash.no_update, dash.no_update
        )


# ============================================================================
# DOCUMENT EDITOR MODAL CALLBACKS
# ============================================================================

@callback(
    Output('doc-editor-modal', 'is_open'),
    Output('doc-editor-title', 'children'),
    Output('doc-editor-path', 'children'),
    Output('doc-editor-textarea', 'value'),
    Output('doc-editor-store', 'data'),
    Output('doc-editor-status', 'children'),
    Input({'type': 'doc-edit-btn', 'index': ALL}, 'n_clicks'),
    Input('doc-editor-cancel-btn', 'n_clicks'),
    Input('doc-editor-save-btn', 'n_clicks'),
    State('doc-editor-textarea', 'value'),
    State('doc-editor-store', 'data'),
    prevent_initial_call=True
)
def handle_document_editor(
    btn_clicks, cancel_clicks, save_clicks,
    textarea_content, store_data
):
    """
    Handle document editor modal: open, save, cancel.
    
    This callback manages:
    - Opening modal when a document is clicked
    - Loading document content into textarea
    - Saving edited content back to file
    - Closing modal on cancel or after save
    """
    import base64
    import json
    from pathlib import Path
    
    # Debug: log what triggered the callback
    triggered = ctx.triggered
    triggered_id = ctx.triggered_id
    logger.debug(f"DOC EDITOR - triggered: {triggered}")
    logger.debug(f"DOC EDITOR - triggered_id: {triggered_id}")
    logger.debug(f"DOC EDITOR - btn_clicks: {btn_clicks}")
    
    # If no trigger info, prevent update
    if not triggered or triggered[0]['value'] is None:
        raise PreventUpdate
    
    # Cancel button - close modal
    if triggered_id == 'doc-editor-cancel-btn':
        return False, "", "", "", {"filepath": None}, ""
    
    # Save button - save content and close
    if triggered_id == 'doc-editor-save-btn':
        if store_data and store_data.get('filepath'):
            try:
                filepath = Path(store_data['filepath'])
                if filepath.exists() and filepath.suffix == '.md':
                    filepath.write_text(textarea_content, encoding='utf-8')
                    logger.info(f"Document saved: {filepath}")
                    return (
                        False, "", "", "",
                        {"filepath": None},
                        ""
                    )
                else:
                    return (
                        True,
                        f"📝 {store_data.get('filename', 'Document')}",
                        f"📁 {store_data.get('filepath', '')}",
                        textarea_content,
                        store_data,
                        "❌ Cannot save: invalid file path or not .md file"
                    )
            except Exception as e:
                logger.error(f"Error saving document: {e}")
                return (
                    True,
                    f"📝 {store_data.get('filename', 'Document')}",
                    f"📁 {store_data.get('filepath', '')}",
                    textarea_content,
                    store_data,
                    f"❌ Error saving: {str(e)[:50]}"
                )
        raise PreventUpdate
    
    # Document button click - check if any button was actually clicked
    # With ALL pattern, btn_clicks is a list, check if any is not None
    if btn_clicks and any(c is not None for c in btn_clicks):
        # Find which button was clicked from ctx.triggered
        triggered_prop = triggered[0].get('prop_id', '')
        logger.debug(f"DOC EDITOR - prop_id: {triggered_prop}")
        
        # prop_id format: {"type":"doc-edit-btn","index":"cat|idx|b64"}.n_clicks
        if 'doc-edit-btn' in triggered_prop:
            try:
                # Extract the JSON part before .n_clicks
                json_part = triggered_prop.rsplit('.', 1)[0]
                btn_info = json.loads(json_part)
                click_index = btn_info.get('index', '')
                
                logger.debug(f"DOC EDITOR - click_index: {click_index}")
                
                parts = click_index.split('|')
                if len(parts) >= 3:
                    encoded_path = parts[2]
                    
                    if encoded_path:
                        filepath = base64.b64decode(encoded_path.encode()).decode()
                        filename = Path(filepath).name if filepath else "Document"
                        
                        file_path = Path(filepath)
                        if file_path.exists():
                            content = file_path.read_text(encoding='utf-8')
                            logger.info(f"Opening document for edit: {filepath}")
                            return (
                                True,
                                f"📝 {filename}",
                                f"📁 {filepath}",
                                content,
                                {"filepath": filepath, "filename": filename},
                                ""
                            )
                        else:
                            return (
                                True,
                                f"📝 {filename}",
                                f"📁 {filepath}",
                                f"# File not found\n\nPath: {filepath}",
                                {"filepath": filepath, "filename": filename},
                                "⚠️ File does not exist"
                            )
                    else:
                        logger.warning(
                            f"No filepath in button index: {click_index}"
                        )
            except Exception as e:
                logger.error(f"Error parsing document button click: {e}")
                return (
                    True,
                    "📝 Error",
                    "",
                    f"# Error loading document\n\n{str(e)}",
                    {"filepath": None},
                    f"❌ Error: {str(e)[:50]}"
                )
    
    raise PreventUpdate


@callback(
    Output('dashboard-container', 'children'),
    Input('dashboard-selector', 'value'),
    Input('session-store', 'data'),
    Input('simulation-time-store', 'data'),  # Real-time updates
    State('driver-selector', 'value'),
    prevent_initial_call=False
)
def update_dashboards(
    selected_dashboards,
    session_data,
    simulation_time_data,
    focused_driver
):
    """Update visible dashboards based on selection."""
    global current_session_obj  # Declare at function start
    
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
                        dbc.CardHeader(html.H5("🏁 Race Overview", className="mb-0", style={"fontSize": "1.2rem"}), className="py-1"),
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
                        ], className="p-2")
                    ], className="mb-3", style={"height": "620px"})
                )
                continue
                
            try:
                if current_session_obj is None:
                    logger.warning("Race overview requested but no session loaded")
                    dashboards.append(
                        dbc.Card([
                            dbc.CardHeader(html.H5("🏁 Race Overview", className="mb-0", style={"fontSize": "1.2rem"}), className="py-1"),
                            dbc.CardBody([
                                html.P("No session loaded. Please select a race session from the sidebar.", 
                                       className="text-muted text-center p-5")
                            ], className="p-2")
                        ], className="mb-3", style={"height": "620px"})
                    )
                else:
                    logger.info("Rendering race overview dashboard...")
                    # Get session_key from loaded session
                    session_key = None
                    simulation_time = None
                    
                    if current_session_obj and hasattr(current_session_obj, 'session_key'):
                        session_key = current_session_obj.session_key
                    
                    # Get simulation time from callback parameter or controller
                    if simulation_time_data and 'time' in simulation_time_data:
                        simulation_time = simulation_time_data.get('time', 0.0)
                        logger.info(f"Using simulation time from store: {simulation_time:.1f}s")
                    elif simulation_controller is not None:
                        try:
                            simulation_time = simulation_controller.get_elapsed_seconds()
                            logger.info(f"Using simulation time from controller: {simulation_time:.1f}s")
                        except Exception as e:
                            logger.warning(f"Could not get simulation time: {e}")
                            simulation_time = 0.0
                    
                    # Get session start time from controller
                    session_start_time = None
                    if simulation_controller is not None:
                        session_start_time = pd.Timestamp(simulation_controller.start_time)
                    
                    # Get current lap from simulation controller
                    # This is the GLOBAL lap (OpenF1 format) from the leader
                    overview_current_lap = None
                    if simulation_controller is not None:
                        try:
                            overview_current_lap = simulation_controller.get_current_lap()
                            logger.info(
                                f"Passing current_lap to overview: {overview_current_lap}"
                            )
                        except Exception as e:
                            logger.warning(f"Could not get lap for overview: {e}")
                    
                    overview_content = race_overview_dashboard.render(
                        session_key=session_key,
                        simulation_time=simulation_time,
                        session_start_time=session_start_time,
                        current_lap=overview_current_lap
                    )
                    dashboards.append(
                        dbc.Card([
                            dbc.CardHeader(html.H5("🏁 Race Overview", className="mb-0", style={"fontSize": "1.2rem"}), className="py-1"),
                            dbc.CardBody(children=[overview_content], className="p-2")
                        ], className="mb-3", style={"height": "620px", "overflow": "auto"})
                    )
                    logger.info("Race overview dashboard rendered successfully")
                    
            except Exception as e:
                logger.error(f"Error creating race overview dashboard: {e}", exc_info=True)
                dashboards.append(
                    dbc.Card([
                        dbc.CardHeader(html.H5("🏁 Race Overview", className="mb-0", style={"fontSize": "1.2rem"}), className="py-1"),
                        dbc.CardBody([
                            html.P(f"Error loading race overview: {str(e)}", className="text-danger")
                        ], className="p-2")
                    ], className="mb-3", style={"height": "620px"})
                )
        
        elif dashboard_id == "race_control":
            # Race Control Dashboard (Flags, SC/VSC, Penalties)
            if not session_loaded:
                logger.info("Race control requested but session not yet loaded")
                dashboards.append(
                    dbc.Card([
                        dbc.CardHeader(html.H5(" Race Control", className="mb-0", style={"fontSize": "1.2rem"}), className="py-1"),
                        dbc.CardBody([
                            dcc.Loading(
                                html.Div([
                                    html.P("Loading session data...", className="text-center p-5 text-muted"),
                                    html.P("Please wait while we load the race control information.",
                                           className="text-center text-muted small")
                                ]),
                                type="circle",
                                color="#e10600"
                            )
                        ], className="p-2")
                    ], className="mb-3", style={"height": "620px"})
                )
                continue
            
            try:
                if current_session_obj is None:
                    logger.warning("Race control requested but no session loaded")
                    dashboards.append(
                        dbc.Card([
                            dbc.CardHeader(html.H5(" Race Control", className="mb-0", style={"fontSize": "1.2rem"}), className="py-1"),
                            dbc.CardBody([
                                html.P("No session loaded. Please select a race session from the sidebar.",
                                       className="text-muted text-center p-5")
                            ], className="p-2")
                        ], className="mb-3", style={"height": "620px"})
                    )
                else:
                    logger.info("Rendering race control dashboard...")
                    session_key = None
                    simulation_time = None
                    
                    if current_session_obj and hasattr(current_session_obj, 'session_key'):
                        session_key = current_session_obj.session_key
                    
                    if simulation_time_data and 'time' in simulation_time_data:
                        simulation_time = simulation_time_data.get('time', 0.0)
                        logger.info(f"Using simulation time from store: {simulation_time:.1f}s")
                    elif simulation_controller is not None:
                        try:
                            simulation_time = simulation_controller.get_elapsed_seconds()
                            logger.info(f"Using simulation time from controller: {simulation_time:.1f}s")
                        except Exception as e:
                            logger.warning(f"Could not get simulation time: {e}")
                            simulation_time = 0.0
                    
                    session_start_time = None
                    if simulation_controller is not None:
                        session_start_time = pd.Timestamp(simulation_controller.start_time)
                    
                    # Calculate current lap
                    current_lap = None
                    if simulation_controller is not None:
                        try:
                            # Get OpenF1 internal lap
                            openf1_lap = simulation_controller.get_current_lap()
                            # Convert to visual racing lap (OpenF1 lap 3 = racing lap 1)
                            current_lap = max(1, openf1_lap - 2) if openf1_lap > 2 else 1
                            logger.info(f"Current lap from controller: OpenF1 {openf1_lap} → Racing {current_lap}")
                        except Exception as e:
                            logger.warning(f"Could not get lap from controller: {e}")
                            current_lap = None
                    
                    control_content = race_control_dashboard.render(
                        session_key=session_key,
                        simulation_time=simulation_time,
                        session_start_time=session_start_time,
                        focused_driver=focused_driver if focused_driver != 'none' else None,
                        current_lap=current_lap
                    )
                    dashboards.append(control_content)
                    logger.info("Race control dashboard rendered successfully")
                    
            except Exception as e:
                logger.error(f"Error creating race control dashboard: {e}", exc_info=True)
                dashboards.append(
                    dbc.Card([
                        dbc.CardHeader(html.H5(" Race Control", className="mb-0", style={"fontSize": "1.2rem"}), className="py-1"),
                        dbc.CardBody([
                            html.P(f"Error loading race control: {str(e)}", className="text-danger")
                        ], className="p-2")
                    ], className="mb-3", style={"height": "620px"})
                )
        
        elif dashboard_id == "weather":
            # Weather Dashboard (Phase 1 MVP) - Compact 33% width
            if not session_loaded:
                logger.info("Weather dashboard requested but session not yet loaded")
                dashboards.append(
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader(html.H5("🌤️ Weather", className="mb-0"), className="py-1"),
                            dbc.CardBody([
                                dcc.Loading(
                                    html.Div([
                                        html.P("Loading...", className="text-center p-3 text-muted", style={"fontSize": "0.8rem"}),
                                    ]),
                                    type="circle",
                                    color="#e10600"
                                )
                            ], className="p-2")
                        ], className="mb-3 h-100")
                    ], width=4, className="d-flex")
                )
            else:
                logger.info("Rendering weather dashboard...")
                try:
                    # Get simulation time
                    simulation_time = None
                    if simulation_time_data and 'time' in simulation_time_data:
                        simulation_time = simulation_time_data.get('time', 0.0)
                    elif simulation_controller is not None:
                        try:
                            simulation_time = simulation_controller.get_elapsed_seconds()
                        except Exception:
                            simulation_time = 0.0
                    
                    # Generate weather content
                    weather_content = weather_dashboard.render_weather_content(
                        session_key=current_session_obj.session_key if current_session_obj else None,
                        simulation_time=simulation_time
                    )
                    
                    dashboards.append(
                        dbc.Col([weather_content], width=4)
                    )
                except Exception as e:
                    logger.error(f"Error rendering weather dashboard: {e}", exc_info=True)
                    dashboards.append(
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader(html.H5("🌤️ Weather", className="mb-0")),
                                dbc.CardBody([
                                    html.P(f"Error: {str(e)}", className="text-danger text-center")
                                ])
                            ])
                        ], width=4)
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
    
    # Layout dashboards:
    # Grid layout: 2 rows x 3 columns (33% width each, 50vh height each row)
    # No vertical scroll - all dashboards fit in viewport
    if len(dashboards) == 0:
        return html.Div("No dashboards selected", className="text-center text-muted p-5")
    
    # Wrap all dashboards in standardized columns with fixed height
    wrapped_dashboards = []
    for idx, dash in enumerate(dashboards):
        # Add border-right to all columns except every 3rd one (for visual separation)
        border_style = {} if (idx + 1) % 3 == 0 else {"borderRight": "1px solid #000"}
        
        if isinstance(dash, dbc.Col):
            # Already wrapped (e.g., weather) - recreate with height constraint
            wrapped_dashboards.append(
                dbc.Col(
                    dash.children,
                    width=4,
                    style={"height": "50vh", "overflow": "hidden", "maxWidth": "31.5%", **border_style},
                    className="mb-2"
                )
            )
        else:
            # Wrap in 4-column (31.5% to avoid horizontal scroll) with fixed height
            wrapped_dashboards.append(
                dbc.Col(
                    dash, 
                    width=4, 
                    style={"height": "50vh", "overflow": "hidden", "maxWidth": "31.5%", **border_style},
                    className="mb-2"
                )
            )
    
    # Create grid: 3 dashboards per row
    rows = []
    for i in range(0, len(wrapped_dashboards), 3):
        row_dashboards = wrapped_dashboards[i:i+3]
        rows.append(
            dbc.Row(
                row_dashboards, 
                className="g-0",
                style={"height": "50vh"}
            )
        )
    
    return html.Div(
        rows,
        style={
            "height": "100%",
            "overflowY": "hidden"
        }
    )


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
    
    # Toggle play/pause state (simulation always starts from 0)
    is_playing = simulation_controller.toggle_play_pause()
    logger.info(f"Play/Pause toggled: is_playing={is_playing}")
    
    if is_playing:
        return "⏸️", "warning", False, "Pause simulation"
    else:
        return "▶️", "success", True, "Play simulation"


# Callback: Restart simulation
@callback(
    Output('restart-btn', 'n_clicks'),
    Input('restart-btn', 'n_clicks'),
    prevent_initial_call=True
)
def restart_simulation(n_clicks):
    """Restart simulation from beginning."""
    global simulation_controller
    
    if simulation_controller:
        simulation_controller.restart()
    
    raise PreventUpdate  # Don't update anything, just execute the action


# Callback: Change simulation speed
@callback(
    Output('speed-slider', 'value'),
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
            return speed
        except ValueError as e:
            logger.error(f"Invalid speed value: {e}")
            return 1.0
    
    return speed


# Callback: Handle lap jump buttons (forward/backward)
# These MUST update simulation-time-store to trigger dashboard refresh
@callback(
    Output('simulation-time-store', 'data', allow_duplicate=True),
    Input('back-btn', 'n_clicks'),
    Input('forward-btn', 'n_clicks'),
    State('simulation-time-store', 'data'),
    prevent_initial_call=True
)
def handle_lap_jumps(back_clicks, forward_clicks, current_time_data):
    """Handle lap jump buttons and update simulation time store."""
    global simulation_controller
    
    if simulation_controller is None:
        raise PreventUpdate
    
    triggered = ctx.triggered_id
    old_lap = simulation_controller.get_current_lap()
    
    if triggered == 'back-btn':
        simulation_controller.jump_backward(90)  # ~90 seconds per lap
        logger.info("Jumped to previous lap")
    elif triggered == 'forward-btn':
        simulation_controller.jump_forward(90)  # ~90 seconds per lap
        logger.info("Jumped to next lap")
    else:
        raise PreventUpdate
    
    # Return updated time to trigger dashboard refresh
    new_time = simulation_controller.get_elapsed_seconds()
    new_lap = simulation_controller.get_current_lap()
    
    logger.info(f"Lap jump: {old_lap} -> {new_lap} (time={new_time:.1f}s)")
    
    return {
        'time': new_time,
        'timestamp': datetime.now().timestamp()
    }


# Callback: Update simulation progress display every second
@callback(
    Output('simulation-progress', 'children'),
    Input('simulation-interval', 'n_intervals'),
    prevent_initial_call=False
)
def update_simulation_progress(n_intervals):
    """Update the simulation progress display in real-time."""
    global simulation_controller
    
    logger.info(f"update_simulation_progress called: n_intervals={n_intervals}, controller={'present' if simulation_controller else 'None'}")
    
    if simulation_controller is None:
        return "⏱️ Not started"
    
    try:
        # Update simulation time
        simulation_controller.update()
        logger.info("Controller updated successfully")
        
        # Get progress information
        remaining = simulation_controller.get_remaining_time()
        logger.info(f"Remaining time: {remaining}")
        
        # Get EXACT current lap from simulation controller (no estimation)
        current_lap = simulation_controller.get_current_lap()
        logger.info(f"Current lap (OpenF1 internal): {current_lap}")
        
        # Convert to VISUAL racing lap
        # OpenF1 has 2 laps before racing starts (lap 3 = racing lap 1)
        visual_lap = max(1, current_lap - 2)
        total_laps = 57  # 57 racing laps
        
        logger.info(f"Visual racing lap: {visual_lap}/{total_laps}")
        
        # Format remaining time
        remaining_minutes = int(remaining.total_seconds() // 60)
        remaining_seconds = int(remaining.total_seconds() % 60)
        
        # Get current speed multiplier
        speed = simulation_controller.speed_multiplier
        
        progress_text = f"⏱️ Lap {int(visual_lap)}/{int(total_laps)} | ⏳ {remaining_minutes}m {remaining_seconds}s left | 🚀 {speed}x"
        logger.info(f"Progress text: {progress_text}")
        
        return progress_text
    except Exception as e:
        logger.error(f"Error in update_simulation_progress: {e}", exc_info=True)
        return f"⏱️ Error: {str(e)}"


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
    Output('simulation-time-store', 'data'),
    Input('simulation-interval', 'n_intervals'),
    State('dashboard-selector', 'value'),
    prevent_initial_call=True
)
def update_simulation_time_store(n_intervals, selected_dashboards):
    """Update simulation time store for all dashboards to consume."""
    global simulation_controller
    
    # Only update if race_overview dashboard is selected
    if not selected_dashboards or 'race_overview' not in selected_dashboards:
        raise PreventUpdate
    
    # Check if simulation is running
    if simulation_controller is None:
        raise PreventUpdate
    
    # Only update if simulation is actively playing
    if not simulation_controller.is_playing:
        raise PreventUpdate
    
    try:
        # Get current simulation time
        simulation_time = simulation_controller.get_elapsed_seconds()
        
        return {
            'time': simulation_time,
            'timestamp': n_intervals  # Force update even if time is same
        }
        
    except Exception as e:
        logger.error(
            f"Error updating simulation time store: {e}",
            exc_info=True
        )
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
                        pd.notna(driver_laps['Time']) &  # type: ignore
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
    logger.info("Open: http://localhost:8502")
    logger.info("="*60)

    # Initialize session with last completed race (dynamic from OpenF1)
    last_race = get_last_completed_race_context()
    session.race_context = last_race
    logger.info(
        f"Initialized with {last_race.country} GP "
        f"(Round {last_race.round_number}, {last_race.year})"
    )

    app.run(debug=False, port=8502)
