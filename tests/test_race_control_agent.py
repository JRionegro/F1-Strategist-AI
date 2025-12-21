"""
Unit Tests for Race Control Agent

Tests the Race Control Agent for race and qualifying sessions.
"""

import pytest
from unittest.mock import Mock

from src.agents.race_control_agent import RaceControlAgent
from src.agents.base_agent import AgentConfig, AgentContext, AgentResponse
from src.llm.provider import LLMProvider
from src.llm.models import LLMResponse


class TestRaceControlAgent:
    """Test Race Control Agent implementation."""
    
    @pytest.fixture
    def mock_llm_provider(self):
        """Create mock LLM provider."""
        mock_llm = Mock(spec=LLMProvider)
        
        # Create mock response
        mock_response = LLMResponse(
            content="Safety Car deployed on Lap 23. Strategic pit window open.",
            model="test-model",
            provider="test-provider",
            tokens_input=45,
            tokens_output=28,
            cost_input=0.0045,
            cost_output=0.0028,
            latency_ms=125.0
        )
        
        # Mock async generate method
        async def mock_generate(*args, **kwargs):
            return mock_response
        
        mock_llm.generate = mock_generate
        return mock_llm
    
    @pytest.fixture
    def race_control_agent(self, mock_llm_provider):
        """Create Race Control Agent instance."""
        config = AgentConfig(
            name="RaceControlAgent",
            description="F1 race control and flag interpretation",
            llm_provider=mock_llm_provider
        )
        return RaceControlAgent(config)
    
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
            race_name="Silverstone"
        )
    
    def test_race_control_agent_initialization(self, race_control_agent):
        """Test Race Control Agent initialization."""
        assert race_control_agent.config.name == "RaceControlAgent"
        assert race_control_agent.context is None
    
    def test_get_available_tools(self, race_control_agent):
        """Test Race Control Agent available tools."""
        tools = race_control_agent.get_available_tools()
        
        assert "get_race_control_messages" in tools
        assert "get_track_status" in tools
        assert "get_session_info" in tools
        assert "get_race_results" in tools
        assert len(tools) == 4
    
    def test_validate_query_flags(self, race_control_agent):
        """Test query validation for flag queries."""
        assert race_control_agent.validate_query("Is there a yellow flag?") is True
        assert race_control_agent.validate_query("Red flag situation") is True
        assert race_control_agent.validate_query("Blue flag shown") is True
        assert race_control_agent.validate_query("Checkered flag") is True
    
    def test_validate_query_safety_car(self, race_control_agent):
        """Test query validation for safety car queries."""
        assert race_control_agent.validate_query("Is the safety car out?") is True
        assert race_control_agent.validate_query("VSC deployed") is True
        assert race_control_agent.validate_query("Virtual safety car active") is True
    
    def test_validate_query_penalties(self, race_control_agent):
        """Test query validation for penalty queries."""
        assert race_control_agent.validate_query("Did Hamilton get a penalty?") is True
        assert race_control_agent.validate_query("5 second time penalty") is True
        assert race_control_agent.validate_query("Penalty under investigation") is True
        assert race_control_agent.validate_query("Grid penalty applied") is True
    
    def test_validate_query_incidents(self, race_control_agent):
        """Test query validation for incident queries."""
        assert race_control_agent.validate_query("Incident under investigation") is True
        assert race_control_agent.validate_query("Collision between cars") is True
        assert race_control_agent.validate_query("Track limits violation") is True
    
    def test_validate_query_track_status(self, race_control_agent):
        """Test query validation for track status queries."""
        assert race_control_agent.validate_query("What's the track status?") is True
        assert race_control_agent.validate_query("Is DRS enabled?") is True
        assert race_control_agent.validate_query("Debris on track") is True
    
    def test_validate_query_invalid(self, race_control_agent):
        """Test query validation rejects invalid queries."""
        assert race_control_agent.validate_query("") is False
        assert race_control_agent.validate_query("   ") is False
        assert race_control_agent.validate_query("What's the fastest lap?") is False
        assert race_control_agent.validate_query("Tire strategy analysis") is False
    
    def test_get_system_prompt_race_mode(self, race_control_agent, race_context):
        """Test system prompt for race mode."""
        race_control_agent.set_context(race_context)
        prompt = race_control_agent.get_system_prompt()
        
        assert "Race Control Agent" in prompt
        assert "Monaco Grand Prix" in prompt
        assert "2024" in prompt
        assert "FLAG INTERPRETATION" in prompt
        assert "SAFETY CAR" in prompt
        assert "VIRTUAL SAFETY CAR" in prompt
        assert "PENALTY TRACKING" in prompt
    
    def test_get_system_prompt_qualifying_mode(
        self, race_control_agent, qualifying_context
    ):
        """Test system prompt for qualifying mode."""
        race_control_agent.set_context(qualifying_context)
        prompt = race_control_agent.get_system_prompt()
        
        assert "Race Control Agent" in prompt
        assert "Silverstone" in prompt
        assert "2024" in prompt
        assert "QUALIFYING FLAGS" in prompt
        assert "TRACK LIMITS" in prompt
        assert "SESSION INTERRUPTIONS" in prompt
    
    def test_get_system_prompt_no_context(self, race_control_agent):
        """Test system prompt without context."""
        prompt = race_control_agent.get_system_prompt()
        
        assert "Race Control Agent" in prompt
        assert "flag" in prompt.lower()
        assert "safety car" in prompt.lower()
    
    @pytest.mark.asyncio
    async def test_query_safety_car_deployment(
        self, race_control_agent, race_context
    ):
        """Test querying safety car deployment."""
        race_control_agent.set_context(race_context)
        
        response = await race_control_agent.query("Is the safety car out?")
        
        assert isinstance(response, AgentResponse)
        assert response.agent_name == "RaceControlAgent"
        assert (
            "safety car" in response.response.lower() or
            "lap 23" in response.response.lower()
        )
    
    @pytest.mark.asyncio
    async def test_query_penalty_status(self, race_control_agent, race_context):
        """Test querying penalty status."""
        race_control_agent.set_context(race_context)
        
        response = await race_control_agent.query(
            "Did Verstappen receive a penalty?"
        )
        
        assert isinstance(response, AgentResponse)
        assert response.agent_name == "RaceControlAgent"
        assert response.confidence > 0.0
    
    @pytest.mark.asyncio
    async def test_query_yellow_flag(self, race_control_agent, race_context):
        """Test querying yellow flag status."""
        race_control_agent.set_context(race_context)
        
        response = await race_control_agent.query(
            "Is there a yellow flag in sector 2?"
        )
        
        assert isinstance(response, AgentResponse)
        assert response.agent_name == "RaceControlAgent"
    
    @pytest.mark.asyncio
    async def test_query_track_status(self, race_control_agent, race_context):
        """Test querying track status."""
        race_control_agent.set_context(race_context)
        
        response = await race_control_agent.query("What's the current track status?")
        
        assert isinstance(response, AgentResponse)
        assert response.agent_name == "RaceControlAgent"
    
    @pytest.mark.asyncio
    async def test_query_qualifying_red_flag(
        self, race_control_agent, qualifying_context
    ):
        """Test querying red flag in qualifying."""
        race_control_agent.set_context(qualifying_context)
        
        response = await race_control_agent.query(
            "Red flag in Q2, how much time is left?"
        )
        
        assert isinstance(response, AgentResponse)
        assert response.agent_name == "RaceControlAgent"
    
    @pytest.mark.asyncio
    async def test_query_with_invalid_query_raises_error(
        self, race_control_agent, race_context
    ):
        """Test that invalid query raises ValueError."""
        race_control_agent.set_context(race_context)
        
        with pytest.raises(ValueError, match="not suitable"):
            await race_control_agent.query("What's the weather forecast?")
    
    def test_system_prompt_adapts_to_session_type(self, race_control_agent):
        """Test system prompt adapts based on session type."""
        # Race context
        race_ctx = AgentContext(
            session_type="race",
            year=2024,
            race_name="Spa"
        )
        race_control_agent.set_context(race_ctx)
        race_prompt = race_control_agent.get_system_prompt()
        
        # Qualifying context
        qual_ctx = AgentContext(
            session_type="qualifying",
            year=2024,
            race_name="Spa"
        )
        race_control_agent.set_context(qual_ctx)
        qual_prompt = race_control_agent.get_system_prompt()
        
        # Prompts should be different
        assert race_prompt != qual_prompt
        assert "SAFETY CAR" in race_prompt
        assert "VIRTUAL SAFETY CAR" in race_prompt
        assert "TRACK LIMITS" in qual_prompt
    
    def test_get_capabilities(self, race_control_agent):
        """Test getting agent capabilities."""
        capabilities = race_control_agent.get_capabilities()
        
        assert capabilities["name"] == "RaceControlAgent"
        assert "race control" in capabilities["description"].lower()
        assert "get_race_control_messages" in capabilities["tools"]
        assert "get_track_status" in capabilities["tools"]
        assert capabilities["rag_enabled"] is True
        assert capabilities["tools_enabled"] is True
    
    def test_validate_query_comprehensive_keywords(self, race_control_agent):
        """Test query validation with comprehensive keyword coverage."""
        # VSC variations
        assert race_control_agent.validate_query("Virtual safety car ending") is True
        assert race_control_agent.validate_query("VSC deployed") is True
        
        # Penalty types
        assert race_control_agent.validate_query("Stop-go penalty given") is True
        assert race_control_agent.validate_query("Drive through penalty") is True
        assert race_control_agent.validate_query("Reprimand issued") is True
        
        # Incident types
        assert race_control_agent.validate_query("Unsafe release investigation") is True
        assert race_control_agent.validate_query("Causing collision penalty") is True
        
        # DRS
        assert race_control_agent.validate_query("DRS disabled") is True
        assert race_control_agent.validate_query("DRS zone active") is True
        
        # Session control
        assert race_control_agent.validate_query("Session suspended") is True
        assert race_control_agent.validate_query("Race resumed") is True
        
        # Stewards
        assert race_control_agent.validate_query("Stewards decision") is True
        assert race_control_agent.validate_query("FIA investigation") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
