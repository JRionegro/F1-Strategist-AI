"""
Unit Tests for Race Position Agent

Tests the Race Position Agent for race and qualifying sessions.
"""

import pytest
from unittest.mock import Mock

from src.agents.race_position_agent import RacePositionAgent
from src.agents.base_agent import AgentConfig, AgentContext, AgentResponse
from src.llm.provider import LLMProvider
from src.llm.models import LLMResponse


class TestRacePositionAgent:
    """Test Race Position Agent implementation."""

    @pytest.fixture
    def mock_llm_provider(self):
        """Create mock LLM provider."""
        mock_llm = Mock(spec=LLMProvider)

        # Create mock response
        mock_response = LLMResponse(
            content="Verstappen in P1, gap to Hamilton +2.5s. Closing at 0.2s/lap.",
            model="test-model",
            provider="test-provider",
            tokens_input=48,
            tokens_output=32,
            cost_input=0.0048,
            cost_output=0.0032,
            latency_ms=128.0
        )

        # Mock async generate method
        async def mock_generate(*args, **kwargs):
            return mock_response

        mock_llm.generate = mock_generate
        return mock_llm

    @pytest.fixture
    def race_position_agent(self, mock_llm_provider):
        """Create Race Position Agent instance."""
        config = AgentConfig(
            name="RacePositionAgent",
            description="F1 position tracking and overtake analysis",
            llm_provider=mock_llm_provider
        )
        return RacePositionAgent(config)

    @pytest.fixture
    def race_context(self):
        """Create race context."""
        return AgentContext(
            session_type="race",
            year=2024,
            race_name="Silverstone"
        )

    @pytest.fixture
    def qualifying_context(self):
        """Create qualifying context."""
        return AgentContext(
            session_type="qualifying",
            year=2024,
            race_name="Monza"
        )

    def test_race_position_agent_initialization(self, race_position_agent):
        """Test Race Position Agent initialization."""
        assert race_position_agent.config.name == "RacePositionAgent"
        assert race_position_agent.context is None

    def test_get_available_tools(self, race_position_agent):
        """Test Race Position Agent available tools."""
        tools = race_position_agent.get_available_tools()

        assert "get_race_results" in tools
        assert "get_lap_times" in tools
        assert "get_position_data" in tools
        assert "get_session_info" in tools
        assert len(tools) == 4

    def test_validate_query_positions(self, race_position_agent):
        """Test query validation for position queries."""
        assert race_position_agent.validate_query("What's Verstappen's position?") is True
        assert race_position_agent.validate_query("Who is P1?") is True
        assert race_position_agent.validate_query("Race leader analysis") is True
        assert race_position_agent.validate_query("Podium positions") is True

    def test_validate_query_gaps(self, race_position_agent):
        """Test query validation for gap queries."""
        assert race_position_agent.validate_query("What's the gap to the leader?") is True
        assert race_position_agent.validate_query("How far behind is Hamilton?") is True
        assert race_position_agent.validate_query("Gap closing rate") is True

    def test_validate_query_overtaking(self, race_position_agent):
        """Test query validation for overtaking queries."""
        assert race_position_agent.validate_query("Can Leclerc overtake?") is True
        assert race_position_agent.validate_query("Overtaking opportunity") is True
        assert race_position_agent.validate_query("Battle between drivers") is True
        assert race_position_agent.validate_query("Defending position") is True

    def test_validate_query_drs(self, race_position_agent):
        """Test query validation for DRS queries."""
        assert race_position_agent.validate_query("Is DRS available?") is True
        assert race_position_agent.validate_query("Within DRS range") is True
        assert race_position_agent.validate_query("DRS zone effectiveness") is True

    def test_validate_query_strategy(self, race_position_agent):
        """Test query validation for strategy queries."""
        assert race_position_agent.validate_query("Undercut opportunity?") is True
        assert race_position_agent.validate_query("Track position value") is True
        assert race_position_agent.validate_query("Overcut potential") is True

    def test_validate_query_invalid(self, race_position_agent):
        """Test query validation rejects invalid queries."""
        assert race_position_agent.validate_query("") is False
        assert race_position_agent.validate_query("   ") is False
        assert race_position_agent.validate_query("Weather forecast") is False
        assert race_position_agent.validate_query("Telemetry analysis") is False

    def test_get_system_prompt_race_mode(self, race_position_agent, race_context):
        """Test system prompt for race mode."""
        race_position_agent.set_context(race_context)
        prompt = race_position_agent.get_system_prompt()

        assert "Race Position Agent" in prompt
        assert "Silverstone" in prompt
        assert "2024" in prompt
        assert "POSITION TRACKING" in prompt
        assert "GAP ANALYSIS" in prompt
        assert "OVERTAKE OPPORTUNITIES" in prompt
        assert "DRS ZONES" in prompt

    def test_get_system_prompt_qualifying_mode(
        self, race_position_agent, qualifying_context
    ):
        """Test system prompt for qualifying mode."""
        race_position_agent.set_context(qualifying_context)
        prompt = race_position_agent.get_system_prompt()

        assert "Race Position Agent" in prompt
        assert "Monza" in prompt
        assert "2024" in prompt
        assert "GRID POSITION" in prompt
        assert "SESSION PROGRESSION" in prompt
        assert "Q1" in prompt and "Q2" in prompt and "Q3" in prompt

    def test_get_system_prompt_no_context(self, race_position_agent):
        """Test system prompt without context."""
        prompt = race_position_agent.get_system_prompt()

        assert "Race Position Agent" in prompt
        assert "position" in prompt.lower()
        assert "overtake" in prompt.lower()

    @pytest.mark.asyncio
    async def test_query_position_tracking(self, race_position_agent, race_context):
        """Test querying position tracking."""
        race_position_agent.set_context(race_context)

        response = await race_position_agent.query("What position is Verstappen in?")

        assert isinstance(response, AgentResponse)
        assert response.agent_name == "RacePositionAgent"
        assert "p1" in response.response.lower() or "verstappen" in response.response.lower()

    @pytest.mark.asyncio
    async def test_query_gap_analysis(self, race_position_agent, race_context):
        """Test querying gap analysis."""
        race_position_agent.set_context(race_context)

        response = await race_position_agent.query(
            "What's the gap between P1 and P2?"
        )

        assert isinstance(response, AgentResponse)
        assert response.agent_name == "RacePositionAgent"
        assert response.confidence > 0.0

    @pytest.mark.asyncio
    async def test_query_overtake_opportunity(
        self, race_position_agent, race_context
    ):
        """Test querying overtake opportunity."""
        race_position_agent.set_context(race_context)

        response = await race_position_agent.query(
            "Can Hamilton overtake Verstappen?"
        )

        assert isinstance(response, AgentResponse)
        assert response.agent_name == "RacePositionAgent"

    @pytest.mark.asyncio
    async def test_query_drs_effectiveness(self, race_position_agent, race_context):
        """Test querying DRS effectiveness."""
        race_position_agent.set_context(race_context)

        response = await race_position_agent.query(
            "Is Leclerc within DRS range?"
        )

        assert isinstance(response, AgentResponse)
        assert response.agent_name == "RacePositionAgent"

    @pytest.mark.asyncio
    async def test_query_undercut_potential(self, race_position_agent, race_context):
        """Test querying undercut potential."""
        race_position_agent.set_context(race_context)

        response = await race_position_agent.query(
            "Can we undercut the car ahead?"
        )

        assert isinstance(response, AgentResponse)
        assert response.agent_name == "RacePositionAgent"

    @pytest.mark.asyncio
    async def test_query_qualifying_position(
        self, race_position_agent, qualifying_context
    ):
        """Test querying qualifying position."""
        race_position_agent.set_context(qualifying_context)

        response = await race_position_agent.query(
            "What position is needed to advance from Q2?"
        )

        assert isinstance(response, AgentResponse)
        assert response.agent_name == "RacePositionAgent"

    @pytest.mark.asyncio
    async def test_query_with_invalid_query_raises_error(
        self, race_position_agent, race_context
    ):
        """Test that invalid query raises ValueError."""
        race_position_agent.set_context(race_context)

        with pytest.raises(ValueError, match="not suitable"):
            await race_position_agent.query("What's the tire degradation?")

    def test_system_prompt_adapts_to_session_type(self, race_position_agent):
        """Test system prompt adapts based on session type."""
        # Race context
        race_ctx = AgentContext(
            session_type="race",
            year=2024,
            race_name="Spa"
        )
        race_position_agent.set_context(race_ctx)
        race_prompt = race_position_agent.get_system_prompt()

        # Qualifying context
        qual_ctx = AgentContext(
            session_type="qualifying",
            year=2024,
            race_name="Spa"
        )
        race_position_agent.set_context(qual_ctx)
        qual_prompt = race_position_agent.get_system_prompt()

        # Prompts should be different
        assert race_prompt != qual_prompt
        assert "OVERTAKE OPPORTUNITIES" in race_prompt
        assert "DRS ZONES" in race_prompt
        assert "SESSION PROGRESSION" in qual_prompt

    def test_get_capabilities(self, race_position_agent):
        """Test getting agent capabilities."""
        capabilities = race_position_agent.get_capabilities()

        assert capabilities["name"] == "RacePositionAgent"
        assert "position" in capabilities["description"].lower()
        assert "get_race_results" in capabilities["tools"]
        assert "get_position_data" in capabilities["tools"]
        assert capabilities["rag_enabled"] is True
        assert capabilities["tools_enabled"] is True

    def test_validate_query_comprehensive_keywords(self, race_position_agent):
        """Test query validation with comprehensive keyword coverage."""
        # Position numbers
        assert race_position_agent.validate_query("P5 analysis") is True
        assert race_position_agent.validate_query("P10 points position") is True

        # Gap terminology
        assert race_position_agent.validate_query("Interval to next car") is True
        assert race_position_agent.validate_query("Pulling away from pack") is True

        # Battle terminology
        assert race_position_agent.validate_query("Fight for position") is True
        assert race_position_agent.validate_query("Racing wheel to wheel") is True

        # Movement
        assert race_position_agent.validate_query("Climbing through field") is True
        assert race_position_agent.validate_query("Dropped to P7") is True

        # Blue flags
        assert race_position_agent.validate_query("Blue flag situation") is True
        assert race_position_agent.validate_query("Lapping backmarkers") is True

        # Team orders
        assert race_position_agent.validate_query("Team orders to swap") is True
        assert race_position_agent.validate_query("Let teammate through") is True

        # Closing rates
        assert race_position_agent.validate_query("Closing rate analysis") is True
        assert race_position_agent.validate_query("Will catch in 5 laps") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
