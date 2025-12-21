"""Shared fixtures for integration tests."""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from src.agents.base_agent import AgentConfig, AgentContext
from src.agents.strategy_agent import StrategyAgent
from src.agents.weather_agent import WeatherAgent
from src.agents.performance_agent import PerformanceAgent
from src.agents.race_control_agent import RaceControlAgent
from src.agents.race_position_agent import RacePositionAgent
from src.agents.orchestrator import AgentOrchestrator


@pytest.fixture
def mock_mcp_client():
    """Create a mock MCP client with realistic F1 data."""
    client = Mock()
    
    # Mock race results
    client.get_race_results = AsyncMock(return_value={
        "session_info": {
            "event": "Bahrain Grand Prix",
            "year": 2023,
            "circuit": "Bahrain International Circuit"
        },
        "results": [
            {"position": 1, "driver": "VER", "team": "Red Bull", "time": "1:33:56.736"},
            {"position": 2, "driver": "PER", "team": "Red Bull", "time": "+11.987s"},
            {"position": 3, "driver": "ALO", "team": "Aston Martin", "time": "+38.637s"}
        ]
    })
    
    # Mock lap times
    client.get_lap_times = AsyncMock(return_value={
        "driver": "VER",
        "laps": [
            {"lap": 1, "time": "1:35.234", "compound": "MEDIUM"},
            {"lap": 2, "time": "1:34.123", "compound": "MEDIUM"},
            {"lap": 3, "time": "1:33.987", "compound": "MEDIUM"}
        ]
    })
    
    # Mock pit stops
    client.get_pit_stops = AsyncMock(return_value={
        "pit_stops": [
            {"driver": "VER", "lap": 15, "duration": 2.3, "compound_out": "HARD"},
            {"driver": "PER", "lap": 16, "duration": 2.5, "compound_out": "HARD"}
        ]
    })
    
    # Mock weather data
    client.get_weather = AsyncMock(return_value={
        "current": {
            "air_temp": 28.5,
            "track_temp": 42.3,
            "humidity": 45,
            "wind_speed": 3.2,
            "rainfall": False
        },
        "forecast": [
            {"time": "14:00", "rain_probability": 10, "temp": 29.0},
            {"time": "15:00", "rain_probability": 15, "temp": 29.5},
            {"time": "16:00", "rain_probability": 20, "temp": 30.0}
        ]
    })
    
    # Mock race control messages
    client.get_race_control_messages = AsyncMock(return_value={
        "messages": [
            {
                "lap": 1,
                "time": "14:05:23",
                "category": "Flag",
                "message": "GREEN LIGHT - Race start"
            },
            {
                "lap": 12,
                "time": "14:25:45",
                "category": "Flag",
                "message": "YELLOW FLAG - Turn 4"
            }
        ]
    })
    
    # Mock track status
    client.get_track_status = AsyncMock(return_value={
        "status": [
            {"lap": 1, "status": "1", "message": "Track Clear"},
            {"lap": 12, "status": "4", "message": "Yellow Flag"}
        ]
    })
    
    # Mock position data
    client.get_position_data = AsyncMock(return_value={
        "positions": [
            {"lap": 1, "driver": "VER", "position": 1},
            {"lap": 1, "driver": "PER", "position": 2},
            {"lap": 10, "driver": "VER", "position": 1},
            {"lap": 10, "driver": "PER", "position": 2}
        ]
    })
    
    # Mock telemetry
    client.get_telemetry = AsyncMock(return_value={
        "telemetry": [
            {"distance": 0, "speed": 0, "throttle": 0, "brake": 0},
            {"distance": 100, "speed": 150, "throttle": 100, "brake": 0},
            {"distance": 200, "speed": 280, "throttle": 100, "brake": 0}
        ]
    })
    
    return client


@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider for testing."""
    provider = AsyncMock()
    
    # Create a mock response object with content attribute
    class MockLLMResponse:
        def __init__(self, content):
            self.content = content
    
    # Default responses for different agent types
    provider.generate = AsyncMock(return_value=MockLLMResponse(
        content="Based on the data, the optimal strategy is to pit between laps 28-32 for Hard tires. "
                "This provides a good balance between tire life and maintaining track position."
    ))
    
    return provider


@pytest.fixture
def mock_rag_system():
    """Create a mock RAG system for testing."""
    rag = Mock()
    
    # Mock search method (not retrieve)
    class MockSearchResult:
        def __init__(self, content, metadata, score, id_val):
            self.content = content
            self.metadata = metadata
            self.score = score
            self.id = id_val
    
    rag.search = Mock(return_value=[
        MockSearchResult(
            content="Historical data shows Bahrain favors 1-stop strategy",
            metadata={"year": 2022, "event": "Bahrain GP", "source": "Historical Analysis"},
            score=0.92,
            id_val="doc1"
        ),
        MockSearchResult(
            content="Medium tires last 18-22 laps at Bahrain",
            metadata={"year": 2023, "compound": "MEDIUM", "source": "Tire Data"},
            score=0.88,
            id_val="doc2"
        )
    ])
    
    return rag


@pytest.fixture
def strategy_agent(mock_llm_provider, mock_rag_system, mock_mcp_client):
    """Create a StrategyAgent with mocked dependencies."""
    config = AgentConfig(
        name="StrategyAgent",
        description="F1 race and qualifying strategy optimization",
        llm_provider=mock_llm_provider,
        rag_system=mock_rag_system,
        mcp_client=mock_mcp_client
    )
    agent = StrategyAgent(config=config)
    return agent


@pytest.fixture
def weather_agent(mock_llm_provider, mock_rag_system, mock_mcp_client):
    """Create a WeatherAgent with mocked dependencies."""
    config = AgentConfig(
        name="WeatherAgent",
        description="Weather impact analysis for F1 strategy",
        llm_provider=mock_llm_provider,
        rag_system=mock_rag_system,
        mcp_client=mock_mcp_client
    )
    agent = WeatherAgent(config=config)
    return agent


@pytest.fixture
def performance_agent(mock_llm_provider, mock_rag_system, mock_mcp_client):
    """Create a PerformanceAgent with mocked dependencies."""
    config = AgentConfig(
        name="PerformanceAgent",
        description="Lap time and telemetry analysis",
        llm_provider=mock_llm_provider,
        rag_system=mock_rag_system,
        mcp_client=mock_mcp_client
    )
    agent = PerformanceAgent(config=config)
    return agent


@pytest.fixture
def race_control_agent(mock_llm_provider, mock_rag_system, mock_mcp_client):
    """Create a RaceControlAgent with mocked dependencies."""
    config = AgentConfig(
        name="RaceControlAgent",
        description="Track status and race control monitoring",
        llm_provider=mock_llm_provider,
        rag_system=mock_rag_system,
        mcp_client=mock_mcp_client
    )
    agent = RaceControlAgent(config=config)
    return agent


@pytest.fixture
def race_position_agent(mock_llm_provider, mock_rag_system, mock_mcp_client):
    """Create a RacePositionAgent with mocked dependencies."""
    config = AgentConfig(
        name="RacePositionAgent",
        description="Position tracking and overtake analysis",
        llm_provider=mock_llm_provider,
        rag_system=mock_rag_system,
        mcp_client=mock_mcp_client
    )
    agent = RacePositionAgent(config=config)
    return agent


@pytest.fixture
def all_agents(
    strategy_agent,
    weather_agent,
    performance_agent,
    race_control_agent,
    race_position_agent
):
    """Provide all agents for orchestrator testing."""
    return {
        "strategy": strategy_agent,
        "weather": weather_agent,
        "performance": performance_agent,
        "race_control": race_control_agent,
        "position": race_position_agent
    }


@pytest.fixture
def orchestrator(all_agents):
    """Create an AgentOrchestrator with all agents."""
    return AgentOrchestrator(
        strategy_agent=all_agents["strategy"],
        weather_agent=all_agents["weather"],
        performance_agent=all_agents["performance"],
        race_control_agent=all_agents["race_control"],
        race_position_agent=all_agents["position"]
    )


@pytest.fixture
def race_context():
    """Provide a realistic race context for testing."""
    return AgentContext(
        session_type="race",
        year=2023,
        race_name="Bahrain Grand Prix",
        additional_context={
            "current_lap": 25,
            "total_laps": 57,
            "driver": "VER",
            "position": 1,
            "gap_ahead": None,
            "gap_behind": "+5.4s"
        }
    )


@pytest.fixture
def qualifying_context():
    """Provide a realistic qualifying context for testing."""
    return AgentContext(
        session_type="qualifying",
        year=2023,
        race_name="Monaco Grand Prix",
        additional_context={
            "session_part": "Q3",
            "time_remaining": "5:30",
            "driver": "LEC",
            "current_position": 2,
            "best_lap": "1:11.365"
        }
    )
