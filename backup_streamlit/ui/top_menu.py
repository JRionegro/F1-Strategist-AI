"""
Top menu component for F1 Strategist AI.

Provides mode selection, configuration, and dashboard controls.
"""

import logging
from typing import Any, Dict, List, Optional

import streamlit as st
from streamlit_option_menu import option_menu

from src.session.global_session import GlobalSession, SessionMode, SessionType

logger = logging.getLogger(__name__)


class TopMenu:
    """
    Top navigation menu for the application.
    
    Provides:
    - Mode selector (Live/Simulation)
    - Configuration access
    - Dashboard visibility controls
    - Help/About
    """

    DASHBOARD_OPTIONS = {
        "ai_assistant": {
            "name": "AI Assistant",
            "icon": "🤖",
            "description": "Multi-agent chat interface"
        },
        "circuit_positions": {
            "name": "Circuit & Positions",
            "icon": "🏎️",
            "description": "Live track positions"
        },
        "telemetry": {
            "name": "Telemetry",
            "icon": "📈",
            "description": "Multi-driver telemetry"
        },
        "tire_strategy": {
            "name": "Tire Strategy",
            "icon": "🔴",
            "description": "Pit stop analysis"
        },
        "weather": {
            "name": "Weather",
            "icon": "🌦️",
            "description": "Meteorological conditions"
        },
        "lap_analysis": {
            "name": "Lap Analysis",
            "icon": "⏱️",
            "description": "Lap time heatmaps"
        },
        "race_control": {
            "name": "Race Control",
            "icon": "🚩",
            "description": "Flags and incidents"
        },
        "qualifying": {
            "name": "Qualifying",
            "icon": "🏁",
            "description": "Cutoff time tracking"
        }
    }

    @staticmethod
    def render_mode_selector(session: GlobalSession) -> SessionMode:
        """
        Render the Live/Simulation mode selector.
        
        Args:
            session: Global session state
        
        Returns:
            Selected mode
        """
        mode = st.radio(
            "Mode",
            options=[SessionMode.LIVE, SessionMode.SIMULATION],
            format_func=lambda x: (
                "🔴 Live" if x == SessionMode.LIVE
                else "⏯️ Sim"
            ),
            index=0 if session.mode == SessionMode.LIVE else 1,
            horizontal=True,
            label_visibility="collapsed"
        )
        
        return mode
    
    @staticmethod
    def render_main_menu() -> str:
        """
        Render main horizontal menu.
        
        Returns:
            Selected menu item
        """
        selected = option_menu(
            menu_title=None,
            options=["Dashboards", "Configuration", "Help"],
            icons=["grid-3x3-gap", "gear", "question-circle"],
            menu_icon="cast",
            default_index=0,
            orientation="horizontal",
            styles={
                "container": {
                    "padding": "0!important",
                    "background-color": "#0D0D0D"
                },
                "icon": {"color": "#E10600", "font-size": "18px"},
                "nav-link": {
                    "font-size": "14px",
                    "text-align": "center",
                    "margin": "0px",
                    "--hover-color": "#2E2E2E"
                },
                "nav-link-selected": {"background-color": "#E10600"}
            }
        )
        
        return selected
    
    @staticmethod
    def render_dashboard_selector(
        session: GlobalSession
    ) -> List[str]:
        """
        Render dashboard visibility selector.
        
        Args:
            session: Global session state
        
        Returns:
            List of selected dashboard IDs
        """
        selected_dashboards = []
        
        # Get saved dashboard preferences
        if "user_prefs" in st.session_state:
            default_visible = st.session_state.user_prefs.get(
                "visible_dashboards",
                ["ai_assistant"]
            )
        else:
            default_visible = ["ai_assistant"]
        
        # Single column layout for dashboard checkboxes
        for dash_id, dash_info in TopMenu.DASHBOARD_OPTIONS.items():
            is_selected = st.checkbox(
                f"{dash_info['icon']} {dash_info['name']}",
                value=dash_id in default_visible,
                key=f"dash_{dash_id}",
                help=dash_info["description"]
            )
            
            if is_selected:
                selected_dashboards.append(dash_id)
        
        # Save dashboard preferences
        if "user_prefs" in st.session_state:
            st.session_state.user_prefs["visible_dashboards"] = (
                selected_dashboards
            )
        
        return selected_dashboards
    
    @staticmethod
    def render_configuration_panel() -> Dict[str, Any]:
        """
        Render configuration panel.
        
        Returns:
            Configuration values
        """
        st.subheader("⚙️ Configuration")
        
        # API Keys section
        with st.expander("🔑 API Keys", expanded=False):
            st.info(
                "API keys are loaded from .env file. "
                "Edit .env to update keys."
            )
            
            claude_key = st.text_input(
                "Anthropic Claude API Key",
                value="••••••••",
                type="password",
                disabled=True
            )
            
            gemini_key = st.text_input(
                "Google Gemini API Key",
                value="••••••••",
                type="password",
                disabled=True
            )
        
        # LLM Settings
        with st.expander("🤖 LLM Settings", expanded=False):
            provider = st.selectbox(
                "Provider",
                options=["Hybrid (Auto)", "Claude Only", "Gemini Only"],
                index=0
            )
            
            temperature = st.slider(
                "Temperature",
                min_value=0.0,
                max_value=1.0,
                value=0.7,
                step=0.1,
                help="Higher = more creative, Lower = more deterministic"
            )
            
            max_tokens = st.number_input(
                "Max Tokens",
                min_value=1024,
                max_value=8192,
                value=4096,
                step=512
            )
        
        # Data Sources
        with st.expander("📂 Data Sources", expanded=False):
            cache_dir = st.text_input(
                "FastF1 Cache Directory",
                value="./cache",
                help="Directory for FastF1 cached data"
            )
            
            vector_store = st.selectbox(
                "Vector Store",
                options=["ChromaDB", "Pinecone"],
                index=0
            )
        
        return {
            "provider": provider,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "cache_dir": cache_dir,
            "vector_store": vector_store
        }
    
    @staticmethod
    def render_help_panel() -> None:
        """Render help/about panel."""
        st.subheader("❓ Help & About")
        
        # Quick Start Guide
        with st.expander("🚀 Quick Start", expanded=True):
            st.markdown("""
            ### Getting Started
            
            1. **Select Mode**: Choose Live (real-time) or Simulation
            2. **Set Context**: Select year, race, and session
            3. **Choose Dashboards**: Pick which dashboards to display
            4. **Start Analyzing**: Use AI Assistant or explore data
            
            ### Keyboard Shortcuts
            
            - `Ctrl + K`: Focus chat input
            - `Ctrl + L`: Clear chat history
            - `Ctrl + D`: Toggle dashboard selector
            """)
        
        # Agent Descriptions
        with st.expander("🤖 AI Agents", expanded=False):
            st.markdown("""
            ### Available Agents
            
            - **Strategy Agent**: Race and qualifying strategy optimization
            - **Weather Agent**: Meteorological impact analysis
            - **Performance Agent**: Lap times and telemetry analysis
            - **Race Control Agent**: Track status and incident monitoring
            - **Race Position Agent**: Gap analysis and track position
            
            Agents collaborate automatically to answer your questions.
            """)
        
        # About
        with st.expander("ℹ️ About", expanded=False):
            st.markdown("""
            ### F1 Strategist AI
            
            **Version**: 1.0.0  
            **Status**: MVP Development
            
            Multi-agent F1 strategy assistant with real-time analysis
            and historical simulation capabilities.
            
            **Technologies**:
            - Streamlit (UI)
            - Claude & Gemini (LLM)
            - FastF1 (Data)
            - ChromaDB (RAG)
            - MCP (Tool Integration)
            
            **Documentation**: See `docs/` folder
            """)
