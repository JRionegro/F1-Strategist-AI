"""
Unit Tests for Performance Agent

Tests the Performance Agent for both race and qualifying modes.
"""

import pytest
from unittest.mock import Mock

from src.agents.performance_agent import PerformanceAgent
from src.agents.base_agent import AgentConfig, AgentContext, AgentResponse
from src.llm.provider import LLMProvider
from src.llm.models import LLMResponse


class TestPerformanceAgent:
    """Test Performance Agent implementation."""
    
    @pytest.fixture
    def mock_llm_provider(self):
        """Create mock LLM provider."""
        mock_llm = Mock(spec=LLMProvider)
        
        # Create mock response
        mock_response = LLMResponse(
            content="Verstappen's lap time 1:23.456 is 0.234s faster than Hamilton.",
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
    def performance_agent(self, mock_llm_provider):
        """Create Performance Agent instance."""
        config = AgentConfig(
            name="PerformanceAgent",
            description="F1 lap time and telemetry analysis",
            llm_provider=mock_llm_provider
        )
        return PerformanceAgent(config)
    
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
            race_name="Monza"
        )
    
    def test_performance_agent_initialization(self, performance_agent):
        """Test Performance Agent initialization."""
        assert performance_agent.config.name == "PerformanceAgent"
        assert performance_agent.context is None
    
    def test_get_available_tools(self, performance_agent):
        """Test Performance Agent available tools."""
        tools = performance_agent.get_available_tools()
        
        assert "get_telemetry" in tools
        assert "get_lap_times" in tools
        assert "get_race_results" in tools
        assert "get_qualifying_results" in tools
        assert "get_session_info" in tools
        assert len(tools) == 5
    
    def test_validate_query_lap_times(self, performance_agent):
        """Test query validation for lap time queries."""
        assert performance_agent.validate_query("What's the fastest lap time?") is True
        assert performance_agent.validate_query("Show me sector times") is True
        assert performance_agent.validate_query("S1 analysis") is True
        assert performance_agent.validate_query("Sector 2 comparison") is True
    
    def test_validate_query_pace(self, performance_agent):
        """Test query validation for pace queries."""
        assert performance_agent.validate_query("Who has the best pace?") is True
        assert performance_agent.validate_query("Is Hamilton faster than Verstappen?") is True
        assert performance_agent.validate_query("Compare race pace") is True
    
    def test_validate_query_telemetry(self, performance_agent):
        """Test query validation for telemetry queries."""
        assert performance_agent.validate_query("Show telemetry data") is True
        assert performance_agent.validate_query("Speed trap comparison") is True
        assert performance_agent.validate_query("Throttle application analysis") is True
        assert performance_agent.validate_query("Braking point differences") is True
    
    def test_validate_query_comparison(self, performance_agent):
        """Test query validation for comparison queries."""
        assert performance_agent.validate_query("Compare Verstappen vs Leclerc") is True
        assert performance_agent.validate_query("Gap to pole position") is True
        assert performance_agent.validate_query("How much faster is P1?") is True
    
    def test_validate_query_qualifying(self, performance_agent):
        """Test query validation for qualifying queries."""
        assert performance_agent.validate_query("Q3 lap time analysis") is True
        assert performance_agent.validate_query("Pole position gap") is True
        assert performance_agent.validate_query("Theoretical best lap") is True
    
    def test_validate_query_invalid(self, performance_agent):
        """Test query validation rejects invalid queries."""
        assert performance_agent.validate_query("") is False
        assert performance_agent.validate_query("   ") is False
        assert performance_agent.validate_query("What's the weather forecast?") is False
        assert performance_agent.validate_query("When should we pit?") is False
    
    def test_get_system_prompt_race_mode(self, performance_agent, race_context):
        """Test system prompt for race mode."""
        performance_agent.set_context(race_context)
        prompt = performance_agent.get_system_prompt()
        
        assert "Performance Agent" in prompt
        assert "Monaco Grand Prix" in prompt
        assert "2024" in prompt
        assert "LAP TIME ANALYSIS" in prompt
        assert "PACE COMPARISON" in prompt
        assert "TIRE DEGRADATION" in prompt
        assert "FUEL EFFECT" in prompt
    
    def test_get_system_prompt_qualifying_mode(
        self, performance_agent, qualifying_context
    ):
        """Test system prompt for qualifying mode."""
        performance_agent.set_context(qualifying_context)
        prompt = performance_agent.get_system_prompt()
        
        assert "Performance Agent" in prompt
        assert "Monza" in prompt
        assert "2024" in prompt
        assert "SECTOR ANALYSIS" in prompt
        assert "OPTIMAL LAP CONSTRUCTION" in prompt
        assert "TIRE PREPARATION" in prompt
        assert "GAP ANALYSIS" in prompt
        assert "Q1" in prompt and "Q2" in prompt and "Q3" in prompt
    
    def test_get_system_prompt_no_context(self, performance_agent):
        """Test system prompt without context."""
        prompt = performance_agent.get_system_prompt()
        
        assert "Performance Agent" in prompt
        assert "lap time" in prompt.lower()
        assert "telemetry" in prompt.lower()
    
    @pytest.mark.asyncio
    async def test_query_lap_time_analysis(self, performance_agent, race_context):
        """Test querying lap time analysis."""
        performance_agent.set_context(race_context)
        
        response = await performance_agent.query(
            "What's Verstappen's fastest lap time?"
        )
        
        assert isinstance(response, AgentResponse)
        assert response.agent_name == "PerformanceAgent"
        assert "1:23.456" in response.response or "faster" in response.response.lower()
    
    @pytest.mark.asyncio
    async def test_query_pace_comparison(self, performance_agent, race_context):
        """Test querying pace comparison."""
        performance_agent.set_context(race_context)
        
        response = await performance_agent.query(
            "Compare Verstappen's pace to Hamilton's"
        )
        
        assert isinstance(response, AgentResponse)
        assert response.agent_name == "PerformanceAgent"
        assert response.confidence > 0.0
    
    @pytest.mark.asyncio
    async def test_query_sector_analysis(
        self, performance_agent, qualifying_context
    ):
        """Test querying sector analysis in qualifying."""
        performance_agent.set_context(qualifying_context)
        
        response = await performance_agent.query(
            "Show me sector 2 times for all drivers"
        )
        
        assert isinstance(response, AgentResponse)
        assert response.agent_name == "PerformanceAgent"
    
    @pytest.mark.asyncio
    async def test_query_telemetry_data(self, performance_agent, race_context):
        """Test querying telemetry data."""
        performance_agent.set_context(race_context)
        
        response = await performance_agent.query(
            "Show me speed trap data for turn 3"
        )
        
        assert isinstance(response, AgentResponse)
        assert response.agent_name == "PerformanceAgent"
    
    @pytest.mark.asyncio
    async def test_query_qualifying_gaps(
        self, performance_agent, qualifying_context
    ):
        """Test querying qualifying gaps."""
        performance_agent.set_context(qualifying_context)
        
        response = await performance_agent.query(
            "What's the gap to pole position?"
        )
        
        assert isinstance(response, AgentResponse)
        assert response.agent_name == "PerformanceAgent"
    
    @pytest.mark.asyncio
    async def test_query_with_invalid_query_raises_error(
        self, performance_agent, race_context
    ):
        """Test that invalid query raises ValueError."""
        performance_agent.set_context(race_context)
        
        with pytest.raises(ValueError, match="not suitable"):
            await performance_agent.query("Will it rain tomorrow?")
    
    def test_system_prompt_adapts_to_session_type(self, performance_agent):
        """Test system prompt adapts based on session type."""
        # Race context
        race_ctx = AgentContext(
            session_type="race",
            year=2024,
            race_name="Spa"
        )
        performance_agent.set_context(race_ctx)
        race_prompt = performance_agent.get_system_prompt()
        
        # Qualifying context
        qual_ctx = AgentContext(
            session_type="qualifying",
            year=2024,
            race_name="Spa"
        )
        performance_agent.set_context(qual_ctx)
        qual_prompt = performance_agent.get_system_prompt()
        
        # Prompts should be different
        assert race_prompt != qual_prompt
        assert "PACE COMPARISON" in race_prompt
        assert "SECTOR ANALYSIS" in qual_prompt
        assert "OPTIMAL LAP CONSTRUCTION" in qual_prompt
    
    def test_get_capabilities(self, performance_agent):
        """Test getting agent capabilities."""
        capabilities = performance_agent.get_capabilities()
        
        assert capabilities["name"] == "PerformanceAgent"
        assert "lap time" in capabilities["description"].lower()
        assert "get_telemetry" in capabilities["tools"]
        assert "get_lap_times" in capabilities["tools"]
        assert capabilities["rag_enabled"] is True
        assert capabilities["tools_enabled"] is True
    
    def test_validate_query_comprehensive_keywords(self, performance_agent):
        """Test query validation with comprehensive keyword coverage."""
        # Delta and gaps
        assert performance_agent.validate_query("What's the delta to P1?") is True
        assert performance_agent.validate_query("Gap behind leader") is True
        
        # Purple/green sectors
        assert performance_agent.validate_query("Who has purple sector 1?") is True
        assert performance_agent.validate_query("Green sector analysis") is True
        
        # Degradation
        assert performance_agent.validate_query("Tire degradation impact") is True
        assert performance_agent.validate_query("Performance drop off") is True
        
        # DRS
        assert performance_agent.validate_query("DRS effectiveness") is True
        
        # Consistency
        assert performance_agent.validate_query("Driver consistency analysis") is True
        
        # Theoretical best
        assert performance_agent.validate_query("Theoretical best lap time") is True
        
        # Stint analysis
        assert performance_agent.validate_query("Stint performance comparison") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
