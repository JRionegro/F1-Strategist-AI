"""
Agent Orchestrator - Multi-Agent Coordination for F1 Strategy

This orchestrator coordinates multiple specialized agents to handle complex
queries that may require expertise from multiple domains (strategy, weather,
performance, race control, position).
"""

from typing import List, Dict, Optional, Any
import logging
from dataclasses import dataclass, field

from src.agents.base_agent import BaseAgent, AgentContext, AgentResponse

logger = logging.getLogger(__name__)


@dataclass(kw_only=False)
class OrchestratedResponse:
    """
    Response from orchestrator containing multiple agent responses.

    Attributes:
        query: Original user query
        primary_response: Main response from primary agent
        supporting_responses: Additional responses from supporting agents
        agents_used: List of agent names that contributed
        confidence: Overall confidence score (0.0 to 1.0)
        context: Session context used
        metadata: Additional orchestration metadata
    """
    query: str
    primary_response: str
    supporting_responses: List[AgentResponse] = field(default_factory=list)
    agents_used: List[str] = field(default_factory=list)
    confidence: float = 0.0
    context: Optional[AgentContext] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentOrchestrator:
    """
    Orchestrator for coordinating multiple specialized F1 strategy agents.

    The orchestrator:
    - Routes queries to appropriate agent(s)
    - Handles multi-agent coordination
    - Aggregates responses intelligently
    - Resolves conflicts between agents
    - Manages priorities
    """

    def __init__(
        self,
        strategy_agent: BaseAgent,
        weather_agent: BaseAgent,
        performance_agent: BaseAgent,
        race_control_agent: BaseAgent,
        race_position_agent: BaseAgent
    ):
        """
        Initialize orchestrator with all specialized agents.

        Args:
            strategy_agent: Tire and pit strategy agent
            weather_agent: Weather impact agent
            performance_agent: Lap time and telemetry agent
            race_control_agent: Flag and penalty agent
            race_position_agent: Position and overtake agent
        """
        self.agents: Dict[str, BaseAgent] = {
            "strategy": strategy_agent,
            "weather": weather_agent,
            "performance": performance_agent,
            "race_control": race_control_agent,
            "race_position": race_position_agent
        }

        # Agent priority for conflict resolution (higher = higher priority)
        self.agent_priority = {
            "race_control": 5,  # Safety-critical, highest priority
            "strategy": 4,      # Core strategy decisions
            "weather": 3,       # Environmental factors
            "position": 2,      # Tactical positioning
            "performance": 1    # Performance analysis
        }

        self._context: Optional[AgentContext] = None
        logger.info("AgentOrchestrator initialized with 5 specialized agents")

    def set_context(self, context: AgentContext) -> None:
        """
        Set session context for all agents.

        Args:
            context: Session context (race/qualifying, year, race name)
        """
        self._context = context
        for agent in self.agents.values():
            agent.set_context(context)
        logger.info(
            f"Context set for all agents: {
                context.session_type} - {
                context.race_name} {
                context.year}")

    async def query(
            self,
            query: str,
            context: Optional[AgentContext] = None) -> OrchestratedResponse:
        """
        Process query through appropriate agent(s).

        Main orchestrator entry point. Routes query to agent(s), coordinates
        multi-agent responses, and returns aggregated result.

        Args:
            query: User query string
            context: Optional session context (overrides current context)

        Returns:
            OrchestratedResponse with primary and supporting responses

        Raises:
            ValueError: If no agents can handle the query
        """
        # Update context if provided
        if context:
            self.set_context(context)

        # Route query to appropriate agents
        capable_agents = self._route_query(query)

        if not capable_agents:
            raise ValueError(f"No agents can handle query: {query}")

        logger.info(
            f"Routing query to {
                len(capable_agents)} agent(s): {capable_agents}")

        # Execute query on all capable agents
        responses = await self._execute_multi_agent_query(query, capable_agents)

        # Aggregate responses
        orchestrated = self._aggregate_responses(
            query, responses, capable_agents)

        return orchestrated

    def _route_query(self, query: str) -> List[str]:
        """
        Determine which agents can handle the query.

        Uses each agent's validate_query() method to check capability.

        Args:
            query: User query string

        Returns:
            List of agent names that can handle the query
        """
        capable_agents = []

        for agent_name, agent in self.agents.items():
            if agent.validate_query(query):
                capable_agents.append(agent_name)
                logger.debug(f"Agent '{agent_name}' can handle query")

        # Sort by priority (highest first)
        capable_agents.sort(
            key=lambda name: self.agent_priority.get(name, 0),
            reverse=True
        )

        return capable_agents

    async def _execute_multi_agent_query(
        self,
        query: str,
        agent_names: List[str]
    ) -> Dict[str, AgentResponse]:
        """
        Execute query on multiple agents.

        Args:
            query: User query string
            agent_names: List of agent names to query

        Returns:
            Dictionary mapping agent name to response
        """
        responses = {}

        for agent_name in agent_names:
            agent = self.agents[agent_name]
            try:
                response = await agent.query(query)
                responses[agent_name] = response
                logger.info(f"Agent '{agent_name}' responded successfully")
            except Exception as e:
                logger.error(f"Agent '{agent_name}' failed: {e}")
                # Continue with other agents even if one fails

        return responses

    def _aggregate_responses(
        self,
        query: str,
        responses: Dict[str, AgentResponse],
        agent_names: List[str]
    ) -> OrchestratedResponse:
        """
        Aggregate multiple agent responses into orchestrated response.

        Primary agent is the highest priority agent that responded.
        Other agents provide supporting context.

        Args:
            query: Original user query
            responses: Agent responses dictionary
            agent_names: Ordered list of agent names (by priority)

        Returns:
            OrchestratedResponse with aggregated data
        """
        if not responses:
            raise ValueError("No successful responses from agents")

        # Primary agent is first (highest priority) that succeeded
        primary_agent_name = agent_names[0]
        primary_response = responses[primary_agent_name]

        # Supporting agents are the rest
        supporting_responses = [
            responses[name] for name in agent_names[1:]
            if name in responses
        ]

        # Calculate overall confidence (weighted by priority)
        total_weight = 0
        weighted_confidence = 0.0
        for agent_name in agent_names:
            if agent_name in responses:
                priority = self.agent_priority.get(agent_name, 1)
                confidence = responses[agent_name].confidence
                weighted_confidence += confidence * priority
                total_weight += priority

        overall_confidence = weighted_confidence / \
            total_weight if total_weight > 0 else 0.0

        # Build aggregated response text
        if len(responses) == 1:
            # Single agent response
            aggregated_text = primary_response.response
        else:
            # Multi-agent response - combine primary with supporting insights
            aggregated_text = self._build_multi_agent_response(
                primary_response,
                supporting_responses
            )

        return OrchestratedResponse(
            query=query,
            primary_response=aggregated_text,
            supporting_responses=supporting_responses,
            agents_used=[name for name in agent_names if name in responses],
            confidence=overall_confidence,
            context=self._context,
            metadata={
                "primary_agent": primary_agent_name,
                "total_agents": len(responses),
                "response_method": "multi-agent" if len(responses) > 1 else "single-agent"
            }
        )

    def _build_multi_agent_response(
        self,
        primary: AgentResponse,
        supporting: List[AgentResponse]
    ) -> str:
        """
        Build combined response from primary and supporting agents.

        Args:
            primary: Primary agent response
            supporting: List of supporting agent responses

        Returns:
            Combined response text
        """
        # Start with primary response
        combined = f"PRIMARY ANALYSIS ({
            primary.agent_name}):\n{
            primary.response}"

        # Add supporting insights
        if supporting:
            combined += "\n\nSUPPORTING INSIGHTS:"
            for response in supporting:
                combined += f"\n\n{response.agent_name}:\n{response.response}"

        return combined

    def get_agent_capabilities(self) -> Dict[str, Dict[str, Any]]:
        """
        Get capabilities of all agents.

        Returns:
            Dictionary mapping agent name to capabilities
        """
        capabilities = {}
        for agent_name, agent in self.agents.items():
            capabilities[agent_name] = agent.get_capabilities()
        return capabilities

    def get_orchestrator_status(self) -> Dict[str, Any]:
        """
        Get orchestrator status and configuration.

        Returns:
            Dictionary with orchestrator status
        """
        return {
            "total_agents": len(self.agents),
            "agents": list(self.agents.keys()),
            "context": {
                "session_type": self._context.session_type if self._context else None,
                "year": self._context.year if self._context else None,
                "race_name": self._context.race_name if self._context else None
            } if self._context else None,
            "priority_order": sorted(
                self.agent_priority.items(),
                key=lambda x: x[1],
                reverse=True
            )
        }
