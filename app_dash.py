"""
F1 Strategist AI - Main Dash Application.

Multi-dashboard F1 strategy platform with live and simulation modes.
Migrated from Streamlit to Dash for better layout control.
"""

import asyncio
import json
import logging
import os
import sys
import math
import importlib
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

import dash
from dash import Dash, html, dcc, Input, Output, State, callback, ctx, Patch, ALL, no_update
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
from src.session.event_detector import RaceEventDetector, RaceEvent

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
from src.dashboards_dash.telemetry_dashboard import TelemetryDashboard
from src.dashboards_dash import weather_dashboard

# RAG Manager for document loading
from src.rag.rag_manager import get_rag_manager, reset_rag_manager
from src.rag.template_generator import get_template_generator
from src.rag.document_loader import DocumentLoader

# LLM providers for AI responses
from dotenv import load_dotenv
from src.llm.hybrid_router import HybridRouter
from src.llm.claude_provider import ClaudeProvider
from src.llm.gemini_provider import GeminiProvider
from src.llm.provider import LLMProvider
from src.llm.models import LLMConfig, LLMResponse
from src.llm.config import get_claude_config, get_gemini_config

# Centralized logging configuration
from src.utils.logging_config import (
    setup_logging, get_logger, LogCategory,
    enable_category, disable_category, apply_debug_profile
)

# Load environment variables for API keys
load_dotenv()

# Initialize centralized logging system
# By default: only STARTUP and critical messages are shown
# To enable debugging, use: apply_debug_profile('telemetry') or enable_category(LogCategory.SIMULATION)
setup_logging(console_level=logging.INFO)

# Get loggers for different categories
logger = get_logger(LogCategory.STARTUP)  # Main app logger (startup messages)
sim_logger = get_logger(LogCategory.SIMULATION)  # Simulation timing
dash_logger = get_logger(LogCategory.DASHBOARD)  # Dashboard rendering
telem_logger = get_logger(LogCategory.TELEMETRY)  # Telemetry data
overview_logger = get_logger(LogCategory.RACE_OVERVIEW)  # Race overview
control_logger = get_logger(LogCategory.RACE_CONTROL)  # Race control
api_logger = get_logger(LogCategory.API)  # API calls
chat_logger = get_logger(LogCategory.CHAT)  # Chat/AI
proactive_logger = get_logger(LogCategory.PROACTIVE)  # Proactive AI alerts

# Enable PROACTIVE and CHAT debugging by default for development
enable_category(LogCategory.PROACTIVE)
enable_category(LogCategory.CHAT)

# Uncomment to enable specific debugging:
# enable_category(LogCategory.SIMULATION)  # See simulation updates
# enable_category(LogCategory.TELEMETRY)   # See DRS/telemetry data
# apply_debug_profile('race')              # Enable race overview + control

# Initialize OpenF1 provider with SSL verification disabled for corporate proxies
openf1_provider = OpenF1DataProvider(verify_ssl=False)

# Initialize Race Overview Dashboard
race_overview_dashboard = RaceOverviewDashboard(openf1_provider)

# Initialize Race Control Dashboard
race_control_dashboard = RaceControlDashboard(openf1_provider)

# Initialize Telemetry Dashboard
telemetry_dashboard = TelemetryDashboard(openf1_provider)

# Initialize Race Event Detector for proactive AI alerts
event_detector = RaceEventDetector(openf1_provider)

# Bootstrap Icons CDN for icon support
BOOTSTRAP_ICONS = "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css"

# Initialize Dash app with F1 theme
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG, BOOTSTRAP_ICONS],
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

# LLM provider singleton (lazy initialization)
_llm_provider: Optional[LLMProvider] = None
_llm_provider_type: Optional[str] = None  # 'hybrid', 'claude', 'gemini'


# Circuit total laps lookup table (works for both LIVE and historical)
# This is the authoritative source - matches official F1 race distances
CIRCUIT_TOTAL_LAPS = {
    "bahrain": 57,
    "sakhir": 57,
    "saudi": 50,
    "jeddah": 50,
    "australia": 58,
    "melbourne": 58,
    "japan": 53,
    "suzuka": 53,
    "china": 56,
    "shanghai": 56,
    "miami": 57,
    "monaco": 78,
    "monte carlo": 78,
    "spain": 66,
    "barcelona": 66,
    "canada": 70,
    "montreal": 70,
    "austria": 71,
    "spielberg": 71,
    "britain": 52,
    "silverstone": 52,
    "hungary": 70,
    "hungaroring": 70,
    "belgium": 44,
    "spa": 44,
    "netherlands": 72,
    "zandvoort": 72,
    "italy": 53,
    "monza": 53,
    "singapore": 62,
    "marina bay": 62,
    "qatar": 57,
    "lusail": 57,
    "usa": 56,
    "austin": 56,
    "cota": 56,
    "united states": 56,
    "las vegas": 50,
    "vegas": 50,
    "mexico": 71,
    "brazil": 71,
    "interlagos": 71,
    "sao paulo": 71,
    "abu dhabi": 58,
    "yas marina": 58,
    "azerbaijan": 51,
    "baku": 51,
    "imola": 63,
    "emilia": 63,
}


def _get_total_laps_for_circuit(circuit_name: str) -> int:
    """
    Get total racing laps for a circuit by name.
    
    Works for both LIVE and historical sessions by using
    the circuit name lookup table.
    
    Args:
        circuit_name: Circuit name (e.g., 'Las Vegas', 'Silverstone')
    
    Returns:
        Total racing laps for the circuit, or 57 as default
    """
    if not circuit_name:
        return 57
    
    circuit_lower = circuit_name.lower().strip()
    
    # Direct lookup
    if circuit_lower in CIRCUIT_TOTAL_LAPS:
        return CIRCUIT_TOTAL_LAPS[circuit_lower]
    
    # Partial match (e.g., "Las Vegas Street Circuit" -> "las vegas")
    for key, laps in CIRCUIT_TOTAL_LAPS.items():
        if key in circuit_lower or circuit_lower in key:
            return laps
    
    logger.warning(
        f"Unknown circuit '{circuit_name}', using default 57 laps"
    )
    return 57


def _calculate_total_laps(session_obj, circuit_name: Optional[str] = None) -> int:
    """
    Calculate total racing laps for a session.
    
    Strategy:
    1. If circuit_name provided, use lookup table (best for LIVE)
    2. Try to get from session lap data (for historical/completed races)
    3. Fall back to circuit lookup from session info
    4. Default to 57
    
    Args:
        session_obj: FastF1/OpenF1 session object
        circuit_name: Optional circuit name for direct lookup
    
    Returns:
        Total racing laps (int)
    """
    # Priority 1: Use circuit name if provided
    if circuit_name:
        laps = _get_total_laps_for_circuit(circuit_name)
        if laps != 57:  # Found a match
            return laps
    
    # Priority 2: Try to get circuit from session and use lookup
    try:
        if session_obj:
            # Try to get circuit name from session
            session_circuit = None
            if hasattr(session_obj, 'event') and session_obj.event is not None:
                if hasattr(session_obj.event, 'Location'):
                    session_circuit = session_obj.event.Location
                elif hasattr(session_obj.event, 'CircuitName'):
                    session_circuit = session_obj.event.CircuitName
            
            if session_circuit:
                laps = _get_total_laps_for_circuit(session_circuit)
                if laps != 57:
                    return laps
            
            # Priority 3: Calculate from actual lap data (historical only)
            if hasattr(session_obj, 'laps') and not session_obj.laps.empty:
                max_lap = session_obj.laps['LapNumber'].max()
                if pd.notna(max_lap) and max_lap > 10:
                    # Subtract 2 for formation laps
                    calculated = max(1, int(max_lap) - 2)
                    logger.info(
                        f"Calculated total_laps from data: {calculated}"
                    )
                    return calculated
    except Exception as e:
        logger.warning(f"Error calculating total_laps: {e}")
    
    return 57  # Default fallback


def get_llm_provider() -> Optional[LLMProvider]:
    """
    Get or initialize the LLM provider (singleton).
    
    Logic:
    - If both keys configured: Use HybridRouter (balances by complexity)
    - If only Claude key: Use ClaudeProvider only
    - If only Gemini key: Use GeminiProvider only
    - If no keys: Return None (will show error in chatbot)
    """
    global _llm_provider, _llm_provider_type
    
    if _llm_provider is not None:
        return _llm_provider
    
    # Get API keys from environment
    claude_api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    gemini_api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    
    # No keys configured
    if not claude_api_key and not gemini_api_key:
        logger.warning(
            "No LLM API keys configured. "
            "Set ANTHROPIC_API_KEY or GOOGLE_API_KEY in Configuration."
        )
        return None
    
    try:
        # Case 1: Both keys - use HybridRouter for smart routing
        if claude_api_key and gemini_api_key:
            claude_config = get_claude_config()
            claude_config.max_tokens = 2048
            claude_config.temperature = 0.7

            gemini_config = get_gemini_config()
            gemini_config.max_tokens = 2048
            gemini_config.temperature = 0.7
            gemini_config.extra_params["enable_thinking"] = False
            _llm_provider = HybridRouter(
                claude_config=claude_config,
                gemini_config=gemini_config
            )
            _llm_provider_type = 'hybrid'
            logger.info(
                "LLM initialized: HybridRouter (Claude + Gemini, "
                "routes by complexity)"
            )
        
        # Case 2: Only Claude key
        elif claude_api_key:
            claude_config = get_claude_config()
            claude_config.max_tokens = 2048
            claude_config.temperature = 0.7
            _llm_provider = ClaudeProvider(claude_config)
            _llm_provider_type = 'claude'
            logger.info("LLM initialized: Claude only")
        
        # Case 3: Only Gemini key
        elif gemini_api_key:
            gemini_config = get_gemini_config()
            gemini_config.max_tokens = 2048
            gemini_config.temperature = 0.7
            gemini_config.extra_params["enable_thinking"] = False
            _llm_provider = GeminiProvider(gemini_config)
            _llm_provider_type = 'gemini'
            logger.info("LLM initialized: Gemini only")
        
        return _llm_provider
        
    except Exception as e:
        logger.error(f"Failed to initialize LLM provider: {e}")
        return None


def get_llm_provider_type() -> Optional[str]:
    """Get the type of LLM provider currently in use."""
    return _llm_provider_type


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
            ], className="text-center mb-1"),
            
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
                        className="mb-1"
                    )
                ], title="🎮 Mode", className="mb-1")
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
                        className="mb-1",
                        clearable=False
                    ),
                    
                    dbc.Label("Circuit", className="fw-bold"),
                    dcc.Dropdown(
                        id='circuit-selector',
                        options=[],  # Will be populated by callback
                        value=None,
                        className="mb-1",
                        clearable=False
                    ),
                    
                    dbc.Label("Session", className="fw-bold"),
                    dcc.Dropdown(
                        id='session-selector',
                        options=[],  # Will be populated by callback
                        value=None,
                        className="mb-1",
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
                                className="mb-1",
                                clearable=True
                            ),
                            type="circle",
                            color="#e10600"
                        )
                    ])
                ], title="🗺️ Context", className="mb-1")
            ], start_collapsed=False),
            
            html.Hr(),
            
            # Dashboard selector (collapsed)
            dbc.Accordion([
                dbc.AccordionItem([
                    dbc.Checklist(
                        id="dashboard-selector",
                        options=[
                            {"label": " AI Assistant", "value": "ai"},
                            {
                                "label": " Race Overview",
                                "value": "race_overview",
                                "disabled": True  # Must stay visible in sim/live
                            },
                            {"label": " Race Control", "value": "race_control"},
                            {"label": " Weather", "value": "weather"},
                            {"label": " Telemetry", "value": "telemetry"},
                            # Phase 2 Dashboards (Coming Soon)
                            # {"label": " Tire Strategy", "value": "tires"},
                            # {"label": " Lap Analysis", "value": "laps"},
                            # {"label": " Qualifying", "value": "qualifying"},
                        ],
                        value=["ai", "race_overview", "race_control", "weather", "telemetry"],
                        className="mb-1"
                    )
                ], title="📊 Dashboards", className="mb-1")
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
                                className="w-100 mb-1"
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
                                className="w-100 mb-1"
                            ),
                            dbc.Tooltip("Restart simulation", target="restart-btn", placement="top")
                        ], width=6)
                    ]),
                    
                    dbc.Label("Speed", className="mt-1"),
                    dcc.Slider(
                        id='speed-slider',
                        min=1.0,
                        max=10.0,
                        step=0.5,
                        value=1.0,
                        marks={
                            1.0: '1x',
                            2.0: '2x',
                            4.0: '4x',
                            6.0: '6x',
                            8.0: '8x',
                            10.0: '10x'
                        },
                        className="mb-1"
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
                        className="text-center mt-1 small text-muted"
                    ),
                    
                    # Interval for updating simulation progress
                    # Base interval is 1.5 seconds, adjusted dynamically by speed
                    dcc.Interval(
                        id='simulation-interval',
                        interval=1500,  # milliseconds (1.5 seconds base)
                        n_intervals=0,
                        disabled=True  # Start disabled, enable when playing
                    )
                ], title="⏯️ Playback", className="mb-1", id="playback-accordion-item")
            ], start_collapsed=True, id="playback-accordion"),
            
            html.Hr(),
            
            # Hidden dummy components for removed FIA Manager (to keep callbacks working)
            html.Div([
                dcc.Dropdown(id='fia-year-selector', style={'display': 'none'}),
                html.Div(id='fia-reg-status', style={'display': 'none'}),
                html.Div(id='fia-existing-regs', style={'display': 'none'}),
                dcc.Upload(id='fia-reg-upload', style={'display': 'none'}),
                html.Div(id='fia-upload-preview', style={'display': 'none'}),
            ], style={'display': 'none'}),
            
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
                    ], className="mb-1"),
                    
                    # Document list by category
                    html.Div([
                        # Global Documents
                        html.Div([
                            html.Div([
                                html.H6(
                                    "🌐 Global",
                                    className="text-info mb-1 d-inline-block",
                                    style={'fontSize': '0.85rem'}
                                ),
                                html.Button(
                                    "+",
                                    id={'type': 'rag-upload-btn', 'category': 'global'},
                                    n_clicks=0,
                                    className="btn btn-sm btn-outline-info ms-2",
                                    style={'fontSize': '0.7rem', 'padding': '0px 6px', 'lineHeight': '1.2'}
                                )
                            ], className="d-flex align-items-center"),
                            html.Div(
                                id="rag-global-docs",
                                className="ps-2 small text-muted"
                            )
                        ], className="mb-1"),
                        
                        # Strategy Documents
                        html.Div([
                            html.Div([
                                html.H6(
                                    "📋 Strategy",
                                    className="text-info mb-1 d-inline-block",
                                    style={'fontSize': '0.85rem'}
                                ),
                                html.Button(
                                    "+",
                                    id={'type': 'rag-upload-btn', 'category': 'strategy'},
                                    n_clicks=0,
                                    className="btn btn-sm btn-outline-info ms-2",
                                    style={'fontSize': '0.7rem', 'padding': '0px 6px', 'lineHeight': '1.2'}
                                )
                            ], className="d-flex align-items-center"),
                            html.Div(
                                id="rag-strategy-docs",
                                className="ps-2 small text-muted"
                            )
                        ], className="mb-1"),
                        
                        # Weather Documents
                        html.Div([
                            html.Div([
                                html.H6(
                                    "🌦️ Weather",
                                    className="text-info mb-1 d-inline-block",
                                    style={'fontSize': '0.85rem'}
                                ),
                                html.Button(
                                    "+",
                                    id={'type': 'rag-upload-btn', 'category': 'weather'},
                                    n_clicks=0,
                                    className="btn btn-sm btn-outline-info ms-2",
                                    style={'fontSize': '0.7rem', 'padding': '0px 6px', 'lineHeight': '1.2'}
                                )
                            ], className="d-flex align-items-center"),
                            html.Div(
                                id="rag-weather-docs",
                                className="ps-2 small text-muted"
                            )
                        ], className="mb-1"),
                        
                        # Performance Documents
                        html.Div([
                            html.Div([
                                html.H6(
                                    "📊 Performance",
                                    className="text-info mb-1 d-inline-block",
                                    style={'fontSize': '0.85rem'}
                                ),
                                html.Button(
                                    "+",
                                    id={'type': 'rag-upload-btn', 'category': 'performance'},
                                    n_clicks=0,
                                    className="btn btn-sm btn-outline-info ms-2",
                                    style={'fontSize': '0.7rem', 'padding': '0px 6px', 'lineHeight': '1.2'}
                                )
                            ], className="d-flex align-items-center"),
                            html.Div(
                                id="rag-performance-docs",
                                className="ps-2 small text-muted"
                            )
                        ], className="mb-1"),
                        
                        # Race Control Documents
                        html.Div([
                            html.Div([
                                html.H6(
                                    "🚦 Race Control",
                                    className="text-info mb-1 d-inline-block",
                                    style={'fontSize': '0.85rem'}
                                ),
                                html.Button(
                                    "+",
                                    id={'type': 'rag-upload-btn', 'category': 'race_control'},
                                    n_clicks=0,
                                    className="btn btn-sm btn-outline-info ms-2",
                                    style={'fontSize': '0.7rem', 'padding': '0px 6px', 'lineHeight': '1.2'}
                                )
                            ], className="d-flex align-items-center"),
                            html.Div(
                                id="rag-race-control-docs",
                                className="ps-2 small text-muted"
                            )
                        ], className="mb-1"),
                        
                        # Race Position Documents
                        html.Div([
                            html.Div([
                                html.H6(
                                    "🏁 Positions",
                                    className="text-info mb-1 d-inline-block",
                                    style={'fontSize': '0.85rem'}
                                ),
                                html.Button(
                                    "+",
                                    id={'type': 'rag-upload-btn', 'category': 'race_position'},
                                    n_clicks=0,
                                    className="btn btn-sm btn-outline-info ms-2",
                                    style={'fontSize': '0.7rem', 'padding': '0px 6px', 'lineHeight': '1.2'}
                                )
                            ], className="d-flex align-items-center"),
                            html.Div(
                                id="rag-race-position-docs",
                                className="ps-2 small text-muted"
                            )
                        ], className="mb-1"),
                        
                        # FIA Regulations Documents
                        html.Div([
                            html.Div([
                                html.H6(
                                    "📖 FIA Regulations",
                                    className="text-info mb-1 d-inline-block",
                                    style={'fontSize': '0.85rem'}
                                ),
                                html.Button(
                                    "+",
                                    id={'type': 'rag-upload-btn', 'category': 'fia'},
                                    n_clicks=0,
                                    className="btn btn-sm btn-outline-info ms-2",
                                    style={'fontSize': '0.7rem', 'padding': '0px 6px', 'lineHeight': '1.2'}
                                )
                            ], className="d-flex align-items-center"),
                            html.Div(
                                id="rag-fia-docs",
                                className="ps-2 small text-muted"
                            )
                        ], className="mb-1"),
                    ]),
                    
                    # Hidden Upload Components (one per category)
                    html.Div([
                        dcc.Upload(
                            id={'type': 'rag-upload-input', 'category': cat},
                            accept='.pdf,.docx,.md',
                            max_size=10*1024*1024,  # 10MB
                            style={'display': 'none'}
                        ) for cat in ['global', 'strategy', 'weather', 'performance', 'race_control', 'race_position', 'fia']
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
                    ], className="mt-1 d-flex"),
                    
                    # RAG reload status message
                    html.Div(
                        id="rag-reload-status",
                        className="small text-muted mt-1"
                    )
                ], title="📚 RAG Documents", className="mb-1")
            ], start_collapsed=True, id="rag-accordion"),
            
            html.Hr(),
            
            # Menu (collapsed)
            dbc.Accordion([
                dbc.AccordionItem([
                    # Config option
                    html.Div([
                        # API Keys
                        html.Div([
                            html.P("🔑 API Keys", className="fw-bold mb-1"),
                            dbc.Label("Claude API Key", className="small"),
                            dbc.Input(
                                id='claude-api-key-input',
                                type="password",
                                placeholder="Enter Anthropic Claude API Key",
                                value=os.getenv("ANTHROPIC_API_KEY", ""),
                                className="mb-1",
                                style={'fontSize': '0.85rem'}
                            ),
                            dbc.Label("Gemini API Key", className="small"),
                            dbc.Input(
                                id='gemini-api-key-input',
                                type="password",
                                placeholder="Enter Google Gemini API Key",
                                value=os.getenv("GOOGLE_API_KEY", ""),
                                className="mb-1",
                                style={'fontSize': '0.85rem'}
                            ),
                            dbc.Label("OpenF1 API Key", className="small"),
                            dbc.Input(
                                id='openf1-api-key-input',
                                type="password",
                                placeholder="Enter OpenF1 API Key",
                                value=os.getenv("OPENF1_API_KEY", ""),
                                className="mb-1",
                                style={'fontSize': '0.85rem'}
                            ),
                            dbc.Button(
                                "💾 Save Keys",
                                id="save-api-keys-btn",
                                color="primary",
                                size="sm",
                                className="w-100 mb-1"
                            ),
                            html.Div(id="api-keys-save-status", className="small text-muted")
                        ], className="mb-1"),
                        
                        # LLM Settings
                        html.Div([
                            html.P("🤖 LLM Settings", className="fw-bold mb-1"),
                            dbc.Label("Provider", className="small"),
                            dcc.Dropdown(
                                id='llm-provider-selector',
                                options=[
                                    {'label': 'Hybrid (Auto)', 'value': 'hybrid'},
                                    {'label': 'Claude Only', 'value': 'claude'},
                                    {'label': 'Gemini Only', 'value': 'gemini'}
                                ],
                                value='hybrid',
                                className="mb-1",
                                clearable=False,
                                style={'fontSize': '0.85rem'}
                            )
                        ], className="mb-1"),
                        
                        # Data Sources
                        html.Div([
                            html.P("📂 Data Sources", className="fw-bold mb-1"),
                            html.Small(f"Cache: ./cache", className="text-muted d-block"),
                            html.Small(f"Vector Store: ChromaDB", className="text-muted d-block")
                        ])
                    ])
                ], title="⚙️ Configuration", className="mb-1")
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

# Responsive CSS is loaded from assets/responsive_grid.css automatically by Dash

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
    dcc.Store(id='current-lap-store', data={'lap': 1, 'total': 57}),  # For fast lap updates
    dcc.Store(id='weather-last-update-store', data={'timestamp': 0, 'state': None}),
    
    # Telemetry comparison driver store
    dcc.Store(id='telemetry-comparison-store', data={'driver': None}),
    
    # AI Chat stores
    dcc.Store(id='chat-messages-store', storage_type='memory', data=[]),
    dcc.Store(id='chat-pending-query-store', data={'query': None, 'quick': None}),
    dcc.Store(id='proactive-last-check-store', data={'last_lap': 0}),
    
    # Interval for proactive AI alerts (every 15 seconds when simulation running)
    dcc.Interval(
        id='proactive-check-interval',
        interval=15000,  # 15 seconds
        n_intervals=0,
        disabled=True  # Enable when simulation is playing
    ),
    
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
    
    # Document Upload Confirmation Modal
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("📤 Confirm Document Upload")),
        dbc.ModalBody([
            # File info section
            html.Div([
                html.H6("📄 File Information", className="text-info mb-2"),
                html.Div(id="upload-file-info", className="mb-3")
            ]),
            
            # Category selection
            html.Div([
                html.H6("📂 Category", className="text-info mb-2"),
                dcc.Dropdown(
                    id='upload-category-override',
                    options=[
                        {'label': '🌐 Global', 'value': 'global'},
                        {'label': '📋 Strategy', 'value': 'strategy'},
                        {'label': '🌦️ Weather', 'value': 'weather'},
                        {'label': '📊 Performance', 'value': 'performance'},
                        {'label': '🚦 Race Control', 'value': 'race_control'},
                        {'label': '🏁 Positions', 'value': 'race_position'},
                        {'label': '📖 FIA Regulations', 'value': 'fia'},
                    ],
                    placeholder="Select document category...",
                    className="mb-3"
                ),
            ]),
            
            # Conversion preview (collapsible)
            html.Div([
                dbc.Button(
                    "👁️ Preview Converted Content",
                    id="upload-preview-toggle",
                    color="info",
                    size="sm",
                    className="mb-2"
                ),
                dbc.Collapse([
                    html.Pre(
                        id="upload-preview-content",
                        className="bg-dark text-light p-2",
                        style={"maxHeight": "200px", "overflow": "auto", "fontSize": "0.75rem"}
                    )
                ], id="upload-preview-collapse", is_open=False)
            ], className="mb-3"),
            
            # Target path
            html.Div([
                html.H6("📍 Target Path", className="text-info mb-2"),
                html.Code(id="upload-target-path", className="d-block p-2 bg-dark text-light")
            ], className="mb-3"),
            
            # Filename editor
            html.Div([
                html.H6("✏️ Filename", className="text-info mb-2"),
                dbc.Input(
                    id="upload-filename-edit",
                    type="text",
                    placeholder="Enter filename (without extension)...",
                    className="mb-2"
                ),
                html.Small("Extension .md will be added automatically", className="text-muted")
            ], className="mb-3"),
            
            # Duplicate warning
            html.Div(id="upload-duplicate-warning", className="mb-2"),
            
            # Processing status/spinner - This will show the loading overlay
            html.Div(id="upload-processing-status", className="text-center"),
            
            # Loading overlay (hidden by default, shown during processing)
            html.Div(
                id="upload-loading-overlay",
                children=[
                    html.Div([
                        dbc.Spinner(color="primary", size="lg"),
                        html.H5("🔄 Processing...", className="mt-3 text-primary"),
                        html.P("Converting PDF to markdown and indexing...", className="text-muted"),
                        html.P("This may take 10-30 seconds for large PDFs", className="text-muted small"),
                    ], className="text-center")
                ],
                style={
                    "display": "none",  # Hidden by default
                    "position": "absolute",
                    "top": 0,
                    "left": 0,
                    "right": 0,
                    "bottom": 0,
                    "backgroundColor": "rgba(0, 0, 0, 0.8)",
                    "zIndex": 1000,
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "center",
                    "borderRadius": "0.3rem"
                }
            )
        ], style={"position": "relative"}),  # Make ModalBody relative for overlay positioning
        dbc.ModalFooter([
            dbc.Button(
                "✅ Upload & Index",
                id="upload-confirm-btn",
                color="primary",
                className="me-2"
            ),
            dbc.Button(
                "❌ Cancel",
                id="upload-cancel-btn",
                color="secondary",
                outline=True
            )
        ])
    ], id="upload-modal", is_open=False, size="lg", centered=True, backdrop="static"),
    
    # Hidden stores for upload state
    dcc.Store(id="upload-file-store", data=None),
    dcc.Store(id="upload-metadata-store", data=None),
    
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
# CLIENTSIDE CALLBACKS
# ============================================================================

# (Auto-scroll removed - user prefers seeing newest messages at top)


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
    Output('dashboard-selector', 'value'),
    Input('dashboard-selector', 'value'),
    State('mode-selector', 'value'),
    prevent_initial_call=True
)
def enforce_race_overview(selected_dashboards, mode):
    """Ensure Race Overview stays selected in simulation/live modes."""
    required = {'race_overview'}
    selected_set = set(selected_dashboards or [])

    # If the required dashboard is missing, add it back preserving order
    if mode in ('sim', 'live') and not required.issubset(selected_set):
        base_order = ["ai", "race_overview", "race_control", "weather", "telemetry"]
        selected_set.update(required)
        fixed = [item for item in base_order if item in selected_set]
        return fixed

    raise PreventUpdate


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
        
        # DEBUG: Log session_info keys and meeting_name
        logger.info(f"Session info keys: {session_info.keys()}")
        logger.info(f"Meeting name from session_info: {session_info.get('meeting_name', 'NOT_FOUND')}")
        logger.info(f"Session name from session_info: {session_info.get('session_name', 'NOT_FOUND')}")
        
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
        ), {
            'loaded': True,
            'year': year,
            'meeting_key': meeting_key,
            'session': session,
            'session_key': session_key,
            'race_name': session_info.get('meeting_name', 'Race'),
            'session_type': session_name,
            'drivers': {
                opt['value']: opt['label'] for opt in driver_options
            },
            'total_laps': _calculate_total_laps(
                session_obj,
                str(session_info.get('circuit_short_name')
                    or session_info.get('location') or '')
            )
        }
    
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
            [], [], [], [], [], []
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
            [], [], [], [], [], []
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


@callback(
    Output('fia-reg-status', 'children'),
    Output('fia-existing-regs', 'children'),
    Input('fia-year-selector', 'value'),
    prevent_initial_call=False
)
def update_fia_regulations_status(selected_year):
    """Update FIA regulations status and list existing regulations."""
    from pathlib import Path
    
    if not selected_year:
        return "⚠️ No year selected", ""
    
    try:
        # Check for existing regulation file
        fia_dir = Path('data/rag') / str(selected_year)
        reg_file = fia_dir / f"fia_regulations_{selected_year}.md"
        
        if reg_file.exists():
            status = html.Span([
                html.I(className="fas fa-check-circle text-success me-1"),
                f"✅ {selected_year} regulations loaded"
            ], className="small text-success")
            
            # Show file with edit button
            existing_list = html.Div([
                html.Button(
                    [html.I(className="fas fa-file-alt me-1"), f"fia_regulations_{selected_year}.md"],
                    id={'type': 'doc-edit-btn', 'index': str(reg_file)},
                    n_clicks=0,
                    className="btn btn-sm btn-link text-start p-0 text-info"
                ),
                html.Small(f" • {reg_file.stat().st_size / 1024:.1f} KB", className="text-muted ms-2")
            ])
        else:
            status = html.Span([
                html.I(className="fas fa-exclamation-circle text-warning me-1"),
                f"⚠️ No regulations for {selected_year}"
            ], className="small text-warning")
            existing_list = html.Small("No regulation file found. Upload one above.", className="text-muted")
        
        return status, existing_list
        
    except Exception as e:
        logger.error(f"Error checking FIA regulations: {e}")
        return html.Span(f"❌ Error: {str(e)[:30]}", className="small text-danger"), ""


@callback(
    Output('fia-upload-preview', 'children'),
    Input('fia-reg-upload', 'contents'),
    State('fia-reg-upload', 'filename'),
    prevent_initial_call=True
)
def preview_fia_upload(contents, filename):
    """Show preview of uploaded FIA regulation file."""
    if not contents or not filename:
        return ""
    
    try:
        file_size = len(contents) * 3 / 4  # Approximate decoded size
        return html.Div([
            html.Small([
                html.I(className="fas fa-file-pdf text-danger me-1"),
                html.Strong(filename),
                f" ({file_size / 1024:.1f} KB)"
            ], className="text-muted"),
            html.Br(),
            html.Small("Click to open upload modal and confirm", className="text-info")
        ], className="p-2 bg-dark rounded")
        
    except Exception:
        return ""


# ============================================================================
# DOCUMENT UPLOAD CALLBACKS
# ============================================================================

# Hidden style for overlay (used to hide it)
OVERLAY_HIDDEN = {"display": "none"}
OVERLAY_VISIBLE = {
    "display": "flex",
    "position": "absolute",
    "top": 0,
    "left": 0,
    "right": 0,
    "bottom": 0,
    "backgroundColor": "rgba(0, 0, 0, 0.85)",
    "zIndex": 1000,
    "alignItems": "center",
    "justifyContent": "center",
    "borderRadius": "0.3rem"
}

@callback(
    Output('upload-modal', 'is_open'),
    Output('upload-file-info', 'children'),
    Output('upload-category-override', 'value'),
    Output('upload-preview-content', 'children'),
    Output('upload-target-path', 'children'),
    Output('upload-filename-edit', 'value'),
    Output('upload-duplicate-warning', 'children'),
    Output('upload-file-store', 'data'),
    Output('upload-processing-status', 'children'),
    Output('upload-loading-overlay', 'style', allow_duplicate=True),
    Output('upload-confirm-btn', 'disabled'),
    Output('upload-confirm-btn', 'children'),
    # Add RAG status outputs to update sidebar after upload
    Output('rag-status', 'children', allow_duplicate=True),
    Output('rag-doc-count', 'children', allow_duplicate=True),
    Output('rag-global-docs', 'children', allow_duplicate=True),
    Output('rag-strategy-docs', 'children', allow_duplicate=True),
    Output('rag-weather-docs', 'children', allow_duplicate=True),
    Output('rag-performance-docs', 'children', allow_duplicate=True),
    Output('rag-race-control-docs', 'children', allow_duplicate=True),
    Output('rag-race-position-docs', 'children', allow_duplicate=True),
    Output('rag-fia-docs', 'children', allow_duplicate=True),
    Input({'type': 'rag-upload-input', 'category': ALL}, 'contents'),
    Input('fia-reg-upload', 'contents'),
    Input('upload-confirm-btn', 'n_clicks'),
    Input('upload-cancel-btn', 'n_clicks'),
    State({'type': 'rag-upload-input', 'category': ALL}, 'filename'),
    State('fia-reg-upload', 'filename'),
    State('fia-year-selector', 'value'),
    State('year-selector', 'value'),
    State('circuit-selector', 'value'),
    State('upload-category-override', 'value'),
    State('upload-filename-edit', 'value'),
    State('upload-file-store', 'data'),
    prevent_initial_call=True
)
def handle_document_upload(
    category_upload_contents_list, fia_contents, confirm_clicks, cancel_clicks,
    category_upload_filenames_list, fia_filename, fia_year, context_year, context_circuit,
    category_override, edited_filename, stored_file_data
):
    """Handle document upload flow: file selection → preview/LLM → confirmation → save."""
    import base64
    import io
    from pathlib import Path
    
    triggered_id = ctx.triggered_id
    
    # Helper for RAG no_update tuple (9 values for RAG outputs)
    rag_no_updates = (
        dash.no_update, dash.no_update,  # status, doc_count
        dash.no_update, dash.no_update, dash.no_update,  # global, strategy, weather
        dash.no_update, dash.no_update, dash.no_update, dash.no_update  # perf, rc, pos, fia
    )
    
    # UI reset values (overlay hidden, button enabled, button text)
    ui_reset = (OVERLAY_HIDDEN, False, "✅ Upload & Index")
    
    # Cancel button - close modal (9 original + 3 UI + 9 RAG = 21 outputs)
    if triggered_id == 'upload-cancel-btn':
        return (False, "", "", None, "", "", "", None, "") + ui_reset + rag_no_updates
    
    # Confirm button - process and save document
    if triggered_id == 'upload-confirm-btn' and stored_file_data:
        try:
            # Decode file
            content_type, content_string = stored_file_data['content'].split(',')
            decoded = base64.b64decode(content_string)
            filename = stored_file_data['filename']
            category = category_override if category_override else stored_file_data.get('default_category', 'global')
            
            # Check if user selected FIA category OR if uploaded via FIA button
            is_fia_category = (category == 'fia') or stored_file_data.get('is_fia')
            
            # Determine target directory
            if is_fia_category:
                # FIA documents go to year level: data/rag/2025/fia_regulations.md
                year = fia_year if fia_year else context_year
                target_dir = Path('data/rag') / str(year)
                if edited_filename:
                    final_filename = edited_filename if edited_filename.endswith('.md') else f"{edited_filename}.md"
                else:
                    final_filename = f"fia_regulations_{year}.md"
            elif category == 'global':
                # Global category goes to data/rag/global/
                target_dir = Path('data/rag') / 'global'
                if edited_filename:
                    final_filename = edited_filename if edited_filename.endswith('.md') else f"{edited_filename}.md"
                else:
                    final_filename = filename.replace('.pdf', '.md').replace('.docx', '.md').replace('.doc', '.md')
                    final_filename = final_filename.lower().replace(' ', '_')
            else:
                # Circuit-specific categories: strategy, weather, performance, race_control, race_position
                if context_circuit and context_year:
                    circuit_name = _get_circuit_name_for_rag(context_circuit, context_year)
                    target_dir = Path('data/rag') / str(context_year) / 'circuits' / circuit_name
                    # Use category as filename: strategy.md, weather.md, etc.
                    if category in ['strategy', 'weather', 'performance', 'race_control', 'race_position']:
                        final_filename = f"{category}.md"
                    else:
                        # Other category - use original filename
                        if edited_filename:
                            final_filename = edited_filename if edited_filename.endswith('.md') else f"{edited_filename}.md"
                        else:
                            final_filename = filename.replace('.pdf', '.md').replace('.docx', '.md').replace('.doc', '.md')
                            final_filename = final_filename.lower().replace(' ', '_')
                elif context_year:
                    # Year level but no circuit - save to year folder
                    target_dir = Path('data/rag') / str(context_year)
                    if edited_filename:
                        final_filename = edited_filename if edited_filename.endswith('.md') else f"{edited_filename}.md"
                    else:
                        final_filename = filename.replace('.pdf', '.md').replace('.docx', '.md').replace('.doc', '.md')
                        final_filename = final_filename.lower().replace(' ', '_')
                else:
                    # No context - save to global
                    target_dir = Path('data/rag') / 'global'
                    if edited_filename:
                        final_filename = edited_filename if edited_filename.endswith('.md') else f"{edited_filename}.md"
                    else:
                        final_filename = filename.replace('.pdf', '.md').replace('.docx', '.md').replace('.doc', '.md')
                        final_filename = final_filename.lower().replace(' ', '_')
            
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path = target_dir / final_filename
            
            # No backup - just overwrite existing file if it exists
            
            # Convert to markdown
            file_ext = Path(filename).suffix.lower()
            
            if file_ext == '.pdf':
                # Convert PDF
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                    tmp.write(decoded)
                    tmp_path = tmp.name
                
                try:
                    document_loader = DocumentLoader()
                    markdown_content = document_loader.convert_pdf_to_markdown(tmp_path, str(target_path))
                    
                except Exception as conv_error:
                    # Conversion failed - reject upload
                    error_msg = html.Div([
                        html.I(className="fas fa-exclamation-triangle text-danger me-2"),
                        html.Span(f"PDF conversion failed: {str(conv_error)[:100]}", className="text-danger"),
                        html.Br(),
                        html.Small("File may be corrupted, password-protected, or have unsupported formatting.", className="text-muted")
                    ], className="alert alert-danger")
                    
                    return False, "", "", None, "", "", "", None, error_msg
                finally:
                    Path(tmp_path).unlink(missing_ok=True)
                    
            elif file_ext in ['.docx', '.doc']:
                # Convert DOCX
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
                    tmp.write(decoded)
                    tmp_path = tmp.name
                
                try:
                    document_loader = DocumentLoader()
                    markdown_content = document_loader.convert_docx_to_markdown(tmp_path, str(target_path))
                except Exception as conv_error:
                    error_msg = html.Div([
                        html.I(className="fas fa-exclamation-triangle text-danger me-2"),
                        html.Span(f"DOCX conversion failed: {str(conv_error)[:100]}", className="text-danger")
                    ], className="alert alert-danger")
                    return False, "", "", None, "", "", "", None, error_msg
                finally:
                    Path(tmp_path).unlink(missing_ok=True)
                    
            elif file_ext == '.md':
                # Already markdown - just save
                markdown_content = decoded.decode('utf-8')
                with open(target_path, 'w', encoding='utf-8') as f:
                    # Add metadata header if not present
                    if not markdown_content.strip().startswith('---'):
                        from datetime import datetime
                        metadata = f"""---
category: {category}
year: {context_year or fia_year}
uploaded_at: {datetime.now().isoformat()}
---

"""
                        f.write(metadata + markdown_content)
                    else:
                        f.write(markdown_content)
            
            # Reload RAG with correct year from UI state (not cached context)
            rag_manager = get_rag_manager()
            # Use context_year from UI, or fia_year for FIA docs
            reload_year = context_year or fia_year
            # Convert circuit selector value to circuit name
            reload_circuit = None
            if context_circuit:
                reload_circuit = _get_circuit_name_for_rag(context_circuit, reload_year)
            chunk_count = rag_manager.load_context(
                year=reload_year,
                circuit=reload_circuit,
                clear_existing=True
            )
            
            # Get updated document lists for sidebar
            docs = rag_manager.list_documents()
            
            # Format lists for display
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
            
            # Success - show toast and close modal
            success_msg = html.Div([
                html.I(className="fas fa-check-circle text-success me-2"),
                html.Span(f"✅ {final_filename} uploaded successfully ({chunk_count} chunks indexed)", className="text-success")
            ], className="alert alert-success")
            
            # Close modal and show success (9 original + 3 UI + 9 RAG = 21 outputs)
            return (
                False, "", "", None, "", "", "", None, success_msg,
                # UI reset (hide overlay, enable button, reset text)
                OVERLAY_HIDDEN, False, "✅ Upload & Index",
                # RAG status updates
                "🟢 Loaded",
                f"({chunk_count} chunks)",
                global_list, strategy_list, weather_list,
                performance_list, race_control_list, race_position_list, fia_list
            )
            
        except Exception as e:
            logger.error(f"Upload processing error: {e}", exc_info=True)
            error_msg = html.Div([
                html.I(className="fas fa-times-circle text-danger me-2"),
                html.Span(f"Upload failed: {str(e)[:100]}", className="text-danger")
            ], className="alert alert-danger")
            return (False, "", "", None, "", "", "", None, error_msg) + ui_reset + rag_no_updates
    
    # File upload - open modal with preview and LLM suggestion
    file_contents = None
    filename = None
    is_fia = False
    category_hint = None
    
    # Check which upload triggered
    if triggered_id and isinstance(triggered_id, dict) and triggered_id.get('type') == 'rag-upload-input':
        # Category upload from hidden dcc.Upload
        category_hint = triggered_id.get('category')
        
        # Find which upload has content
        for i, contents in enumerate(category_upload_contents_list):
            if contents:
                file_contents = contents
                filename = category_upload_filenames_list[i]
                break
        
    elif triggered_id == 'fia-reg-upload' and fia_contents:
        file_contents = fia_contents
        filename = fia_filename
        is_fia = True
        category_hint = 'fia'
    
    if not file_contents or not filename:
        raise PreventUpdate
    
    try:
        # Parse file
        content_type, content_string = file_contents.split(',')
        decoded = base64.b64decode(content_string)
        file_size = len(decoded)
        file_ext = Path(filename).suffix.lower()
        
        # Validate file
        if file_size > 10 * 1024 * 1024:  # 10MB limit
            error_msg = html.Div([
                html.I(className="fas fa-exclamation-triangle text-warning me-2"),
                html.Span(f"File too large: {file_size / 1024 / 1024:.1f}MB (max 10MB)", className="text-warning")
            ], className="alert alert-warning")
            return (False, error_msg, "", None, "", "", "", None, "") + ui_reset + rag_no_updates
        
        if file_ext not in ['.pdf', '.docx', '.doc', '.md']:
            error_msg = html.Div([
                html.I(className="fas fa-exclamation-triangle text-warning me-2"),
                html.Span(f"Unsupported file type: {file_ext}", className="text-warning")
            ], className="alert alert-warning")
            return (False, error_msg, "", None, "", "", "", None, "") + ui_reset + rag_no_updates
        
        # File info display
        file_info = html.Div([
            html.P([html.Strong("Name: "), filename]),
            html.P([html.Strong("Size: "), f"{file_size / 1024:.1f} KB"]),
            html.P([html.Strong("Type: "), file_ext.upper()])
        ])
        
        # Quick preview (detailed extraction happens at save time)
        preview_text = ""
        if file_ext == '.md':
            preview_text = decoded.decode('utf-8', errors='ignore')[:500]
        elif file_ext == '.pdf':
            preview_text = f"📄 PDF file ready to upload. Content will be extracted during save."
        elif file_ext in ['.docx', '.doc']:
            preview_text = f"📝 Word document ready to upload. Content will be extracted during save."
        
        # Determine default category based on button source
        if is_fia:
            default_category = 'fia'
        else:
            # Try to infer from filename
            fname_lower = filename.lower()
            if 'fia' in fname_lower or 'regulation' in fname_lower or 'sporting' in fname_lower:
                default_category = 'fia'
            elif 'strategy' in fname_lower or 'tyre' in fname_lower or 'pit' in fname_lower:
                default_category = 'strategy'
            elif 'weather' in fname_lower or 'rain' in fname_lower or 'temperature' in fname_lower:
                default_category = 'weather'
            elif 'telemetry' in fname_lower or 'performance' in fname_lower or 'lap' in fname_lower:
                default_category = 'performance'
            elif 'flag' in fname_lower or 'incident' in fname_lower or 'safety' in fname_lower:
                default_category = 'race_control'
            elif 'position' in fname_lower or 'gap' in fname_lower or 'overtake' in fname_lower:
                default_category = 'race_position'
            else:
                default_category = None  # User must select
        
        # Determine initial target path based on default category
        is_fia_category = (default_category == 'fia')
        
        if default_category:
            if is_fia_category:
                # FIA documents go to year level
                year = fia_year if fia_year else context_year
                target_path_str = f"data/rag/{year}/fia_regulations_{year}.md"
                suggested_filename = f"fia_regulations_{year}"
            elif default_category == 'global':
                # Global category
                target_path_str = f"data/rag/global/{filename.replace(file_ext, '.md')}"
                suggested_filename = filename.replace(file_ext, '')
            elif default_category in ['strategy', 'weather', 'performance', 'race_control', 'race_position']:
                # Circuit-specific categories
                if context_circuit and context_year:
                    circuit = _get_circuit_name_for_rag(context_circuit, context_year)
                    target_path_str = f"data/rag/{context_year}/circuits/{circuit}/{default_category}.md"
                    suggested_filename = default_category
                elif context_year:
                    target_path_str = f"data/rag/{context_year}/{default_category}.md"
                    suggested_filename = default_category
                else:
                    target_path_str = f"data/rag/global/{filename.replace(file_ext, '.md')}"
                    suggested_filename = filename.replace(file_ext, '')
            else:
                # Fallback
                target_path_str = f"data/rag/global/{filename.replace(file_ext, '.md')}"
                suggested_filename = filename.replace(file_ext, '')
        else:
            # No default - show placeholder until user selects
            target_path_str = "⚠️ Select a category first"
            suggested_filename = filename.replace(file_ext, '')
        
        # Check for duplicates
        target_path_obj = Path(target_path_str)
        if target_path_obj.exists():
            duplicate_warning = html.Div([
                html.I(className="fas fa-exclamation-triangle text-warning me-2"),
                html.Span("⚠️ File exists! Uploading will create a backup of the old version.", className="text-warning fw-bold")
            ], className="alert alert-warning")
        else:
            duplicate_warning = ""
        
        # Store file data for confirmation
        stored_data = {
            'content': file_contents,
            'filename': filename,
            'default_category': default_category,
            'is_fia': is_fia
        }
        
        # Return modal opened with all info (9 original + 3 UI + 9 RAG no_update)
        return (
            True,  # is_open
            file_info,
            default_category,  # Pre-select default category (if any)
            preview_text[:500],  # Preview first 500 chars
            target_path_str,
            suggested_filename,
            duplicate_warning,
            stored_data,
            ""  # No processing status yet
        ) + ui_reset + rag_no_updates
        
    except Exception as e:
        logger.error(f"Error preparing upload: {e}", exc_info=True)
        error_msg = html.Div([
            html.I(className="fas fa-times-circle text-danger me-2"),
            html.Span(f"Error: {str(e)[:100]}", className="text-danger")
        ], className="alert alert-danger")
        return (False, error_msg, "", None, "", "", "", None, "") + ui_reset + rag_no_updates


@callback(
    Output('upload-target-path', 'children', allow_duplicate=True),
    Output('upload-filename-edit', 'value', allow_duplicate=True),
    Input('upload-category-override', 'value'),
    State('upload-file-store', 'data'),
    State('year-selector', 'value'),
    State('circuit-selector', 'value'),
    State('fia-year-selector', 'value'),
    prevent_initial_call=True
)
def update_target_path_on_category_change(
    selected_category, stored_file_data, context_year, context_circuit, fia_year
):
    """Update target path display when user changes category in dropdown."""
    if not stored_file_data or not selected_category:
        raise PreventUpdate
    
    try:
        from pathlib import Path
        
        filename = stored_file_data['filename']
        file_ext = Path(filename).suffix.lower()
        is_fia_from_button = stored_file_data.get('is_fia', False)
        
        # User selected category takes priority
        is_fia_category = (selected_category == 'fia') or is_fia_from_button
        
        # Calculate new target path based on selected category
        if is_fia_category:
            year = fia_year if fia_year else context_year
            target_path_str = f"data/rag/{year}/fia_regulations_{year}.md"
            suggested_filename = f"fia_regulations_{year}"
        elif selected_category == 'global':
            target_path_str = f"data/rag/global/{filename.replace(file_ext, '.md')}"
            suggested_filename = filename.replace(file_ext, '')
        elif selected_category in ['strategy', 'weather', 'performance', 'race_control', 'race_position']:
            if context_circuit and context_year:
                circuit = _get_circuit_name_for_rag(context_circuit, context_year)
                target_path_str = f"data/rag/{context_year}/circuits/{circuit}/{selected_category}.md"
                suggested_filename = selected_category
            elif context_year:
                target_path_str = f"data/rag/{context_year}/{selected_category}.md"
                suggested_filename = selected_category
            else:
                target_path_str = f"data/rag/global/{filename.replace(file_ext, '.md')}"
                suggested_filename = filename.replace(file_ext, '')
        else:
            # Other/unknown category
            if context_circuit and context_year:
                circuit = _get_circuit_name_for_rag(context_circuit, context_year)
                target_path_str = f"data/rag/{context_year}/circuits/{circuit}/{filename.replace(file_ext, '.md')}"
            elif context_year:
                target_path_str = f"data/rag/{context_year}/{filename.replace(file_ext, '.md')}"
            else:
                target_path_str = f"data/rag/global/{filename.replace(file_ext, '.md')}"
            
            suggested_filename = filename.replace(file_ext, '')
        
        return target_path_str, suggested_filename
        
    except Exception as e:
        logger.error(f"Error updating target path: {e}", exc_info=True)
        raise PreventUpdate


@callback(
    Output('upload-preview-collapse', 'is_open'),
    Input('upload-preview-toggle', 'n_clicks'),
    State('upload-preview-collapse', 'is_open'),
    prevent_initial_call=True
)
def toggle_upload_preview(n_clicks, is_open):
    """Toggle preview content visibility."""
    return not is_open if n_clicks else is_open


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
        
        # Reload RAG context with correct year/circuit (not cached context)
        rag_manager = get_rag_manager()
        chunk_count = rag_manager.load_context(
            year=year,
            circuit=circuit,
            clear_existing=True
        )
        
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
# UPLOAD BUTTON TRIGGER (Clientside to activate file picker)
# ============================================================================

app.clientside_callback(
    """
    function(n_clicks_list) {
        // Find which button was clicked
        const triggered = dash_clientside.callback_context.triggered;
        if (!triggered || triggered.length === 0) {
            return window.dash_clientside.no_update;
        }
        
        const triggeredId = triggered[0].prop_id;
        
        // Extract category from the triggered button
        const match = triggeredId.match(/"category":"([^"]+)"/);
        if (match && match[1]) {
            const category = match[1];
            
            // Find and click the corresponding hidden upload input
            const uploadInputs = document.querySelectorAll('[id*="rag-upload-input"]');
            for (let input of uploadInputs) {
                const inputId = input.id;
                if (inputId.includes(category)) {
                    // Trigger click on the hidden dcc.Upload's file input
                    const fileInput = input.querySelector('input[type="file"]');
                    if (fileInput) {
                        fileInput.click();
                        return window.dash_clientside.no_update;
                    }
                }
            }
        }
        
        return window.dash_clientside.no_update;
    }
    """,
    Output({'type': 'rag-upload-btn', 'category': ALL}, 'n_clicks', allow_duplicate=True),
    Input({'type': 'rag-upload-btn', 'category': ALL}, 'n_clicks'),
    prevent_initial_call=True
)


# Clientside callback to show loading overlay immediately on upload confirm
app.clientside_callback(
    """
    function(n_clicks) {
        if (n_clicks) {
            // Show the loading overlay immediately
            const overlay = document.getElementById('upload-loading-overlay');
            if (overlay) {
                overlay.style.display = 'flex';
            }
            // Disable the buttons to prevent double-click
            const confirmBtn = document.getElementById('upload-confirm-btn');
            const cancelBtn = document.getElementById('upload-cancel-btn');
            if (confirmBtn) {
                confirmBtn.disabled = true;
                confirmBtn.innerHTML = '⏳ Processing...';
            }
            if (cancelBtn) {
                cancelBtn.disabled = true;
            }
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output('upload-loading-overlay', 'style'),
    Input('upload-confirm-btn', 'n_clicks'),
    prevent_initial_call=True
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
    Input('driver-selector', 'value'),
    Input('circuit-selector', 'value'),
    Input('session-selector', 'value'),
    State('telemetry-comparison-store', 'data'),  # Telemetry comparison driver
    State('circuit-selector', 'options'),
    prevent_initial_call=False
)
def update_dashboards(
    selected_dashboards,
    session_data,
    focused_driver,
    selected_circuit,
    selected_session,
    telemetry_comparison_data,
    circuit_options,
):
    """Update visible dashboards based on selection."""
    global current_session_obj
    global _cached_weather_component, _cached_weather_lap, _cached_weather_session_key
    global _cached_telemetry_component, _cached_telemetry_key
    global _cached_race_control_component, _cached_race_control_sig

    driver_code = None
    if focused_driver and focused_driver != 'none':
        parts = focused_driver.split('_')
        driver_code = parts[0] if parts else focused_driver
    
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
            # Placeholder; real rendering happens in dedicated callback to avoid re-mounts
            dashboards.append(html.Div(id='ai-dashboard-slot'))
        elif dashboard_id == "race_overview":
            # Race Overview Dashboard (Leaderboard + Circuit Map)
            if not session_loaded:
                dash_logger.debug("Race overview: session not yet loaded")
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
                    overview_logger.info("Rendering race overview dashboard...")
                    # Get session_key from loaded session
                    session_key = None
                    simulation_time = None
                    
                    if current_session_obj and hasattr(current_session_obj, 'session_key'):
                        session_key = current_session_obj.session_key

                    if simulation_controller is not None:
                        try:
                            simulation_time = simulation_controller.get_elapsed_seconds()
                            sim_logger.debug(
                                "Race overview using controller time: %.1fs",
                                simulation_time
                            )
                        except Exception as exc:
                            logger.warning("Could not get simulation time: %s", exc)
                            simulation_time = 0.0
                    else:
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
                            sim_logger.debug(
                                f"Passing current_lap to overview: {overview_current_lap}"
                            )
                        except Exception as e:
                            logger.warning(f"Could not get lap for overview: {e}")
                    
                    overview_content = race_overview_dashboard.render(
                        session_key=session_key,
                        simulation_time=simulation_time,
                        session_start_time=session_start_time,
                        current_lap=overview_current_lap,
                        focused_driver_code=driver_code
                    )
                    
                    # Build lap info for header
                    total_laps = session_data.get('total_laps', 57) if session_data else 57
                    racing_lap = max(1, overview_current_lap - 2) if overview_current_lap else 1
                    lap_info_text = f"Lap {racing_lap}/{total_laps}"
                    
                    dashboards.append(
                        dbc.Card([
                            dbc.CardHeader(
                                dbc.Row([
                                    dbc.Col(
                                        html.H5("🏁 Race Overview", className="mb-0", style={"fontSize": "1.2rem"}),
                                        width="auto"
                                    ),
                                    dbc.Col(
                                        html.Span(
                                            lap_info_text,
                                            id="race-overview-lap-badge",  # ID for fast updates
                                            className="badge bg-danger ms-2",
                                            style={"fontSize": "0.85rem", "fontWeight": "normal"}
                                        ),
                                        width="auto",
                                        className="ms-auto"
                                    ),
                                ], className="align-items-center g-0"),
                                className="py-1"
                            ),
                            dbc.CardBody(children=[overview_content], className="p-2", id="race-overview-body")
                        ], className="mb-3", style={"height": "620px", "overflow": "auto"})
                    )
                    overview_logger.info("Race overview dashboard rendered successfully")
                    
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
                dash_logger.debug("Race control: session not yet loaded")
                dashboards.append(
                    html.Div(
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
                        ], className="mb-3", style={"height": "620px"}),
                        id="race-control-wrapper"
                    )
                )
                continue

            try:
                if current_session_obj is None:
                    logger.warning("Race control requested but no session loaded")
                    dashboards.append(
                        html.Div(
                            dbc.Card([
                                dbc.CardHeader(html.H5(" Race Control", className="mb-0", style={"fontSize": "1.2rem"}), className="py-1"),
                                dbc.CardBody([
                                    html.P("No session loaded. Please select a race session from the sidebar.",
                                           className="text-muted text-center p-5")
                                ], className="p-2")
                            ], className="mb-3", style={"height": "620px"}),
                            id="race-control-wrapper"
                        )
                    )
                else:
                    control_logger.info("Rendering race control dashboard (static mount)...")
                    race_control_component = _render_race_control(
                        focused_driver=focused_driver,
                        use_store_time=False,
                    )
                    dashboards.append(html.Div(race_control_component, id="race-control-wrapper"))
                    control_logger.info("Race control dashboard mounted")

            except Exception as e:
                logger.error(f"Error creating race control dashboard: {e}", exc_info=True)
                dashboards.append(
                    html.Div(
                        dbc.Card([
                            dbc.CardHeader(html.H5(" Race Control", className="mb-0", style={"fontSize": "1.2rem"}), className="py-1"),
                            dbc.CardBody([
                                html.P(f"Error loading race control: {str(e)}", className="text-danger")
                            ], className="p-2")
                        ], className="mb-3", style={"height": "620px"}),
                        id="race-control-wrapper"
                    )
                )

        elif dashboard_id == "weather":
            # Weather Dashboard (Phase 1 MVP) - Compact 33% width
            if not session_loaded:
                dash_logger.info("Weather dashboard requested but session not yet loaded")
                dashboards.append(
                    html.Div(
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
                        ], className="mb-3 h-100"),
                        id="weather-wrapper"
                    )
                )
            else:
                dash_logger.info("Rendering weather dashboard (static mount)...")
                try:
                    weather_component = _render_weather()
                    dashboards.append(html.Div(weather_component, id="weather-wrapper"))
                except Exception as e:
                    logger.error(f"Error rendering weather dashboard: {e}", exc_info=True)
                    dashboards.append(
                        html.Div(
                            dbc.Card([
                                dbc.CardHeader(html.H5("🌤️ Weather", className="mb-0")),
                                dbc.CardBody([
                                    html.P(f"Error: {str(e)}", className="text-danger text-center")
                                ])
                            ], className="mb-3 h-100"),
                            id="weather-wrapper"
                        )
                    )

        elif dashboard_id == "telemetry":
            # Telemetry Dashboard - Speed, Throttle, Brake, Gear for focus driver
            try:
                telem_logger.info("Rendering telemetry dashboard (static mount)...")

                telemetry_component = _render_telemetry(
                    focused_driver=focused_driver,
                    telemetry_comparison_data=telemetry_comparison_data,
                    session_data=session_data,
                    use_store_time=False,
                )
                dashboards.append(html.Div(telemetry_component, id="telemetry-wrapper"))
                telem_logger.info("Telemetry dashboard mounted")

            except Exception as e:
                logger.error(f"Error creating telemetry dashboard: {e}", exc_info=True)
                dashboards.append(
                    html.Div(
                        dbc.Card([
                            dbc.CardHeader(
                                html.H5(
                                    "📊 Telemetry",
                                    className="mb-0",
                                    style={"fontSize": "1.2rem"}
                                ),
                                className="py-1"
                            ),
                            dbc.CardBody([
                                html.P(
                                    f"Error loading telemetry: {str(e)}",
                                    className="text-danger"
                                )
                            ], className="p-2")
                        ], className="mb-3", style={"height": "620px"}),
                        id="telemetry-wrapper"
                    )
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
    
    # Wrap all dashboards in responsive columns
    # CSS handles the layout switching between landscape (3 cols) and portrait (2 cols)
    wrapped_dashboards = []
    for idx, dash in enumerate(dashboards):
        # Border style for visual separation
        border_style = {"borderRight": "1px solid #333"}
        
        if isinstance(dash, dbc.Col):
            # Already wrapped (e.g., weather) - recreate with responsive class
            wrapped_dashboards.append(
                html.Div(
                    dash.children,
                    className="dashboard-grid-col",
                    style={**border_style}
                )
            )
        else:
            # Wrap with responsive class
            wrapped_dashboards.append(
                html.Div(
                    dash,
                    className="dashboard-grid-col",
                    style={**border_style}
                )
            )
    
    # Return flex container - CSS handles responsive layout
    # Landscape: wraps at 3 items per row (33% each)
    # Portrait: wraps at 2 items per row (50% each)
    return html.Div(
        wrapped_dashboards,
        className="dashboard-grid-container"
    )


# Callback: Render AI dashboard independently to avoid refresh flicker
@callback(
    Output('ai-dashboard-slot', 'children'),
    Input('chat-messages-store', 'data'),
    Input('driver-selector', 'value'),
    Input('circuit-selector', 'value'),
    Input('session-selector', 'value'),
    State('session-store', 'data'),
    State('circuit-selector', 'options'),
    prevent_initial_call=False
)
def render_ai_dashboard(
    chat_messages: list[dict[str, Any]] | dict[str, Any] | None,
    focused_driver: str | None,
    selected_circuit: str | None,
    selected_session: str | None,
    session_data: dict[str, Any] | None,
    circuit_options: list[dict[str, Any]] | None,
):
    """Render AI assistant without being driven by simulation ticks."""
    global _cached_ai_component, _cached_ai_sig
    # Circuit name from options label
    circuit_name = 'Unknown Circuit'
    if selected_circuit and circuit_options:
        for opt in circuit_options:
            if opt.get('value') == selected_circuit:
                label = opt.get('label', '')
                circuit_name = label.split(' - ', 1)[1] if ' - ' in label else label
                break

    session_type = selected_session if selected_session else 'Race'

    driver_code = None
    if focused_driver and focused_driver != 'none':
        parts = focused_driver.split('_')
        driver_code = parts[0] if parts else focused_driver

    # Prefer sanitized incoming store; fall back to last known messages to avoid empties
    effective_chat = _ensure_json_safe_messages(chat_messages)
    if not effective_chat and _last_chat_messages:
        try:
            effective_chat = json.loads(json.dumps(_last_chat_messages))
        except Exception:
            effective_chat = _ensure_json_safe_messages(_last_chat_messages)

    session_loaded = bool(session_data and session_data.get('loaded'))
    ai_signature_payload = {
        "messages": effective_chat,
        "driver_code": driver_code,
        "circuit_name": circuit_name,
        "session_type": session_type,
        "session_loaded": session_loaded,
    }
    ai_signature = json.dumps(ai_signature_payload, sort_keys=True, default=str)

    # If layout was remounted (e.g., other dashboards refresh) re-serve cached AI
    if _cached_ai_component is not None and _cached_ai_sig == ai_signature:
        return _cached_ai_component

    # Only allow proactive AI if session is loaded; otherwise show placeholder
    if not session_loaded:
        component = AIAssistantDashboard.create_layout(
            focused_driver=driver_code,
            race_name=circuit_name,
            session_type=session_type,
            messages=[]
        )
        _cached_ai_component = component
        _cached_ai_sig = ai_signature
        return component

    component = AIAssistantDashboard.create_layout(
        focused_driver=driver_code,
        race_name=circuit_name,
        session_type=session_type,
        messages=effective_chat
    )
    _cached_ai_component = component
    _cached_ai_sig = ai_signature
    return component


# Callback: Refresh race overview body using simulation time without re-rendering other dashboards
@callback(
    Output('race-overview-body', 'children'),
    Input('simulation-time-store', 'data'),
    Input('driver-selector', 'value'),
    State('dashboard-selector', 'value'),
    State('session-store', 'data'),
    prevent_initial_call=True
)
def refresh_race_overview_body(
    simulation_time_data: dict[str, Any] | None,
    focused_driver: str | None,
    selected_dashboards: list[str] | None,
    session_data: dict[str, Any] | None,
):
    """Refresh the race overview content frequently without rebuilding all dashboards."""
    global current_session_obj, simulation_controller

    if not selected_dashboards or 'race_overview' not in selected_dashboards:
        raise PreventUpdate
    if not session_data or not session_data.get('loaded'):
        raise PreventUpdate
    if current_session_obj is None:
        raise PreventUpdate

    try:
        session_key = getattr(current_session_obj, 'session_key', None)

        driver_code = None
        if focused_driver and focused_driver != 'none':
            parts = focused_driver.split('_')
            driver_code = parts[0] if parts else focused_driver

        simulation_time = 0.0
        if simulation_time_data and 'time' in simulation_time_data:
            simulation_time = simulation_time_data.get('time', 0.0)
        elif simulation_controller is not None:
            simulation_time = simulation_controller.get_elapsed_seconds()

        session_start_time = None
        if simulation_controller is not None:
            session_start_time = pd.Timestamp(simulation_controller.start_time)

        overview_current_lap = None
        if simulation_controller is not None:
            try:
                overview_current_lap = simulation_controller.get_current_lap()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not read lap for overview refresh: %s", exc)

        overview_content = race_overview_dashboard.render(
            session_key=session_key,
            simulation_time=simulation_time,
            session_start_time=session_start_time,
            current_lap=overview_current_lap,
            focused_driver_code=driver_code
        )
        return overview_content
    except Exception as exc:  # noqa: BLE001
        logger.error("Error refreshing race overview body: %s", exc, exc_info=True)
        raise PreventUpdate


# NOTE: Render callback REMOVED - chat callback writes directly to container
# This avoids Dash callback conflicts with allow_duplicate=True


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
        os.environ['ANTHROPIC_API_KEY'] = claude_key or ''
        os.environ['GOOGLE_API_KEY'] = gemini_key or ''
        os.environ['OPENF1_API_KEY'] = openf1_key or ''
        
        # Reset LLM provider to use new keys
        global _llm_provider, _llm_provider_type
        _llm_provider = None
        _llm_provider_type = None
        
        # Determine which provider will be used
        has_claude = bool(claude_key and claude_key.strip())
        has_gemini = bool(gemini_key and gemini_key.strip())
        
        if has_claude and has_gemini:
            provider_msg = "HybridRouter (Claude + Gemini)"
        elif has_claude:
            provider_msg = "Claude only"
        elif has_gemini:
            provider_msg = "Gemini only"
        else:
            return dbc.Alert(
                "⚠️ No API keys provided. At least one is required.",
                color="warning", dismissable=True, duration=5000,
                className="small py-1 mb-0 mt-2"
            )
        
        return dbc.Alert(
            f"✅ Keys saved! Using: {provider_msg}",
            color="success", dismissable=True, duration=5000,
            className="small py-1 mb-0 mt-2"
        )
    
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
    sim_logger.info(f"Play/Pause toggled: is_playing={is_playing}")
    
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
    Output('simulation-interval', 'interval'),
    Input('speed-slider', 'value'),
    prevent_initial_call=True
)
def change_speed(speed):
    """Change simulation playback speed and adjust update interval."""
    global simulation_controller
    
    # Calculate optimal interval based on speed
    # At high speeds, we need faster updates to keep UI in sync
    # Base interval: 1500ms at 1x, decreasing at higher speeds
    # Formula: interval = 1500 / sqrt(speed) to balance responsiveness and load
    import math
    base_interval = 1500
    # Minimum 500ms to avoid overwhelming the browser
    optimal_interval = max(500, int(base_interval / math.sqrt(float(speed))))
    
    if simulation_controller:
        try:
            simulation_controller.set_speed(float(speed))
            sim_logger.debug(
                f"Speed changed to {speed}x, interval={optimal_interval}ms"
            )
            return speed, optimal_interval
        except ValueError as e:
            logger.error(f"Invalid speed value: {e}")
            return 1.0, base_interval
    
    return speed, optimal_interval


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
        sim_logger.debug("Jumped to previous lap")
    elif triggered == 'forward-btn':
        simulation_controller.jump_forward(90)  # ~90 seconds per lap
        sim_logger.debug("Jumped to next lap")
    else:
        raise PreventUpdate
    
    # Return updated time to trigger dashboard refresh
    new_time = simulation_controller.get_elapsed_seconds()
    new_lap = simulation_controller.get_current_lap()
    
    sim_logger.debug(f"Lap jump: {old_lap} -> {new_lap} (time={new_time:.1f}s)")
    
    return {
        'time': new_time,
        'timestamp': datetime.now().timestamp()
    }


# Callback: Update simulation progress display every second
@callback(
    Output('simulation-progress', 'children'),
    Input('simulation-interval', 'n_intervals'),
    State('session-store', 'data'),
    prevent_initial_call=False
)
def update_simulation_progress(n_intervals, session_data):
    """Update the simulation progress display in real-time."""
    global simulation_controller
    
    sim_logger.debug(f"update_simulation_progress: n_intervals={n_intervals}")
    
    if simulation_controller is None:
        return "⏱️ Not started"
    
    try:
        # Update simulation time
        simulation_controller.update()
        
        # Get progress information
        remaining = simulation_controller.get_remaining_time()
        
        # Get EXACT current lap from simulation controller (no estimation)
        current_lap = simulation_controller.get_current_lap()
        
        # Convert to VISUAL racing lap
        # OpenF1 has 2 laps before racing starts (lap 3 = racing lap 1)
        visual_lap = max(1, current_lap - 2)
        # Get total_laps from session_data (calculated from actual race data)
        total_laps = session_data.get('total_laps', 57) if session_data else 57
        
        sim_logger.debug(f"Lap {visual_lap}/{total_laps}, remaining: {remaining}")
        
        # Format remaining time
        remaining_minutes = int(remaining.total_seconds() // 60)
        remaining_seconds = int(remaining.total_seconds() % 60)
        
        # Get current speed multiplier
        speed = simulation_controller.speed_multiplier
        
        progress_text = f"⏱️ Lap {int(visual_lap)}/{int(total_laps)} | ⏳ {remaining_minutes}m {remaining_seconds}s left | 🚀 {speed}x"
        
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


# Track last dashboard update time (real-world time) to throttle updates
_last_dashboard_update_time = 0.0
_DASHBOARD_UPDATE_INTERVAL = 2.0  # Update dashboard every 2 real seconds

# Lightweight dashboard cache to avoid unnecessary re-renders
_cached_weather_component = None
_cached_weather_lap = None
_cached_weather_session_key = None

_cached_telemetry_component = None
_cached_telemetry_key = None  # (session_key, focused_driver, comparison_driver, lap)

_cached_ai_component = None
_cached_ai_sig = None  # hash over messages + context

_cached_race_control_component = None
_cached_race_control_sig = None  # (session_key, message_count, latest_time, focused_driver, lap)


def _render_race_control(
    focused_driver: str | None,
    use_store_time: bool,
    simulation_time_data: dict | None = None,
):
    """Build Race Control dashboard content with optional store-based time."""
    global current_session_obj, simulation_controller
    global _cached_race_control_component, _cached_race_control_sig

    if current_session_obj is None:
        raise PreventUpdate

    session_key = None
    simulation_time = None

    if current_session_obj and hasattr(current_session_obj, 'session_key'):
        session_key = current_session_obj.session_key

    if use_store_time and simulation_time_data and 'time' in simulation_time_data:
        simulation_time = simulation_time_data.get('time', 0.0)
        sim_logger.debug("Race control using simulation time from store: %.1fs", simulation_time)
    elif simulation_controller is not None:
        try:
            simulation_time = simulation_controller.get_elapsed_seconds()
            sim_logger.debug("Race control using controller time: %.1fs", simulation_time)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not get simulation time: %s", exc)
            simulation_time = 0.0

    session_start_time = None
    if simulation_controller is not None:
        session_start_time = pd.Timestamp(simulation_controller.start_time)

    current_lap = None
    if simulation_controller is not None:
        try:
            openf1_lap = simulation_controller.get_current_lap()
            current_lap = max(1, openf1_lap - 2) if openf1_lap > 2 else 1
            sim_logger.debug("Current lap from controller: OpenF1 %s → Racing %s", openf1_lap, current_lap)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not get lap from controller: %s", exc)
            current_lap = None

    rc_signature = race_control_dashboard.get_signature(
        session_key=session_key,
        simulation_time=simulation_time,
        session_start_time=session_start_time,
        focused_driver=focused_driver if focused_driver != 'none' else None,
        current_lap=current_lap,
    )

    if (
        _cached_race_control_component is not None
        and rc_signature is not None
        and rc_signature == _cached_race_control_sig
    ):
        control_logger.info("Race control unchanged; reusing cached component")
        return _cached_race_control_component

    control_content = race_control_dashboard.render(
        session_key=session_key,
        simulation_time=simulation_time,
        session_start_time=session_start_time,
        focused_driver=focused_driver if focused_driver != 'none' else None,
        current_lap=current_lap
    )
    _cached_race_control_component = control_content
    _cached_race_control_sig = rc_signature
    return control_content


def _render_weather(simulation_time_data: dict | None = None):
    """Build Weather dashboard content with lap-aware caching."""
    global current_session_obj, simulation_controller
    global _cached_weather_component, _cached_weather_lap, _cached_weather_session_key

    weather_session_key = current_session_obj.session_key if current_session_obj else None

    if weather_session_key is None:
        raise PreventUpdate

    simulation_time = None
    if simulation_time_data and 'time' in simulation_time_data:
        simulation_time = simulation_time_data.get('time', 0.0)
    elif simulation_controller is not None:
        try:
            simulation_time = simulation_controller.get_elapsed_seconds()
        except Exception:  # noqa: BLE001
            simulation_time = 0.0

    weather_lap = None
    if simulation_controller is not None:
        try:
            openf1_lap = simulation_controller.get_current_lap()
            weather_lap = max(1, openf1_lap - 2) if openf1_lap else None
        except Exception as exc:  # noqa: BLE001
            logger.debug("Weather lap read failed: %s", exc)
            weather_lap = None

    if (
        _cached_weather_component is not None
        and weather_lap is not None
        and _cached_weather_lap == weather_lap
        and _cached_weather_session_key == weather_session_key
    ):
        return _cached_weather_component

    session_start_time = None
    if simulation_controller is not None:
        try:
            session_start_time = pd.Timestamp(simulation_controller.start_time)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Weather start_time unavailable: %s", exc)

    weather_content = weather_dashboard.render_weather_content(
        session_key=weather_session_key,
        simulation_time=simulation_time,
        session_start_time=session_start_time
    )

    _cached_weather_component = weather_content
    _cached_weather_lap = weather_lap
    _cached_weather_session_key = weather_session_key
    return weather_content


def _render_telemetry(
    focused_driver: str | None,
    telemetry_comparison_data: dict | None,
    session_data: dict | None,
    use_store_time: bool,
    simulation_time_data: dict | None = None,
):
    """Build Telemetry dashboard content with caching."""
    global current_session_obj, simulation_controller
    global _cached_telemetry_component, _cached_telemetry_key

    session_key = None
    simulation_time = None

    if current_session_obj and hasattr(current_session_obj, 'session_key'):
        session_key = current_session_obj.session_key

    if use_store_time and simulation_time_data and 'time' in simulation_time_data:
        simulation_time = simulation_time_data.get('time', 0.0)
        sim_logger.debug("Telemetry using simulation time from store: %.1fs", simulation_time)
    elif simulation_controller is not None:
        try:
            simulation_time = simulation_controller.get_elapsed_seconds()
            sim_logger.debug("Telemetry using controller time: %.1fs", simulation_time)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not get simulation time: %s", exc)
            simulation_time = 0.0

    session_start_time = None
    if simulation_controller is not None:
        session_start_time = pd.Timestamp(simulation_controller.start_time)

    current_lap = None
    if simulation_controller is not None:
        try:
            openf1_lap = simulation_controller.get_current_lap()
            current_lap = max(1, openf1_lap - 2) if openf1_lap > 2 else 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not get lap: %s", exc)
            current_lap = None

    comparison_driver = None
    if telemetry_comparison_data:
        comparison_driver = telemetry_comparison_data.get('driver')

    driver_options = []
    if session_data and session_data.get('drivers'):
        drivers_dict = session_data.get('drivers', {})
        driver_options = [
            {'label': label, 'value': value}
            for value, label in drivers_dict.items()
        ]

    cache_key = (
        session_key,
        focused_driver if focused_driver != 'none' else None,
        comparison_driver,
        current_lap
    )

    if _cached_telemetry_component is not None and cache_key == _cached_telemetry_key:
        return _cached_telemetry_component

    telemetry_content = telemetry_dashboard.render(
        session_key=session_key,
        simulation_time=simulation_time,
        session_start_time=session_start_time,
        focused_driver=focused_driver if focused_driver != 'none' else None,
        comparison_driver=comparison_driver,
        current_lap=current_lap,
        driver_options=driver_options
    )
    _cached_telemetry_component = telemetry_content
    _cached_telemetry_key = cache_key
    return telemetry_content


@callback(
    Output('race-control-wrapper', 'children', allow_duplicate=True),
    Input('simulation-time-store', 'data'),
    State('dashboard-selector', 'value'),
    State('driver-selector', 'value'),
    State('session-store', 'data'),
    prevent_initial_call=True
)
def refresh_race_control_wrapper(
    simulation_time_data: dict[str, Any] | None,
    selected_dashboards: list[str] | None,
    focused_driver: str | None,
    session_data: dict[str, Any] | None,
):
    """Refresh Race Control without rebuilding the main grid or AI."""
    if not selected_dashboards or 'race_control' not in selected_dashboards:
        raise PreventUpdate
    if not session_data or not session_data.get('loaded'):
        raise PreventUpdate

    return _render_race_control(
        focused_driver=focused_driver,
        use_store_time=True,
        simulation_time_data=simulation_time_data,
    )


@callback(
    Output('weather-wrapper', 'children', allow_duplicate=True),
    Input('simulation-time-store', 'data'),
    State('dashboard-selector', 'value'),
    State('session-store', 'data'),
    prevent_initial_call=True
)
def refresh_weather_wrapper(
    simulation_time_data: dict[str, Any] | None,
    selected_dashboards: list[str] | None,
    session_data: dict[str, Any] | None,
):
    """Refresh Weather dashboard independently to avoid AI flicker."""
    if not selected_dashboards or 'weather' not in selected_dashboards:
        raise PreventUpdate
    if not session_data or not session_data.get('loaded'):
        raise PreventUpdate
    if current_session_obj is None:
        raise PreventUpdate

    return _render_weather(simulation_time_data=simulation_time_data)


@callback(
    Output('telemetry-wrapper', 'children', allow_duplicate=True),
    Input('simulation-time-store', 'data'),
    State('dashboard-selector', 'value'),
    State('driver-selector', 'value'),
    State('session-store', 'data'),
    State('telemetry-comparison-store', 'data'),
    prevent_initial_call=True
)
def refresh_telemetry_wrapper(
    simulation_time_data: dict[str, Any] | None,
    selected_dashboards: list[str] | None,
    focused_driver: str | None,
    session_data: dict[str, Any] | None,
    telemetry_comparison_data: dict[str, Any] | None,
):
    """Refresh Telemetry dashboard without remounting other panels."""
    if not selected_dashboards or 'telemetry' not in selected_dashboards:
        raise PreventUpdate
    if not session_data or not session_data.get('loaded'):
        raise PreventUpdate

    return _render_telemetry(
        focused_driver=focused_driver,
        telemetry_comparison_data=telemetry_comparison_data,
        session_data=session_data,
        use_store_time=True,
        simulation_time_data=simulation_time_data,
    )


@callback(
    Output('simulation-time-store', 'data'),
    Input('simulation-interval', 'n_intervals'),
    State('dashboard-selector', 'value'),
    State('simulation-time-store', 'data'),
    prevent_initial_call=True
)
def update_simulation_time_store(n_intervals, selected_dashboards, current_store):
    """Update simulation time store for dashboard updates.
    
    This triggers the full dashboard refresh including gaps/intervals.
    Throttled to update every 2 real seconds to prevent UI freezing.
    """
    global simulation_controller, _last_dashboard_update_time
    
    # Only update if race_overview dashboard is selected
    if not selected_dashboards or 'race_overview' not in selected_dashboards:
        raise PreventUpdate
    
    # Check if simulation is running
    if simulation_controller is None:
        raise PreventUpdate
    
    # NOTE: Removed is_playing check here.
    # The interval is disabled when paused (via toggle_play_pause),
    # so this callback won't run anyway when paused.
    # The previous is_playing check was causing race conditions.
    
    try:
        # Throttle: only update dashboard every N real seconds
        current_real_time = time.time()
        time_since_last_update = current_real_time - _last_dashboard_update_time
        
        if time_since_last_update < _DASHBOARD_UPDATE_INTERVAL:
            # Not enough real time has passed, skip this update
            raise PreventUpdate
        
        # Update timestamp for throttling
        _last_dashboard_update_time = current_real_time
        
        # Get current simulation time
        simulation_time = simulation_controller.get_elapsed_seconds()
        
        logger.debug(
            f"Dashboard update triggered: sim_time={simulation_time:.1f}s, "
            f"real_interval={time_since_last_update:.1f}s"
        )
        
        return {
            'time': simulation_time,
            'timestamp': n_intervals  # Force update even if time is same
        }
        
    except PreventUpdate:
        raise
    except Exception as e:
        logger.error(
            f"Error updating simulation time store: {e}",
            exc_info=True
        )
        raise PreventUpdate


# Callback: Fast update for lap badge only (lightweight, runs on every interval)
# This updates the lap counter immediately without regenerating the dashboard
@callback(
    Output('current-lap-store', 'data'),
    Input('simulation-interval', 'n_intervals'),
    State('session-store', 'data'),
    prevent_initial_call=True
)
def update_current_lap_store(n_intervals, session_data):
    """Update current lap store for fast badge updates."""
    global simulation_controller
    
    if simulation_controller is None or not simulation_controller.is_playing:
        raise PreventUpdate
    
    try:
        # Get current lap from controller
        current_lap = simulation_controller.get_current_lap()
        total_laps = session_data.get('total_laps', 57) if session_data else 57
        
        # Convert OpenF1 lap to racing lap (lap 3 = racing lap 1)
        racing_lap = max(1, current_lap - 2) if current_lap else 1
        
        return {
            'lap': racing_lap,
            'total': total_laps,
            'timestamp': n_intervals
        }
    except Exception as e:
        logger.error(f"Error updating lap store: {e}")
        raise PreventUpdate


# Callback: Update race overview lap badge independently (fast path)
@callback(
    Output('race-overview-lap-badge', 'children'),
    Input('current-lap-store', 'data'),
    prevent_initial_call=True
)
def update_lap_badge(lap_data):
    """Update lap badge text quickly without regenerating dashboard."""
    if not lap_data:
        raise PreventUpdate
    
    lap = lap_data.get('lap', 1)
    total = lap_data.get('total', 57)
    
    return f"Lap {lap}/{total}"


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


# ============================================================================
# AI CHAT CALLBACKS
# ============================================================================

# Rate limiting for chat requests (prevent flooding LLM API)
_last_chat_request_time: float = 0.0
_last_chat_messages: list[dict[str, Any]] = []
_last_render_signature: Optional[str] = None
_cached_ai_component: Any | None = None
_cached_ai_sig: Optional[str] = None


def _ensure_json_safe_messages(raw_messages: Any) -> list[dict]:
    """Convert incoming store data to a JSON-serializable list of messages."""
    safe_list: list[dict] = []

    # Normalize dict payloads (dcc.Store can send a dict when hydrated)
    if isinstance(raw_messages, dict):
        candidate_messages = [v for v in raw_messages.values() if v is not None]
    elif isinstance(raw_messages, list):
        candidate_messages = raw_messages
    else:
        candidate_messages = []

    def _sanitize_value(value: Any) -> Any:
        """Recursively sanitize values to make them JSON-safe."""
        if isinstance(value, float):
            if not math.isfinite(value):
                return str(value)
            return float(value)
        if isinstance(value, (int, str, bool)) or value is None:
            return value
        if isinstance(value, dict):
            return {str(k): _sanitize_value(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [_sanitize_value(v) for v in value]
        try:
            json.dumps(value)  # type: ignore[arg-type]
            return value
        except Exception:
            return str(value)

    for msg in candidate_messages:
        if not isinstance(msg, dict):
            continue
        safe_msg: dict[str, Any] = {}

        safe_msg['type'] = str(msg.get('type', 'assistant'))
        safe_msg['content'] = str(msg.get('content', ''))
        safe_msg['timestamp'] = str(msg.get('timestamp', datetime.now().isoformat()))

        metadata = msg.get('metadata', {})
        if isinstance(metadata, dict):
            safe_msg['metadata'] = _sanitize_value(metadata)
        else:
            safe_msg['metadata'] = {}

        # Preserve optional priority if present
        if 'priority' in msg:
            safe_msg['priority'] = _sanitize_value(msg['priority'])

        safe_list.append(safe_msg)

    return safe_list


@callback(
    Output('chat-messages-store', 'data', allow_duplicate=True),
    Output('chat-messages-container', 'children', allow_duplicate=True),
    Input('chat-send-btn', 'n_clicks'),
    Input('chat-input', 'n_submit'),
    Input('quick-pit-btn', 'n_clicks'),
    Input('quick-weather-btn', 'n_clicks'),
    Input('quick-gap-btn', 'n_clicks'),
    State('chat-input', 'value'),
    State('chat-messages-store', 'data'),
    State('session-store', 'data'),
    State('driver-selector', 'value'),
    State('simulation-time-store', 'data'),
    prevent_initial_call=True
)
def handle_chat_send(
    send_clicks,
    input_submit,
    pit_clicks,
    weather_clicks,
    gap_clicks,
    user_input,
    current_messages,
    session_data,
    focused_driver,
    sim_time_data
):
    """
    Handle user chat input and quick action buttons.
    Adds user message and generates AI response.
    Simple rate limiting to prevent API quota exhaustion.
    """
    global _last_chat_request_time, _last_chat_messages

    from src.dashboards_dash.ai_assistant_dashboard import AIAssistantDashboard
    
    if not ctx.triggered:
        raise PreventUpdate
    
    triggered_id = ctx.triggered_id
    
    # Ignore chat-input triggers unless they have actual content
    # This prevents the callback firing on every keystroke/focus change
    if triggered_id == 'chat-input':
        if not user_input or not user_input.strip():
            raise PreventUpdate
        # Only log actual submissions
        chat_logger.info(f"[CHAT] Text submitted via Enter: {user_input[:30]}...")
    else:
        chat_logger.info(f"[CHAT] Callback triggered by: {triggered_id}")
    
    # Normalize and JSON-sanitize incoming store data before appending
    messages = _ensure_json_safe_messages(current_messages)
    if not messages and _last_chat_messages:
        # Restore history if store was unexpectedly empty
        messages = json.loads(json.dumps(_last_chat_messages))
    
    # Simple rate limiting - only block very rapid clicks (< 0.5s)
    current_time = time.time()
    time_since_last = current_time - _last_chat_request_time
    
    chat_logger.info(f"[CHAT] Time since last: {time_since_last:.2f}s")
    
    if time_since_last < 0.5 and _last_chat_request_time > 0:
        chat_logger.info("[CHAT] Rate limited - ignoring rapid click")
        raise PreventUpdate  # Silently ignore rapid double-clicks
    
    _last_chat_request_time = current_time
    
    # Determine the query based on what was triggered
    if triggered_id in ['chat-send-btn', 'chat-input']:
        if not user_input or not user_input.strip():
            chat_logger.debug("[CHAT] Empty input, preventing update")
            raise PreventUpdate
        query = user_input.strip()
    elif triggered_id == 'quick-pit-btn':
        driver = focused_driver if focused_driver != 'none' else 'our driver'
        query = f"Should {driver} pit now? What's the optimal tire strategy?"
    elif triggered_id == 'quick-weather-btn':
        query = "What's the current weather situation? Any rain expected?"
    elif triggered_id == 'quick-gap-btn':
        driver = focused_driver if focused_driver != 'none' else 'our driver'
        query = f"What are the gaps around {driver}? Any overtake opportunities?"
    else:
        chat_logger.debug(f"[CHAT] Unknown trigger: {triggered_id}")
        raise PreventUpdate
    
    chat_logger.info(f"[CHAT] Processing query: {query[:50]}...")
    
    # Add user message
    timestamp = datetime.now().isoformat()
    messages.append({
        'type': 'user',
        'content': query,
        'timestamp': timestamp
    })
    history_for_ai = [
        m for m in messages[-8:]
        if not m.get('metadata', {}).get('thinking')
    ]
    
    # Add "thinking" message immediately for visual feedback
    thinking_msg = {
        'type': 'assistant',
        'content': '🤔 Analyzing race data...',
        'timestamp': datetime.now().isoformat(),
        'metadata': {'thinking': True}
    }
    messages.append(thinking_msg)
    
    # Generate AI response
    chat_logger.info("[CHAT] Calling generate_ai_response...")
    try:
        response = generate_ai_response(
            query=query,
            session_data=session_data,
            focused_driver=focused_driver,
            sim_time_data=sim_time_data,
            message_history=history_for_ai
        )
        
        chat_logger.info("[CHAT] Response received successfully")
        
        # Remove the "thinking" message and add real response
        messages = [m for m in messages if not m.get('metadata', {}).get('thinking')]
        messages.append({
            'type': 'assistant',
            'content': response['content'],
            'timestamp': datetime.now().isoformat(),
            'metadata': response.get('metadata', {})
        })
    except Exception as e:
        chat_logger.error(f"[CHAT] AI response failed: {e}")
        logger.error(f"AI response generation failed: {e}", exc_info=True)
        # Remove thinking message and add error
        messages = [m for m in messages if not m.get('metadata', {}).get('thinking')]
        messages.append({
            'type': 'assistant',
            'content': (
                "I'm having trouble analyzing the data right now. "
                "Please try again in a moment."
            ),
            'timestamp': datetime.now().isoformat(),
            'metadata': {'error': str(e)}
        })
    
    # Return updated messages to store ONLY
    # The sync_store_to_container callback will update the UI
    # Ensure outgoing payload is JSON-safe to avoid silent client-side drops
    safe_messages = _ensure_json_safe_messages(messages)
    if not safe_messages and messages:
        try:
            safe_messages = json.loads(json.dumps(messages, default=str))
            chat_logger.warning(
                "[CHAT] Sanitizer produced empty list; using JSON-coerced fallback with %d messages",
                len(safe_messages)
            )
        except Exception as fallback_exc:
            chat_logger.error(f"[CHAT] Fallback serialization failed: {fallback_exc}")
            safe_messages = []
    _last_chat_messages = safe_messages
    chat_logger.info(f"[CHAT] Returning {len(safe_messages)} messages to store")
    rendered = AIAssistantDashboard.render_messages(safe_messages)
    return safe_messages, rendered


# Callback to sync store to container - THE ONLY writer to chat-messages-container
# This ensures the container always reflects the store state
@callback(
    Output('chat-messages-container', 'children', allow_duplicate=True),
    Input('chat-messages-store', 'data'),
    prevent_initial_call='initial_duplicate'
)
def sync_store_to_container(messages):
    """
    Sync chat-messages-store to chat-messages-container.
    
    This callback fires whenever the store changes (new message added).
    It's the ONLY callback that writes to chat-messages-container.
    """
    from src.dashboards_dash.ai_assistant_dashboard import AIAssistantDashboard
    global _last_chat_messages, _last_render_signature
    
    chat_logger.info(f"[SYNC] Called with messages type={type(messages)}, count={len(messages) if messages else 0}")

    def _signature(payload: Any) -> Optional[str]:
        try:
            return hashlib.sha1(
                json.dumps(payload, sort_keys=True, default=str).encode('utf-8')
            ).hexdigest()
        except Exception as exc:
            chat_logger.debug(f"[SYNC] Signature generation failed: {exc}")
            return None

    # If we receive a JSON string, try to decode it
    if isinstance(messages, str):
        try:
            decoded = json.loads(messages)
            chat_logger.warning("[SYNC] Decoded messages from JSON string payload")
            messages = decoded
        except Exception as decode_exc:
            chat_logger.error(f"[SYNC] Failed to decode string payload: {decode_exc}")
            messages = []
    
    # Handle None or empty with fallback to last known messages
    if not messages:
        if _last_chat_messages:
            sig = _signature(_last_chat_messages)
            if sig and sig == _last_render_signature:
                chat_logger.debug("[SYNC] No content change; skipping render")
                return no_update
            _last_render_signature = sig
            chat_logger.warning("[SYNC] Store empty; rendering last known chat messages (%d)", len(_last_chat_messages))
            return AIAssistantDashboard.render_messages(_last_chat_messages)
        chat_logger.info("[SYNC] Rendering empty placeholder (no messages)")
        placeholder = [
            html.Div([
                html.P([
                    html.I(className="bi bi-info-circle me-2"),
                    "AI will send proactive alerts during the race. ",
                    "You can also ask questions anytime."
                ], className="text-muted small text-center mb-0")
            ], style={"padding": "20px"})
        ]
        if _last_render_signature != 'EMPTY_PLACEHOLDER':
            _last_render_signature = 'EMPTY_PLACEHOLDER'
            return placeholder
        return no_update
    
    # Handle dict (dcc.Store serialization quirk)
    if isinstance(messages, dict):
        messages = [v for v in messages.values() if v is not None]
    
    # Filter valid messages
    messages = [m for m in messages if m is not None and isinstance(m, dict)]

    if messages:
        sig = _signature(messages)
        if sig and sig == _last_render_signature:
            chat_logger.debug("[SYNC] No content change; skipping render")
            return no_update
        _last_render_signature = sig
        _last_chat_messages = messages
    
    chat_logger.debug(f"[SYNC] Rendering {len(messages)} messages")
    return AIAssistantDashboard.render_messages(messages)


@callback(
    Output('chat-messages-store', 'data', allow_duplicate=True),
    Input('clear-chat-btn', 'n_clicks'),
    prevent_initial_call=True
)
def clear_chat(n_clicks):
    """Clear all chat messages."""
    if not n_clicks:
        raise PreventUpdate
    global _last_chat_messages
    _last_chat_messages = []
    return []


# Store to track last known context for chat clearing
_last_chat_context = {'year': None, 'circuit': None, 'session': None}


@callback(
    Output('chat-messages-store', 'data', allow_duplicate=True),
    Input('year-selector', 'value'),
    Input('circuit-selector', 'value'),
    Input('session-selector', 'value'),
    State('chat-messages-store', 'data'),
    prevent_initial_call=True
)
def clear_chat_on_context_change(year, circuit, session_type, current_messages):
    """Clear chat history when year, circuit or session changes.
    
    Only clears when there's a REAL context change, not on every trigger.
    Driver changes don't clear chat (user may be comparing drivers).
    """
    global _last_chat_context
    
    # Check if this is a real context change
    context_changed = (
        _last_chat_context['year'] is not None and (
            year != _last_chat_context['year'] or
            circuit != _last_chat_context['circuit'] or
            session_type != _last_chat_context['session']
        )
    )
    
    # Update stored context
    _last_chat_context = {
        'year': year,
        'circuit': circuit,
        'session': session_type
    }
    
    # Only clear if there was a real change AND we had previous context
    if context_changed:
        chat_logger.info(
            f"[CHAT] Context changed - clearing chat "
            f"(year={year}, circuit={circuit}, session={session_type})"
        )
        global _last_chat_messages
        _last_chat_messages = []
        return []
    
    # No change - keep existing messages
    raise PreventUpdate


@callback(
    Output('chat-input', 'value'),
    Input('chat-send-btn', 'n_clicks'),
    Input('chat-input', 'n_submit'),
    prevent_initial_call=True
)
def clear_input(send_clicks, enter_submit):
    """Clear input field after sending."""
    return ""


@callback(
    Output('chat-messages-store', 'data', allow_duplicate=True),
    Output('proactive-last-check-store', 'data'),
    Input('proactive-check-interval', 'n_intervals'),
    State('chat-messages-store', 'data'),
    State('proactive-last-check-store', 'data'),
    State('session-store', 'data'),
    State('driver-selector', 'value'),
    State('simulation-time-store', 'data'),
    prevent_initial_call=True
)
def check_proactive_alerts(
    n_intervals,
    current_messages,
    last_check_data,
    session_data,
    focused_driver,
    sim_time_data
):
    """
    Periodically check for race events and generate proactive alerts.
    
    CRITICAL: Only uses data up to current simulation time (NO FUTURE DATA).
    """
    proactive_logger.debug(
        f"[PROACTIVE] check_proactive_alerts triggered, "
        f"interval={n_intervals}, focused_driver={focused_driver}"
    )
    
    if not session_data or not session_data.get('loaded'):
        proactive_logger.debug("[PROACTIVE] No session loaded, skipping")
        raise PreventUpdate
    
    # Check if driver is selected - required for most alerts
    if not focused_driver or focused_driver == 'none':
        proactive_logger.debug("[PROACTIVE] No driver selected, skipping (select a driver to enable alerts)")
        raise PreventUpdate
    
    global _last_chat_messages

    messages = _ensure_json_safe_messages(current_messages)
    if not messages and _last_chat_messages:
        messages = json.loads(json.dumps(_last_chat_messages))
    last_lap = last_check_data.get('last_lap', 0) if last_check_data else 0
    
    try:
        # Get current simulation state
        session_key = session_data.get('session_key')
        if not session_key:
            proactive_logger.debug("[PROACTIVE] No session_key, skipping")
            raise PreventUpdate
        
        # Parse simulation time
        sim_time = sim_time_data.get('time', 0) if sim_time_data else 0
        
        # Get current lap from simulation controller
        current_lap = 1
        if simulation_controller:
            current_lap = simulation_controller.get_current_lap()
        
        proactive_logger.debug(f"[PROACTIVE] current_lap={current_lap}, last_lap={last_lap}")
        
        # Get current time from simulation
        current_time = None
        if simulation_controller:
            current_time = simulation_controller.current_time
        
        if not current_time:
            proactive_logger.debug("[PROACTIVE] No current_time, skipping")
            raise PreventUpdate
        
        proactive_logger.info(f"[PROACTIVE] Checking events at lap {current_lap}, time={current_time}")
        
        # Get focused driver number from the value format "VER_2025_1"
        driver_number = None
        if focused_driver and focused_driver != 'none':
            try:
                # focused_driver format: "CODE_YEAR_NUMBER" e.g. "VER_2025_1"
                parts = focused_driver.split('_')
                if len(parts) >= 3:
                    driver_number = int(parts[-1])  # Last part is driver number
                    proactive_logger.info(
                        f"[PROACTIVE] Tracking driver #{driver_number} ({parts[0]})"
                    )
            except (ValueError, IndexError) as e:
                proactive_logger.warning(
                    f"[PROACTIVE] Could not parse driver from {focused_driver}: {e}"
                )
        
        proactive_logger.debug(f"[PROACTIVE] focused_driver={focused_driver}, driver_number={driver_number}")
        
        # Detect events
        events = event_detector.detect_events(
            session_key=session_key,
            current_time=current_time,
            current_lap=current_lap,
            focused_driver=driver_number,
            total_laps=session_data.get('total_laps', 57)
        )
        
        if events:
            proactive_logger.info(f"[PROACTIVE] ✓ Detected {len(events)} events!")
        else:
            proactive_logger.info(f"[PROACTIVE] No events (driver={driver_number}, lap={current_lap})")
        
        # Add alerts for detected events
        for event in events:
            proactive_logger.info(f"[PROACTIVE] EVENT: {event.event_type} - {event.message[:50]}...")
            messages.append({
                'type': 'alert',
                'content': event.message,
                'timestamp': datetime.now().isoformat(),
                'priority': event.priority,
                'metadata': {
                    'event_type': event.event_type,
                    'data': event.data
                }
            })
        
        # CRITICAL: Only update store if we actually added new events
        # This prevents overwriting chat messages added by other callbacks
        if events:
            safe_messages = _ensure_json_safe_messages(messages)
            _last_chat_messages = safe_messages
            return safe_messages, {'last_lap': current_lap}
        else:
            # No events - don't touch the store, just update last_lap tracking
            return no_update, {'last_lap': current_lap}
        
    except PreventUpdate:
        raise  # Re-raise PreventUpdate without logging
    except Exception as e:
        import traceback
        proactive_logger.warning(f"[PROACTIVE] Alert check failed: {e}")
        proactive_logger.debug(f"[PROACTIVE] Traceback: {traceback.format_exc()}")
        raise PreventUpdate


@callback(
    Output('proactive-check-interval', 'disabled'),
    Input('play-btn', 'n_clicks'),
    prevent_initial_call=True
)
def toggle_proactive_interval(n_clicks):
    """Enable/disable proactive checking when simulation plays/pauses."""
    if not n_clicks:
        raise PreventUpdate
    
    # Check actual simulation state
    if simulation_controller is None:
        proactive_logger.debug("[PROACTIVE] No simulation controller, interval stays disabled")
        return True  # Keep disabled
    
    # Get actual is_playing state (after toggle_play_pause was called)
    is_playing = simulation_controller.is_playing
    
    # If playing, enable interval (disabled=False). If paused, disable (disabled=True)
    new_disabled = not is_playing
    proactive_logger.info(f"[PROACTIVE] Interval toggled: disabled={new_disabled} (is_playing={is_playing})")
    return new_disabled


# ============================================================================
# RACE STATE SNAPSHOT AND AI CONTEXT
# ============================================================================

def get_race_state_snapshot(
    session_data: Optional[Dict],
    sim_time_data: Optional[Dict],
    focused_driver: Optional[str]
) -> Dict[str, Any]:
    """
    Generate comprehensive snapshot of current race state for AI context.
    
    Args:
        session_data: Session store data (race_name, session_key, etc.)
        sim_time_data: Simulation time store data (time, timestamp)
        focused_driver: Driver identifier (e.g., "RUS_2025_63")
        
    Returns:
        Dict with race state snapshot including leaderboard, weather, flags, etc.
    """
    try:
        # Check for None values
        if not session_data or not sim_time_data:
            return {'error': 'Missing session or simulation data'}
        
        session_key = session_data.get('session_key')
        simulation_time = sim_time_data.get('time', 0)
        total_laps = session_data.get('total_laps', 57)
        
        if not session_key or simulation_controller is None:
            return {'error': 'No session loaded or controller unavailable'}
        
        # Get current lap
        current_lap = simulation_controller.get_current_lap()
        session_start_time = simulation_controller.start_time
        
        # Convert datetime to pandas Timestamp for compatibility
        import pandas as pd
        session_start_timestamp = pd.Timestamp(session_start_time)
        
        snapshot = {
            'lap': current_lap,
            'total_laps': total_laps,
            'simulation_time': simulation_time,
            'race_name': session_data.get('race_name', 'Unknown'),
            'session_type': session_data.get('session_type', 'Race')
        }
        
        # Get leaderboard summary
        try:
            if race_overview_dashboard._cached_positions is not None:
                leaderboard = race_overview_dashboard.get_leaderboard_summary(
                    session_key=session_key,
                    simulation_time=simulation_time,
                    session_start_time=session_start_timestamp,
                    current_lap=current_lap,
                    focused_driver=focused_driver,
                    pit_window_range=3
                )
                snapshot['leaderboard'] = leaderboard
            else:
                snapshot['leaderboard'] = {'error': 'No leaderboard data cached'}
        except Exception as e:
            logger.error(f"Error getting leaderboard summary: {e}")
            snapshot['leaderboard'] = {'error': str(e)}
        
        # Get weather summary
        try:
            from src.dashboards_dash.weather_dashboard import get_weather_summary
            weather = get_weather_summary(
                session_key=session_key,
                simulation_time=simulation_time,
                provider=openf1_provider
            )
            snapshot['weather'] = weather
        except Exception as e:
            logger.error(f"Error getting weather summary: {e}")
            snapshot['weather'] = {'error': str(e)}
        
        # Get race control status
        try:
            if race_control_dashboard._cached_messages is not None:
                status = race_control_dashboard.get_status_summary(
                    session_key=session_key,
                    simulation_time=simulation_time,
                    session_start_time=session_start_timestamp,
                    current_lap=current_lap
                )
                snapshot['race_control'] = status
            else:
                snapshot['race_control'] = {'error': 'No race control data cached'}
        except Exception as e:
            logger.error(f"Error getting race control summary: {e}")
            snapshot['race_control'] = {'error': str(e)}
        
        return snapshot
        
    except Exception as e:
        logger.error(f"Error generating race state snapshot: {e}")
        return {'error': str(e)}


def format_race_snapshot_for_ai(snapshot: dict) -> str:
    """
    Format race state snapshot as markdown for AI prompt.
    
    Args:
        snapshot: Race state snapshot dict from get_race_state_snapshot()
        
    Returns:
        Formatted markdown string for system prompt
    """
    if 'error' in snapshot:
        return f"⚠️ **No race data available**: {snapshot['error']}"
    
    lines = []
    
    # Check for Safety Car or VSC FIRST - this is critical info!
    race_control = snapshot.get('race_control', {})
    safety_car_active = race_control.get('safety_car', False)
    vsc_active = race_control.get('virtual_safety_car', False)
    flag = race_control.get('flag', 'GREEN')
    
    # PROMINENT SC/VSC WARNING AT THE TOP
    if safety_car_active or flag == 'SC':
        lines.append("## 🚨🚨🚨 SAFETY CAR DEPLOYED 🚨🚨🚨")
        lines.append("")
        lines.append("**⚠️ CRITICAL: The Safety Car is currently on track!**")
        lines.append("- **Pit window is OPEN** - Gap to cars behind is minimized")
        lines.append("- All drivers can pit with minimal time loss")
        lines.append("- Field is bunched up - positions will be closer on restart")
        lines.append("")
        lines.append("---")
        lines.append("")
    elif vsc_active or flag == 'VSC':
        lines.append("## 🟡🟡🟡 VIRTUAL SAFETY CAR ACTIVE 🟡🟡🟡")
        lines.append("")
        lines.append("**⚠️ VSC is deployed - speeds are reduced**")
        lines.append("- Pit stop time loss is reduced (~5-7 seconds)")
        lines.append("- Good opportunity to pit if strategy allows")
        lines.append("")
        lines.append("---")
        lines.append("")
    elif flag == 'RED':
        lines.append("## 🔴🔴🔴 RED FLAG 🔴🔴🔴")
        lines.append("")
        lines.append("**Race is stopped. All cars must return to pit lane.**")
        lines.append("")
        lines.append("---")
        lines.append("")
    
    lines.append("## 🏁 CURRENT RACE STATE")
    lines.append("")
    
    # Race info
    lines.append(
        f"**Race**: {snapshot.get('race_name', 'Unknown')} - "
        f"{snapshot.get('session_type', 'Race')}"
    )
    lines.append(f"**Lap**: {snapshot.get('lap', '?')}/{snapshot.get('total_laps', '?')}")
    lines.append("")
    
    # Leaderboard
    leaderboard = snapshot.get('leaderboard', {})
    if 'error' not in leaderboard:
        # Focus driver
        focus = leaderboard.get('focus_driver')
        if focus:
            lines.append(f"### 🎯 {focus['driver']} (P{focus['pos']})")
            lines.append(f"- **Gap to leader**: {focus['gap_to_leader']}")
            lines.append(f"- **Gap ahead**: {focus['gap_ahead']}")
            lines.append(f"- **Gap behind**: {focus['gap_behind']}")
            lines.append(f"- **Tire**: {focus['tire']} (Age: {focus['age']} laps)")
            lines.append(f"- **Pit stops**: {focus['stops']}")
            lines.append("")
        
        # Pit window drivers
        pit_window = leaderboard.get('pit_window', [])
        if pit_window:
            lines.append("### 🔧 Pit Window (nearby drivers)")
            lines.append("| Pos | Driver | Gap | Tire | Age | Stops |")
            lines.append("|-----|--------|-----|------|-----|-------|")
            for driver in pit_window:
                lines.append(
                    f"| P{driver['pos']} | {driver['driver']} | {driver['gap']} | "
                    f"{driver['tire']} | {driver['age']} | {driver['stops']} |"
                )
            lines.append("")
        
        # Top 10
        top_10 = leaderboard.get('top_10', [])
        if top_10 and not focus:  # Only show if no focus driver
            lines.append("### 🏆 Top 10")
            lines.append("| Pos | Driver | Gap | Tire | Age | Stops |")
            lines.append("|-----|--------|-----|------|-----|-------|")
            for driver in top_10[:5]:  # Only top 5
                lines.append(
                    f"| P{driver['pos']} | {driver['driver']} | {driver['gap']} | "
                    f"{driver['tire']} | {driver['age']} | {driver['stops']} |"
                )
            lines.append("")
    
    # Weather
    weather = snapshot.get('weather', {})
    if 'error' not in weather:
        lines.append("### 🌤️ Weather")
        lines.append(f"- **Air temp**: {weather.get('air_temp', '?')}°C")
        lines.append(f"- **Track temp**: {weather.get('track_temp', '?')}°C")
        lines.append(f"- **Wind**: {weather.get('wind_speed', '?')} km/h {weather.get('wind_direction', '')}")
        lines.append(f"- **Humidity**: {weather.get('humidity', '?')}%")
        if weather.get('rainfall'):
            lines.append(f"- **⚠️ RAINFALL DETECTED**")
        lines.append("")
    
    # Race control - show recent events (SC/VSC already shown at top)
    if 'error' not in race_control:
        recent_events = race_control.get('recent_events', [])
        if recent_events:
            lines.append("### 🚦 Recent Race Control Messages")
            for event in recent_events[:3]:
                lines.append(f"- {event}")
        lines.append("")
    
    return "\n".join(lines)


# ============================================================================
# PROACTIVE AI WARNINGS SYSTEM
# ============================================================================

# Global warning tracking to avoid spam
warning_tracker = {}


def analyze_race_state_for_warnings(
    snapshot: Dict[str, Any],
    session_data: Dict,
    focused_driver: str
) -> Optional[str]:
    """
    Analyze race state snapshot and generate proactive warnings using AI.
    
    Returns warning message if significant tactical situation detected,
    None otherwise.
    
    Checks for:
    - Undercut/overcut opportunities
    - Pit window entry/exit timing
    - Tire degradation issues
    - Safety car situations
    - Weather changes
    """
    if not snapshot:
        return None
    
    # Get current lap and driver info
    current_lap = snapshot.get('lap', 0)
    driver_code = focused_driver if focused_driver != 'none' else None
    
    if not driver_code or current_lap == 0:
        return None
    
    # Check if we've warned recently for this situation
    warning_key = f"{driver_code}_{current_lap // 3}"  # Group by 3-lap windows
    
    if warning_key in warning_tracker:
        last_warning_lap = warning_tracker[warning_key]
        if current_lap - last_warning_lap < 3:
            return None  # Don't spam warnings
    
    # Get AI-formatted snapshot
    race_context = format_race_snapshot_for_ai(snapshot)
    
    # Build prompt for tactical analysis
    analysis_prompt = (
        "You are an F1 race strategist monitoring the live race. "
        "Analyze this race state and determine if there are any "
        "CRITICAL tactical situations that require immediate attention.\n\n"
        f"Focus driver: {driver_code}\n\n"
        f"{race_context}\n\n"
        "Analyze for:\n"
        "- Undercut/overcut opportunities (cars within 3s with different tire ages)\n"
        "- Pit window timing (optimal laps to pit based on tire age and gaps)\n"
        "- Safety car/VSC situations (pit now or wait?)\n"
        "- Weather changes (tire strategy changes needed?)\n"
        "- Position battles (DRS trains, blue flags)\n\n"
        "ONLY respond if there is a CRITICAL situation requiring immediate action. "
        "If everything is normal or no urgent decisions needed, respond with: "
        "'NO_WARNING'\n\n"
        "If warning needed, respond with format:\n"
        "**WARNING:** [Brief title]\n"
        "[2-3 sentence explanation with specific numbers and recommendation]"
    )
    
    # Get LLM provider
    llm_provider = get_llm_provider()
    if not llm_provider:
        return None
    
    try:
        import asyncio
        
        async def get_warning():
            return await llm_provider.generate(
                prompt=analysis_prompt,
                system_prompt="You are an F1 race strategist providing tactical warnings."
            )
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            response: LLMResponse = loop.run_until_complete(get_warning())
        finally:
            loop.close()
        
        warning_text = response.content.strip()
        
        # Check if AI indicates no warning needed
        if 'NO_WARNING' in warning_text or len(warning_text) < 20:
            return None
        
        # Update warning tracker
        warning_tracker[warning_key] = current_lap
        
        # Clean old entries from tracker (keep last 20 laps)
        keys_to_remove = [
            k for k, v in warning_tracker.items()
            if current_lap - v > 20
        ]
        for k in keys_to_remove:
            del warning_tracker[k]
        
        return warning_text
    
    except Exception as e:
        logger.debug(f"AI warning generation failed: {e}")
        return None


# NOTE: check_proactive_ai_warnings callback DISABLED for Phase 1
# This uses LLM analysis which can block the UI. 
# Use rule-based check_proactive_alerts instead.
# Will be re-enabled in Phase 3 with async/background processing.
#
# @callback(
#     Output('chat-messages-store', 'data', allow_duplicate=True),
#     Input('proactive-check-interval', 'n_intervals'),
#     State('session-store', 'data'),
#     State('simulation-time-store', 'data'),
#     State('driver-selector', 'value'),
#     State('chat-messages-store', 'data'),
#     prevent_initial_call=True
# )
def check_proactive_ai_warnings_DISABLED(
    n_intervals,
    session_data,
    sim_time_data,
    focused_driver,
    existing_messages
):
    """
    DISABLED: Periodically check race state and generate AI-powered tactical warnings.
    
    Runs every 5 seconds (configured in proactive-check-interval).
    Only generates warnings for significant tactical situations.
    
    NOTE: This callback is disabled in Phase 1 because:
    1. LLM calls can take 2-5 seconds, blocking the UI
    2. It conflicts with check_proactive_alerts (same interval)
    3. Will be re-enabled with async processing in Phase 3
    """
    proactive_logger.debug("[PROACTIVE-LLM] Callback disabled in Phase 1")
    raise PreventUpdate
    
    # Original code preserved for Phase 3:
    if not session_data or not simulation_controller:
        raise PreventUpdate
    
    if not simulation_controller.is_playing:
        raise PreventUpdate
    
    try:
        # Get race state snapshot
        snapshot = get_race_state_snapshot(
            session_data=session_data,
            sim_time_data=sim_time_data,
            focused_driver=focused_driver
        )
        
        if not snapshot:
            raise PreventUpdate
        
        # Analyze for warnings
        warning = analyze_race_state_for_warnings(
            snapshot=snapshot,
            session_data=session_data,
            focused_driver=focused_driver
        )
        
        if not warning:
            raise PreventUpdate
        
        # Create warning message
        messages = existing_messages or []
        messages.append({
            'type': 'ai',
            'content': f"🚨 **TACTICAL ALERT**\n\n{warning}",
            'timestamp': datetime.now().isoformat(),
            'metadata': {
                'proactive': True,
                'lap': snapshot.get('lap', 0)
            }
        })
        
        return messages
        
    except Exception as e:
        proactive_logger.warning(f"[PROACTIVE-LLM] AI warning check failed: {e}")
        raise PreventUpdate


def generate_ai_response(
    query: str,
    session_data: Optional[Dict],
    focused_driver: Optional[str],
    sim_time_data: Optional[Dict],
    message_history: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Generate AI response using RAG + LLM.
    
    Process:
    1. Search RAG for relevant context documents
    2. Build context from RAG results  
    3. Send to LLM with context for intelligent response
    4. If no LLM available, return informative message
    """
    query_lower = query.lower()

    history_block = ""
    if message_history:
        trimmed_history = message_history[-8:]
        history_lines = []
        for msg in trimmed_history:
            role = str(msg.get('type', 'assistant')).lower()
            prefix = "User" if role == 'user' else "AI"
            content = str(msg.get('content', '')).strip()
            if len(content) > 280:
                content = f"{content[:277]}..."
            history_lines.append(f"- {prefix}: {content}")
        if history_lines:
            history_block = "Recent conversation:\n" + "\n".join(history_lines)
    
    # Get context info
    race_name = (
        session_data.get('race_name', 'the race') if session_data else 'the race'
    )
    driver = (
        focused_driver if focused_driver and focused_driver != 'none'
        else 'a driver'
    )
    year = session_data.get('year', 2024) if session_data else 2024
    
    # Get current lap (available whether playing or paused)
    current_lap = None
    if simulation_controller:
        openf1_lap = simulation_controller.get_current_lap()
        current_lap = max(1, openf1_lap - 2) if openf1_lap > 2 else 1
    
    lap_info = f"Lap {current_lap}" if current_lap else "Pre-race"
    
    # Search RAG for context
    rag_manager = get_rag_manager()
    rag_context = ""
    rag_sources = []
    
    if rag_manager.is_context_loaded():
        # Determine category based on query
        category = None
        if any(w in query_lower for w in ['pit', 'tire', 'tyre', 'stop', 'strategy']):
            category = 'strategy'
        elif any(w in query_lower for w in ['weather', 'rain', 'wet', 'dry']):
            category = 'weather'
        elif any(w in query_lower for w in ['fia', 'rule', 'regulation', 'penalty']):
            category = 'fia'
        
        # Search RAG
        rag_results = rag_manager.search(query=query, k=5, category=category)
        
        if rag_results:
            context_parts = []
            for result in rag_results:
                source = result.get('metadata', {}).get('source', 'unknown')
                content = result.get('content', '')
                if content:
                    context_parts.append(content)
                    rag_sources.append(source)
            rag_context = "\n\n".join(context_parts)
    
    # Get live race state snapshot
    race_context = ""
    if simulation_controller and session_data and sim_time_data:
        try:
            snapshot = get_race_state_snapshot(
                session_data=session_data,
                sim_time_data=sim_time_data,
                focused_driver=focused_driver
            )
            
            if snapshot and 'error' not in snapshot:
                race_context = format_race_snapshot_for_ai(snapshot)
            else:
                logger.warning(f"No valid snapshot - error: {snapshot.get('error') if snapshot else 'None'}")
        except Exception as e:
            logger.error(f"Failed to get race snapshot: {e}")
            race_context = ""
    
    # Get LLM provider
    llm_provider = get_llm_provider()
    
    if llm_provider is not None:
        # Build system prompt for F1 strategy expert with specific guidance
        base_prompt = (
            f"You are an expert F1 race strategist. Session: {race_name} ({year}), {lap_info}. "
            f"Focused on driver: {driver}.\n\n"
            "Guidelines:\n"
            "- Provide SPECIFIC strategic recommendations (pit stops, tire strategy, overtaking)\n"
            "- Use real numbers from the live data (tire age, lap times, gaps)\n"
            "- Be concise but COMPLETE (3-5 sentences for complex questions)\n"
            "- For pit stop questions: analyze tire wear, lap delta, and track position\n"
            "- Always reference the current race situation in your answer"
        )
        
        # Add live race state if available
        if race_context:
            system_prompt = (
                f"{base_prompt}\n\n"
                f"## CURRENT RACE STATE\n{race_context}\n\n"
                f"Use this live data to provide tactical advice. Be specific and data-driven."
            )
        else:
            system_prompt = base_prompt + "\n\nNote: Limited live data available. Use general F1 strategy knowledge."
        
        # Build concise user prompt
        prompt_sections: list[str] = []
        if history_block:
            prompt_sections.append(history_block)
        if rag_context:
            prompt_sections.append(f"Context:\n{rag_context}")
            prompt_sections.append(
                f"Q: {query}\n\n"
                f"Give a brief, specific answer using the context."
            )
        else:
            prompt_sections.append(
                f"Q: {query}\n\nAnswer briefly with available general F1 knowledge."
            )
        user_prompt = "\n\n".join(prompt_sections)
        
        try:
            # Call LLM asynchronously
            import asyncio
            
            async def get_llm_response():
                return await llm_provider.generate(
                    prompt=user_prompt,
                    system_prompt=system_prompt
                )
            
            # Run async function
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                llm_response: LLMResponse = loop.run_until_complete(
                    get_llm_response()
                )
            finally:
                loop.close()
            
            # Format response with provider prefix
            response_content = llm_response.content
            
            # Add provider prefix (Claude: or Gemi:)
            provider_name = llm_response.provider.lower() if llm_response.provider else ''
            if 'claude' in provider_name or 'anthropic' in provider_name:
                provider_prefix = "**Claude:** "
            elif 'gemini' in provider_name or 'google' in provider_name:
                provider_prefix = "**Gemi:** "
            else:
                provider_prefix = ""
            
            response_content = provider_prefix + response_content
            
            # Add source attribution if RAG was used
            if rag_sources:
                unique_sources = list(set(rag_sources))
                source_text = ", ".join(unique_sources[:3])
                response_content += (
                    f"\n\n---\n"
                    f"_📚 Sources: {source_text}_"
                )
            
            return {
                'content': response_content,
                'metadata': {
                    'confidence': 0.9,
                    'agents_used': ['LLM', 'RAG'] if rag_context else ['LLM'],
                    'llm_provider': llm_response.provider,
                    'llm_model': llm_response.model,
                    'tokens_used': llm_response.total_tokens,
                    'rag_sources': len(rag_sources)
                }
            }
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            # Fall through to no-LLM response
    
    # No LLM available - show clear error
    return {
        'content': (
            f"❌ **API Key Required**\n\n"
            f"The AI Assistant needs at least one LLM API key to respond.\n\n"
            f"**Configure in sidebar → ⚙️ Configuration:**\n"
            f"• **Claude** (Anthropic): `ANTHROPIC_API_KEY`\n"
            f"• **Gemini** (Google): `GOOGLE_API_KEY`\n\n"
            f"After entering your key, click **'💾 Save Keys'**.\n\n"
            f"---\n"
            f"_Your question: \"{query}\"_"
        ),
        'metadata': {
            'confidence': 0.0,
            'agents_used': [],
            'error': 'No LLM API key configured'
        }
    }


# ============================================================================
# TELEMETRY COMPARISON DRIVER CALLBACK
# ============================================================================

@callback(
    Output('telemetry-comparison-store', 'data'),
    Input('telemetry-comparison-driver', 'value'),
    prevent_initial_call=True
)
def update_telemetry_comparison(comparison_driver):
    """Update the comparison driver for telemetry dashboard."""
    telem_logger.debug(f"Telemetry comparison driver: {comparison_driver}")
    return {'driver': comparison_driver}


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

    # debug=False to ensure logs appear in terminal
    app.run(debug=False, port=8502)
