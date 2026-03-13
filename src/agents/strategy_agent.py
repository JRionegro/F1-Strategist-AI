"""
Strategy Agent - F1 Race and Qualifying Strategy Optimization

This agent specializes in race strategy decisions including tire selection,
pit stop timing, fuel management, and qualifying strategy optimization.

Supports both Race and Qualifying modes with session-specific adaptations.
"""

from typing import List
import logging

from src.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class StrategyAgent(BaseAgent):
    """
    Specialized agent for F1 race and qualifying strategy optimization.

    Race Mode Responsibilities:
    - Tire strategy (compound selection, stint length)
    - Pit stop timing (optimal windows, undercut/overcut)
    - Fuel management and race pace
    - Team strategy coordination

    Qualifying Mode Responsibilities:
    - Track exit strategy (timing, track evolution)
    - Number of attempts (1, 2, or 3 flying laps)
    - Fuel management (minimum vs weight)
    - Out-lap strategy (tire preparation)
    - Q1/Q2/Q3 progression tactics
    """

    def get_system_prompt(self) -> str:
        """
        Get system prompt for Strategy Agent.

        Adapts based on session type (race vs qualifying).

        Returns:
            System prompt string with role and capabilities
        """
        if not self.context:
            return self._get_default_prompt()

        if self.context.session_type == "qualifying":
            return self._get_qualifying_prompt()
        elif self.context.session_type in ["race", "sprint"]:
            return self._get_race_prompt()
        else:
            return self._get_default_prompt()

    def _get_default_prompt(self) -> str:
        """Default prompt for Strategy Agent."""
        return """You are an expert F1 Strategy Agent specializing in race and qualifying strategy optimization.

Your expertise includes:
- Tire strategy and compound selection
- Pit stop timing and execution
- Fuel management and race pace
- Qualifying strategy and timing
- Track evolution and adaptation

Provide clear, data-driven recommendations based on F1 regulations and historical data.
Always explain your reasoning and consider multiple strategic options when relevant.
"""

    def _get_race_prompt(self) -> str:
        """Prompt for race strategy mode."""
        return """You are an expert F1 Race Strategy Agent for the {race} {year}.

Your core responsibilities:
1. TIRE STRATEGY
   - Compound selection (Soft/Medium/Hard)
   - Stint length optimization
   - Degradation management
   - Two-stop vs one-stop analysis

2. PIT STOP TIMING
   - Optimal pit windows
   - Undercut/overcut opportunities
   - Track position considerations
   - Safety car scenarios

3. RACE PACE MANAGEMENT
   - Fuel saving strategies
   - Tire management (lift and coast)
   - Battery deployment (ERS)
   - Gap management to cars ahead/behind

4. STRATEGIC DECISIONS
   - Free practice vs race strategy
   - Team orders implications
   - Risk vs reward analysis

ALWAYS:
- Base recommendations on current F1 regulations
- Consider track-specific characteristics
- Explain trade-offs between options
- Reference historical data when available
- Provide confidence levels for recommendations

FORMAT: Provide clear, concise answers with strategic reasoning.
""".format(
            race=self.context.race_name if self.context else "Unknown",
            year=self.context.year if self.context else "Unknown")

    def _get_qualifying_prompt(self) -> str:
        """Prompt for qualifying strategy mode."""
        return """You are an expert F1 Qualifying Strategy Agent for the {race} {year}.

Your core responsibilities:
1. TRACK EXIT STRATEGY
   - Optimal timing to exit pits
   - Track evolution prediction
   - Traffic management
   - Clean lap opportunities

2. ATTEMPT OPTIMIZATION
   - Number of flying laps (1, 2, or 3)
   - Tire allocation per session
   - Banker lap strategy
   - Final attempt timing

3. OUT-LAP MANAGEMENT
   - Tire preparation (temperature, pressure)
   - Gap to cars ahead (slipstream vs clean air)
   - Brake/tire warm-up procedures

4. SESSION PROGRESSION
   - Q1: Advance safely, save tires
   - Q2: Tire choice for race start
   - Q3: Maximum attack, optimal timing

5. CONTINGENCY PLANNING
   - Rain risk assessment
   - Red flag scenarios
   - Track limits and deletion risk

ALWAYS:
- Consider track temperature evolution
- Factor in weather forecast
- Account for tire behavior (new vs used)
- Explain risk vs reward
- Reference similar sessions when relevant

FORMAT: Provide clear timing recommendations with strategic reasoning.
""".format(
            race=self.context.race_name if self.context else "Unknown",
            year=self.context.year if self.context else "Unknown")

    def get_available_tools(self) -> List[str]:
        """
        Get list of MCP tools available to Strategy Agent.

        Returns:
            List of tool names
        """
        return [
            "get_race_results",
            "get_lap_times",
            "get_pit_stops",
            "get_weather",
            "get_qualifying_results",
            "get_session_info"
        ]

    def validate_query(self, query: str) -> bool:
        """
        Validate if query is suitable for Strategy Agent.

        Strategy queries typically contain keywords related to:
        - Tire/tyre strategy
        - Pit stops
        - Race strategy
        - Qualifying strategy
        - Fuel management
        - Compound selection

        Args:
            query: User query string

        Returns:
            True if query is suitable for Strategy Agent
        """
        if not query or len(query.strip()) == 0:
            return False

        query_lower = query.lower()

        # Strategy-related keywords
        strategy_keywords = [
            "tire", "tyre", "pit", "stop", "strategy", "compound",
            "soft", "medium", "hard", "intermediate", "wet",
            "stint", "undercut", "overcut", "two-stop", "one-stop",
            "qualifying", "q1", "q2", "q3", "pole", "grid",
            "fuel", "save", "manage", "pace", "window",
            "optimal", "best", "recommend", "should",
            "previous", "historical", "past", "worked", "bahrain", "race"
        ]

        # Check if any strategy keyword is in the query
        return any(keyword in query_lower for keyword in strategy_keywords)
