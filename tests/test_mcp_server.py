"""Tests for F1 Data MCP Server."""

import pytest
from src.mcp_server.f1_data_server import F1DataMCPServer


@pytest.fixture
def mcp_server():
    """Fixture providing MCP server instance."""
    return F1DataMCPServer(cache_dir="./test_cache")


class TestF1DataMCPServer:
    """Test suite for F1 Data MCP Server."""

    def test_server_initialization(self, mcp_server):
        """Verify server initializes correctly."""
        assert mcp_server is not None
        assert mcp_server.server is not None
        assert mcp_server.provider is not None

    def test_tool_schemas_exist(self, mcp_server):
        """Verify tool creation methods exist."""
        methods = [
            "_create_get_race_results_tool",
            "_create_get_telemetry_tool",
            "_create_get_qualifying_results_tool",
            "_create_get_season_schedule_tool",
            "_create_get_lap_times_tool",
            "_create_get_pit_stops_tool",
            "_create_get_weather_tool",
            "_create_get_tire_strategy_tool",
            "_create_get_practice_results_tool",
            "_create_get_sprint_results_tool",
            "_create_get_driver_info_tool",
            "_create_get_track_status_tool",
            "_create_get_race_control_tool"
        ]
        for method in methods:
            assert hasattr(mcp_server, method)

    @pytest.mark.asyncio
    async def test_get_race_results(self, mcp_server):
        """Test get_race_results handler."""
        arguments = {
            "year": 2023,
            "round_number": 1,
            "use_realtime": False
        }
        result = await mcp_server.handle_get_race_results(
            arguments
        )
        assert result is not None
        assert len(result) > 0
        assert result[0].type == "text"

    @pytest.mark.asyncio
    async def test_get_season_schedule(self, mcp_server):
        """Test get_season_schedule handler."""
        arguments = {"year": 2024}
        result = await mcp_server.handle_get_season_schedule(
            arguments
        )
        assert result is not None
        assert len(result) > 0
        assert result[0].type == "text"

    @pytest.mark.asyncio
    async def test_get_lap_times(self, mcp_server):
        """Test get_lap_times handler."""
        arguments = {
            "year": 2023,
            "round_number": 1,
            "session_type": "R"
        }
        result = await mcp_server.handle_get_lap_times(
            arguments
        )
        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_get_pit_stops(self, mcp_server):
        """Test get_pit_stops handler."""
        arguments = {
            "year": 2023,
            "round_number": 1
        }
        result = await mcp_server.handle_get_pit_stops(
            arguments
        )
        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_get_weather(self, mcp_server):
        """Test get_weather handler."""
        arguments = {
            "year": 2023,
            "round_number": 1
        }
        result = await mcp_server.handle_get_weather(arguments)
        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_get_tire_strategy(self, mcp_server):
        """Test get_tire_strategy handler."""
        arguments = {
            "year": 2023,
            "round_number": 1
        }
        result = await mcp_server.handle_get_tire_strategy(
            arguments
        )
        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_get_driver_info(self, mcp_server):
        """Test get_driver_info handler."""
        arguments = {
            "year": 2023,
            "round_number": 1
        }
        result = await mcp_server.handle_get_driver_info(
            arguments
        )
        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_get_track_status(self, mcp_server):
        """Test get_track_status handler."""
        arguments = {
            "year": 2023,
            "round_number": 1
        }
        result = await mcp_server.handle_get_track_status(
            arguments
        )
        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_get_race_control(self, mcp_server):
        """Test get_race_control_messages handler."""
        arguments = {
            "year": 2023,
            "round_number": 1
        }
        result = await mcp_server.handle_get_race_control(
            arguments
        )
        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_invalid_year(self, mcp_server):
        """Test handling of invalid year."""
        arguments = {
            "year": 2050,
            "round_number": 1
        }
        result = await mcp_server.handle_get_race_results(
            arguments
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_telemetry_handler(self, mcp_server):
        """Test telemetry handler."""
        arguments = {
            "year": 2023,
            "round_number": 1,
            "driver": "VER"
        }
        result = await mcp_server.handle_get_telemetry(
            arguments
        )
        assert result is not None
        assert len(result) > 0


class TestToolSchemas:
    """Test tool input schemas."""

    def test_race_results_schema(self, mcp_server):
        """Verify race results schema."""
        tool = mcp_server._create_get_race_results_tool()
        assert tool.name == "get_race_results"
        schema = tool.inputSchema
        assert "year" in schema["properties"]
        assert "round_number" in schema["properties"]

    def test_telemetry_schema(self, mcp_server):
        """Verify telemetry schema."""
        tool = mcp_server._create_get_telemetry_tool()
        assert tool.name == "get_telemetry"
        schema = tool.inputSchema
        assert "driver" in schema["properties"]

    def test_lap_times_schema(self, mcp_server):
        """Verify lap times schema."""
        tool = mcp_server._create_get_lap_times_tool()
        assert tool.name == "get_lap_times"
        schema = tool.inputSchema
        assert "session_type" in schema["properties"]

    def test_pit_stops_schema(self, mcp_server):
        """Verify pit stops schema."""
        tool = mcp_server._create_get_pit_stops_tool()
        assert tool.name == "get_pit_stops"
        assert "year" in tool.inputSchema["properties"]

    def test_weather_schema(self, mcp_server):
        """Verify weather schema."""
        tool = mcp_server._create_get_weather_tool()
        assert tool.name == "get_weather"
        assert "year" in tool.inputSchema["properties"]

    def test_tire_strategy_schema(self, mcp_server):
        """Verify tire strategy schema."""
        tool = mcp_server._create_get_tire_strategy_tool()
        assert tool.name == "get_tire_strategy"
        assert "year" in tool.inputSchema["properties"]

    def test_practice_results_schema(self, mcp_server):
        """Verify practice results schema."""
        tool = mcp_server._create_get_practice_results_tool()
        assert tool.name == "get_practice_results"
        schema = tool.inputSchema
        assert "session_type" in schema["properties"]

    def test_sprint_results_schema(self, mcp_server):
        """Verify sprint results schema."""
        tool = mcp_server._create_get_sprint_results_tool()
        assert tool.name == "get_sprint_results"
        assert "year" in tool.inputSchema["properties"]

    def test_driver_info_schema(self, mcp_server):
        """Verify driver info schema."""
        tool = mcp_server._create_get_driver_info_tool()
        assert tool.name == "get_driver_info"
        assert "year" in tool.inputSchema["properties"]

    def test_track_status_schema(self, mcp_server):
        """Verify track status schema."""
        tool = mcp_server._create_get_track_status_tool()
        assert tool.name == "get_track_status"
        assert "year" in tool.inputSchema["properties"]

    def test_race_control_schema(self, mcp_server):
        """Verify race control schema."""
        tool = mcp_server._create_get_race_control_tool()
        assert tool.name == "get_race_control_messages"
        assert "year" in tool.inputSchema["properties"]
