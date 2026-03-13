"""
F1 Strategist AI - Main Application Container.

Multi-dashboard F1 strategy platform with live and simulation modes.
"""

import logging
import os
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional, List, Tuple

import fastf1
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# Core infrastructure
from src.agents.base_agent import AgentConfig, AgentContext
from src.agents.orchestrator import AgentOrchestrator
from src.agents.performance_agent import PerformanceAgent
from src.agents.race_control_agent import RaceControlAgent
from src.agents.race_position_agent import RacePositionAgent
from src.agents.strategy_agent import StrategyAgent
from src.agents.weather_agent import WeatherAgent
from src.chatbot.message_handler import MessageHandler
from src.chatbot.session_manager import SessionManager
from src.llm.hybrid_router import HybridRouter
from src.llm.models import LLMConfig
from src.rag.chromadb_store import ChromaDBStore

# Session management
from src.session.global_session import (
    GlobalSession,
    RaceContext,
    SessionMode,
    SessionType,
)
from src.session.live_detector import check_for_live_session

# UI components
from src.ui.simulation_controls import SimulationControls
from src.ui.top_menu import TopMenu
from src.ui.live_session_info import LiveSessionInfo

# Dashboards
from src.dashboards.ai_assistant_dashboard import AIAssistantDashboard

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables from centralized config/.env
load_dotenv(Path(__file__).parent / "config" / ".env", override=True)

# Page configuration
st.set_page_config(
    page_title="F1 Strategist AI",
    page_icon="🏎️",
    layout="wide",
    initial_sidebar_state="expanded"
)


@st.cache_resource
def initialize_agents() -> Optional[Dict[str, Any]]:
    """
    Initialize the agent system.

    Creates all agents, orchestrator, and supporting infrastructure.
    Returns components needed for the application.
    """
    logger.info("Initializing F1 Strategist AI agent system...")

    try:
        # Get API keys from environment
        claude_api_key = os.getenv("ANTHROPIC_API_KEY", "")
        gemini_api_key = os.getenv("GOOGLE_API_KEY", "")

        # Create LLM configurations
        claude_config = LLMConfig(
            model_name="claude-3-5-sonnet-20241022",
            api_key=claude_api_key,
            max_tokens=4096,
            temperature=0.7
        )

        gemini_config = LLMConfig(
            model_name="gemini-2.0-flash-exp",
            api_key=gemini_api_key,
            max_tokens=4096,
            temperature=0.7,
            extra_params={"enable_thinking": False}
        )

        # Initialize LLM provider
        llm_provider = HybridRouter(
            claude_config=claude_config,
            gemini_config=gemini_config
        )

        # Initialize RAG system (optional)
        try:
            rag_system = ChromaDBStore(
                collection_name="f1_strategy_knowledge"
            )
        except Exception as e:
            logger.warning(f"RAG system not available: {e}")
            rag_system = None

        # Create agent configurations
        base_config = {
            "llm_provider": llm_provider,
            "rag_system": rag_system,
            "enable_tools": False
        }

        strategy_config = AgentConfig(
            name="StrategyAgent",
            description="F1 race and qualifying strategy optimization",
            temperature=0.7,
            **base_config
        )

        weather_config = AgentConfig(
            name="WeatherAgent",
            description="Weather impact analysis",
            temperature=0.6,
            **base_config
        )

        performance_config = AgentConfig(
            name="PerformanceAgent",
            description="Lap time and telemetry analysis",
            temperature=0.5,
            **base_config
        )

        race_control_config = AgentConfig(
            name="RaceControlAgent",
            description="Track status and incident monitoring",
            temperature=0.6,
            **base_config
        )

        position_config = AgentConfig(
            name="RacePositionAgent",
            description="Gap analysis and track position",
            temperature=0.6,
            **base_config
        )

        # Create agents
        strategy_agent = StrategyAgent(strategy_config)
        weather_agent = WeatherAgent(weather_config)
        performance_agent = PerformanceAgent(performance_config)
        race_control_agent = RaceControlAgent(race_control_config)
        position_agent = RacePositionAgent(position_config)

        # Create orchestrator
        orchestrator = AgentOrchestrator(
            strategy_agent=strategy_agent,
            weather_agent=weather_agent,
            performance_agent=performance_agent,
            race_control_agent=race_control_agent,
            race_position_agent=position_agent
        )

        # Create chat infrastructure
        session_manager = SessionManager()
        message_handler = MessageHandler(
            orchestrator=orchestrator,
            session_manager=session_manager
        )

        logger.info("Agent system initialized successfully!")

        return {
            "orchestrator": orchestrator,
            "session_manager": session_manager,
            "message_handler": message_handler,
            "agents": {
                "strategy": strategy_agent,
                "weather": weather_agent,
                "performance": performance_agent,
                "race_control": race_control_agent,
                "position": position_agent
            }
        }

    except Exception as e:
        logger.warning(f"Agent system not available: {e}")
        return None  # Return None but don't show error yet


def get_last_completed_race() -> Optional[RaceContext]:
    """
    Get the most recent completed race based on current date.

    Returns:
        RaceContext for last completed race, or None if error
    """
    try:
        current_year = datetime.now().year
        # Use timezone-aware datetime for comparison
        current_time = pd.Timestamp.now(tz='UTC')

        # Try current year first
        schedule = fastf1.get_event_schedule(current_year)

        # Find the last race that already happened
        last_race = None
        for _, event in schedule.iterrows():
            # Check Session5 (Race) date
            race_date = event.get('Session5Date')
            if pd.isna(race_date):
                continue

            if isinstance(race_date, str):
                race_date = pd.to_datetime(race_date, utc=True)

            # If race is in the past
            if race_date < current_time:
                last_race = event
            else:
                # Stop when we hit a future race
                break

        if last_race is not None:
            round_num = int(last_race['RoundNumber'])
            country = last_race['Country']
            circuit_name = last_race['OfficialEventName']
            race_date = last_race['Session5Date']

            if isinstance(race_date, str):
                race_date = pd.to_datetime(race_date, utc=True)

            # Convert to naive datetime for RaceContext
            if hasattr(race_date, 'tz_localize'):
                race_date = race_date.tz_localize(None)
            elif hasattr(race_date, 'tz_convert'):
                race_date = race_date.tz_convert(None)

            return RaceContext(
                year=current_year,
                round_number=round_num,
                circuit_name=circuit_name,
                circuit_key=country.lower().replace(' ', '_'),
                country=country,
                session_type=SessionType.RACE,
                session_date=race_date.to_pydatetime() if hasattr(race_date, 'to_pydatetime') else race_date,
                total_laps=57,
                current_lap=1
            )

        # If no past races in current year, try previous year
        prev_year = current_year - 1
        schedule_prev = fastf1.get_event_schedule(prev_year)
        last_event = schedule_prev.iloc[-1]

        round_num = int(last_event['RoundNumber'])
        country = last_event['Country']
        circuit_name = last_event['OfficialEventName']
        race_date = last_event['Session5Date']

        if isinstance(race_date, str):
            race_date = pd.to_datetime(race_date, utc=True)

        # Convert to naive datetime
        if hasattr(race_date, 'tz_localize'):
            race_date = race_date.tz_localize(None)
        elif hasattr(race_date, 'tz_convert'):
            race_date = race_date.tz_convert(None)

        return RaceContext(
            year=prev_year,
            round_number=round_num,
            circuit_name=circuit_name,
            circuit_key=country.lower().replace(' ', '_'),
            country=country,
            session_type=SessionType.RACE,
            session_date=race_date.to_pydatetime() if hasattr(race_date, 'to_pydatetime') else race_date,
            total_laps=57,
            current_lap=1
        )

    except Exception as e:
        logger.error(f"Error getting last completed race: {e}")
        return None


def initialize_session() -> GlobalSession:
    """
    Initialize or retrieve global session state.

    Returns:
        Global session instance
    """
    if "global_session" not in st.session_state:
        logger.info("Initializing new global session...")

        # Try to get the last completed race
        race_context = get_last_completed_race()

        # Fallback to Bahrain if error
        if not race_context:
            logger.warning("Could not find last completed race, using Bahrain fallback")
            current_year = datetime.now().year
            race_context = RaceContext(
                year=current_year,
                round_number=1,
                circuit_name="Bahrain International Circuit",
                circuit_key="bahrain",
                country="Bahrain",
                session_type=SessionType.RACE,
                session_date=datetime(current_year, 3, 1, 15, 0),
                total_laps=57,
                current_lap=1
            )

        st.session_state.global_session = (
            GlobalSession.create_simulation_session(
                race_context=race_context,
                start_time=race_context.session_date
            )
        )

        logger.info(
            f"Global session initialized with {
                race_context.country} GP (Round {
                race_context.round_number}, {
                race_context.year})")

    return st.session_state.global_session


def check_live_session() -> Optional[RaceContext]:
    """
    Check if there's a live F1 session happening now.

    Checks if current time matches a session (with -3 hour buffer).
    Uses FastF1 calendar to detect active sessions.

    Returns:
        RaceContext if live session detected, None otherwise
    """
    try:
        return check_for_live_session()
    except Exception as e:
        logger.error(f"Error checking for live session: {e}")
        return None


@st.cache_data(ttl=3600)
def load_f1_calendar(year: int) -> pd.DataFrame:
    """Load F1 calendar for a specific year."""
    try:
        schedule = fastf1.get_event_schedule(year)
        return schedule
    except Exception as e:
        logger.error(f"Error loading F1 calendar for {year}: {e}")
        return pd.DataFrame()


def get_available_sessions(
    schedule: pd.DataFrame,
    round_number: int
) -> List[Tuple[str, SessionType]]:
    """
    Get available sessions for a specific race weekend.

    Args:
        schedule: F1 calendar DataFrame
        round_number: Race round number (1-based)

    Returns:
        List of (session_name, SessionType) tuples
    """
    try:
        event = schedule[schedule['RoundNumber'] == round_number].iloc[0]
        sessions = []

        # Map session names to SessionType
        session_mapping = {
            'Practice 1': SessionType.FP1,
            'Practice 2': SessionType.FP2,
            'Practice 3': SessionType.FP3,
            'Qualifying': SessionType.QUALIFYING,
            'Sprint Qualifying': SessionType.SPRINT_QUALIFYING,
            'Sprint Shootout': SessionType.SPRINT_QUALIFYING,
            'Sprint': SessionType.SPRINT,
            'Race': SessionType.RACE,
        }

        # Check each session slot
        for session_num in range(1, 6):
            session_col = f'Session{session_num}'
            session_date_col = f'Session{session_num}Date'

            # Check if session exists and has a date
            if session_col in event.index and pd.notna(event.get(session_date_col)):
                session_name = event[session_col]

                if session_name and str(session_name) != 'nan':
                    # Find matching SessionType
                    session_type = session_mapping.get(session_name)

                    if session_type:
                        sessions.append((session_name, session_type))
                    else:
                        # Log unknown session type
                        logger.warning(f"Unknown session type: {session_name}")

        return sessions if sessions else [("Race", SessionType.RACE)]
    except Exception as e:
        logger.error(f"Error getting sessions for round {round_number}: {e}")
        return [("Race", SessionType.RACE)]


def render_session_context_selector(
    session: GlobalSession,
    live_session_context: Optional[RaceContext] = None
) -> RaceContext:
    """
    Render session context selector using real FastF1 data.
    Should be called from within a sidebar context.

    Args:
        session: Global session state
        live_session_context: Live session context if detected

    Returns:
        Updated race context
    """

    # Determine initial values from live session or current context
    if live_session_context:
        default_year = live_session_context.year
        default_circuit = live_session_context.country
        default_session_type = live_session_context.session_type
    elif session.race_context:
        default_year = session.race_context.year
        default_circuit = session.race_context.country
        default_session_type = session.race_context.session_type
    else:
        default_year = datetime.now().year
        default_circuit = "Bahrain"
        default_session_type = SessionType.RACE

    # Year selector
    year_options = list(range(2018, 2027))  # Extended to 2026
    # Ensure default_year is current year if not from live/previous context
    if default_year < 2024:  # If old year detected, use current year
        default_year = datetime.now().year

    year = st.selectbox(
        "**Year**",
        options=year_options,
        index=year_options.index(default_year) if default_year in year_options else len(year_options) - 2
    )

    # Load calendar for selected year
    schedule = load_f1_calendar(year)

    if schedule.empty:
        st.error(f"No calendar data available for {year}")
        return session.race_context or RaceContext(
            year=year,
            round_number=1,
            circuit_name="Bahrain International Circuit",
            circuit_key="bahrain",
            country="Bahrain",
            session_type=SessionType.RACE,
            session_date=datetime(year, 3, 1, 15, 0),
            total_laps=57,
            current_lap=1
        )

    # Build circuit options from schedule with shorter names
    circuit_options = {}
    circuit_short_names = {
        'United Arab Emirates': 'Abu Dhabi',
        'United States': 'USA',
        'United Kingdom': 'Britain',
        'Saudi Arabia': 'Saudi',
    }

    for _, event in schedule.iterrows():
        country = event['Country']
        location = event['Location']
        round_num = int(event['RoundNumber'])
        circuit_name = event['OfficialEventName']

        # Use short name for display
        country_short = circuit_short_names.get(country, country)

        # Create compact display names
        if country == 'United States':
            if 'Miami' in location:
                display_name = "Miami"
            elif 'Austin' in location:
                display_name = "USA (Austin)"
            elif 'Las Vegas' in location:
                display_name = "Las Vegas"
            else:
                display_name = country_short
        elif country == 'Italy':
            if 'Imola' in location:
                display_name = "Imola"
            elif 'Monza' in location:
                display_name = "Monza"
            else:
                display_name = country_short
        else:
            display_name = country_short

        circuit_options[display_name] = (round_num, country, location, circuit_name)

    # Find default circuit index
    default_circuit_idx = 0
    for idx, (display_name, (_, country, _, _)) in enumerate(circuit_options.items()):
        if default_circuit.lower() in country.lower() or country.lower() in default_circuit.lower():
            default_circuit_idx = idx
            break

    # Circuit selector
    circuit_display = st.selectbox(
        "**Circuit**",
        options=list(circuit_options.keys()),
        index=default_circuit_idx,
        key=f"circuit_selector_{year}"
    )

    round_number, country, location, circuit_name = circuit_options[circuit_display]
    circuit_key = country.lower().replace(' ', '_')

    # Get available sessions for this race
    available_sessions = get_available_sessions(schedule, round_number)

    # Find default session index
    default_session_idx = len(available_sessions) - 1  # Default to last (usually Race)
    for idx, (_, session_enum) in enumerate(available_sessions):
        if session_enum == default_session_type:
            default_session_idx = idx
            break

    # Session type selector
    session_display = st.selectbox(
        "**Session**",
        options=[name for name, _ in available_sessions],
        index=default_session_idx
    )

    # Get selected session type
    session_type = next(
        (enum_val for name, enum_val in available_sessions if name == session_display),
        SessionType.RACE
    )

    # Driver/Team focus
    st.markdown("**🎯 Focus**")

    # Dynamic driver list based on year
    drivers_by_year = {
        2025: ["VER", "HAM", "LEC", "RUS", "SAI", "NOR", "PIA", "ALO",
               "STR", "GAS", "ALB", "TSU", "OCO", "HUL", "MAG", "BEA",
               "BOT", "ZHO", "COL", "DOO"],
        2024: ["VER", "PER", "HAM", "RUS", "LEC", "SAI", "NOR", "PIA",
               "ALO", "STR", "TSU", "RIC", "GAS", "OCO", "ALB", "SAR",
               "MAG", "HUL", "BOT", "ZHO"],
        2023: ["VER", "PER", "HAM", "RUS", "LEC", "SAI", "NOR", "PIA",
               "ALO", "STR", "GAS", "OCO", "ALB", "SAR", "MAG", "HUL",
               "TSU", "DEV", "BOT", "ZHO"],
    }
    drivers = drivers_by_year.get(year, drivers_by_year[2025])

    # Restore last selected driver if available
    default_driver_idx = 0
    if st.session_state.user_prefs["focused_driver"] in drivers:
        default_driver_idx = drivers.index(
            st.session_state.user_prefs["focused_driver"]
        ) + 1

    focused_driver = st.selectbox(
        "**Driver**",
        options=["None"] + drivers,
        index=default_driver_idx,
        key=f"driver_selector_{year}"
    )

    # Save driver selection to preferences
    if focused_driver != "None":
        st.session_state.user_prefs["focused_driver"] = focused_driver

    # Create race context
    # Get event details for session date and laps
    event = schedule[schedule['RoundNumber'] == round_number].iloc[0]

    # Map session type to session date column
    session_date_col = {
        SessionType.FP1: 'Session1Date',
        SessionType.FP2: 'Session2Date',
        SessionType.FP3: 'Session3Date',
        SessionType.QUALIFYING: 'Session4Date',
        SessionType.SPRINT_QUALIFYING: 'Session4Date',
        SessionType.SPRINT: 'Session5Date',
        SessionType.RACE: 'Session5Date',
    }.get(session_type, 'Session5Date')

    session_date = event.get(session_date_col)
    if isinstance(session_date, str):
        session_date = pd.to_datetime(session_date)
    elif pd.isna(session_date):
        session_date = datetime.now()

    race_context = RaceContext(
        year=year,
        round_number=round_number,
        circuit_name=circuit_name,
        circuit_key=circuit_key,
        country=country,
        session_type=session_type,
        session_date=session_date,
        total_laps=57,  # Default, will be updated from actual data
        current_lap=1,
        focused_driver=focused_driver if focused_driver != "None" else None,
        focused_team=None  # Auto-derived from focused_driver
    )

    return race_context


def render_dashboard_area(
    session: GlobalSession,
    system: Optional[Dict[str, Any]]
) -> None:
    """
    Render the main dashboard area.

    Args:
        session: Global session state
        system: Agent system components (optional)
    """
    # Display session summary
    st.markdown(f"### {session.get_session_summary()}")

    if session.is_simulation():
        st.caption(
            f"⚡ Playback: "
            f"{SimulationControls.get_playback_status(session)}"
        )

    st.divider()

    # Render visible dashboards
    for dashboard_id in session.visible_dashboards:
        if dashboard_id == "ai_assistant":
            # Check if system is available
            if not system:
                st.error(
                    "🤖 **AI Assistant Unavailable**\n\n"
                    "The AI Assistant requires API keys to function. "
                    "Please configure your API keys in the Configuration menu.\n\n"
                    "**Required:**\n"
                    "- `ANTHROPIC_API_KEY` for Claude\n"
                    "- `GOOGLE_API_KEY` for Gemini"
                )
                st.info(
                    "💡 **Tip**: Add these keys to your `.env` file "
                    "in the project root directory."
                )
                continue

            # Create agent context from race context
            if session.race_context:
                context = AgentContext(
                    session_type=session.race_context.session_type.value,
                    year=session.race_context.year,
                    race_name=session.race_context.circuit_name
                )
            else:
                context = AgentContext(
                    session_type="Race",
                    year=2023,
                    race_name="Unknown"
                )

            # Render AI Assistant dashboard
            dashboard = AIAssistantDashboard(
                orchestrator=system["orchestrator"],
                session_manager=system["session_manager"],
                message_handler=system["message_handler"]
            )
            dashboard.render(context)

        elif dashboard_id == "circuit_positions":
            st.info("🏎️ Circuit & Positions dashboard (Coming Soon)")

        elif dashboard_id == "telemetry":
            st.info("📈 Telemetry Comparison dashboard (Coming Soon)")

        elif dashboard_id == "tire_strategy":
            st.info("🔴 Tire Strategy dashboard (Coming Soon)")

        elif dashboard_id == "weather":
            st.info("🌦️ Weather dashboard (Coming Soon)")

        elif dashboard_id == "lap_analysis":
            st.info("⏱️ Lap Analysis dashboard (Coming Soon)")

        elif dashboard_id == "race_control":
            st.info("🚩 Race Control dashboard (Coming Soon)")

        elif dashboard_id == "qualifying":
            st.info("🏁 Qualifying Progress dashboard (Coming Soon)")


def main():
    """Main application entry point."""

    # Page configuration for wide layout
    st.set_page_config(
        page_title="F1 Strategist AI",
        page_icon="🏎️",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Initialize agent system (optional - only needed for AI Assistant)
    system = initialize_agents()

    # Initialize session
    session = initialize_session()

    # Initialize user preferences for persistence
    if "user_prefs" not in st.session_state:
        st.session_state.user_prefs = {
            "focused_driver": None,
            "visible_dashboards": ["ai_assistant"]
        }

    # Check for live session
    live_context = check_live_session()
    if live_context:
        session.mode = SessionMode.LIVE
        session.race_context = live_context

    # ========== SIDEBAR - ALL CONTROLS ==========
    with st.sidebar:
        st.markdown("# 🏎️ F1 Strategist")

        # Live session indicator (compact)
        if live_context:
            circuit_name = live_context.country
            if circuit_name == "United Arab Emirates":
                circuit_name = "Abu Dhabi"
            elif circuit_name == "United Kingdom":
                circuit_name = "Britain"
            st.success(f"🔴 **LIVE**: {circuit_name}")

        # Mode selector
        st.markdown("**🎮 Mode**")
        new_mode = TopMenu.render_mode_selector(session)
        if new_mode != session.mode:
            session.mode = new_mode
            st.rerun()

        # Session context selector (collapsed by default)
        with st.expander("📍 Context", expanded=False):
            new_context = render_session_context_selector(session, live_context)
            session.race_context = new_context

        # Dashboard selector
        st.markdown("**📊 Dashboards**")
        selected_dashboards = TopMenu.render_dashboard_selector(session)
        session.visible_dashboards = selected_dashboards

        # Simulation controls (only in simulation mode)
        if session.is_simulation():
            with st.expander("⏯️ Playback", expanded=False):
                SimulationControls.render(session, controller=None)

        # Upcoming sessions
        if not live_context:
            with st.expander("📅 Upcoming", expanded=False):
                LiveSessionInfo.render_upcoming_sessions(days_ahead=7)

        # Navigation menu
        st.markdown("**⚙️ Menu**")
        menu_selection = st.radio(
            "Navigation",
            ["Dashboards", "Config", "Help"],
            label_visibility="collapsed"
        )

        # Actions
        if st.button("🗑️ Clear History", use_container_width=True):
            if "ai_assistant_messages" in st.session_state:
                st.session_state.ai_assistant_messages = []
            if system and "session_manager" in system:
                system["session_manager"].clear_history()
            st.rerun()

    # ========== MAIN AREA - DASHBOARDS ONLY ==========

    if menu_selection == "Dashboards":
        # Show compact header with session info
        col1, col2, col3 = st.columns([1, 3, 1])
        with col1:
            mode_emoji = "🔴" if session.mode == SessionMode.LIVE else "⏯️"
            st.markdown(f"**{mode_emoji} {session.mode.value}**")
        with col2:
            if session.race_context:
                circuit_short = session.race_context.country
                if circuit_short == "United Arab Emirates":
                    circuit_short = "Abu Dhabi"
                elif circuit_short == "United Kingdom":
                    circuit_short = "Britain"

                st.markdown(
                    f"**{session.race_context.year} · {circuit_short} · "
                    f"{session.race_context.session_type.value}**"
                )
        with col3:
            st.markdown(f"**{len(session.visible_dashboards)} Active**")

        st.markdown("---")

        # Render dashboards (full width, no distractions)
        render_dashboard_area(session, system)

    elif menu_selection == "Config":
        st.markdown("## ⚙️ Configuration")
        if not system:
            st.warning(
                "⚠️ AI Assistant is not available. "
                "Please configure your API keys to enable the AI Assistant."
            )
        TopMenu.render_configuration_panel()
        # TODO: Apply configuration changes

    elif menu_selection == "Help":
        st.markdown("## 📖 Help & Documentation")
        TopMenu.render_help_panel()


if __name__ == "__main__":
    main()
