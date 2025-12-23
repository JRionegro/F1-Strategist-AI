"""
Simulation controller for replay and time manipulation.

Handles simulation playback controls and time progression.
"""

import logging
from datetime import datetime, timedelta
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class SimulationController:
    """
    Controls simulation playback and time progression.
    
    Manages:
    - Play/Pause
    - Speed control (1x to 3x)
    - Time jumps
    - Event callbacks
    """

    def __init__(
        self,
        start_time: datetime,
        end_time: datetime,
        on_time_update: Optional[Callable[[datetime], None]] = None
    ):
        """
        Initialize simulation controller.
        
        Args:
            start_time: Session start time
            end_time: Session end time
            on_time_update: Callback when time updates
        """
        self.start_time = start_time
        self.end_time = end_time
        self.current_time = start_time
        self.on_time_update = on_time_update
        
        self.is_playing = False
        self.speed_multiplier = 1.0
        self.last_update = datetime.now()
        
        logger.info(
            f"Initialized SimulationController: "
            f"{start_time} to {end_time}"
        )
    
    def play(self, start_from_seconds: Optional[float] = None) -> None:
        """
        Start simulation playback.
        
        Args:
            start_from_seconds: Optional offset in seconds from session start to begin simulation
        """
        if not self.is_playing:
            self.is_playing = True
            self.last_update = datetime.now()
            self.play_start_time = datetime.now()  # Track when playback started
            self.play_start_session_time = self.current_time  # Track session time when started
            self.simulation_offset = start_from_seconds if start_from_seconds is not None else 0.0
            logger.info(f"Simulation started (offset: {self.simulation_offset:.1f}s)")
    
    def get_elapsed_seconds(self) -> float:
        """
        Get elapsed simulation seconds since play started.
        
        Returns:
            Elapsed seconds in simulation time (including offset)
        """
        if not hasattr(self, 'simulation_offset'):
            self.simulation_offset = 0.0
            
        if not self.is_playing:
            # Return elapsed from start of session to current position
            return (self.current_time - self.start_time).total_seconds() + self.simulation_offset
        
        # Calculate real time elapsed since play started
        real_elapsed = (datetime.now() - self.play_start_time).total_seconds()
        # Apply speed multiplier
        sim_elapsed = real_elapsed * self.speed_multiplier
        # Add offset
        
        return self.simulation_offset + sim_elapsed
    
    def pause(self) -> None:
        """Pause simulation playback."""
        if self.is_playing:
            self.is_playing = False
            logger.info("Simulation paused")
    
    def toggle_play_pause(self, start_from_seconds: Optional[float] = None) -> bool:
        """
        Toggle play/pause state.
        
        Args:
            start_from_seconds: Optional offset to start simulation from
            
        Returns:
            New playing state
        """
        if self.is_playing:
            self.pause()
        else:
            self.play(start_from_seconds)
        return self.is_playing
    
    def set_speed(self, speed: float) -> None:
        """
        Set playback speed multiplier.
        
        Args:
            speed: Speed multiplier (1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0)
        """
        allowed_speeds = [1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]
        
        if speed not in allowed_speeds:
            raise ValueError(
                f"Invalid speed: {speed}. "
                f"Allowed: {allowed_speeds}"
            )
        
        self.speed_multiplier = speed
        logger.info(f"Simulation speed set to {speed}x")
    
    def jump_to_time(self, target_time: datetime) -> None:
        """
        Jump to specific time in session.
        
        Args:
            target_time: Target time to jump to
        """
        if target_time < self.start_time:
            target_time = self.start_time
        elif target_time > self.end_time:
            target_time = self.end_time
        
        self.current_time = target_time
        self.last_update = datetime.now()
        
        if self.on_time_update:
            self.on_time_update(self.current_time)
        
        logger.info(f"Jumped to time: {target_time}")
    
    def jump_to_lap(self, lap_number: int, lap_duration: float = 90.0) -> None:
        """
        Jump to specific lap.
        
        Args:
            lap_number: Target lap number
            lap_duration: Average lap duration in seconds
        """
        lap_offset = timedelta(seconds=lap_duration * (lap_number - 1))
        target_time = self.start_time + lap_offset
        self.jump_to_time(target_time)
    
    def jump_forward(self, seconds: int) -> None:
        """Jump forward by specified seconds."""
        new_time = self.current_time + timedelta(seconds=seconds)
        self.jump_to_time(new_time)
    
    def jump_backward(self, seconds: int) -> None:
        """Jump backward by specified seconds."""
        new_time = self.current_time - timedelta(seconds=seconds)
        self.jump_to_time(new_time)
    
    def restart(self) -> None:
        """Restart simulation from beginning."""
        self.jump_to_time(self.start_time)
        self.pause()
        logger.info("Simulation restarted")
    
    def update(self) -> datetime:
        """
        Update simulation time based on elapsed real time.
        
        Should be called regularly (e.g., every frame).
        
        Returns:
            Updated current time
        """
        if not self.is_playing:
            return self.current_time
        
        now = datetime.now()
        real_elapsed = (now - self.last_update).total_seconds()
        sim_elapsed = real_elapsed * self.speed_multiplier
        
        self.current_time += timedelta(seconds=sim_elapsed)
        self.last_update = now
        
        # Stop at end time
        if self.current_time >= self.end_time:
            self.current_time = self.end_time
            self.pause()
            logger.info("Simulation reached end")
        
        # Trigger callback
        if self.on_time_update:
            self.on_time_update(self.current_time)
        
        return self.current_time
    
    def get_progress(self) -> float:
        """
        Get simulation progress as percentage.
        
        Returns:
            Progress from 0.0 to 100.0
        """
        total_duration = (self.end_time - self.start_time).total_seconds()
        elapsed = (self.current_time - self.start_time).total_seconds()
        
        if total_duration == 0:
            return 100.0
        
        return (elapsed / total_duration) * 100.0
    
    def get_remaining_time(self) -> timedelta:
        """Get remaining time in simulation."""
        return self.end_time - self.current_time
    
    def get_elapsed_time(self) -> timedelta:
        """Get elapsed time in simulation."""
        return self.current_time - self.start_time
    
    def is_at_start(self) -> bool:
        """Check if at session start."""
        return self.current_time <= self.start_time
    
    def is_at_end(self) -> bool:
        """Check if at session end."""
        return self.current_time >= self.end_time
