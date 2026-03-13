"""
Chat Interface - Streamlit UI Components

Provides reusable Streamlit components for the chat interface.
"""

from typing import List, Dict, Any, Optional
import streamlit as st

from src.chatbot.session_manager import ChatMessage


class ChatInterface:
    """
    Streamlit chat interface components.

    Provides reusable UI components for displaying chat messages,
    agent information, and session statistics.
    """

    @staticmethod
    def display_message(message: ChatMessage) -> None:
        """
        Display a single chat message.

        Args:
            message: ChatMessage to display
        """
        with st.chat_message(message.role):
            st.write(message.content)

            # Display metadata for assistant messages
            if message.role == "assistant" and message.metadata:
                ChatInterface._display_message_metadata(message.metadata)

    @staticmethod
    def _display_message_metadata(metadata: Dict[str, Any]) -> None:
        """Display message metadata in an expander."""
        if not metadata:
            return

        with st.expander("🔍 Details", expanded=False):
            col1, col2, col3 = st.columns(3)

            with col1:
                if "confidence" in metadata:
                    confidence = metadata["confidence"]
                    st.metric(
                        "Confidence",
                        f"{confidence:.0%}",
                        delta=None
                    )

            with col2:
                if "processing_time" in metadata:
                    time = metadata["processing_time"]
                    st.metric(
                        "Response Time",
                        f"{time:.2f}s",
                        delta=None
                    )

            with col3:
                if "agents_used" in metadata:
                    agents = metadata["agents_used"]
                    st.metric(
                        "Agents Used",
                        len(agents),
                        delta=None
                    )

            if "agents_used" in metadata:
                st.caption(f"**Agents**: {', '.join(metadata['agents_used'])}")

    @staticmethod
    def display_conversation(messages: List[ChatMessage]) -> None:
        """
        Display a list of chat messages.

        Args:
            messages: List of ChatMessage objects
        """
        for message in messages:
            ChatInterface.display_message(message)

    @staticmethod
    def display_agent_status(agents_status: Dict[str, bool]) -> None:
        """
        Display agent availability status.

        Args:
            agents_status: Dictionary mapping agent names to availability
        """
        st.sidebar.subheader("🤖 Agent Status")

        for agent_name, available in agents_status.items():
            status_icon = "✅" if available else "❌"
            st.sidebar.text(f"{status_icon} {agent_name.title()}")

    @staticmethod
    def display_context_info(context: Optional[Any]) -> None:
        """
        Display current session context.

        Args:
            context: AgentContext or None
        """
        if not context:
            st.sidebar.info("No race context set")
            return

        st.sidebar.subheader("📍 Race Context")
        st.sidebar.text(f"**Year**: {context.year}")
        st.sidebar.text(f"**Race**: {context.race_name}")
        st.sidebar.text(f"**Session**: {context.session_type}")

        if context.additional_context:
            with st.sidebar.expander("Additional Info"):
                for key, value in context.additional_context.items():
                    st.text(f"{key}: {value}")

    @staticmethod
    def display_session_stats(stats: Dict[str, Any]) -> None:
        """
        Display session statistics.

        Args:
            stats: Session statistics dictionary
        """
        if not stats.get("active_session"):
            return

        st.sidebar.divider()
        st.sidebar.caption("**Session Stats**")
        st.sidebar.caption(f"Messages: {stats['total_messages']}")
        st.sidebar.caption(
            f"Duration: {stats.get('session_duration', 0):.0f}s"
        )

    @staticmethod
    def create_context_selector() -> Dict[str, Any]:
        """
        Create UI for selecting race context.

        Returns:
            Dictionary with selected context values
        """
        st.sidebar.subheader("⚙️ Race Context")

        year = st.sidebar.selectbox(
            "Year",
            options=[2024, 2023, 2022, 2021, 2020],
            index=1  # Default 2023
        )

        race_name = st.sidebar.text_input(
            "Race Name",
            value="Bahrain Grand Prix"
        )

        session_type = st.sidebar.selectbox(
            "Session Type",
            options=["race", "qualifying", "sprint", "practice"],
            index=0
        )

        return {
            "year": year,
            "race_name": race_name,
            "session_type": session_type
        }

    @staticmethod
    def display_welcome_message() -> None:
        """Display welcome message and instructions."""
        st.title("🏎️ F1 Strategist AI")
        st.caption("Multi-Agent Strategy Assistant")

        with st.expander("ℹ️ How to use", expanded=False):
            st.markdown("""
            **Welcome to F1 Strategist AI!**

            This AI assistant uses multiple specialized agents to answer
            your F1 strategy questions:

            - 🎯 **Strategy Agent**: Tire strategy, pit stops, race planning
            - 🌦️ **Weather Agent**: Weather impact, rain strategies
            - ⚡ **Performance Agent**: Lap times, pace analysis, telemetry
            - 🚩 **Race Control Agent**: Flags, penalties, safety cars
            - 📊 **Position Agent**: Gaps, overtaking, track position

            **Example Questions**:
            - "What's the optimal pit strategy for Verstappen at Bahrain?"
            - "How will rain affect tire choices?"
            - "Is Hamilton's pace degrading?"
            - "What was the impact of the safety car?"

            Set your race context in the sidebar, then start asking questions!
            """)
