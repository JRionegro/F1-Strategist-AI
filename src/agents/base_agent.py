"""
Base Agent - Abstract Foundation for F1 Strategy Agents

This module provides the abstract base class for all specialized agents
in the F1 Strategist AI system. It defines the common interface, LLM
integration, tool management, and state handling.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
import logging

from src.llm.provider import LLMProvider


logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Configuration for an agent instance."""

    name: str
    description: str
    llm_provider: LLMProvider
    temperature: float = 0.7
    max_tokens: int = 2000
    enable_rag: bool = True
    enable_tools: bool = True
    rag_system: Optional[Any] = None  # VectorStore instance
    mcp_client: Optional[Any] = None  # MCP client for tool access


@dataclass
class AgentContext:
    """Context information for agent execution."""

    session_type: str  # 'race', 'qualifying', 'sprint', 'practice'
    year: int
    race_name: str
    additional_context: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Initialize additional_context if None."""
        if self.additional_context is None:
            self.additional_context = {}


@dataclass
class AgentResponse:
    """Standardized response from an agent."""

    agent_name: str
    query: str
    response: str
    confidence: float  # 0.0 to 1.0
    sources: List[str]  # RAG sources or tool calls used
    reasoning: str  # Explanation of the decision
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Initialize metadata if None."""
        if self.metadata is None:
            self.metadata = {}


class BaseAgent(ABC):
    """
    Abstract base class for all F1 strategy agents.

    This class provides the common interface and functionality that all
    specialized agents must implement. It handles LLM integration, tool
    management, state handling, and error recovery.

    Attributes:
        config: Agent configuration
        context: Current execution context
        _tools: Available tools for this agent
        _conversation_history: Recent conversation for context
    """

    def __init__(self, config: AgentConfig):
        """
        Initialize the base agent.

        Args:
            config: Agent configuration object
        """
        self.config = config
        self.context: Optional[AgentContext] = None
        self._tools: Dict[str, Callable] = {}
        self._conversation_history: List[Dict[str, str]] = []
        self.rag_system = config.rag_system
        self.mcp_client = config.mcp_client

        # Auto-register MCP tools if client is available
        if self.mcp_client and self.config.enable_tools:
            self._register_mcp_tools()

        logger.info(f"Initialized agent: {self.config.name}")

    def _register_mcp_tools(self) -> None:
        """
        Register MCP tools from the client.

        Automatically registers all tools specified in get_available_tools()
        by creating wrapper functions that call the MCP client methods.
        """
        if not self.mcp_client:
            return

        available_tools = self.get_available_tools()

        for tool_name in available_tools:
            # Create a wrapper function that calls the MCP client
            if hasattr(self.mcp_client, tool_name):
                tool_method = getattr(self.mcp_client, tool_name)
                self.register_tool(tool_name, tool_method)
                logger.debug(
                    f"Registered MCP tool '{tool_name}' for {self.config.name}"
                )
            else:
                logger.warning(
                    f"MCP tool '{tool_name}' not found in client "
                    f"for {self.config.name}"
                )

    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Get the system prompt for this agent.

        This defines the agent's role, capabilities, and behavior.
        Must be implemented by each specialized agent.

        Returns:
            System prompt string
        """
        pass

    @abstractmethod
    def get_available_tools(self) -> List[str]:
        """
        Get the list of MCP tools this agent can use.

        Returns:
            List of tool names (e.g., ['get_race_results', 'get_lap_times'])
        """
        pass

    @abstractmethod
    def validate_query(self, query: str) -> bool:
        """
        Validate if this agent can handle the given query.

        Args:
            query: User query string

        Returns:
            True if agent can handle this query, False otherwise
        """
        pass

    def set_context(self, context: AgentContext) -> None:
        """
        Set the execution context for this agent.

        Args:
            context: Agent context with session info
        """
        self.context = context
        logger.debug(
            f"{self.config.name} context set: "
            f"{context.session_type} - {context.year} {context.race_name}"
        )

    def register_tool(self, tool_name: str, tool_func: Callable) -> None:
        """
        Register a tool function for this agent.

        Args:
            tool_name: Name of the tool (matches MCP tool name)
            tool_func: Callable function that executes the tool
        """
        self._tools[tool_name] = tool_func
        logger.debug(f"Registered tool '{tool_name}' for {self.config.name}")

    def call_tool(self, tool_name: str, **kwargs) -> Any:
        """
        Execute a registered tool.

        Args:
            tool_name: Name of the tool to execute
            **kwargs: Tool-specific parameters

        Returns:
            Tool execution result

        Raises:
            ValueError: If tool is not registered or not available
        """
        if tool_name not in self._tools:
            raise ValueError(
                f"Tool '{tool_name}' not registered for {self.config.name}"
            )

        if not self.config.enable_tools:
            raise ValueError(f"Tools disabled for {self.config.name}")

        logger.debug(f"Calling tool '{tool_name}' with params: {kwargs}")

        try:
            result = self._tools[tool_name](**kwargs)
            logger.debug(f"Tool '{tool_name}' executed successfully")
            return result
        except Exception as e:
            logger.error(f"Tool '{tool_name}' failed: {str(e)}")
            raise

    async def _call_relevant_tools(self, query: str) -> Dict[str, Any]:
        """
        Identify and call relevant MCP tools based on query keywords.

        Args:
            query: User query to analyze

        Returns:
            Dictionary mapping tool names to their results
        """
        tool_results = {}
        query_lower = query.lower()

        # Tool keyword mappings
        tool_keywords = {
            "get_pit_stops": ["pit stop", "pit", "stops", "pitstop"],
            "get_lap_times": ["lap time", "pace", "degrading", "speed"],
            "get_weather": ["weather", "rain", "temperature", "conditions"],
            "get_telemetry": ["telemetry", "data", "sensor"],
            "get_race_results": ["result", "finish", "position", "standing"],
            "get_qualifying_results": ["qualifying", "quali", "q1", "q2", "q3"],
            "get_session_info": ["session", "info"],
            "get_track_status": ["track status", "flag", "safety car", "vsc"]
        }

        # Check which tools match query keywords
        for tool_name, keywords in tool_keywords.items():
            if tool_name in self._tools:
                # Check if any keyword matches
                if any(keyword in query_lower for keyword in keywords):
                    try:
                        logger.debug(
                            f"Calling tool '{tool_name}' based on query keywords")
                        # Call tool - most tools need year, race, session
                        # context
                        tool_params = {}
                        if self.context:
                            if hasattr(self.context, 'year'):
                                tool_params['year'] = self.context.year
                            if hasattr(self.context, 'race_name'):
                                tool_params['race_name'] = self.context.race_name
                            if hasattr(self.context, 'session_type'):
                                tool_params['session'] = self.context.session_type

                        # Call the tool (might be async)
                        result = self._tools[tool_name](**tool_params)

                        # Handle async results
                        import inspect
                        if inspect.iscoroutine(result):
                            result = await result

                        tool_results[tool_name] = result
                        logger.debug(
                            f"Tool '{tool_name}' executed successfully"
                        )
                    except Exception as e:
                        logger.warning(
                            f"Tool '{tool_name}' call failed: {str(e)}"
                        )
                        # Continue with other tools even if one fails
                        continue

        return tool_results

    async def query(
        self,
        user_query: str,
        context: Optional[AgentContext] = None
    ) -> AgentResponse:
        """
        Process a user query and return a response.

        This is the main entry point for agent interaction. It validates
        the query, sets context, calls the LLM, and returns a structured
        response.

        Args:
            user_query: User's question or request
            context: Optional execution context (uses self.context if None)

        Returns:
            AgentResponse with answer and metadata

        Raises:
            ValueError: If query is invalid for this agent
        """
        # Validate query
        if not self.validate_query(user_query):
            raise ValueError(
                f"Query not suitable for {self.config.name}: {user_query}"
            )

        # Set context if provided
        if context is not None:
            self.set_context(context)

        # Ensure context is set
        if self.context is None:
            raise ValueError("Context must be set before querying agent")

        logger.info(f"{self.config.name} processing query: {user_query}")

        # Call relevant MCP tools if enabled
        tool_results = {}
        if self.config.enable_tools and self.mcp_client:
            tool_results = await self._call_relevant_tools(user_query)

        # Retrieve relevant context from RAG if enabled
        rag_sources = []
        if self.config.enable_rag and self.rag_system:
            rag_sources = await self._retrieve_rag_context(user_query)

        # Build the prompt
        system_prompt = self.get_system_prompt()
        full_prompt = self._build_full_prompt(
            user_query,
            rag_sources,
            tool_results
        )

        # Call LLM
        try:
            llm_response = await self._call_llm(system_prompt, full_prompt)

            # Build response
            response = self._build_response(
                user_query,
                llm_response,
                sources=[s['metadata'].get('source', 'RAG')
                         for s in rag_sources],
                reasoning=""  # TODO: Extract from LLM response
            )

            # Update conversation history
            self._add_to_history(user_query, response.response)

            logger.info(
                f"{self.config.name} completed query "
                f"(confidence: {response.confidence:.2f})"
            )

            return response

        except Exception as e:
            logger.error(f"{self.config.name} query failed: {str(e)}")
            raise

    def _build_full_prompt(
        self,
        user_query: str,
        rag_sources: Optional[List[Dict[str, Any]]] = None,
        tool_results: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build the full prompt including context, RAG, tools, and history.

        Args:
            user_query: User's query
            rag_sources: Retrieved RAG documents
            tool_results: Results from MCP tool calls

        Returns:
            Complete prompt string
        """
        prompt_parts = []

        # Add context information
        if self.context:
            prompt_parts.append(f"Session Type: {self.context.session_type}")
            prompt_parts.append(
                f"Race: {
                    self.context.year} {
                    self.context.race_name}")

            if self.context.additional_context:
                prompt_parts.append(
                    f"Additional Context: {self.context.additional_context}"
                )

        # Add tool results if available
        if tool_results:
            prompt_parts.append("\nReal-time Data from MCP Tools:")
            for tool_name, result in tool_results.items():
                prompt_parts.append(f"\n{tool_name}:")
                prompt_parts.append(f"{result}")

        # Add RAG retrieved context
        if rag_sources:
            prompt_parts.append("\nRelevant Historical Context:")
            for i, doc in enumerate(rag_sources[:3], 1):  # Top 3 results
                prompt_parts.append(f"{i}. {doc['content']}")

        # Add conversation history (last 3 exchanges)
        if self._conversation_history:
            prompt_parts.append("\nRecent Conversation:")
            for exchange in self._conversation_history[-3:]:
                prompt_parts.append(f"User: {exchange['user']}")
                prompt_parts.append(f"Assistant: {exchange['assistant']}")

        # Add current query
        prompt_parts.append(f"\nCurrent Query: {user_query}")

        return "\n".join(prompt_parts)

    async def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """
        Call the LLM provider with prompts.

        Args:
            system_prompt: System instructions
            user_prompt: User message

        Returns:
            LLM response text
        """
        response = await self.config.llm_provider.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens
        )
        return response.content

    def _build_response(
        self,
        query: str,
        llm_response: str,
        sources: List[str],
        reasoning: str
    ) -> AgentResponse:
        """
        Build a structured AgentResponse.

        Args:
            query: Original user query
            llm_response: Response from LLM
            sources: List of sources used
            reasoning: Reasoning explanation

        Returns:
            Structured AgentResponse
        """
        # TODO: Implement confidence scoring based on response quality
        confidence = 0.8

        return AgentResponse(
            agent_name=self.config.name,
            query=query,
            response=llm_response,
            confidence=confidence,
            sources=sources,
            reasoning=reasoning,
            metadata={
                "session_type": self.context.session_type if self.context else None,
                "year": self.context.year if self.context else None,
                "race_name": self.context.race_name if self.context else None})

    def _add_to_history(
            self,
            user_query: str,
            assistant_response: str) -> None:
        """
        Add exchange to conversation history.

        Args:
            user_query: User's query
            assistant_response: Agent's response
        """
        self._conversation_history.append({
            "user": user_query,
            "assistant": assistant_response
        })

        # Keep only last 10 exchanges
        if len(self._conversation_history) > 10:
            self._conversation_history = self._conversation_history[-10:]

    def clear_history(self) -> None:
        """Clear conversation history."""
        self._conversation_history.clear()

    async def _retrieve_rag_context(
        self,
        query: str,
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant context from RAG system.

        Args:
            query: User query for retrieval
            k: Number of documents to retrieve

        Returns:
            List of retrieved documents with content and metadata
        """
        if not self.rag_system:
            return []

        try:
            # Build metadata filters based on context
            filters = {}
            if self.context:
                filters["year"] = self.context.year
                filters["session_type"] = self.context.session_type

            # Retrieve from vector store
            results = self.rag_system.search(
                query=query,
                k=k,
                filter_metadata=filters if filters else None
            )

            # Convert SearchResult objects to dicts
            rag_docs = []
            for result in results:
                rag_docs.append({
                    "content": result.content,
                    "metadata": result.metadata,
                    "score": result.score,
                    "id": result.id
                })

            logger.debug(
                f"{self.config.name} retrieved {len(rag_docs)} RAG documents "
                f"(scores: {[d['score'] for d in rag_docs[:3]]})"
            )

            return rag_docs

        except Exception as e:
            logger.warning(f"RAG retrieval failed: {e}")
            return []
        logger.debug(f"Cleared conversation history for {self.config.name}")

    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get agent capabilities summary.

        Returns:
            Dictionary with agent capabilities
        """
        return {
            "name": self.config.name,
            "description": self.config.description,
            "tools": self.get_available_tools(),
            "rag_enabled": self.config.enable_rag,
            "tools_enabled": self.config.enable_tools,
            "session_types": ["race", "qualifying", "sprint", "practice"]
        }
