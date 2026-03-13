"""
Tests for F1 Data MCP Server.

Tests all MCP server tools including new OpenF1 APIs.
Uses OpenF1 as primary data source for 2023+ seasons.
"""

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
            "_create_get_race_control_tool",
            "_create_get_positions_tool",
            "_create_get_intervals_tool",
            "_create_get_location_tool",
            "_create_get_team_radio_tool",
            "_create_get_meetings_tool",
            "_create_get_overtakes_tool"
        ]
        for method in methods:
            assert hasattr(mcp_server, method)

    @pytest.mark.asyncio
    async def test_get_race_results_openf1(self, mcp_server):
        """
        Test get_race_results with OpenF1 (2024 season).

        OpenF1 is primary data source for 2023+.
        """
        arguments = {
            "year": 2024,
            "round_number": 1,
            "use_realtime": True
        }
        result = await mcp_server.handle_get_race_results(arguments)
        assert result is not None
        assert len(result) > 0
        assert result[0].type == "text"

    @pytest.mark.asyncio
    async def test_get_season_schedule(self, mcp_server):
        """Test get_season_schedule handler with 2024 season."""
        arguments = {"year": 2024}
        result = await mcp_server.handle_get_season_schedule(arguments)
        assert result is not None
        assert len(result) > 0
        assert result[0].type == "text"

    @pytest.mark.asyncio
    async def test_get_lap_times_openf1(self, mcp_server):
        """
        Test get_lap_times with OpenF1 (2024 season).

        OpenF1 provides lap times via /laps endpoint.
        """
        arguments = {
            "year": 2024,
            "round_number": 1,
            "session_type": "R"
        }
        result = await mcp_server.handle_get_lap_times(arguments)
        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_get_pit_stops_openf1(self, mcp_server):
        """
        Test get_pit_stops with OpenF1 (2024 season).

        OpenF1 provides pit stops via /pit endpoint.
        """
        arguments = {
            "year": 2024,
            "round_number": 1
        }
        result = await mcp_server.handle_get_pit_stops(arguments)
        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_get_qualifying_results_openf1(self, mcp_server):
        """
        Test get_qualifying_results with OpenF1 (2024 season).

        OpenF1 provides qualifying via /sessions and /laps endpoints.
        """
        arguments = {
            "year": 2024,
            "round_number": 1
        }
        result = await mcp_server.handle_get_qualifying_results(
            arguments
        )
        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_get_practice_results_openf1(self, mcp_server):
        """
        Test get_practice_results with OpenF1 (2024 season).

        OpenF1 provides practice via /sessions and /laps endpoints.
        """
        arguments = {
            "year": 2024,
            "round_number": 1,
            "session_type": "FP1"
        }
        result = await mcp_server.handle_get_practice_results(
            arguments
        )
        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_get_sprint_results_openf1(self, mcp_server):
        """
        Test get_sprint_results with OpenF1 (2024 season).

        OpenF1 provides sprint via /sessions and /laps endpoints.
        """
        arguments = {
            "year": 2024,
            "round_number": 4
        }
        result = await mcp_server.handle_get_sprint_results(
            arguments
        )
        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_get_weather_openf1(self, mcp_server):
        """
        Test get_weather with OpenF1 (2024 season).

        OpenF1 provides weather via /weather endpoint.
        """
        arguments = {
            "year": 2024,
            "round_number": 1
        }
        result = await mcp_server.handle_get_weather(arguments)
        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_get_tire_strategy_openf1(self, mcp_server):
        """
        Test get_tire_strategy with OpenF1 (2024 season).

        OpenF1 provides stints via /stints endpoint.
        """
        arguments = {
            "year": 2024,
            "round_number": 1
        }
        result = await mcp_server.handle_get_tire_strategy(arguments)
        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_get_driver_info_openf1(self, mcp_server):
        """
        Test get_driver_info with OpenF1 (2024 season).

        OpenF1 provides drivers via /drivers endpoint.
        """
        arguments = {
            "year": 2024,
            "round_number": 1
        }
        result = await mcp_server.handle_get_driver_info(arguments)
        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_get_track_status(self, mcp_server):
        """Test get_track_status handler."""
        arguments = {
            "year": 2024,
            "round_number": 1
        }
        result = await mcp_server.handle_get_track_status(arguments)
        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_get_race_control_openf1(self, mcp_server):
        """
        Test get_race_control_messages with OpenF1 (2024 season).

        OpenF1 provides race control via /race_control endpoint.
        """
        arguments = {
            "year": 2024,
            "round_number": 1
        }
        result = await mcp_server.handle_get_race_control(arguments)
        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_get_positions_openf1(self, mcp_server):
        """
        Test get_positions with OpenF1 (NEW API).

        OpenF1 /position endpoint provides real race positions.
        CRITICAL: Use this instead of calculating from lap times.
        """
        arguments = {
            "session_key": 9165,  # Saudi Arabia 2024
        }
        result = await mcp_server.handle_get_positions(arguments)
        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_get_intervals_openf1(self, mcp_server):
        """
        Test get_intervals with OpenF1 (NEW API).

        OpenF1 /intervals endpoint provides time gaps.
        """
        arguments = {
            "session_key": 9165,  # Saudi Arabia 2024
        }
        result = await mcp_server.handle_get_intervals(arguments)
        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_get_location_openf1(self, mcp_server):
        """
        Test get_location with OpenF1 (NEW API).

        OpenF1 /location endpoint provides GPS coordinates.
        """
        arguments = {
            "session_key": 9165,  # Saudi Arabia 2024
            "driver_number": 1
        }
        result = await mcp_server.handle_get_location(arguments)
        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_get_team_radio_openf1(self, mcp_server):
        """
        Test get_team_radio with OpenF1 (NEW API).

        OpenF1 /team_radio endpoint provides radio messages.
        """
        arguments = {
            "session_key": 9165,  # Saudi Arabia 2024
            "driver_number": 1
        }
        result = await mcp_server.handle_get_team_radio(arguments)
        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_get_meetings_openf1(self, mcp_server):
        """
        Test get_meetings with OpenF1 (NEW API).

        OpenF1 /meetings endpoint provides race weekend info.
        """
        arguments = {
            "year": 2024
        }
        result = await mcp_server.handle_get_meetings(arguments)
        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_get_overtakes_openf1(self, mcp_server):
        """
        Test get_overtakes with OpenF1 (NEW API).

        OpenF1 /overtakes endpoint provides overtaking maneuvers.
        """
        arguments = {
            "session_key": 9165,  # Saudi Arabia 2024
        }
        result = await mcp_server.handle_get_overtakes(arguments)
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
    async def test_telemetry_handler_openf1(self, mcp_server):
        """
        Test telemetry handler with OpenF1 (2024 season).

        OpenF1 provides telemetry via /car_data endpoint.
        """
        arguments = {
            "year": 2024,
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

    def test_positions_schema(self, mcp_server):
        """Verify positions schema (OpenF1 NEW)."""
        tool = mcp_server._create_get_positions_tool()
        assert tool.name == "get_positions"
        assert "session_key" in tool.inputSchema["properties"]

    def test_intervals_schema(self, mcp_server):
        """Verify intervals schema (OpenF1 NEW)."""
        tool = mcp_server._create_get_intervals_tool()
        assert tool.name == "get_intervals"
        assert "session_key" in tool.inputSchema["properties"]

    def test_location_schema(self, mcp_server):
        """Verify location schema (OpenF1 NEW)."""
        tool = mcp_server._create_get_location_tool()
        assert tool.name == "get_location"
        assert "session_key" in tool.inputSchema["properties"]

    def test_team_radio_schema(self, mcp_server):
        """Verify team radio schema (OpenF1 NEW)."""
        tool = mcp_server._create_get_team_radio_tool()
        assert tool.name == "get_team_radio"
        assert "session_key" in tool.inputSchema["properties"]

    def test_meetings_schema(self, mcp_server):
        """Verify meetings schema (OpenF1 NEW)."""
        tool = mcp_server._create_get_meetings_tool()
        assert tool.name == "get_meetings"
        assert "year" in tool.inputSchema["properties"]

    def test_overtakes_schema(self, mcp_server):
        """Verify overtakes schema (OpenF1 NEW)."""
        tool = mcp_server._create_get_overtakes_tool()
        assert tool.name == "get_overtakes"
        assert "session_key" in tool.inputSchema["properties"]
