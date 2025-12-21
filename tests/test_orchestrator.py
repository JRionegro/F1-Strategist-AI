"""
Unit Tests for Agent Orchestrator

Tests multi-agent coordination, query routing, and response aggregation.
"""

import pytest
from unittest.mock import Mock, AsyncMock

from src.agents.orchestrator import AgentOrchestrator, OrchestratedResponse
from src.agents.base_agent import BaseAgent, AgentConfig, AgentContext, AgentResponse
from src.llm.provider import LLMProvider
from src.llm.models import LLMResponse


class TestAgentOrchestrator:
    """Test Agent Orchestrator implementation."""
    
    @pytest.fixture
    def mock_llm_provider(self):
        """Create mock LLM provider."""
        mock_llm = Mock(spec=LLMProvider)
        
        # Create mock response
        mock_response = LLMResponse(
            content="Test response from agent",
            model="test-model",
            provider="test-provider",
            tokens_input=50,
            tokens_output=30,
            cost_input=0.005,
            cost_output=0.003,
            latency_ms=130.0
        )
        
        # Mock async generate method
        async def mock_generate(*args, **kwargs):
            return mock_response
        
        mock_llm.generate = mock_generate
        return mock_llm
    
    @pytest.fixture
    def mock_strategy_agent(self, mock_llm_provider):
        """Create mock strategy agent."""
        agent = Mock(spec=BaseAgent)
        agent.config = AgentConfig(
            name="StrategyAgent",
            description="Test strategy agent",
            llm_provider=mock_llm_provider
        )
        agent.validate_query = Mock(return_value=True)
        agent.get_capabilities = Mock(return_value={
            "name": "StrategyAgent",
            "tools": ["get_pit_stops"]
        })
        
        async def mock_query(query: str):
            return AgentResponse(
                agent_name="StrategyAgent",
                query=query,
                response="Pit on lap 25 for medium tires",
                confidence=0.85,
                sources=["get_pit_stops"],
                reasoning="Based on tire degradation analysis"
            )
        
        agent.query = AsyncMock(side_effect=mock_query)
        agent.set_context = Mock()
        return agent
    
    @pytest.fixture
    def mock_weather_agent(self, mock_llm_provider):
        """Create mock weather agent."""
        agent = Mock(spec=BaseAgent)
        agent.config = AgentConfig(
            name="WeatherAgent",
            description="Test weather agent",
            llm_provider=mock_llm_provider
        )
        agent.validate_query = Mock(return_value=False)  # Default: can't handle
        agent.get_capabilities = Mock(return_value={
            "name": "WeatherAgent",
            "tools": ["get_weather"]
        })
        
        async def mock_query(query: str):
            return AgentResponse(
                agent_name="WeatherAgent",
                query=query,
                response="Rain expected in 15 minutes",
                confidence=0.75,
                sources=["get_weather"],
                reasoning="Weather radar analysis"
            )
        
        agent.query = AsyncMock(side_effect=mock_query)
        agent.set_context = Mock()
        return agent
    
    @pytest.fixture
    def mock_performance_agent(self, mock_llm_provider):
        """Create mock performance agent."""
        agent = Mock(spec=BaseAgent)
        agent.config = AgentConfig(
            name="PerformanceAgent",
            description="Test performance agent",
            llm_provider=mock_llm_provider
        )
        agent.validate_query = Mock(return_value=False)
        agent.get_capabilities = Mock(return_value={
            "name": "PerformanceAgent",
            "tools": ["get_telemetry"]
        })
        
        async def mock_query(query: str):
            return AgentResponse(
                agent_name="PerformanceAgent",
                query=query,
                response="Lap time 1:23.456",
                confidence=0.90,
                sources=["get_telemetry"],
                reasoning="Telemetry data analysis"
            )
        
        agent.query = AsyncMock(side_effect=mock_query)
        agent.set_context = Mock()
        return agent
    
    @pytest.fixture
    def mock_race_control_agent(self, mock_llm_provider):
        """Create mock race control agent."""
        agent = Mock(spec=BaseAgent)
        agent.config = AgentConfig(
            name="RaceControlAgent",
            description="Test race control agent",
            llm_provider=mock_llm_provider
        )
        agent.validate_query = Mock(return_value=False)
        agent.get_capabilities = Mock(return_value={
            "name": "RaceControlAgent",
            "tools": ["get_race_control_messages"]
        })
        
        async def mock_query(query: str):
            return AgentResponse(
                agent_name="RaceControlAgent",
                query=query,
                response="Safety car deployed",
                confidence=0.95,
                sources=["get_race_control_messages"],
                reasoning="Race control message analysis"
            )
        
        agent.query = AsyncMock(side_effect=mock_query)
        agent.set_context = Mock()
        return agent
    
    @pytest.fixture
    def mock_race_position_agent(self, mock_llm_provider):
        """Create mock race position agent."""
        agent = Mock(spec=BaseAgent)
        agent.config = AgentConfig(
            name="RacePositionAgent",
            description="Test race position agent",
            llm_provider=mock_llm_provider
        )
        agent.validate_query = Mock(return_value=False)
        agent.get_capabilities = Mock(return_value={
            "name": "RacePositionAgent",
            "tools": ["get_race_results"]
        })
        
        async def mock_query(query: str):
            return AgentResponse(
                agent_name="RacePositionAgent",
                query=query,
                response="P1 gap to P2: 2.5s",
                confidence=0.88,
                sources=["get_race_results"],
                reasoning="Position data analysis"
            )
        
        agent.query = AsyncMock(side_effect=mock_query)
        agent.set_context = Mock()
        return agent
    
    @pytest.fixture
    def orchestrator(
        self,
        mock_strategy_agent,
        mock_weather_agent,
        mock_performance_agent,
        mock_race_control_agent,
        mock_race_position_agent
    ):
        """Create orchestrator with all mock agents."""
        return AgentOrchestrator(
            strategy_agent=mock_strategy_agent,
            weather_agent=mock_weather_agent,
            performance_agent=mock_performance_agent,
            race_control_agent=mock_race_control_agent,
            race_position_agent=mock_race_position_agent
        )
    
    @pytest.fixture
    def race_context(self):
        """Create race context."""
        return AgentContext(
            session_type="race",
            year=2024,
            race_name="Monaco Grand Prix"
        )
    
    def test_orchestrator_initialization(self, orchestrator):
        """Test orchestrator initialization."""
        assert len(orchestrator.agents) == 5
        assert "strategy" in orchestrator.agents
        assert "weather" in orchestrator.agents
        assert "performance" in orchestrator.agents
        assert "race_control" in orchestrator.agents
        assert "race_position" in orchestrator.agents
    
    def test_set_context(self, orchestrator, race_context):
        """Test setting context for all agents."""
        orchestrator.set_context(race_context)
        
        # Verify context set on all agents
        for agent in orchestrator.agents.values():
            agent.set_context.assert_called_once_with(race_context)
    
    def test_route_query_single_agent(self, orchestrator):
        """Test query routing to single agent."""
        # Only strategy agent can handle this query
        orchestrator.agents["strategy"].validate_query.return_value = True
        
        capable = orchestrator._route_query("What's the pit strategy?")
        
        assert capable == ["strategy"]
    
    def test_route_query_multiple_agents(self, orchestrator):
        """Test query routing to multiple agents."""
        # Multiple agents can handle this query
        orchestrator.agents["strategy"].validate_query.return_value = True
        orchestrator.agents["weather"].validate_query.return_value = True
        orchestrator.agents["race_control"].validate_query.return_value = True
        
        capable = orchestrator._route_query("Should we pit now?")
        
        # Should be sorted by priority: race_control (5), strategy (4), weather (3)
        assert "race_control" in capable
        assert "strategy" in capable
        assert "weather" in capable
        assert capable.index("race_control") < capable.index("strategy")
        assert capable.index("strategy") < capable.index("weather")
    
    def test_route_query_no_agents(self, orchestrator):
        """Test query routing when no agents can handle."""
        # No agents can handle
        for agent in orchestrator.agents.values():
            agent.validate_query.return_value = False
        
        capable = orchestrator._route_query("Random query")
        
        assert capable == []
    
    @pytest.mark.asyncio
    async def test_query_single_agent(self, orchestrator, race_context):
        """Test query with single capable agent."""
        orchestrator.set_context(race_context)
        orchestrator.agents["strategy"].validate_query.return_value = True
        
        response = await orchestrator.query("What's the tire strategy?")
        
        assert isinstance(response, OrchestratedResponse)
        assert response.query == "What's the tire strategy?"
        assert "strategy" in response.agents_used
        assert len(response.agents_used) == 1
        assert "Pit on lap 25" in response.primary_response
    
    @pytest.mark.asyncio
    async def test_query_multiple_agents(self, orchestrator, race_context):
        """Test query with multiple capable agents."""
        orchestrator.set_context(race_context)
        
        # Multiple agents can handle
        orchestrator.agents["strategy"].validate_query.return_value = True
        orchestrator.agents["weather"].validate_query.return_value = True
        
        response = await orchestrator.query("Should we pit considering the weather?")
        
        assert isinstance(response, OrchestratedResponse)
        assert len(response.agents_used) == 2
        assert "strategy" in response.agents_used
        assert "weather" in response.agents_used
        assert len(response.supporting_responses) == 1
        assert response.metadata["response_method"] == "multi-agent"
    
    @pytest.mark.asyncio
    async def test_query_with_no_capable_agents_raises_error(
        self, orchestrator, race_context
    ):
        """Test query raises error when no agents can handle."""
        orchestrator.set_context(race_context)
        
        # No agents can handle
        for agent in orchestrator.agents.values():
            agent.validate_query.return_value = False
        
        with pytest.raises(ValueError, match="No agents can handle query"):
            await orchestrator.query("Invalid query")
    
    @pytest.mark.asyncio
    async def test_query_with_agent_failure_continues(
        self, orchestrator, race_context
    ):
        """Test orchestrator continues when one agent fails."""
        orchestrator.set_context(race_context)
        
        # Two agents can handle
        orchestrator.agents["strategy"].validate_query.return_value = True
        orchestrator.agents["weather"].validate_query.return_value = True
        
        # Weather agent fails
        orchestrator.agents["weather"].query.side_effect = Exception("Agent error")
        
        response = await orchestrator.query("Strategy with weather?")
        
        # Should still get response from strategy agent
        assert isinstance(response, OrchestratedResponse)
        assert "strategy" in response.agents_used
        # Weather agent should not be in used agents due to failure
        assert len(response.agents_used) >= 1
    
    def test_aggregate_responses_single_agent(self, orchestrator):
        """Test response aggregation with single agent."""
        responses = {
            "strategy": AgentResponse(
                agent_name="StrategyAgent",
                query="Test",
                response="Strategy response",
                confidence=0.85,
                sources=["tool1"],
                reasoning="Test reasoning"
            )
        }
        
        orchestrated = orchestrator._aggregate_responses(
            "Test query",
            responses,
            ["strategy"]
        )
        
        assert orchestrated.primary_response == "Strategy response"
        assert len(orchestrated.supporting_responses) == 0
        assert orchestrated.metadata["response_method"] == "single-agent"
    
    def test_aggregate_responses_multiple_agents(self, orchestrator):
        """Test response aggregation with multiple agents."""
        responses = {
            "strategy": AgentResponse(
                agent_name="StrategyAgent",
                query="Test",
                response="Strategy response",
                confidence=0.85,
                sources=["tool1"],
                reasoning="Strategy reasoning"
            ),
            "weather": AgentResponse(
                agent_name="WeatherAgent",
                query="Test",
                response="Weather response",
                confidence=0.75,
                sources=["tool2"],
                reasoning="Weather reasoning"
            )
        }
        
        orchestrated = orchestrator._aggregate_responses(
            "Test query",
            responses,
            ["strategy", "weather"]
        )
        
        assert "PRIMARY ANALYSIS" in orchestrated.primary_response
        assert "SUPPORTING INSIGHTS" in orchestrated.primary_response
        assert len(orchestrated.supporting_responses) == 1
        assert orchestrated.metadata["response_method"] == "multi-agent"
    
    def test_get_agent_capabilities(self, orchestrator):
        """Test getting all agent capabilities."""
        capabilities = orchestrator.get_agent_capabilities()
        
        assert len(capabilities) == 5
        assert "strategy" in capabilities
        assert "weather" in capabilities
        assert capabilities["strategy"]["name"] == "StrategyAgent"
    
    def test_get_orchestrator_status_no_context(self, orchestrator):
        """Test getting orchestrator status without context."""
        status = orchestrator.get_orchestrator_status()
        
        assert status["total_agents"] == 5
        assert len(status["agents"]) == 5
        assert status["context"] is None
        assert len(status["priority_order"]) == 5
    
    def test_get_orchestrator_status_with_context(self, orchestrator, race_context):
        """Test getting orchestrator status with context."""
        orchestrator.set_context(race_context)
        status = orchestrator.get_orchestrator_status()
        
        assert status["context"]["session_type"] == "race"
        assert status["context"]["year"] == 2024
        assert status["context"]["race_name"] == "Monaco Grand Prix"
    
    def test_agent_priority_order(self, orchestrator):
        """Test agent priority ordering."""
        # Race control should have highest priority
        assert orchestrator.agent_priority["race_control"] == 5
        assert orchestrator.agent_priority["strategy"] == 4
        assert orchestrator.agent_priority["weather"] == 3
        
        # Verify priority affects routing order
        orchestrator.agents["race_control"].validate_query.return_value = True
        orchestrator.agents["strategy"].validate_query.return_value = True
        
        capable = orchestrator._route_query("Test query")
        
        # Race control should come before strategy
        assert capable[0] == "race_control"
        assert capable[1] == "strategy"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
