"""
Race Control Agent - F1 Race Control Messages and Flag Analysis

This agent specializes in interpreting race control messages, flag conditions,
penalties, and race incidents to provide strategic insights.

Primarily focused on race sessions where race control is most active.
"""

from typing import List
import logging

from src.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class RaceControlAgent(BaseAgent):
    """
    Specialized agent for F1 race control and flag interpretation.

    Core Responsibilities:
    - Yellow flag and VSC (Virtual Safety Car) interpretation
    - Safety Car deployment analysis
    - Red flag situations
    - Penalty tracking and impact
    - Race incident monitoring
    - DRS enable/disable status
    - Track status changes
    """

    def get_system_prompt(self) -> str:
        """
        Get system prompt for Race Control Agent.

        Adapts based on session type, primarily race-focused.

        Returns:
            System prompt string with role and capabilities
        """
        if not self.context:
            return self._get_default_prompt()

        if self.context.session_type in ["race", "sprint"]:
            return self._get_race_prompt()
        elif self.context.session_type == "qualifying":
            return self._get_qualifying_prompt()
        else:
            return self._get_default_prompt()

    def _get_default_prompt(self) -> str:
        """Default prompt for Race Control Agent."""
        return """You are an expert F1 Race Control Agent specializing in flag interpretation and race incidents.

Your expertise includes:
- Flag conditions (yellow, red, green, blue)
- Safety Car and VSC situations
- Penalty interpretation and impact
- Race incidents and investigations
- Track status monitoring
- DRS availability
- Race control messages

Provide clear, time-sensitive interpretations of race control decisions.
Always explain strategic implications and required actions.
"""

    def _get_race_prompt(self) -> str:
        """Prompt for race control analysis during race."""
        return """You are an expert F1 Race Control Agent for the {race} {year}.

Your core responsibilities:
1. FLAG INTERPRETATION
   - Yellow Flags: Local caution, specific sectors affected
   - Double Yellow: Slow down significantly, no overtaking
   - Red Flag: Session stopped, return to pits
   - Green Flag: All clear, racing resumed
   - Blue Flags: Let faster cars through
   - Black & White: Warning flag for driving standards
   - Black Flag: Disqualification

2. SAFETY CAR (SC) ANALYSIS
   - SC deployment reason and duration estimate
   - Strategic implications (pit window opening)
   - Positions gained/lost under SC
   - SC restart timing and procedures
   - Lapped cars unlapping
   - Pack bunching effect

3. VIRTUAL SAFETY CAR (VSC)
   - VSC reason (incident location)
   - Duration estimate based on incident severity
   - Delta time requirements (40% slower)
   - Strategic pit opportunity (maintain position)
   - VSC ending prediction
   - Advantage for different strategies

4. PENALTY TRACKING
   - Time penalties (5s, 10s, stop-go)
   - Grid penalties for next race
   - Penalty points on license
   - Impact on current race position
   - When penalty must be served
   - Appeal possibilities

5. RACE INCIDENTS
   - Collision and contact analysis
   - Causing collision investigation
   - Leaving track and gaining advantage
   - Unsafe release from pit
   - Ignoring flags
   - Investigation status (noted, under investigation, decision)

6. TRACK STATUS
   - All clear vs cautionary conditions
   - Sector-specific conditions
   - DRS enabled/disabled
   - Track limits monitoring
   - Debris on track
   - Weather-related changes

7. STRATEGIC IMPLICATIONS
   - Pit stop opportunities under SC/VSC
   - Position changes due to penalties
   - Risk of further incidents
   - Safety car lottery (lucky/unlucky timing)
   - Red flag tire change advantage
   - Race restart positioning

ALWAYS:
- Provide lap number and time of incident
- Explain strategic impact immediately
- State investigation status clearly
- Predict likely penalty outcomes
- Consider safety implications
- Reference specific race control message numbers

FORMAT: Provide urgent, actionable race control alerts with lap numbers and strategic impact.
""".format(
            race=self.context.race_name if self.context else "Unknown",
            year=self.context.year if self.context else "Unknown")

    def _get_qualifying_prompt(self) -> str:
        """Prompt for race control analysis during qualifying."""
        return """You are an expert F1 Race Control Agent for qualifying at {race} {year}.

Your core responsibilities:
1. QUALIFYING FLAGS
   - Yellow Flags: Sector affected, impact on flying laps
   - Red Flag: Session stopped, time remaining consideration
   - Track status changes affecting lap validity
   - Checkered flag timing

2. TRACK LIMITS
   - Lap deletion for exceeding track limits
   - Specific corners being monitored
   - Three strike system
   - Impact on session advancement

3. QUALIFYING INCIDENTS
   - Blocking/impeding investigations
   - Unsafe release from pit
   - Red flag causing incidents
   - Driver under investigation

4. SESSION INTERRUPTIONS
   - Red flag duration estimate
   - Time remaining vs drivers in pit lane
   - Strategic decisions to wait or go
   - Session restart procedures

5. PENALTIES
   - Grid position penalties
   - Reprimands and warnings
   - Pit lane start penalties
   - Impact on race starting grid

ALWAYS:
- State time remaining in session
- Explain impact on Q1/Q2/Q3 advancement
- Identify which drivers are at risk
- Predict session restart timing

FORMAT: Provide time-sensitive qualifying alerts with advancement implications.
""".format(
            race=self.context.race_name if self.context else "Unknown",
            year=self.context.year if self.context else "Unknown")

    def get_available_tools(self) -> List[str]:
        """
        Get list of MCP tools available to Race Control Agent.

        Returns:
            List of tool names
        """
        return [
            "get_race_control_messages",
            "get_track_status",
            "get_session_info",
            "get_race_results"
        ]

    def validate_query(self, query: str) -> bool:
        """
        Validate if query is suitable for Race Control Agent.

        Race control queries typically contain keywords related to:
        - Flags and race control
        - Penalties and incidents
        - Safety car situations
        - Track status

        Args:
            query: User query string

        Returns:
            True if query is suitable for Race Control Agent
        """
        if not query or len(query.strip()) == 0:
            return False

        query_lower = query.lower()

        # Race control keywords
        race_control_keywords = [
            # Flags
            "flag", "yellow", "red flag", "green", "blue flag",
            "checkered", "black flag", "white flag",
            "yellow flag", "double yellow",

            # Safety measures
            "safety car", "sc", "vsc", "virtual safety car",
            "pace car", "safety", "neutralized",

            # Penalties
            "penalty", "penalized", "time penalty",
            "5 second", "10 second", "5s", "10s",
            "stop go", "drive through", "grid penalty",
            "reprimand", "warning", "penalty points",
            "black and white flag", "disqualified",

            # Incidents
            "incident", "crash", "collision", "contact",
            "investigation", "under investigation", "noted",
            "causing collision", "unsafe release",
            "ignoring flags", "track limits",

            # Track status
            "track status", "drs", "drs enabled", "drs disabled",
            "all clear", "caution", "debris",
            "track clear", "marshals",

            # Race control
            "race control", "race director", "stewards",
            "fia", "decision", "verdict",

            # Session status
            "red flagged", "session stopped", "session suspended",
            "restart", "resuming", "resume"
        ]

        # Check if any race control keyword is in the query
        return any(keyword in query_lower for keyword in race_control_keywords)
