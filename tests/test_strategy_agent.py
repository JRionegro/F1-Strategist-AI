"""
Unit Tests for Strategy Agent

Tests the Strategy Agent for both race and qualifying modes.
"""

import pytest
from unittest.mock import Mock

from src.agents.strategy_agent import StrategyAgent
from src.agents.base_agent import AgentConfig, AgentContext, AgentResponse
from src.llm.provider import LLMProvider
from src.llm.models import LLMResponse


class TestStrategyAgent:
    """Test Strategy Agent implementation."""
    
    @pytest.fixture
    def mock_llm_provider(self):
        """Create mock LLM provider."""
        mock_llm = Mock(spec=LLMProvider)
        
        # Create mock response
        mock_response = LLMResponse(
            content="One-stop strategy recommended with Medium tires.",
            model="test-model",
            provider="test-provider",
            tokens_input=50,
            tokens_output=30,
            cost_input=0.005,
            cost_output=0.003,
            latency_ms=150.0
        )
        
        # Mock async generate method
        async def mock_generate(*args, **kwargs):
            return mock_response
        
        mock_llm.generate = mock_generate
        return mock_llm
    
    @pytest.fixture
    def strategy_agent(self, mock_llm_provider):
        """Create Strategy Agent instance."""
        config = AgentConfig(
            name="StrategyAgent",
            description="F1 race and qualifying strategy optimization",
            llm_provider=mock_llm_provider
        )
        return StrategyAgent(config)
    
    @pytest.fixture
    def race_context(self):
        """Create race context."""
        return AgentContext(
            session_type="race",
            year=2024,
            race_name="Monaco Grand Prix"
        )
    
    @pytest.fixture
    def qualifying_context(self):
        """Create qualifying context."""
        return AgentContext(
            session_type="qualifying",
            year=2024,
            race_name="Monaco Grand Prix"
        )
    
    def test_strategy_agent_initialization(self, strategy_agent):
        """Test Strategy Agent initialization."""
        assert strategy_agent.config.name == "StrategyAgent"
        assert strategy_agent.context is None
    
    def test_get_available_tools(self, strategy_agent):
        """Test Strategy Agent available tools."""
        tools = strategy_agent.get_available_tools()
        
        assert "get_race_results" in tools
        assert "get_lap_times" in tools
        assert "get_pit_stops" in tools
        assert "get_weather" in tools
        assert "get_qualifying_results" in tools
        assert "get_session_info" in tools
    
    def test_validate_query_tire_strategy(self, strategy_agent):
        """Test query validation for tire strategy."""
        assert strategy_agent.validate_query("What is the best tire strategy?") is True
        assert strategy_agent.validate_query("Should I use soft or medium tires?") is True
        assert strategy_agent.validate_query("Tyre compound recommendation") is True
    
    def test_validate_query_pit_stops(self, strategy_agent):
        """Test query validation for pit stop queries."""
        assert strategy_agent.validate_query("When should I pit?") is True
        assert strategy_agent.validate_query("Optimal pit stop window") is True
        assert strategy_agent.validate_query("Two-stop or one-stop strategy?") is True
    
    def test_validate_query_qualifying(self, strategy_agent):
        """Test query validation for qualifying queries."""
        assert strategy_agent.validate_query("Q3 strategy recommendation") is True
        assert strategy_agent.validate_query("When to go out in qualifying?") is True
        assert strategy_agent.validate_query("Best qualifying strategy") is True
    
    def test_validate_query_fuel_management(self, strategy_agent):
        """Test query validation for fuel queries."""
        assert strategy_agent.validate_query("Should we save fuel?") is True
        assert strategy_agent.validate_query("Fuel management strategy") is True
    
    def test_validate_query_invalid(self, strategy_agent):
        """Test query validation rejects invalid queries."""
        assert strategy_agent.validate_query("") is False
        assert strategy_agent.validate_query("   ") is False
        assert strategy_agent.validate_query("What's the weather?") is False
        assert strategy_agent.validate_query("Driver comparison") is False
    
    def test_get_system_prompt_race_mode(self, strategy_agent, race_context):
        """Test system prompt for race mode."""
        strategy_agent.set_context(race_context)
        prompt = strategy_agent.get_system_prompt()
        
        assert "Race Strategy Agent" in prompt
        assert "Monaco Grand Prix" in prompt
        assert "2024" in prompt
        assert "TIRE STRATEGY" in prompt
        assert "PIT STOP TIMING" in prompt
        assert "RACE PACE MANAGEMENT" in prompt
    
    def test_get_system_prompt_qualifying_mode(self, strategy_agent, qualifying_context):
        """Test system prompt for qualifying mode."""
        strategy_agent.set_context(qualifying_context)
        prompt = strategy_agent.get_system_prompt()
        
        assert "Qualifying Strategy Agent" in prompt
        assert "Monaco Grand Prix" in prompt
        assert "2024" in prompt
        assert "TRACK EXIT STRATEGY" in prompt
        assert "ATTEMPT OPTIMIZATION" in prompt
        assert "Q1" in prompt and "Q2" in prompt and "Q3" in prompt
    
    def test_get_system_prompt_no_context(self, strategy_agent):
        """Test system prompt without context."""
        prompt = strategy_agent.get_system_prompt()
        
        assert "Strategy Agent" in prompt
        assert "Tire strategy" in prompt
        assert "Pit stop timing" in prompt
    
    @pytest.mark.asyncio
    async def test_query_race_strategy(self, strategy_agent, race_context):
        """Test querying race strategy."""
        strategy_agent.set_context(race_context)
        
        response = await strategy_agent.query(
            "What is the optimal tire strategy for Monaco?"
        )
        
        assert isinstance(response, AgentResponse)
        assert response.agent_name == "StrategyAgent"
        assert "One-stop" in response.response or "tire" in response.response.lower()
    
    @pytest.mark.asyncio
    async def test_query_qualifying_strategy(self, strategy_agent, qualifying_context):
        """Test querying qualifying strategy."""
        strategy_agent.set_context(qualifying_context)
        
        response = await strategy_agent.query(
            "What is the best Q3 strategy?"
        )
        
        assert isinstance(response, AgentResponse)
        assert response.agent_name == "StrategyAgent"
        assert response.confidence > 0.0
    
    @pytest.mark.asyncio
    async def test_query_pit_stop_timing(self, strategy_agent, race_context):
        """Test querying pit stop timing."""
        strategy_agent.set_context(race_context)
        
        response = await strategy_agent.query(
            "When should we pit to undercut the leader?"
        )
        
        assert isinstance(response, AgentResponse)
        assert response.agent_name == "StrategyAgent"
    
    @pytest.mark.asyncio
    async def test_query_with_invalid_query_raises_error(
        self, strategy_agent, race_context
    ):
        """Test that invalid query raises ValueError."""
        strategy_agent.set_context(race_context)
        
        with pytest.raises(ValueError, match="not suitable"):
            await strategy_agent.query("What's the weather forecast?")
    
    def test_system_prompt_adapts_to_session_type(self, strategy_agent):
        """Test system prompt adapts based on session type."""
        # Race context
        race_ctx = AgentContext(
            session_type="race",
            year=2024,
            race_name="Monza"
        )
        strategy_agent.set_context(race_ctx)
        race_prompt = strategy_agent.get_system_prompt()
        
        # Qualifying context
        qual_ctx = AgentContext(
            session_type="qualifying",
            year=2024,
            race_name="Monza"
        )
        strategy_agent.set_context(qual_ctx)
        qual_prompt = strategy_agent.get_system_prompt()
        
        # Prompts should be different
        assert race_prompt != qual_prompt
        assert "Race Strategy" in race_prompt
        assert "Qualifying Strategy" in qual_prompt
    
    def test_get_capabilities(self, strategy_agent):
        """Test getting agent capabilities."""
        capabilities = strategy_agent.get_capabilities()
        
        assert capabilities["name"] == "StrategyAgent"
        assert "tire" in capabilities["description"].lower() or \
               "strategy" in capabilities["description"].lower()
        assert "get_pit_stops" in capabilities["tools"]
        assert capabilities["rag_enabled"] is True
        assert capabilities["tools_enabled"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
