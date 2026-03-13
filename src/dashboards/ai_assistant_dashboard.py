"""
AI Assistant Dashboard.

Multi-agent conversational interface for F1 strategy queries.
"""

import asyncio
import logging
from datetime import datetime

import streamlit as st

from src.agents.base_agent import AgentContext
from src.agents.orchestrator import AgentOrchestrator
from src.chatbot.chat_interface import ChatInterface
from src.chatbot.message_handler import MessageHandler
from src.chatbot.session_manager import SessionManager

logger = logging.getLogger(__name__)


class AIAssistantDashboard:
    """
    AI Assistant Dashboard with multi-agent chat interface.

    Provides conversational interface to 5 specialized agents:
    - Strategy Agent
    - Weather Agent
    - Performance Agent
    - Race Control Agent
    - Race Position Agent
    """

    def __init__(
        self,
        orchestrator: AgentOrchestrator,
        session_manager: SessionManager,
        message_handler: MessageHandler
    ):
        """
        Initialize AI Assistant Dashboard.

        Args:
            orchestrator: Agent orchestrator
            session_manager: Chat session manager
            message_handler: Message processing handler
        """
        self.orchestrator = orchestrator
        self.session_manager = session_manager
        self.message_handler = message_handler

    def render(self, context: AgentContext) -> None:
        """
        Render the AI Assistant dashboard.

        Args:
            context: Current race context
        """
        # Initialize session state for this dashboard
        if "ai_assistant_messages" not in st.session_state:
            st.session_state.ai_assistant_messages = []
            # Create initial session
            session_id = (
                f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            self.session_manager.create_session(session_id)

        # Display welcome message
        ChatInterface.display_welcome_message()

        # Update context
        self.session_manager.update_context(context)
        self.orchestrator.set_context(context)

        # Display conversation history
        for message in st.session_state.ai_assistant_messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])

                # Display metadata for assistant messages
                if (
                    message["role"] == "assistant"
                    and "metadata" in message
                ):
                    metadata = message["metadata"]
                    with st.expander("🔍 Details", expanded=False):
                        col1, col2, col3 = st.columns(3)

                        with col1:
                            if "confidence" in metadata:
                                st.metric(
                                    "Confidence",
                                    f"{metadata['confidence']:.0%}"
                                )

                        with col2:
                            if "processing_time" in metadata:
                                st.metric(
                                    "Time",
                                    f"{metadata['processing_time']:.2f}s"
                                )

                        with col3:
                            if "agents_used" in metadata:
                                st.metric(
                                    "Agents",
                                    len(metadata["agents_used"])
                                )

                        if "agents_used" in metadata:
                            st.caption(
                                f"**Agents**: "
                                f"{', '.join(metadata['agents_used'])}"
                            )

        # Chat input
        if prompt := st.chat_input("Ask a strategy question..."):
            # Add user message to display
            st.session_state.ai_assistant_messages.append({
                "role": "user",
                "content": prompt
            })

            # Display user message
            with st.chat_message("user"):
                st.write(prompt)

            # Display assistant response with spinner
            with st.chat_message("assistant"):
                with st.spinner("Analyzing..."):
                    try:
                        # Process message asynchronously
                        response = asyncio.run(
                            self.message_handler.process_message(
                                prompt,
                                context
                            )
                        )

                        # Display response
                        st.write(response["response"])

                        # Display metadata
                        with st.expander("🔍 Details", expanded=False):
                            col1, col2, col3 = st.columns(3)

                            with col1:
                                st.metric(
                                    "Confidence",
                                    f"{response['confidence']:.0%}"
                                )

                            with col2:
                                st.metric(
                                    "Time",
                                    f"{response['processing_time']:.2f}s"
                                )

                            with col3:
                                st.metric(
                                    "Agents",
                                    len(response["agents_used"])
                                )

                            st.caption(
                                f"**Agents**: "
                                f"{', '.join(response['agents_used'])}"
                            )

                        # Add to session state
                        st.session_state.ai_assistant_messages.append({
                            "role": "assistant",
                            "content": response["response"],
                            "metadata": {
                                "confidence": response["confidence"],
                                "processing_time": (
                                    response["processing_time"]
                                ),
                                "agents_used": response["agents_used"]
                            }
                        })

                    except Exception as e:
                        error_msg = f"Error: {str(e)}"
                        st.error(error_msg)
                        logger.error(f"Error processing message: {e}")

                        # Add error to session state
                        st.session_state.ai_assistant_messages.append({
                            "role": "assistant",
                            "content": error_msg,
                            "metadata": {"error": True}
                        })

    def clear_history(self) -> None:
        """Clear conversation history."""
        st.session_state.ai_assistant_messages = []
        self.session_manager.clear_history()
        logger.info("AI Assistant history cleared")
