"""
Global session management for F1 Strategist AI.

Manages the current race context shared across all dashboards.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class SessionMode(Enum):
    """Operating mode of the application."""

    LIVE = "live"
    SIMULATION = "simulation"


class SessionType(Enum):
    """Type of F1 session."""

    FP1 = "Practice 1"
    FP2 = "Practice 2"
    FP3 = "Practice 3"
    QUALIFYING = "Qualifying"
    SPRINT_QUALIFYING = "Sprint Qualifying"
    SPRINT = "Sprint"
    RACE = "Race"


@dataclass
class RaceContext:
    """Current race context information."""

    year: int
    round_number: int
    circuit_name: str
    circuit_key: str
    country: str
    session_type: SessionType
    session_date: datetime
    total_laps: int
    current_lap: int = 1

    # OpenF1 specific fields
    meeting_key: Optional[int] = None
    session_key: Optional[int] = None

    # Driver/Team focus
    focused_driver: Optional[str] = None  # Driver code (e.g., "VER")
    focused_team: Optional[str] = None    # Team name (e.g., "Red Bull Racing")

    # Additional context
    weather_conditions: Optional[str] = None
    track_status: str = "Unknown"


@dataclass
class GlobalSession:
    """
    Global session state shared across all dashboards.

    This is the single source of truth for:
    - Current operating mode (Live/Simulation)
    - Race context (year, circuit, session, driver, team)
    - Simulation state (if applicable)
    """

    mode: SessionMode = SessionMode.SIMULATION
    race_context: Optional[RaceContext] = None

    # Simulation-specific state
    simulation_speed: float = 1.0  # 1x, 1.25x, 1.5x, 1.75x, 2x, 2.5x, 3x
    simulation_paused: bool = False
    simulation_current_time: Optional[datetime] = None

    # UI state
    visible_dashboards: list[str] = field(
        default_factory=lambda: ["ai_assistant"])
    active_dashboard: str = "ai_assistant"

    @classmethod
    def create_live_session(
        cls,
        race_context: RaceContext
    ) -> "GlobalSession":
        """Create a live session instance."""
        return cls(
            mode=SessionMode.LIVE,
            race_context=race_context,
            simulation_speed=1.0,
            simulation_paused=False
        )

    @classmethod
    def create_simulation_session(
        cls,
        race_context: RaceContext,
        start_time: datetime
    ) -> "GlobalSession":
        """Create a simulation session instance."""
        return cls(
            mode=SessionMode.SIMULATION,
            race_context=race_context,
            simulation_speed=1.0,
            simulation_paused=True,  # Start paused
            simulation_current_time=start_time
        )

    def is_live(self) -> bool:
        """Check if in live mode."""
        return self.mode == SessionMode.LIVE

    def is_simulation(self) -> bool:
        """Check if in simulation mode."""
        return self.mode == SessionMode.SIMULATION

    def get_display_time(self) -> Optional[datetime]:
        """
        Get the current display time.

        In live mode: current real time
        In simulation: simulation time
        """
        if self.is_live():
            return datetime.now()
        return self.simulation_current_time

    def update_simulation_time(self, new_time: datetime) -> None:
        """Update simulation time."""
        if self.is_simulation():
            self.simulation_current_time = new_time

    def set_simulation_speed(self, speed: float) -> None:
        """
        Set simulation speed.

        Args:
            speed: Multiplier (1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0)
        """
        allowed_speeds = [1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0]
        if speed in allowed_speeds:
            self.simulation_speed = speed
        else:
            raise ValueError(
                f"Invalid speed: {speed}. "
                f"Allowed: {allowed_speeds}"
            )

    def toggle_pause(self) -> None:
        """Toggle simulation pause state."""
        if self.is_simulation():
            self.simulation_paused = not self.simulation_paused

    def add_dashboard(self, dashboard_id: str) -> None:
        """Show a dashboard."""
        if dashboard_id not in self.visible_dashboards:
            self.visible_dashboards.append(dashboard_id)

    def remove_dashboard(self, dashboard_id: str) -> None:
        """Hide a dashboard."""
        if dashboard_id in self.visible_dashboards:
            self.visible_dashboards.remove(dashboard_id)

    def set_active_dashboard(self, dashboard_id: str) -> None:
        """Set the active/focused dashboard."""
        self.active_dashboard = dashboard_id

    def get_session_summary(self) -> str:
        """Get a human-readable session summary."""
        if not self.race_context:
            return "No session selected"

        rc = self.race_context
        mode_str = "🔴 LIVE" if self.is_live() else "🔵 SIMULATION"

        summary = (
            f"{mode_str} | "
            f"{rc.year} {rc.circuit_name} | "
            f"{rc.session_type.value} | "
            f"Lap {rc.current_lap}/{rc.total_laps}"
        )

        if rc.focused_driver:
            summary += f" | 🏎️ {rc.focused_driver}"
        if rc.focused_team:
            summary += f" | 🏁 {rc.focused_team}"

        return summary
