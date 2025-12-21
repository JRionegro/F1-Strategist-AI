"""
Race Position Agent - F1 Position Tracking and Overtake Analysis

This agent specializes in race position monitoring, gap analysis, overtake
opportunities, and DRS zone optimization.

Primarily focused on race sessions where position battles occur.
"""

from typing import List
import logging

from src.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class RacePositionAgent(BaseAgent):
    """
    Specialized agent for F1 position tracking and overtake analysis.
    
    Core Responsibilities:
    - Position tracking and changes
    - Gap analysis between drivers
    - Overtake opportunity identification
    - DRS zone effectiveness
    - Undercut/overcut potential
    - Position battle monitoring
    """
    
    def get_system_prompt(self) -> str:
        """
        Get system prompt for Race Position Agent.
        
        Adapts based on session type (race vs qualifying).
        
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
        """Default prompt for Race Position Agent."""
        return """You are an expert F1 Race Position Agent specializing in position tracking and overtake analysis.

Your expertise includes:
- Position tracking and changes
- Gap analysis between drivers
- Overtake opportunity assessment
- DRS zone effectiveness
- Position battle monitoring
- Strategic position implications

Provide clear, tactical insights based on position data and gaps.
Always quantify gaps in seconds and explain overtaking feasibility.
"""
    
    def _get_race_prompt(self) -> str:
        """Prompt for race position analysis mode."""
        return """You are an expert F1 Race Position Agent for the {race} {year}.

Your core responsibilities:
1. POSITION TRACKING
   - Current race positions (P1, P2, P3...)
   - Position changes during race
   - Lap-by-lap position evolution
   - Positions gained/lost since start
   - Net position changes per stint
   - Position under threat assessment
   
2. GAP ANALYSIS
   - Gap to car ahead (seconds)
   - Gap to car behind (seconds)
   - Gap evolution over laps
   - Closing rate calculation (seconds per lap)
   - Time to catch (laps remaining)
   - Safe gap vs vulnerable gap
   
3. OVERTAKE OPPORTUNITIES
   - Pace differential needed for overtake
   - DRS effectiveness at this circuit
   - Track characteristics (overtaking difficulty)
   - Alternative strategies (undercut vs on-track)
   - Tire age advantage/disadvantage
   - Risk vs reward assessment
   
4. DRS ZONES
   - DRS detection point and activation zone
   - Number of DRS zones at circuit
   - DRS effectiveness (typical time gain)
   - Gap requirement (within 1 second)
   - Optimal DRS strategy
   - Defending against DRS attack
   
5. UNDERCUT/OVERCUT POTENTIAL
   - Track position value vs tire age
   - Pit stop time loss (typical 20-25s)
   - Laps needed to make up pit delta
   - Traffic ahead consideration
   - Tire compound advantage needed
   - Undercut window (optimal lap to pit)
   
6. POSITION BATTLES
   - Multi-lap battles in progress
   - Attack vs defend mode
   - Tire/fuel advantage in battle
   - Blue flag situations for lapping
   - Team orders implications
   - Points position importance (P10 vs P11)
   
7. STRATEGIC POSITION VALUE
   - Points positions (top 10)
   - Championship implications
   - Clean air vs DRS advantage
   - Track position vs tire life trade-off
   - Defending position viability
   - Letting teammate through considerations

ALWAYS:
- Provide specific gap times (e.g., "+2.345s")
- Calculate closing rates (e.g., "0.3s per lap")
- Estimate laps to catch (e.g., "will catch in 8 laps")
- State DRS availability clearly
- Consider tire age differential
- Reference specific lap numbers

FORMAT: Provide precise position analysis with gaps, closing rates, and overtake feasibility.
""".format(
            race=self.context.race_name if self.context else "Unknown",
            year=self.context.year if self.context else "Unknown"
        )
    
    def _get_qualifying_prompt(self) -> str:
        """Prompt for qualifying position analysis mode."""
        return """You are an expert F1 Race Position Agent for qualifying at {race} {year}.

Your core responsibilities:
1. GRID POSITION ANALYSIS
   - Current qualifying position
   - Gap to positions above/below
   - Advancement/elimination risk
   - Grid position value for race
   
2. SESSION PROGRESSION
   - Q1: Top 15 advance, bottom 5 eliminated
   - Q2: Top 10 advance, P11-P15 eliminated
   - Q3: Final grid positions P1-P10
   - Cutoff time analysis
   - Margin of safety
   
3. POSITION TARGETS
   - Gap to target position (e.g., P10 cutoff)
   - Time needed to advance
   - Laps remaining for improvement
   - Track evolution benefit
   
4. RACE STARTING POSITION
   - Grid position implications for race
   - Tire choice advantage (Q2 top 10)
   - Clean side vs dirty side
   - Turn 1 positioning

ALWAYS:
- State gaps to cutoff positions
- Calculate time needed to advance
- Consider track evolution
- Explain race implications

FORMAT: Provide qualifying position analysis with advancement predictions.
""".format(
            race=self.context.race_name if self.context else "Unknown",
            year=self.context.year if self.context else "Unknown"
        )
    
    def get_available_tools(self) -> List[str]:
        """
        Get list of MCP tools available to Race Position Agent.
        
        Returns:
            List of tool names
        """
        return [
            "get_race_results",
            "get_lap_times",
            "get_position_data",
            "get_session_info"
        ]
    
    def validate_query(self, query: str) -> bool:
        """
        Validate if query is suitable for Race Position Agent.
        
        Position queries typically contain keywords related to:
        - Race positions and standings
        - Gaps between cars
        - Overtaking possibilities
        - DRS and position battles
        
        Args:
            query: User query string
            
        Returns:
            True if query is suitable for Race Position Agent
        """
        if not query or len(query.strip()) == 0:
            return False
        
        query_lower = query.lower()
        
        # Position-related keywords
        position_keywords = [
            # Positions
            "position", "p1", "p2", "p3", "p4", "p5",
            "p6", "p7", "p8", "p9", "p10",
            "first place", "second place", "third place",
            "leader", "leading", "race leader",
            "podium", "points position",
            
            # Gaps
            "gap", "behind", "ahead", "interval",
            "closing", "catching", "pulling away",
            "distance", "seconds behind", "seconds ahead",
            
            # Overtaking
            "overtake", "overtaking", "pass", "passing",
            "attack", "attacking", "defend", "defending",
            "battle", "fight", "racing",
            
            # DRS
            "drs", "drs zone", "detection point",
            "within 1 second", "drs range",
            
            # Strategy
            "undercut", "overcut", "track position",
            "pit delta", "pit strategy",
            
            # Movement
            "gained position", "lost position",
            "moving up", "moving down", "climbing",
            "falling back", "dropped",
            
            # Specific scenarios
            "blue flag", "lapping", "unlapping",
            "team orders", "let through", "swap positions",
            "teammate", "swap",
            
            # Analysis
            "can catch", "will catch", "within reach",
            "too far", "safe", "under threat",
            "closing rate", "pace advantage"
        ]
        
        # Check if any position keyword is in the query
        return any(keyword in query_lower for keyword in position_keywords)
