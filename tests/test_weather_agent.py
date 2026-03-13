"""
Unit Tests for Weather Agent

Tests the Weather Agent for both race and qualifying modes.
"""

import pytest
from unittest.mock import Mock

from src.agents.weather_agent import WeatherAgent
from src.agents.base_agent import AgentConfig, AgentContext, AgentResponse
from src.llm.provider import LLMProvider
from src.llm.models import LLMResponse


class TestWeatherAgent:
    """Test Weather Agent implementation."""

    @pytest.fixture
    def mock_llm_provider(self):
        """Create mock LLM provider."""
        mock_llm = Mock(spec=LLMProvider)

        # Create mock response
        mock_response = LLMResponse(
            content="Rain expected in 15 minutes. Recommend intermediate tires.",
            model="test-model",
            provider="test-provider",
            tokens_input=40,
            tokens_output=25,
            cost_input=0.004,
            cost_output=0.0025,
            latency_ms=120.0
        )

        # Mock async generate method
        async def mock_generate(*args, **kwargs):
            return mock_response

        mock_llm.generate = mock_generate
        return mock_llm

    @pytest.fixture
    def weather_agent(self, mock_llm_provider):
        """Create Weather Agent instance."""
        config = AgentConfig(
            name="WeatherAgent",
            description="F1 weather impact and timing analysis",
            llm_provider=mock_llm_provider
        )
        return WeatherAgent(config)

    @pytest.fixture
    def race_context(self):
        """Create race context."""
        return AgentContext(
            session_type="race",
            year=2024,
            race_name="Spa-Francorchamps"
        )

    @pytest.fixture
    def qualifying_context(self):
        """Create qualifying context."""
        return AgentContext(
            session_type="qualifying",
            year=2024,
            race_name="Silverstone"
        )

    def test_weather_agent_initialization(self, weather_agent):
        """Test Weather Agent initialization."""
        assert weather_agent.config.name == "WeatherAgent"
        assert weather_agent.context is None

    def test_get_available_tools(self, weather_agent):
        """Test Weather Agent available tools."""
        tools = weather_agent.get_available_tools()

        assert "get_weather" in tools
        assert "get_track_status" in tools
        assert "get_session_info" in tools
        assert "get_lap_times" in tools
        assert len(tools) == 4

    def test_validate_query_rain(self, weather_agent):
        """Test query validation for rain queries."""
        assert weather_agent.validate_query("Will it rain?") is True
        assert weather_agent.validate_query("Rain forecast for the race") is True
        assert weather_agent.validate_query("Is it going to be wet?") is True

    def test_validate_query_temperature(self, weather_agent):
        """Test query validation for temperature queries."""
        assert weather_agent.validate_query("What's the track temperature?") is True
        assert weather_agent.validate_query("Temperature forecast") is True
        assert weather_agent.validate_query("How hot is the track?") is True

    def test_validate_query_track_conditions(self, weather_agent):
        """Test query validation for track condition queries."""
        assert weather_agent.validate_query("Are track conditions improving?") is True
        assert weather_agent.validate_query("Is the track drying?") is True
        assert weather_agent.validate_query("Track surface grip level") is True

    def test_validate_query_timing(self, weather_agent):
        """Test query validation for timing queries."""
        assert weather_agent.validate_query("Should we go out now or wait?") is True
        assert weather_agent.validate_query("What's the optimal timing window?") is True
        assert weather_agent.validate_query("When to go out in Q3?") is True

    def test_validate_query_wind(self, weather_agent):
        """Test query validation for wind queries."""
        assert weather_agent.validate_query("What's the wind speed?") is True
        assert weather_agent.validate_query("Wind impact on lap times") is True

    def test_validate_query_invalid(self, weather_agent):
        """Test query validation rejects invalid queries."""
        assert weather_agent.validate_query("") is False
        assert weather_agent.validate_query("   ") is False
        assert weather_agent.validate_query("What's the best tire strategy?") is False
        assert weather_agent.validate_query("Driver performance analysis") is False

    def test_get_system_prompt_race_mode(self, weather_agent, race_context):
        """Test system prompt for race mode."""
        weather_agent.set_context(race_context)
        prompt = weather_agent.get_system_prompt()

        assert "Weather Agent" in prompt
        assert "Spa-Francorchamps" in prompt
        assert "2024" in prompt
        assert "RAIN PREDICTION" in prompt
        assert "TIRE RECOMMENDATIONS" in prompt
        assert "TRACK CONDITIONS" in prompt

    def test_get_system_prompt_qualifying_mode(self, weather_agent, qualifying_context):
        """Test system prompt for qualifying mode."""
        weather_agent.set_context(qualifying_context)
        prompt = weather_agent.get_system_prompt()

        assert "Weather Agent" in prompt
        assert "Silverstone" in prompt
        assert "2024" in prompt
        assert "IMMINENT RAIN RISK" in prompt
        assert "TRACK EVOLUTION" in prompt
        assert "TIMING STRATEGY" in prompt
        assert "GO/WAIT" in prompt

    def test_get_system_prompt_no_context(self, weather_agent):
        """Test system prompt without context."""
        prompt = weather_agent.get_system_prompt()

        assert "Weather Agent" in prompt
        assert "weather" in prompt.lower()
        assert "temperature" in prompt.lower()

    @pytest.mark.asyncio
    async def test_query_rain_prediction(self, weather_agent, race_context):
        """Test querying rain prediction."""
        weather_agent.set_context(race_context)

        response = await weather_agent.query("Will it rain during the race?")

        assert isinstance(response, AgentResponse)
        assert response.agent_name == "WeatherAgent"
        assert "rain" in response.response.lower() or "15 minutes" in response.response

    @pytest.mark.asyncio
    async def test_query_track_conditions(self, weather_agent, race_context):
        """Test querying track conditions."""
        weather_agent.set_context(race_context)

        response = await weather_agent.query("Is the track drying?")

        assert isinstance(response, AgentResponse)
        assert response.agent_name == "WeatherAgent"
        assert response.confidence > 0.0

    @pytest.mark.asyncio
    async def test_query_qualifying_timing(self, weather_agent, qualifying_context):
        """Test querying qualifying timing window."""
        weather_agent.set_context(qualifying_context)

        response = await weather_agent.query(
            "Should we go out now or wait for better conditions?"
        )

        assert isinstance(response, AgentResponse)
        assert response.agent_name == "WeatherAgent"

    @pytest.mark.asyncio
    async def test_query_tire_recommendation(self, weather_agent, race_context):
        """Test querying tire recommendation based on weather."""
        weather_agent.set_context(race_context)

        response = await weather_agent.query(
            "Should we use intermediates or full wets?"
        )

        assert isinstance(response, AgentResponse)
        assert response.agent_name == "WeatherAgent"

    @pytest.mark.asyncio
    async def test_query_with_invalid_query_raises_error(
        self, weather_agent, race_context
    ):
        """Test that invalid query raises ValueError."""
        weather_agent.set_context(race_context)

        with pytest.raises(ValueError, match="not suitable"):
            await weather_agent.query("Who won the championship?")

    def test_system_prompt_adapts_to_session_type(self, weather_agent):
        """Test system prompt adapts based on session type."""
        # Race context
        race_ctx = AgentContext(
            session_type="race",
            year=2024,
            race_name="Spa"
        )
        weather_agent.set_context(race_ctx)
        race_prompt = weather_agent.get_system_prompt()

        # Qualifying context
        qual_ctx = AgentContext(
            session_type="qualifying",
            year=2024,
            race_name="Spa"
        )
        weather_agent.set_context(qual_ctx)
        qual_prompt = weather_agent.get_system_prompt()

        # Prompts should be different
        assert race_prompt != qual_prompt
        assert "RAIN PREDICTION" in race_prompt
        assert "IMMINENT RAIN RISK" in qual_prompt
        assert "GO/WAIT" in qual_prompt

    def test_get_capabilities(self, weather_agent):
        """Test getting agent capabilities."""
        capabilities = weather_agent.get_capabilities()

        assert capabilities["name"] == "WeatherAgent"
        assert "weather" in capabilities["description"].lower()
        assert "get_weather" in capabilities["tools"]
        assert "get_track_status" in capabilities["tools"]
        assert capabilities["rag_enabled"] is True
        assert capabilities["tools_enabled"] is True

    def test_validate_query_comprehensive_keywords(self, weather_agent):
        """Test query validation with comprehensive keyword coverage."""
        # Rain-related
        assert weather_agent.validate_query("Wet conditions expected?") is True
        assert weather_agent.validate_query("Damp track surface") is True

        # Tire-related weather
        assert weather_agent.validate_query("Need intermediate tires?") is True
        assert weather_agent.validate_query("Switch to wets?") is True

        # Visibility
        assert weather_agent.validate_query("Visibility in the spray") is True
        assert weather_agent.validate_query("Fog on track") is True

        # Temperature
        assert weather_agent.validate_query("Humid conditions impact") is True

        # Track drying
        assert weather_agent.validate_query("Track drainage effectiveness") is True
        assert weather_agent.validate_query("Puddles forming?") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
