"""
Message Handler - Agent Integration Layer

Handles message processing, orchestrator integration, and response formatting
for the chat interface.
"""

from typing import Dict, Any, Optional
import logging
from datetime import datetime

from src.agents.orchestrator import AgentOrchestrator, OrchestratedResponse
from src.agents.base_agent import AgentContext
from src.chatbot.session_manager import SessionManager

logger = logging.getLogger(__name__)


class MessageHandler:
    """
    Handles message processing and agent integration.

    Coordinates between the chat interface, session manager,
    and the multi-agent orchestrator.
    """

    def __init__(
        self,
        orchestrator: AgentOrchestrator,
        session_manager: SessionManager
    ):
        """
        Initialize the message handler.

        Args:
            orchestrator: Agent orchestrator instance
            session_manager: Session manager instance
        """
        self.orchestrator = orchestrator
        self.session_manager = session_manager
        logger.info("MessageHandler initialized")

    async def process_message(
        self,
        user_message: str,
        context: Optional[AgentContext] = None
    ) -> Dict[str, Any]:
        """
        Process a user message and get agent response.

        Args:
            user_message: User's query
            context: Optional agent context

        Returns:
            Dictionary with response and metadata
        """
        start_time = datetime.now()

        # Add user message to session
        self.session_manager.add_message(
            role="user",
            content=user_message
        )

        logger.info(f"Processing message: {user_message[:50]}...")

        try:
            # Set context if provided
            if context:
                self.orchestrator.set_context(context)

            # Query the orchestrator
            response: OrchestratedResponse = await self.orchestrator.query(
                query=user_message,
                context=context
            )

            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()

            # Format response
            formatted_response = self._format_response(
                response, processing_time)

            # Add assistant message to session
            self.session_manager.add_message(
                role="assistant",
                content=response.primary_response,
                metadata={
                    "agents_used": response.agents_used,
                    "confidence": response.confidence,
                    "processing_time": processing_time
                }
            )

            logger.info(
                f"Message processed successfully in {processing_time:.2f}s "
                f"(agents: {', '.join(response.agents_used)})"
            )

            return formatted_response

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")

            error_response = {
                "response": f"Sorry, I encountered an error: {
                    str(e)}",
                "error": True,
                "agents_used": [],
                "confidence": 0.0,
                "processing_time": (
                    datetime.now() -
                    start_time).total_seconds()}

            # Add error message to session
            self.session_manager.add_message(
                role="assistant",
                content=error_response["response"],
                metadata={"error": True}
            )

            return error_response

    def _format_response(
        self,
        response: OrchestratedResponse,
        processing_time: float
    ) -> Dict[str, Any]:
        """
        Format orchestrator response for UI display.

        Args:
            response: Orchestrator response
            processing_time: Time taken to process (seconds)

        Returns:
            Formatted response dictionary
        """
        return {
            "response": response.primary_response,
            "agents_used": response.agents_used,
            "confidence": response.confidence,
            "processing_time": processing_time,
            "supporting_responses": [
                {
                    "agent": resp.agent_name,
                    "response": resp.response,
                    "confidence": resp.confidence
                }
                for resp in response.supporting_responses
            ],
            "metadata": response.metadata,
            "context": {
                "session_type": response.context.session_type if response.context else None,
                "race": response.context.race_name if response.context else None,
                "year": response.context.year if response.context else None
            }
        }

    def get_conversation_summary(self) -> str:
        """
        Get a summary of the current conversation.

        Returns:
            Text summary of conversation
        """
        stats = self.session_manager.get_stats()

        if not stats["active_session"]:
            return "No active conversation"

        return (
            f"Session Duration: {stats['session_duration']:.0f}s | "
            f"Messages: {stats['total_messages']} "
            f"({stats['user_messages']} user, {stats['assistant_messages']} assistant)"
        )
