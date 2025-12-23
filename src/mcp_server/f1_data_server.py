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
from mcp.types import Tool, TextContent
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
                self._create_get_lap_times_tool(),
                self._create_get_pit_stops_tool(),
                self._create_get_weather_tool(),
                self._create_get_tire_strategy_tool(),
                self._create_get_practice_results_tool(),
                self._create_get_sprint_results_tool(),
                self._create_get_driver_info_tool(),
                self._create_get_track_status_tool(),
                self._create_get_race_control_tool(),
                self._create_get_positions_tool(),
                self._create_get_intervals_tool(),
                self._create_get_location_tool(),
                self._create_get_team_radio_tool(),
                self._create_get_meetings_tool(),
                self._create_get_overtakes_tool(),
            ]

        @self.server.call_tool()
        async def call_tool(
            name: str,
            arguments: Dict[str, Any]
        ) -> Sequence[TextContent]:
            """Handle tool calls."""
            try:
                handlers = {
                    "get_race_results": (
                        self.handle_get_race_results
                    ),
                    "get_telemetry": self.handle_get_telemetry,
                    "get_qualifying_results": (
                        self.handle_get_qualifying_results
                    ),
                    "get_season_schedule": (
                        self.handle_get_season_schedule
                    ),
                    "get_lap_times": self.handle_get_lap_times,
                    "get_pit_stops": self.handle_get_pit_stops,
                    "get_weather": self.handle_get_weather,
                    "get_tire_strategy": (
                        self.handle_get_tire_strategy
                    ),
                    "get_practice_results": (
                        self.handle_get_practice_results
                    ),
                    "get_sprint_results": (
                        self.handle_get_sprint_results
                    ),
                    "get_driver_info": (
                        self.handle_get_driver_info
                    ),
                    "get_track_status": (
                        self.handle_get_track_status
                    ),
                    "get_race_control_messages": (
                        self.handle_get_race_control
                    ),
                    "get_positions": (
                        self.handle_get_positions
                    ),
                    "get_intervals": (
                        self.handle_get_intervals
                    ),
                    "get_location": (
                        self.handle_get_location
                    ),
                    "get_team_radio": (
                        self.handle_get_team_radio
                    ),
                    "get_meetings": (
                        self.handle_get_meetings
                    ),
                    "get_overtakes": (
                        self.handle_get_overtakes
                    ),
                }

                if name in handlers:
                    return await handlers[name](arguments)
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
                        "description": "Use OpenF1 real-time",
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
                "Get detailed telemetry data for a driver. "
                "Returns speed, throttle, brake, gear data."
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
                        "description": "Driver code (VER, HAM)",
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
        """Create tool for qualifying results."""
        return Tool(
            name="get_qualifying_results",
            description=(
                "Get qualifying results. "
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
        """Create tool for season schedule."""
        return Tool(
            name="get_season_schedule",
            description=(
                "Get complete season calendar. "
                "Returns race dates, locations, circuit info."
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

    def _create_get_lap_times_tool(self) -> Tool:
        """Create tool for lap times."""
        return Tool(
            name="get_lap_times",
            description=(
                "Get lap times for all drivers. "
                "Returns lap number, time, sectors, compound."
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
                    "session_type": {
                        "type": "string",
                        "description": "Session type",
                        "enum": ["R", "Q", "FP1", "FP2", "FP3"],
                        "default": "R"
                    }
                },
                "required": ["year", "round_number"]
            }
        )

    def _create_get_pit_stops_tool(self) -> Tool:
        """Create tool for pit stops."""
        return Tool(
            name="get_pit_stops",
            description=(
                "Get pit stop data. "
                "Returns pit in/out times, compounds."
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
                    }
                },
                "required": ["year", "round_number"]
            }
        )

    def _create_get_weather_tool(self) -> Tool:
        """Create tool for weather data."""
        return Tool(
            name="get_weather",
            description=(
                "Get weather data. "
                "Returns temperature, humidity, wind, rain."
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
                    }
                },
                "required": ["year", "round_number"]
            }
        )

    def _create_get_tire_strategy_tool(self) -> Tool:
        """Create tool for tire strategy."""
        return Tool(
            name="get_tire_strategy",
            description=(
                "Get tire strategy data. "
                "Returns compound usage, tire life, stints."
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
                    }
                },
                "required": ["year", "round_number"]
            }
        )

    def _create_get_practice_results_tool(self) -> Tool:
        """Create tool for practice results."""
        return Tool(
            name="get_practice_results",
            description=(
                "Get practice session results. "
                "Returns driver positions for FP1/FP2/FP3."
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
                    "session_type": {
                        "type": "string",
                        "description": "Practice session",
                        "enum": ["FP1", "FP2", "FP3"]
                    }
                },
                "required": ["year", "round_number", "session_type"]
            }
        )

    def _create_get_sprint_results_tool(self) -> Tool:
        """Create tool for sprint results."""
        return Tool(
            name="get_sprint_results",
            description=(
                "Get sprint race results. "
                "Returns positions, points for sprint races."
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
                    }
                },
                "required": ["year", "round_number"]
            }
        )

    def _create_get_driver_info_tool(self) -> Tool:
        """Create tool for driver information."""
        return Tool(
            name="get_driver_info",
            description=(
                "Get driver information. "
                "Returns names, teams, numbers, countries."
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
                    }
                },
                "required": ["year", "round_number"]
            }
        )

    def _create_get_track_status_tool(self) -> Tool:
        """Create tool for track status."""
        return Tool(
            name="get_track_status",
            description=(
                "Get track status. "
                "Returns flags, safety car, red flags."
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
                    }
                },
                "required": ["year", "round_number"]
            }
        )

    def _create_get_race_control_tool(self) -> Tool:
        """Create tool for race control messages."""
        return Tool(
            name="get_race_control_messages",
            description=(
                "Get race control messages. "
                "Returns penalties, investigations, decisions."
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
                    }
                },
                "required": ["year", "round_number"]
            }
        )

    async def handle_get_race_results(
        self, arguments: Dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle get_race_results tool call."""
        try:
            results = self.provider.get_race_results(
                year=arguments["year"],
                round_number=arguments["round_number"],
                use_realtime=arguments.get("use_realtime", False)
            )
            data = self._dataframe_to_dict(results)
            return [
                TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )
            ]
        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )
            ]

    async def handle_get_telemetry(
        self, arguments: Dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle get_telemetry tool call."""
        try:
            telemetry = self.provider.get_telemetry(
                year=arguments["year"],
                round_number=arguments["round_number"],
                driver=arguments["driver"],
                use_realtime=arguments.get("use_realtime", False)
            )
            if telemetry.empty:
                return [
                    TextContent(
                        type="text",
                        text="No telemetry data found"
                    )
                ]
            sample = telemetry.head(100)
            data = self._dataframe_to_dict(sample)
            return [
                TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )
            ]
        except Exception as e:
            return [
                TextContent(type="text", text=f"Error: {str(e)}")
            ]

    async def handle_get_qualifying_results(
        self, arguments: Dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle get_qualifying_results tool call."""
        try:
            results = self.provider.get_qualifying_results(
                year=arguments["year"],
                round_number=arguments["round_number"],
                use_realtime=arguments.get("use_realtime", False)
            )
            data = self._dataframe_to_dict(results)
            return [
                TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )
            ]
        except Exception as e:
            return [
                TextContent(type="text", text=f"Error: {str(e)}")
            ]

    async def handle_get_season_schedule(
        self, arguments: Dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle get_season_schedule tool call."""
        try:
            schedule = self.provider.get_season_schedule(
                year=arguments["year"]
            )
            data = self._dataframe_to_dict(schedule)
            return [
                TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )
            ]
        except Exception as e:
            return [
                TextContent(type="text", text=f"Error: {str(e)}")
            ]

    async def handle_get_lap_times(
        self, arguments: Dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle get_lap_times tool call."""
        try:
            lap_times = self.provider.get_lap_times(
                year=arguments["year"],
                round_number=arguments["round_number"],
                session_type=arguments.get("session_type", "R")
            )
            data = self._dataframe_to_dict(lap_times)
            return [
                TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )
            ]
        except Exception as e:
            return [
                TextContent(type="text", text=f"Error: {str(e)}")
            ]

    async def handle_get_pit_stops(
        self, arguments: Dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle get_pit_stops tool call."""
        try:
            pit_stops = self.provider.get_pit_stops(
                year=arguments["year"],
                round_number=arguments["round_number"]
            )
            data = self._dataframe_to_dict(pit_stops)
            return [
                TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )
            ]
        except Exception as e:
            return [
                TextContent(type="text", text=f"Error: {str(e)}")
            ]

    async def handle_get_weather(
        self, arguments: Dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle get_weather tool call."""
        try:
            weather = self.provider.get_weather(
                year=arguments["year"],
                round_number=arguments["round_number"]
            )
            data = self._dataframe_to_dict(weather)
            return [
                TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )
            ]
        except Exception as e:
            return [
                TextContent(type="text", text=f"Error: {str(e)}")
            ]

    async def handle_get_tire_strategy(
        self, arguments: Dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle get_tire_strategy tool call."""
        try:
            strategy = self.provider.get_tire_strategy(
                year=arguments["year"],
                round_number=arguments["round_number"]
            )
            data = self._dataframe_to_dict(strategy)
            return [
                TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )
            ]
        except Exception as e:
            return [
                TextContent(type="text", text=f"Error: {str(e)}")
            ]

    async def handle_get_practice_results(
        self, arguments: Dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle get_practice_results tool call."""
        try:
            results = self.provider.get_practice_results(
                year=arguments["year"],
                round_number=arguments["round_number"],
                session_type=arguments["session_type"]
            )
            data = self._dataframe_to_dict(results)
            return [
                TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )
            ]
        except Exception as e:
            return [
                TextContent(type="text", text=f"Error: {str(e)}")
            ]

    async def handle_get_sprint_results(
        self, arguments: Dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle get_sprint_results tool call."""
        try:
            results = self.provider.get_sprint_results(
                year=arguments["year"],
                round_number=arguments["round_number"]
            )
            data = self._dataframe_to_dict(results)
            return [
                TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )
            ]
        except Exception as e:
            return [
                TextContent(type="text", text=f"Error: {str(e)}")
            ]

    async def handle_get_driver_info(
        self, arguments: Dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle get_driver_info tool call."""
        try:
            info = self.provider.get_driver_info(
                year=arguments["year"],
                round_number=arguments["round_number"]
            )
            data = self._dataframe_to_dict(info)
            return [
                TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )
            ]
        except Exception as e:
            return [
                TextContent(type="text", text=f"Error: {str(e)}")
            ]

    async def handle_get_track_status(
        self, arguments: Dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle get_track_status tool call."""
        try:
            status = self.provider.get_track_status(
                year=arguments["year"],
                round_number=arguments["round_number"]
            )
            data = self._dataframe_to_dict(status)
            return [
                TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )
            ]
        except Exception as e:
            return [
                TextContent(type="text", text=f"Error: {str(e)}")
            ]

    async def handle_get_race_control(
        self, arguments: Dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle get_race_control_messages tool call."""
        try:
            messages = self.provider.get_race_control_messages(
                year=arguments["year"],
                round_number=arguments["round_number"]
            )
            data = self._dataframe_to_dict(messages)
            return [
                TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )
            ]
        except Exception as e:
            return [
                TextContent(type="text", text=f"Error: {str(e)}")
            ]

    async def handle_get_positions(
        self, arguments: Dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle get_positions tool call (OpenF1)."""
        try:
            positions = self.provider.openf1_provider.get_positions(
                session_key=arguments["session_key"],
                driver_number=arguments.get("driver_number")
            )
            data = self._dataframe_to_dict(positions)
            return [
                TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )
            ]
        except Exception as e:
            return [
                TextContent(type="text", text=f"Error: {str(e)}")
            ]

    async def handle_get_intervals(
        self, arguments: Dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle get_intervals tool call (OpenF1)."""
        try:
            intervals = self.provider.openf1_provider.get_intervals(
                session_key=arguments["session_key"],
                driver_number=arguments.get("driver_number")
            )
            data = self._dataframe_to_dict(intervals)
            return [
                TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )
            ]
        except Exception as e:
            return [
                TextContent(type="text", text=f"Error: {str(e)}")
            ]

    async def handle_get_location(
        self, arguments: Dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle get_location tool call (OpenF1)."""
        try:
            location = self.provider.openf1_provider.get_location(
                session_key=arguments["session_key"],
                driver_number=arguments.get("driver_number")
            )
            data = self._dataframe_to_dict(location)
            return [
                TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )
            ]
        except Exception as e:
            return [
                TextContent(type="text", text=f"Error: {str(e)}")
            ]

    async def handle_get_team_radio(
        self, arguments: Dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle get_team_radio tool call (OpenF1)."""
        try:
            radio = self.provider.openf1_provider.get_team_radio(
                session_key=arguments["session_key"],
                driver_number=arguments.get("driver_number")
            )
            data = self._dataframe_to_dict(radio)
            return [
                TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )
            ]
        except Exception as e:
            return [
                TextContent(type="text", text=f"Error: {str(e)}")
            ]

    async def handle_get_meetings(
        self, arguments: Dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle get_meetings tool call (OpenF1)."""
        try:
            meetings = self.provider.openf1_provider.get_meetings(
                year=arguments.get("year"),
                country_name=arguments.get("country")
            )
            data = self._dataframe_to_dict(meetings)
            return [
                TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )
            ]
        except Exception as e:
            return [
                TextContent(type="text", text=f"Error: {str(e)}")
            ]

    async def handle_get_overtakes(
        self, arguments: Dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle get_overtakes tool call (OpenF1)."""
        try:
            overtakes = self.provider.openf1_provider.get_overtakes(
                session_key=arguments["session_key"],
                driver_number=arguments.get("driver_number")
            )
            data = self._dataframe_to_dict(overtakes)
            return [
                TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )
            ]
        except Exception as e:
            return [
                TextContent(type="text", text=f"Error: {str(e)}")
            ]

    def _create_get_positions_tool(self) -> Tool:
        """Create tool for getting real positions (OpenF1)."""
        return Tool(
            name="get_positions",
            description=(
                "Get real race positions from OpenF1 /position endpoint."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_key": {
                        "type": "integer",
                        "description": "OpenF1 session identifier"
                    },
                    "driver_number": {
                        "type": "integer",
                        "description": "Driver number (optional)"
                    }
                },
                "required": ["session_key"]
            }
        )

    def _create_get_intervals_tool(self) -> Tool:
        """Create tool for getting time intervals (OpenF1)."""
        return Tool(
            name="get_intervals",
            description=(
                "Get time gaps between drivers from OpenF1 /intervals."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_key": {
                        "type": "integer",
                        "description": "OpenF1 session identifier"
                    },
                    "driver_number": {
                        "type": "integer",
                        "description": "Driver number (optional)"
                    }
                },
                "required": ["session_key"]
            }
        )

    def _create_get_location_tool(self) -> Tool:
        """Create tool for getting GPS location (OpenF1)."""
        return Tool(
            name="get_location",
            description=(
                "Get driver GPS coordinates from OpenF1 /location."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_key": {
                        "type": "integer",
                        "description": "OpenF1 session identifier"
                    },
                    "driver_number": {
                        "type": "integer",
                        "description": "Driver number (optional)"
                    }
                },
                "required": ["session_key"]
            }
        )

    def _create_get_team_radio_tool(self) -> Tool:
        """Create tool for getting team radio (OpenF1)."""
        return Tool(
            name="get_team_radio",
            description=(
                "Get team radio messages from OpenF1 /team_radio."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_key": {
                        "type": "integer",
                        "description": "OpenF1 session identifier"
                    },
                    "driver_number": {
                        "type": "integer",
                        "description": "Driver number (optional)"
                    }
                },
                "required": ["session_key"]
            }
        )

    def _create_get_meetings_tool(self) -> Tool:
        """Create tool for getting race meetings (OpenF1)."""
        return Tool(
            name="get_meetings",
            description=(
                "Get race weekend info from OpenF1 /meetings."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "year": {
                        "type": "integer",
                        "description": "Season year (optional)"
                    },
                    "country": {
                        "type": "string",
                        "description": "Country name (optional)"
                    }
                }
            }
        )

    def _create_get_overtakes_tool(self) -> Tool:
        """Create tool for getting overtakes (OpenF1)."""
        return Tool(
            name="get_overtakes",
            description=(
                "Get overtaking maneuvers from OpenF1 /overtakes."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_key": {
                        "type": "integer",
                        "description": "OpenF1 session identifier"
                    },
                    "driver_number": {
                        "type": "integer",
                        "description": "Driver number (optional)"
                    }
                },
                "required": ["session_key"]
            }
        )

    def _dataframe_to_dict(
        self, df: pd.DataFrame
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
