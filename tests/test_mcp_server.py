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
        assert hasattr(
            mcp_server,
            "_create_get_race_results_tool"
        )
        assert hasattr(
            mcp_server,
            "_create_get_telemetry_tool"
        )
        tools_exist = hasattr(
            mcp_server,
            "_create_get_qualifying_results_tool"
        )
        assert tools_exist
        schedule_exists = hasattr(
            mcp_server,
            "_create_get_season_schedule_tool"
        )
        assert schedule_exists

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
        assert len(result) > 0

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
        """Verify race results schema is correct."""
        tool = mcp_server._create_get_race_results_tool()

        assert tool.name == "get_race_results"
        schema = tool.inputSchema
        assert "year" in schema["properties"]
        assert "round_number" in schema["properties"]
        min_year = schema["properties"]["year"]["minimum"]
        assert min_year == 2018

    def test_telemetry_schema(self, mcp_server):
        """Verify telemetry schema is correct."""
        tool = mcp_server._create_get_telemetry_tool()

        assert tool.name == "get_telemetry"
        schema = tool.inputSchema
        assert "driver" in schema["properties"]
        pattern = schema["properties"]["driver"]["pattern"]
        assert pattern == "^[A-Z]{3}$"

    def test_qualifying_schema(self, mcp_server):
        """Verify qualifying schema is correct."""
        tool_method = (
            mcp_server._create_get_qualifying_results_tool()
        )
        tool = tool_method

        assert tool.name == "get_qualifying_results"
        assert "year" in tool.inputSchema["properties"]

    def test_schedule_schema(self, mcp_server):
        """Verify schedule schema is correct."""
        tool_method = (
            mcp_server._create_get_season_schedule_tool()
        )
        tool = tool_method

        assert tool.name == "get_season_schedule"
        assert "year" in tool.inputSchema["properties"]