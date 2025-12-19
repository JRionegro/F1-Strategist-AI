"""
F1 Data MCP Server.

Model Context Protocol server providing F1 data access
through unified FastF1 and OpenF1 providers.
"""

import logging
from typing import Any, Dict, Optional, Sequence, cast
import json

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    CallToolResult,
    INVALID_PARAMS,
    INTERNAL_ERROR
)
import pandas as pd

from src.data.f1_data_provider import UnifiedF1DataProvider

logger = logging.getLogger(__name__)


class F1DataMCPServer:
    """MCP Server for F1 data access."""

    def __init__(
        self,
        cache_dir: str = "./cache",
        openf1_api_key: Optional[str] = None
    ) -> None:
        """
        Initialize F1 Data MCP Server.

        Args:
            cache_dir: Cache directory for FastF1
            openf1_api_key: OpenF1 API key (optional)
        """
        self.server = Server("f1-data-server")
        self.provider = UnifiedF1DataProvider(
            use_cache=True,
            cache_dir=cache_dir,
            openf1_api_key=openf1_api_key
        )
        self._setup_handlers()
        logger.info("F1DataMCPServer initialized")

    def _setup_handlers(self) -> None:
        """Setup MCP protocol handlers."""
        
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available tools."""
            return [
                self._create_get_race_results_tool(),
                self._create_get_telemetry_tool(),
                self._create_get_qualifying_results_tool(),
                self._create_get_season_schedule_tool(),
            ]

        @self.server.call_tool()
        async def call_tool(
            name: str,
            arguments: Dict[str, Any]
        ) -> Sequence[TextContent]:
            """Handle tool calls."""
            try:
                if name == "get_race_results":
                    return await self.handle_get_race_results(
                        arguments
                    )
                elif name == "get_telemetry":
                    return await self.handle_get_telemetry(
                        arguments
                    )
                elif name == "get_qualifying_results":
                    result = await (
                        self.handle_get_qualifying_results(
                            arguments
                        )
                    )
                    return result
                elif name == "get_season_schedule":
                    result = await (
                        self.handle_get_season_schedule(
                            arguments
                        )
                    )
                    return result
                else:
                    raise ValueError(f"Unknown tool: {name}")
            except Exception as e:
                logger.error(f"Error calling tool {name}: {e}")
                raise

    def _create_get_race_results_tool(self) -> Tool:
        """Create tool for getting race results."""
        return Tool(
            name="get_race_results",
            description=(
                "Get race results for a specific year and round. "
                "Returns driver positions, points, and status."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "year": {
                        "type": "integer",
                        "description": "Season year (e.g., 2024)",
                        "minimum": 2018,
                        "maximum": 2024
                    },
                    "round_number": {
                        "type": "integer",
                        "description": "Race round (1-24)",
                        "minimum": 1,
                        "maximum": 24
                    },
                    "use_realtime": {
                        "type": "boolean",
                        "description": "Use OpenF1 real-time data",
                        "default": False
                    }
                },
                "required": ["year", "round_number"]
            }
        )

    def _create_get_telemetry_tool(self) -> Tool:
        """Create tool for getting telemetry data."""
        return Tool(
            name="get_telemetry",
            description=(
                "Get detailed telemetry data for a driver "
                "in a specific race. Returns speed, throttle, "
                "brake, and gear data."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "year": {
                        "type": "integer",
                        "description": "Season year",
                        "minimum": 2018,
                        "maximum": 2024
                    },
                    "round_number": {
                        "type": "integer",
                        "description": "Race round",
                        "minimum": 1,
                        "maximum": 24
                    },
                    "driver": {
                        "type": "string",
                        "description": (
                            "Driver code (e.g., VER, HAM, LEC)"
                        ),
                        "pattern": "^[A-Z]{3}$"
                    },
                    "use_realtime": {
                        "type": "boolean",
                        "description": "Use real-time data",
                        "default": False
                    }
                },
                "required": ["year", "round_number", "driver"]
            }
        )

    def _create_get_qualifying_results_tool(self) -> Tool:
        """Create tool for getting qualifying results."""
        return Tool(
            name="get_qualifying_results",
            description=(
                "Get qualifying session results. "
                "Returns Q1, Q2, Q3 times and grid positions."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "year": {
                        "type": "integer",
                        "description": "Season year",
                        "minimum": 2018,
                        "maximum": 2024
                    },
                    "round_number": {
                        "type": "integer",
                        "description": "Race round",
                        "minimum": 1,
                        "maximum": 24
                    },
                    "use_realtime": {
                        "type": "boolean",
                        "description": "Use real-time data",
                        "default": False
                    }
                },
                "required": ["year", "round_number"]
            }
        )

    def _create_get_season_schedule_tool(self) -> Tool:
        """Create tool for getting season schedule."""
        return Tool(
            name="get_season_schedule",
            description=(
                "Get complete season calendar. "
                "Returns race dates, locations, and circuit info."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "year": {
                        "type": "integer",
                        "description": "Season year",
                        "minimum": 2018,
                        "maximum": 2024
                    }
                },
                "required": ["year"]
            }
        )

    async def handle_get_race_results(
        self,
        arguments: Dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle get_race_results tool call."""
        try:
            year = arguments["year"]
            round_number = arguments["round_number"]
            use_realtime = arguments.get("use_realtime", False)

            results = self.provider.get_race_results(
                year=year,
                round_number=round_number,
                use_realtime=use_realtime
            )

            data = self._dataframe_to_dict(results)

            return [
                TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )
            ]
        except Exception as e:
            error_msg = f"Error getting race results: {str(e)}"
            logger.error(error_msg)
            return [
                TextContent(
                    type="text",
                    text=error_msg
                )
            ]

    async def handle_get_telemetry(
        self,
        arguments: Dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle get_telemetry tool call."""
        try:
            year = arguments["year"]
            round_number = arguments["round_number"]
            driver = arguments["driver"]
            use_realtime = arguments.get("use_realtime", False)

            telemetry = self.provider.get_telemetry(
                year=year,
                round_number=round_number,
                driver=driver,
                use_realtime=use_realtime
            )

            if telemetry.empty:
                msg = (
                    f"No telemetry data found for {driver} "
                    f"in {year} R{round_number}"
                )
                return [TextContent(type="text", text=msg)]

            sample = telemetry.head(100)
            data = self._dataframe_to_dict(sample)

            return [
                TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )
            ]
        except Exception as e:
            error_msg = f"Error getting telemetry: {str(e)}"
            logger.error(error_msg)
            return [TextContent(type="text", text=error_msg)]

    async def handle_get_qualifying_results(
        self,
        arguments: Dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle get_qualifying_results tool call."""
        try:
            year = arguments["year"]
            round_number = arguments["round_number"]
            use_realtime = arguments.get("use_realtime", False)

            results = self.provider.get_qualifying_results(
                year=year,
                round_number=round_number,
                use_realtime=use_realtime
            )

            data = self._dataframe_to_dict(results)

            return [
                TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )
            ]
        except Exception as e:
            error_msg = (
                f"Error getting qualifying results: {str(e)}"
            )
            logger.error(error_msg)
            return [TextContent(type="text", text=error_msg)]

    async def handle_get_season_schedule(
        self,
        arguments: Dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle get_season_schedule tool call."""
        try:
            year = arguments["year"]

            schedule = self.provider.get_season_schedule(
                year=year
            )

            data = self._dataframe_to_dict(schedule)

            return [
                TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )
            ]
        except Exception as e:
            error_msg = (
                f"Error getting season schedule: {str(e)}"
            )
            logger.error(error_msg)
            return [TextContent(type="text", text=error_msg)]

    def _dataframe_to_dict(
        self,
        df: pd.DataFrame
    ) -> Sequence[Dict[str, Any]]:
        """Convert DataFrame to dictionary."""
        return cast(
            Sequence[Dict[str, Any]],
            df.to_dict(orient="records")
        )

    async def run(self):
        """Run the MCP server using stdio transport."""
        logger.info("Starting F1 Data MCP Server")
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def main():
    """Main entry point."""
    server = F1DataMCPServer()
    await server.run()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())