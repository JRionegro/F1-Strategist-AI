"""
Simulation controller for replay and time manipulation.

Handles simulation playback controls and time progression.
"""

from datetime import datetime, timedelta
from typing import Callable, Dict, Optional, Tuple
import pandas as pd

from src.utils.logging_config import get_logger, LogCategory

# Use categorized logger for simulation
logger = get_logger(LogCategory.SIMULATION)


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
        on_time_update: Optional[Callable[[datetime], None]] = None,
        lap_data: Optional[pd.DataFrame] = None
    ):
        """
        Initialize simulation controller.

        Args:
            start_time: Session start time
            end_time: Session end time
            on_time_update: Callback when time updates
            lap_data: DataFrame with LapNumber and LapStartTime columns for accurate lap tracking
        """
        self.start_time = start_time
        self.end_time = end_time
        self.current_time = start_time
        self.on_time_update = on_time_update
        self.lap_data = lap_data
        self.current_lap = 1

        self.is_playing = False
        self.speed_multiplier = 1.0
        self.last_update = datetime.now()
        self.play_start_time = datetime.now()
        self._lap_windows: Dict[int, Tuple[float, float]] = {}
        self._normalize_lap_seconds_columns()
        self._build_lap_windows()

        logger.info(
            f"Initialized SimulationController: "
            f"{start_time} to {end_time}"
        )
        self._diag_last_log_time = 0.0
        self._log_lap_data_summary()

    def _log_lap_data_summary(self) -> None:
        """Log a concise summary of lap_data for diagnostics."""
        if self.lap_data is None or self.lap_data.empty:
            logger.warning("[LAP_DIAG] lap_data is None/empty")
            return
        cols = list(self.lap_data.columns)
        logger.warning(
            "[LAP_DIAG] lap_data cols=%s rows=%d",
            cols, len(self.lap_data),
        )
        if 'LapStartTime_seconds' in self.lap_data.columns:
            lss = pd.to_numeric(
                self.lap_data['LapStartTime_seconds'],
                errors='coerce',
            ).dropna()
            lnums = pd.to_numeric(
                self.lap_data.get('LapNumber', pd.Series(dtype=float)),
                errors='coerce',
            ).dropna()
            logger.warning(
                "[LAP_DIAG] LapStartTime_seconds: "
                "min=%.1f max=%.1f count=%d | "
                "LapNumber: min=%s max=%s",
                lss.min() if not lss.empty else -1,
                lss.max() if not lss.empty else -1,
                len(lss),
                lnums.min() if not lnums.empty else '?',
                lnums.max() if not lnums.empty else '?',
            )
            # Show first 5 laps
            preview = self.lap_data[[
                c for c in (
                    'LapNumber',
                    'LapStartTime_seconds',
                    'LapEndTime_seconds',
                ) if c in self.lap_data.columns
            ]].head(5)
            logger.warning(
                "[LAP_DIAG] First 5 rows:\n%s",
                preview.to_string(index=False),
            )
        else:
            logger.warning(
                "[LAP_DIAG] No LapStartTime_seconds column"
            )

    def _normalize_lap_seconds_columns(self) -> None:
        """Rebase lap second columns when they are offset from simulation start.

        Some OpenF1 lap payloads use absolute session seconds that do not start
        from zero for the selected simulation window. Rebase them so
        ``get_current_lap`` can compare against elapsed seconds reliably.
        """
        if self.lap_data is None or self.lap_data.empty:
            return

        if 'LapStartTime_seconds' not in self.lap_data.columns:
            return

        try:
            start_seconds = pd.to_numeric(
                self.lap_data['LapStartTime_seconds'],
                errors='coerce',
            )
        except Exception:  # noqa: BLE001
            return

        if 'LapNumber' in self.lap_data.columns:
            lap_numbers = pd.to_numeric(self.lap_data['LapNumber'], errors='coerce')
            valid_lap_numbers = lap_numbers.dropna()
            if not valid_lap_numbers.empty:
                first_lap_number = float(valid_lap_numbers.min())
                baseline_candidates = start_seconds[lap_numbers == first_lap_number].dropna()
            else:
                baseline_candidates = start_seconds.dropna()
        else:
            baseline_candidates = start_seconds.dropna()

        if baseline_candidates.empty:
            return

        baseline_seconds = float(baseline_candidates.min())
        if baseline_seconds <= 120.0:
            return

        self.lap_data = self.lap_data.copy()
        self.lap_data.loc[:, 'LapStartTime_seconds'] = (start_seconds - baseline_seconds).clip(lower=0.0)

        if 'LapEndTime_seconds' in self.lap_data.columns:
            end_seconds = pd.to_numeric(
                self.lap_data['LapEndTime_seconds'],
                errors='coerce',
            )
            self.lap_data.loc[:, 'LapEndTime_seconds'] = (end_seconds - baseline_seconds).clip(lower=0.0)

        logger.warning(
            "Rebased lap timing inside SimulationController by %.3fs",
            baseline_seconds,
        )

    def play(self, start_from_seconds: Optional[float] = None) -> None:
        """
        Start simulation playback.

        Args:
            start_from_seconds: Optional offset in seconds from session start to begin simulation
        """
        if not self.is_playing:
            if start_from_seconds is not None:
                target_time = self.start_time + timedelta(
                    seconds=float(max(start_from_seconds, 0.0))
                )
                self.jump_to_time(target_time)

            self.is_playing = True
            self.last_update = datetime.now()
            self.play_start_time = datetime.now()
            current_offset = (self.current_time - self.start_time).total_seconds()
            logger.info(
                "Simulation started/resumed at offset: %.1fs",
                current_offset,
            )

    def get_elapsed_seconds(self) -> float:
        """
        Get elapsed simulation seconds since play started.

        Returns:
            Elapsed seconds in simulation time (including offset)
        """
        elapsed = (self.current_time - self.start_time).total_seconds()
        return float(max(elapsed, 0.0))

    def pause(self) -> None:
        """Pause simulation playback."""
        if self.is_playing:
            self.is_playing = False
            logger.info("Simulation paused")

    def toggle_play_pause(
            self,
            start_from_seconds: Optional[float] = None) -> bool:
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
            speed: Speed multiplier (1.0 to 10.0 in 0.5 increments)
        """
        allowed_speeds = [
            1.0,
            1.5,
            2.0,
            2.5,
            3.0,
            3.5,
            4.0,
            4.5,
            5.0,
            5.5,
            6.0,
            6.5,
            7.0,
            7.5,
            8.0,
            8.5,
            9.0,
            9.5,
            10.0]

        if speed not in allowed_speeds:
            raise ValueError(
                f"Invalid speed: {speed}. "
                f"Allowed: {allowed_speeds}"
            )

        if self.is_playing:
            self.last_update = datetime.now()
            self.play_start_time = self.last_update

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
        if self.is_playing:
            self.play_start_time = self.last_update

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

    def get_current_lap(self) -> int:
        """
        Get current lap number based on actual lap start times.
        Uses leader's laps to determine race lap count.

        Returns:
            Current lap number (exact, not estimated)
        """
        if self.lap_data is None or self.lap_data.empty:
            logger.warning("No lap data available for lap calculation")
            return 1

        has_lap_start_seconds = 'LapStartTime_seconds' in self.lap_data.columns
        has_lap_start_time = 'LapStartTime' in self.lap_data.columns
        if 'LapNumber' not in self.lap_data.columns or (
            not has_lap_start_seconds and not has_lap_start_time
        ):
            logger.warning("Lap data missing required columns")
            return 1

        try:
            # Use pre-computed seconds columns to avoid timezone/type issues.
            # LapStartTime_seconds is elapsed seconds from session start,
            # directly comparable with get_elapsed_seconds().
            elapsed = self.get_elapsed_seconds()

            if 'LapStartTime_seconds' in self.lap_data.columns:
                data = self.lap_data.copy()
                data['_lap_num'] = pd.to_numeric(
                    data['LapNumber'], errors='coerce')
                data = data.dropna(subset=['_lap_num', 'LapStartTime_seconds'])

                # Throttled diagnostic (every 10s real-time)
                import time as _time
                _now = _time.time()
                if _now - self._diag_last_log_time >= 10.0:
                    self._diag_last_log_time = _now
                    first_start = (
                        data['LapStartTime_seconds'].min()
                        if not data.empty else None
                    )
                    logger.warning(
                        "[LAP_DIAG] get_current_lap: "
                        "elapsed=%.1f first_lap_start=%s "
                        "rows_before_filter=%d "
                        "current_time=%s start_time=%s",
                        elapsed,
                        first_start,
                        len(data),
                        self.current_time,
                        self.start_time,
                    )

                data = data[data['LapStartTime_seconds'] <= elapsed]

                if _now - (self._diag_last_log_time) < 0.1:
                    # Same log cycle — add post-filter info
                    logger.warning(
                        "[LAP_DIAG] after filter: "
                        "rows=%d max_lap=%s",
                        len(data),
                        int(data['_lap_num'].max())
                        if not data.empty else 'NONE',
                    )

                if not data.empty:
                    self.current_lap = int(data['_lap_num'].max())
                    return self.current_lap
                # Before first lap started
                self.current_lap = 1
                return 1

            # ── Fallback: absolute-timestamp path ──────────────────────────
            current_time = self.current_time
            if isinstance(current_time, pd.Timedelta):
                current_time = self.start_time + current_time

            # Pick any driver that has lap data; prefer driver #1 if present.
            driver_nums = self.lap_data['DriverNumber'].unique()
            target_driver = 1 if 1 in driver_nums else (driver_nums[0] if len(driver_nums) else None)
            if target_driver is None:
                return 1
            leader_laps = self.lap_data[
                self.lap_data['DriverNumber'] == target_driver].copy()

            if leader_laps.empty:
                logger.warning("No laps found for any driver")
                return 1

            def _to_absolute_timestamp(value):
                if isinstance(value, pd.Timestamp):
                    return value
                if isinstance(value, pd.Timedelta):
                    return self.start_time + value
                if isinstance(value, datetime):
                    return value
                return pd.NaT

            leader_laps.loc[:, 'LapStartAbs'] = leader_laps['LapStartTime'].apply(
                _to_absolute_timestamp)
            if 'LapEndTime' in leader_laps.columns:
                leader_laps.loc[:, 'LapEndAbs'] = leader_laps['LapEndTime'].apply(
                    _to_absolute_timestamp)
            else:
                leader_laps.loc[:, 'LapEndAbs'] = pd.NaT

            # Filter out formation lap (lap 1 has NaT)
            valid_laps = leader_laps[leader_laps['LapStartAbs'].notna()].copy()

            if valid_laps.empty:
                return 1

            logger.debug(f"[SimController] current_time: {current_time}")
            logger.debug(
                f"[SimController] valid_laps count: {
                    len(valid_laps)}")
            logger.debug(
                f"[SimController] First lap start: {
                    valid_laps['LapStartAbs'].min()}")

            # At start of race (before any lap has started)
            earliest_started_lap = int(valid_laps['LapNumber'].min())
            formation_row = leader_laps[leader_laps['LapNumber'] == 1]
            formation_start = formation_row['LapStartAbs'].iloc[0] if not formation_row.empty else pd.NaT
            formation_time = formation_row['LapTime'].iloc[0] if (
                not formation_row.empty and 'LapTime' in formation_row.columns) else pd.NaT

            has_untimed_formation = pd.isna(formation_start)

            if has_untimed_formation and pd.notna(formation_time):
                expected_start = self.start_time + formation_time
            else:
                expected_start = valid_laps['LapStartAbs'].min()

            if pd.isna(expected_start):
                expected_start = self.start_time

            if current_time <= expected_start:
                if has_untimed_formation:
                    self.current_lap = 1
                    logger.debug(
                        "[SimController] Before race start, returning untimed lap 1")
                else:
                    self.current_lap = earliest_started_lap
                    logger.debug(
                        f"[SimController] Before race start, returning lap {
                            self.current_lap}")
                return self.current_lap

            # Filter laps that have started
            started_laps = valid_laps[valid_laps['LapStartAbs']
                                      <= current_time]

            if started_laps.empty:
                self.current_lap = int(valid_laps['LapNumber'].min())
                logger.debug(
                    f"[SimController] No started laps, returning lap {
                        self.current_lap}")
                return self.current_lap

            logger.debug(
                f"[SimController] started_laps count: {
                    len(started_laps)}")

            # Sort by start time descending to check most recent laps first
            started_laps_sorted = started_laps.sort_values(
                'LapStartAbs', ascending=False)

            # Find the lap currently in progress
            current_lap = int(started_laps_sorted.iloc[0]['LapNumber'])
            logger.debug(
                f"[SimController] Initial current_lap (most recent): {current_lap}")

            # Check if this lap has ended
            for _, lap_row in started_laps_sorted.iterrows():
                lap_num = int(lap_row['LapNumber'])
                lap_start = lap_row['LapStartAbs']
                lap_end = lap_row.get('LapEndAbs', pd.NaT)

                logger.debug(
                    f"[SimController] Checking lap {lap_num}: start={lap_start}, end={lap_end}, current={current_time}")

                # If lap hasn't ended yet, or ended after current time -> in
                # progress
                if pd.isna(lap_end) or lap_end > current_time:
                    current_lap = lap_num
                    logger.debug(
                        f"[SimController] ✅ Lap {lap_num} is IN PROGRESS (end={lap_end})")
                    break
                else:
                    logger.debug(
                        f"[SimController] ❌ Lap {lap_num} has ENDED (end={lap_end} <= current={current_time})")

            logger.debug(f"[SimController] FINAL current_lap: {current_lap}")
            self.current_lap = current_lap
            return self.current_lap

        except Exception as e:
            logger.error(f"Error in get_current_lap: {e}")
            logger.error(
                f"current_time type: {
                    type(
                        self.current_time)}, value: {
                    self.current_time}")
            logger.error(
                f"LapStartTime dtype: {
                    self.lap_data['LapStartTime'].dtype}")
            logger.error(
                f"LapStartTime sample: {
                    self.lap_data['LapStartTime'].iloc[0]}")
            raise

    def _build_lap_windows(self) -> None:
        """Pre-compute lap start/end windows in session seconds."""
        if self.lap_data is None or self.lap_data.empty:
            return

        try:
            sorted_laps = self.lap_data.sort_values(
                'LapNumber').reset_index(drop=True)
        except Exception:  # noqa: BLE001
            return

        prev_end = 0.0
        for idx, row in sorted_laps.iterrows():
            lap_number_raw = row.get('LapNumber')
            try:
                lap_number = int(lap_number_raw)
            except (TypeError, ValueError):
                continue

            start_value = row.get('LapStartTime')
            start_seconds = prev_end

            if isinstance(start_value, pd.Timestamp):
                start_seconds = (start_value - self.start_time).total_seconds()
            elif isinstance(start_value, pd.Timedelta):
                start_seconds = start_value.total_seconds()
            elif isinstance(start_value, datetime):
                start_seconds = (start_value - self.start_time).total_seconds()

            if pd.isna(start_value):
                start_seconds = prev_end

            start_seconds = float(max(start_seconds, prev_end))

            end_seconds: Optional[float] = None
            end_value = row.get('LapEndTime', pd.NaT)
            if isinstance(end_value, pd.Timestamp):
                end_seconds = (end_value - self.start_time).total_seconds()
            elif isinstance(end_value, pd.Timedelta):
                end_seconds = end_value.total_seconds()
            elif isinstance(end_value, datetime):
                end_seconds = (end_value - self.start_time).total_seconds()

            if pd.isna(end_value) or end_seconds is None:
                lap_time_value = row.get('LapTime', pd.NaT)
                if isinstance(lap_time_value,
                              pd.Timedelta) and not pd.isna(lap_time_value):
                    end_seconds = start_seconds + lap_time_value.total_seconds()
                else:
                    next_start = None
                    if idx + 1 < len(sorted_laps):
                        next_start = sorted_laps.iloc[idx +
                                                      1].get('LapStartTime')
                    if isinstance(next_start, pd.Timestamp):
                        end_seconds = (
                            next_start - self.start_time).total_seconds()
                    elif isinstance(next_start, pd.Timedelta) and not pd.isna(next_start):
                        end_seconds = next_start.total_seconds()

            if end_seconds is None:
                end_seconds = start_seconds

            end_seconds = float(max(end_seconds, start_seconds))
            self._lap_windows[lap_number] = (start_seconds, end_seconds)
            prev_end = end_seconds

    def get_lap_window_seconds(
            self, lap_number: int) -> Optional[Tuple[float, float]]:
        """Return start/end session seconds for a lap if available."""
        return self._lap_windows.get(lap_number)

    def clamp_elapsed_to_lap(
            self,
            elapsed_seconds: float,
            lap_number: int) -> float:
        """Clamp elapsed session seconds to the bounds of a lap window."""
        window = self.get_lap_window_seconds(lap_number)
        if window is None:
            return elapsed_seconds

        start_seconds, _ = window
        if elapsed_seconds < start_seconds:
            return start_seconds
        return elapsed_seconds
