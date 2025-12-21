"""
Performance Agent - F1 Lap Time and Telemetry Analysis

This agent specializes in performance analysis including lap times, sector times,
telemetry data, pace comparison, and driver performance insights.

Supports both Race and Qualifying modes with performance-specific adaptations.
"""

from typing import List
import logging

from src.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class PerformanceAgent(BaseAgent):
    """
    Specialized agent for F1 performance and telemetry analysis.
    
    Race Mode Responsibilities:
    - Lap time analysis and trends
    - Pace comparison between drivers
    - Tire degradation impact on performance
    - Fuel effect analysis
    - Stint performance evaluation
    
    Qualifying Mode Responsibilities:
    - Sector time analysis
    - Optimal lap construction
    - Tire preparation impact
    - Track evolution and improvement
    - Gap analysis to pole/competitors
    """
    
    def get_system_prompt(self) -> str:
        """
        Get system prompt for Performance Agent.
        
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
        """Default prompt for Performance Agent."""
        return """You are an expert F1 Performance Agent specializing in lap time and telemetry analysis.

Your expertise includes:
- Lap time analysis and comparison
- Sector time breakdowns
- Telemetry data interpretation
- Pace trends and evolution
- Driver performance evaluation
- Gap analysis and positioning

Provide detailed, data-driven insights based on timing and telemetry.
Always reference specific lap times, sectors, and performance metrics.
"""
    
    def _get_race_prompt(self) -> str:
        """Prompt for race performance analysis mode."""
        return """You are an expert F1 Performance Agent for the {race} {year}.

Your core responsibilities:
1. LAP TIME ANALYSIS
   - Current pace vs competitors
   - Lap time trends and consistency
   - Fastest laps and potential
   - Sector time breakdowns
   - Traffic impact on lap times

2. PACE COMPARISON
   - Driver-to-driver pace analysis
   - Team pace comparison
   - Gap evolution over stints
   - Overtaking feasibility based on pace delta
   - Defensive capability assessment

3. TIRE DEGRADATION IMPACT
   - Performance drop per lap
   - Stint length vs pace correlation
   - Tire compound comparison
   - Optimal pit window based on degradation
   - Projected lap times for remaining stint

4. FUEL EFFECT ANALYSIS
   - Fuel load impact on lap times
   - Fuel-corrected pace comparison
   - Weight effect per lap
   - Lift-and-coast detection
   - Fuel saving impact on performance

5. STINT EVALUATION
   - Opening lap performance
   - Mid-stint consistency
   - End-of-stint degradation
   - Stint-to-stint comparison
   - Performance delta on different compounds

6. TELEMETRY INSIGHTS
   - Speed trap data
   - Brake point analysis
   - Throttle application patterns
   - Corner speed comparison
   - DRS effectiveness

ALWAYS:
- Provide specific lap times (e.g., "1:23.456")
- Compare to fastest lap or reference time
- Quantify pace advantage/deficit (seconds per lap)
- Reference specific lap numbers
- Consider fuel and tire age

FORMAT: Provide precise, data-driven performance insights with lap times and deltas.
""".format(
            race=self.context.race_name if self.context else "Unknown",
            year=self.context.year if self.context else "Unknown"
        )
    
    def _get_qualifying_prompt(self) -> str:
        """Prompt for qualifying performance analysis mode."""
        return """You are an expert F1 Performance Agent for qualifying at {race} {year}.

Your core responsibilities:
1. SECTOR ANALYSIS
   - Sector 1/2/3 time breakdowns
   - Micro-sector comparison (mini-sectors)
   - Personal best sectors vs actual lap
   - Purple/green/yellow sector identification
   - Sector time trends across runs

2. OPTIMAL LAP CONSTRUCTION
   - Theoretical best lap time (sum of best sectors)
   - Gap to theoretical best
   - Which sectors have improvement potential
   - Perfect lap vs actual performance
   - Consistency across sectors

3. TIRE PREPARATION
   - Out-lap speed vs lap time correlation
   - Tire temperature impact on performance
   - Preparation lap effectiveness
   - First vs second push lap comparison
   - Tire warm-up phase duration

4. TRACK EVOLUTION
   - Lap time improvement over session
   - Track grip progression
   - Optimal timing for flying lap
   - Session-to-session improvement (FP3 → Q1 → Q2 → Q3)
   - Track temperature impact on times

5. GAP ANALYSIS
   - Gap to pole position
   - Gap to teammate
   - Gap to rivals/competitors
   - Time needed to advance (Q1→Q2, Q2→Q3)
   - Sector-by-sector gap breakdown

6. QUALIFYING PERFORMANCE
   - Q1/Q2/Q3 progression
   - Deleted lap analysis (track limits)
   - Aborted lap analysis
   - Traffic impact on lap time
   - Final sector comparison (did they abort?)

SESSION-SPECIFIC:
- Q1: Focus on advancement safety margin
- Q2: Balance between advancement and race tire
- Q3: Maximum performance, optimal lap construction

ALWAYS:
- Provide exact lap times to milliseconds (1:23.456)
- Show sector times (S1: 28.123, S2: 31.456, S3: 23.789)
- Calculate theoretical best lap
- Quantify gaps in seconds and positions
- Reference track position for traffic context

FORMAT: Provide precise sector-by-sector analysis with times, gaps, and improvement areas.
""".format(
            race=self.context.race_name if self.context else "Unknown",
            year=self.context.year if self.context else "Unknown"
        )
    
    def get_available_tools(self) -> List[str]:
        """
        Get list of MCP tools available to Performance Agent.
        
        Returns:
            List of tool names
        """
        return [
            "get_telemetry",
            "get_lap_times",
            "get_race_results",
            "get_qualifying_results",
            "get_session_info"
        ]
    
    def validate_query(self, query: str) -> bool:
        """
        Validate if query is suitable for Performance Agent.
        
        Performance queries typically contain keywords related to:
        - Lap times and sectors
        - Pace and speed
        - Telemetry data
        - Driver comparison
        - Performance analysis
        
        Args:
            query: User query string
            
        Returns:
            True if query is suitable for Performance Agent
        """
        if not query or len(query.strip()) == 0:
            return False
        
        query_lower = query.lower()
        
        # Performance-related keywords
        performance_keywords = [
            # Lap times
            "lap time", "sector", "fastest lap", "personal best",
            "purple", "green", "yellow", "delta", "gap",
            "s1", "s2", "s3", "sector 1", "sector 2", "sector 3",
            
            # Pace
            "pace", "speed", "fast", "slow", "quick", "quicker",
            "slower", "faster", "tempo", "rhythm",
            
            # Telemetry
            "telemetry", "throttle", "brake", "speed trap",
            "corner speed", "apex", "acceleration",
            "braking point", "gear", "rpm", "drs",
            
            # Comparison
            "compare", "comparison", "versus", "vs", "against",
            "better than", "worse than", "faster than", "slower than",
            "gap to", "behind", "ahead",
            
            # Performance
            "performance", "degradation", "drop off", "falling off",
            "improving", "getting faster", "getting slower",
            "consistent", "consistency", "variation",
            
            # Analysis
            "analyze", "analysis", "breakdown", "how fast",
            "how much faster", "time lost", "time gained",
            "optimal", "theoretical", "best possible",
            
            # Qualifying specific
            "q1", "q2", "q3", "pole", "grid position",
            "qualifying", "quali", "shootout",
            
            # Race specific
            "stint", "fuel", "tire deg", "tyre deg"
        ]
        
        # Check if any performance keyword is in the query
        return any(keyword in query_lower for keyword in performance_keywords)
