"""
Session Manager - Chat Session State Management

Manages conversation history, session context, and state persistence
for the Streamlit chat interface.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import logging

from src.agents.base_agent import AgentContext

logger = logging.getLogger(__name__)


@dataclass
class ChatMessage:
    """Represents a single chat message."""

    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatSession:
    """Represents a complete chat session."""

    session_id: str
    messages: List[ChatMessage] = field(default_factory=list)
    context: Optional[AgentContext] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class SessionManager:
    """
    Manages chat sessions and conversation history.

    Handles session creation, message storage, context management,
    and state persistence for the chat interface.
    """

    def __init__(self):
        """Initialize the session manager."""
        self.current_session: Optional[ChatSession] = None
        self._sessions: Dict[str, ChatSession] = {}
        logger.info("SessionManager initialized")

    def create_session(
        self,
        session_id: str,
        context: Optional[AgentContext] = None
    ) -> ChatSession:
        """
        Create a new chat session.

        Args:
            session_id: Unique identifier for the session
            context: Optional agent context (race, year, etc.)

        Returns:
            Created ChatSession
        """
        session = ChatSession(
            session_id=session_id,
            context=context
        )
        self._sessions[session_id] = session
        self.current_session = session

        logger.info(f"Created new session: {session_id}")
        return session

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """
        Get a session by ID.

        Args:
            session_id: Session identifier

        Returns:
            ChatSession or None if not found
        """
        return self._sessions.get(session_id)

    def add_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add a message to the current session.

        Args:
            role: Message role ('user' or 'assistant')
            content: Message content
            metadata: Optional message metadata
        """
        if not self.current_session:
            raise ValueError("No active session. Call create_session() first.")

        message = ChatMessage(
            role=role,
            content=content,
            metadata=metadata or {}
        )

        self.current_session.messages.append(message)
        self.current_session.last_updated = datetime.now()

        logger.debug(
            f"Added {role} message to session {
                self.current_session.session_id}")

    def get_conversation_history(
        self,
        limit: Optional[int] = None
    ) -> List[ChatMessage]:
        """
        Get conversation history from current session.

        Args:
            limit: Maximum number of messages to return (most recent)

        Returns:
            List of ChatMessage objects
        """
        if not self.current_session:
            return []

        messages = self.current_session.messages
        if limit:
            messages = messages[-limit:]

        return messages

    def update_context(self, context: AgentContext) -> None:
        """
        Update the agent context for the current session.

        Args:
            context: New agent context
        """
        if not self.current_session:
            raise ValueError("No active session")

        self.current_session.context = context
        logger.info(
            f"Updated context: {context.year} {context.race_name} "
            f"({context.session_type})"
        )

    def clear_history(self) -> None:
        """Clear conversation history from current session."""
        if self.current_session:
            self.current_session.messages = []
            logger.info(
                f"Cleared history for session {
                    self.current_session.session_id}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get session statistics.

        Returns:
            Dictionary with session stats
        """
        if not self.current_session:
            return {
                "active_session": False,
                "total_messages": 0,
                "user_messages": 0,
                "assistant_messages": 0
            }

        messages = self.current_session.messages
        return {
            "active_session": True,
            "session_id": self.current_session.session_id,
            "total_messages": len(messages),
            "user_messages": sum(
                1 for m in messages if m.role == "user"),
            "assistant_messages": sum(
                1 for m in messages if m.role == "assistant"),
            "session_duration": (
                datetime.now() -
                self.current_session.created_at).total_seconds(),
            "last_updated": self.current_session.last_updated}
