"""
Weather Agent - F1 Weather Impact and Timing Analysis

This agent specializes in weather-related decisions including rain prediction,
track condition monitoring, tire recommendations, and optimal timing windows.

Supports both Race and Qualifying modes with weather-specific adaptations.
"""

from typing import List
import logging

from src.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class WeatherAgent(BaseAgent):
    """
    Specialized agent for F1 weather impact and timing analysis.
    
    Race Mode Responsibilities:
    - Rain prediction during race
    - Impact on tire degradation
    - Wet/intermediate tire change windows
    - Track and air temperature monitoring
    
    Qualifying Mode Responsibilities:
    - Imminent rain risk assessment
    - Track temperature evolution
    - Optimal timing window prediction
    - Wind impact on lap times
    - Track limits conditions
    """
    
    def get_system_prompt(self) -> str:
        """
        Get system prompt for Weather Agent.
        
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
        """Default prompt for Weather Agent."""
        return """You are an expert F1 Weather Agent specializing in weather impact analysis.

Your expertise includes:
- Weather forecasting and rain prediction
- Track temperature and evolution
- Tire selection based on conditions
- Timing windows optimization
- Wind and atmospheric conditions impact

Provide clear, time-sensitive recommendations based on current conditions and forecasts.
Always explain confidence levels and risk factors in your predictions.
"""
    
    def _get_race_prompt(self) -> str:
        """Prompt for race weather analysis mode."""
        return """You are an expert F1 Weather Agent for the {race} {year}.

Your core responsibilities:
1. RAIN PREDICTION
   - Probability of rain during race
   - Intensity forecast (light/moderate/heavy)
   - Duration estimates
   - Timing of rain arrival/departure

2. TIRE RECOMMENDATIONS
   - Slick conditions: Track temperature vs tire compounds
   - Damp conditions: Intermediate tire window
   - Wet conditions: Full wet tire recommendation
   - Mixed conditions: Risk vs reward analysis

3. TRACK CONDITIONS
   - Track temperature trends
   - Drying rate after rain
   - Wet patches and dry line formation
   - Grip level changes

4. STRATEGIC IMPACT
   - Pit stop timing for weather changes
   - Safety car likelihood in wet conditions
   - Risk of red flag (heavy rain)
   - Tire degradation rate changes

5. TEMPERATURE MONITORING
   - Air temperature impact on car performance
   - Track temperature for tire selection
   - Optimal operating windows
   - Cooling system requirements

ALWAYS:
- Provide time-based predictions (e.g., "in 10 laps", "15 minutes")
- State confidence levels (high/medium/low)
- Explain implications for strategy
- Consider safety factors
- Reference real-time weather data when available

FORMAT: Provide urgent, actionable weather alerts with timing and confidence.
""".format(
            race=self.context.race_name if self.context else "Unknown",
            year=self.context.year if self.context else "Unknown"
        )
    
    def _get_qualifying_prompt(self) -> str:
        """Prompt for qualifying weather analysis mode."""
        return """You are an expert F1 Weather Agent for qualifying at {race} {year}.

Your core responsibilities:
1. IMMINENT RAIN RISK
   - Rain arrival time prediction
   - Should teams go out NOW or wait?
   - Window size (minutes until rain)
   - Track drying timeline if raining

2. TRACK EVOLUTION
   - Track temperature trends
   - Rubber buildup and grip improvement
   - Optimal timing for flying lap
   - Track condition deterioration after rain

3. TIMING STRATEGY
   - Early vs late run analysis
   - Risk of session disruption (red flag)
   - Traffic vs track conditions trade-off
   - Multiple run strategy in changing conditions

4. WIND ANALYSIS
   - Wind speed and direction
   - Impact on specific corners/sectors
   - Time gain/loss per sector
   - Optimal lap timing with wind

5. TRACK LIMITS
   - Surface conditions (damp/wet patches)
   - Risk of lap deletion
   - Safe vs aggressive lines

SESSION-SPECIFIC:
- Q1: Safety first, ensure advancement
- Q2: Balance risk, consider race tire
- Q3: Maximum risk tolerance, predict optimal moment

ALWAYS:
- Provide minute-by-minute timing recommendations
- State probability percentages for rain
- Explain risk factors clearly
- Give GO/WAIT/ABORT recommendations
- Consider data from practice sessions

FORMAT: Provide urgent GO/WAIT decisions with timing windows and risk assessment.
""".format(
            race=self.context.race_name if self.context else "Unknown",
            year=self.context.year if self.context else "Unknown"
        )
    
    def get_available_tools(self) -> List[str]:
        """
        Get list of MCP tools available to Weather Agent.
        
        Returns:
            List of tool names
        """
        return [
            "get_weather",
            "get_track_status",
            "get_session_info",
            "get_lap_times"
        ]
    
    def validate_query(self, query: str) -> bool:
        """
        Validate if query is suitable for Weather Agent.
        
        Weather queries typically contain keywords related to:
        - Weather conditions
        - Rain/wet/dry
        - Temperature
        - Track conditions
        - Wind
        - Timing windows
        
        Args:
            query: User query string
            
        Returns:
            True if query is suitable for Weather Agent
        """
        if not query or len(query.strip()) == 0:
            return False
        
        query_lower = query.lower()
        
        # Weather-related keywords
        weather_keywords = [
            "weather", "rain", "wet", "dry", "damp",
            "temperature", "temp", "wind", "forecast",
            "track condition", "surface", "grip",
            "intermediate", "inters", "wets",
            "slick", "humid", "cloud", "sun",
            "drying", "drainage", "puddle", "spray",
            "visibility", "mist", "fog",
            "go out", "wait", "timing", "window",
            "now or later", "when to go",
            "hot", "cold", "cool", "warm"
        ]
        
        # Check if any weather keyword is in the query
        return any(keyword in query_lower for keyword in weather_keywords)
