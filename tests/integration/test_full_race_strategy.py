"""Integration Test 1: Full Race Strategy Analysis.

Tests the complete system with all 5 agents working together
to analyze a race scenario and provide strategic recommendations.

Scenario: Mid-race strategy decision at Bahrain GP
- Current lap: 25/57
- Leader: Verstappen on Medium tires (15 laps old)
- Weather: Clear, slight temperature increase expected
- No safety car or incidents
- All agents must contribute to comprehensive strategy analysis
"""

import pytest
from unittest.mock import AsyncMock


@pytest.mark.asyncio
class TestFullRaceStrategyAnalysis:
    """Test complete race strategy analysis with all agents."""
    
    async def test_orchestrator_coordinates_all_agents(
        self,
        orchestrator,
        race_context
    ):
        """Test orchestrator routes query to all relevant agents."""
        query = (
            "What is the optimal pit strategy for Verstappen? "
            "He's leading on 15-lap old Mediums, lap 25/57."
        )
        
        # Execute query through orchestrator
        result = await orchestrator.query(query,
            context=race_context
        )
        
        # Verify orchestrator returned a response
        assert result is not None
        assert hasattr(result, 'primary_response')
        assert hasattr(result, 'agents_used')
        assert hasattr(result, 'confidence')
        assert result.primary_response is not None
        
        # Verify multiple agents were consulted
        agents_used = result.agents_used
        assert len(agents_used) >= 2  # At least Strategy + one more
        assert "strategy" in [a.lower() for a in agents_used]
    
    async def test_strategy_agent_provides_pit_window(
        self,
        strategy_agent,
        race_context
    ):
        """Test StrategyAgent calculates optimal pit window."""
        query = "When should Verstappen pit? Currently lap 25, Mediums 15 laps old."
        
        result = await strategy_agent.query(query,
            context=race_context
        )
        
        # Verify response structure
        assert result is not None
        assert hasattr(result, 'response')
        assert result.response is not None
        assert result.confidence > 0.0
        
        # Response should mention pit window or lap numbers
        response_text = result.response.lower()
        assert any(word in response_text for word in ["pit", "stop", "lap", "window"])
    
    async def test_weather_agent_assesses_conditions(
        self,
        weather_agent,
        race_context
    ):
        """Test WeatherAgent evaluates weather impact on strategy."""
        query = "Will weather affect tire strategy for the rest of the race?"
        
        result = await weather_agent.query(query,
            context=race_context
        )
        
        assert result is not None
        
        assert hasattr(result, 'response')
        
        assert result.response is not None
        assert result.confidence > 0.7
        
        # Should mention temperature, conditions, or tires
        response_text = result.response.lower()
        assert any(
            word in response_text
            for word in ["temperature", "weather", "tire", "condition"]
        )
    
    async def test_performance_agent_analyzes_pace(
        self,
        performance_agent,
        race_context
    ):
        """Test PerformanceAgent evaluates current pace."""
        query = "How is Verstappen's pace compared to his teammates?"
        
        result = await performance_agent.query(query,
            context=race_context
        )
        
        assert result is not None
        
        assert hasattr(result, 'response')
        
        assert result.response is not None
        assert result.confidence > 0.6
        
        # Should mention pace, lap times, or performance
        response_text = result.response.lower()
        assert any(
            word in response_text
            for word in ["pace", "lap", "time", "fast", "slow"]
        )
    
    async def test_race_control_agent_checks_flags(
        self,
        race_control_agent,
        race_context
    ):
        """Test RaceControlAgent monitors track status."""
        query = "Are there any flags or track issues affecting strategy?"
        
        result = await race_control_agent.query(query,
            context=race_context
        )
        
        assert result is not None
        
        assert hasattr(result, 'response')
        
        assert result.response is not None
        
        # Should mention flags, safety, or track status
        response_text = result.response.lower()
        assert any(
            word in response_text
            for word in ["flag", "track", "clear", "yellow", "safety"]
        )
    
    async def test_position_agent_analyzes_gaps(
        self,
        race_position_agent,
        race_context
    ):
        """Test RacePositionAgent evaluates position and gaps."""
        query = "What is the gap to second place? Safe to pit?"
        
        result = await race_position_agent.query(query,
            context=race_context
        )
        
        assert result is not None
        
        assert hasattr(result, 'response')
        
        assert result.response is not None
        
        # Should mention gap, position, or time
        response_text = result.response.lower()
        assert any(
            word in response_text
            for word in ["gap", "position", "second", "behind", "ahead"]
        )
    
    async def test_agents_access_mcp_tools(
        self,
        strategy_agent,
        mock_mcp_client,
        race_context
    ):
        """Test agents successfully call MCP tools for data."""
        query = "Analyze pit stop strategy based on historical data."
        
        await strategy_agent.query(query, context=race_context)
        
        # Verify MCP client was called
        assert mock_mcp_client.get_pit_stops.called or \
               mock_mcp_client.get_lap_times.called
    
    async def test_agents_use_rag_system(
        self,
        strategy_agent,
        mock_rag_system,
        race_context
    ):
        """Test agents retrieve historical context from RAG."""
        query = "What worked well in previous Bahrain races?"
        
        await strategy_agent.query(query, context=race_context)
        
        # Verify RAG was queried
        assert mock_rag_system.search.called
    
    async def test_multi_agent_coordination(
        self,
        orchestrator,
        race_context
    ):
        """Test multiple agents coordinate on complex query."""
        query = (
            "Complete race analysis: optimal pit strategy considering "
            "weather forecast, current pace, track position, and any incidents."
        )
        
        result = await orchestrator.query(query,
            context=race_context
        )
        
        # Should consult multiple agents for this complex query
        agents_used = result.agents_used
        assert len(agents_used) >= 3  # Strategy + Weather + at least one more
        
        # Should have high overall confidence
        assert result.confidence > 0.65
    
    async def test_response_time_under_2_seconds(
        self,
        orchestrator,
        race_context
    ):
        """Test system responds within performance target (<2s)."""
        import time
        
        query = "What is the optimal strategy right now?"
        
        start_time = time.time()
        result = await orchestrator.query(query,
            context=race_context
        )
        elapsed = time.time() - start_time
        
        # Should respond quickly (mocked LLM is instant)
        assert elapsed < 2.0
        assert result is not None
    
    async def test_comprehensive_strategy_response(
        self,
        orchestrator,
        race_context
    ):
        """Test orchestrator provides comprehensive analysis."""
        query = (
            "Provide complete race strategy: when to pit, "
            "which tires, risks, and alternatives."
        )
        
        result = await orchestrator.query(query,
            context=race_context
        )
        
        assert result is not None
        
        assert hasattr(result, 'primary_response')
        
        assert result.primary_response is not None
        
        # Response should be substantial
        response_text = result.primary_response
        assert len(response_text) > 50  # Not just a one-liner
        
        # Should include strategy-related content
        response_lower = response_text.lower()
        strategy_keywords = ["pit", "tire", "lap", "strategy", "stop"]
        assert any(keyword in response_lower for keyword in strategy_keywords)
    
    async def test_agents_handle_race_session_type(
        self,
        strategy_agent,
        race_context
    ):
        """Test agents correctly handle RACE session type."""
        # Verify session type is RACE
        assert race_context.session_type == "race"
        
        query = "Pit strategy for Verstappen?"
        result = await strategy_agent.query(query, context=race_context)
        
        # Agent should successfully process race-specific query
        assert result is not None
        assert hasattr(result, 'response')
        assert result.response is not None
        
        # Response should be race-focused (not qualifying)
        response_text = result.response.lower()
        race_terms = ["race", "pit", "stop", "stint", "tire"]
        assert any(term in response_text for term in race_terms)


@pytest.mark.asyncio
class TestRealDataIntegration:
    """Test integration with real F1 data structures."""
    
    async def test_handles_real_pit_stop_data(
        self,
        strategy_agent,
        mock_mcp_client,
        race_context
    ):
        """Test agent processes realistic pit stop data."""
        # Set up realistic pit stop data
        mock_mcp_client.get_pit_stops.return_value = {
            "pit_stops": [
                {
                    "driver": "VER",
                    "lap": 15,
                    "duration": 2.3,
                    "compound_in": "MEDIUM",
                    "compound_out": "HARD",
                    "total_laps_on_compound_in": 15
                },
                {
                    "driver": "PER",
                    "lap": 16,
                    "duration": 2.5,
                    "compound_in": "MEDIUM",
                    "compound_out": "HARD",
                    "total_laps_on_compound_in": 16
                }
            ]
        }
        
        query = "Analyze recent pit stops."
        result = await strategy_agent.query(query, context=race_context)
        
        assert result is not None
        
        assert hasattr(result, 'response')
        
        assert result.response is not None
        assert mock_mcp_client.get_pit_stops.called
    
    async def test_handles_real_weather_data(
        self,
        weather_agent,
        mock_mcp_client,
        race_context
    ):
        """Test agent processes realistic weather data."""
        mock_mcp_client.get_weather.return_value = {
            "current": {
                "air_temp": 28.5,
                "track_temp": 42.3,
                "humidity": 45,
                "wind_speed": 3.2,
                "wind_direction": 180,
                "pressure": 1013.2,
                "rainfall": False
            },
            "forecast": [
                {
                    "time": "14:00",
                    "rain_probability": 10,
                    "air_temp": 29.0,
                    "track_temp": 43.0
                },
                {
                    "time": "15:00",
                    "rain_probability": 15,
                    "air_temp": 29.5,
                    "track_temp": 44.0
                }
            ]
        }
        
        query = "Weather impact on tire strategy?"
        result = await weather_agent.query(query, context=race_context)
        
        assert result is not None
        
        assert hasattr(result, 'response')
        
        assert result.response is not None
        assert mock_mcp_client.get_weather.called
    
    async def test_handles_real_lap_time_data(
        self,
        performance_agent,
        mock_mcp_client,
        race_context
    ):
        """Test agent processes realistic lap time data."""
        mock_mcp_client.get_lap_times.return_value = {
            "driver": "VER",
            "laps": [
                {
                    "lap": 23,
                    "time": "1:34.123",
                    "compound": "MEDIUM",
                    "tire_life": 13,
                    "is_personal_best": False
                },
                {
                    "lap": 24,
                    "time": "1:34.456",
                    "compound": "MEDIUM",
                    "tire_life": 14,
                    "is_personal_best": False
                },
                {
                    "lap": 25,
                    "time": "1:34.789",
                    "compound": "MEDIUM",
                    "tire_life": 15,
                    "is_personal_best": False
                }
            ],
            "average_lap_time": "1:34.456",
            "degradation_rate": 0.15
        }
        
        query = "Is pace degrading?"
        result = await performance_agent.query(query, context=race_context)
        
        assert result is not None
        
        assert hasattr(result, 'response')
        
        assert result.response is not None
        assert mock_mcp_client.get_lap_times.called



