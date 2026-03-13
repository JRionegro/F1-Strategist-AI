"""Labeling utilities for predictive AI.

Option B target (MVP): Suggested pit window.

In early iterations we define the label as the *next pit lap* (center), with an
optional symmetric window around it.

Later phases can replace this with quantile labels, hazard models, or learned
windows.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence


@dataclass(frozen=True)
class PitWindowLabel:
    """Pit window label for a single (driver, lap) row."""

    start_lap: Optional[int]
    end_lap: Optional[int]
    center_lap: Optional[int]


def next_pit_lap(
    current_lap: int,
    pit_laps: Sequence[int],
    horizon_laps: Optional[int] = None,
) -> Optional[int]:
    """Return the next pit lap strictly after current_lap.

    Args:
        current_lap: Current lap (1-indexed).
        pit_laps: Sorted or unsorted sequence of pit lap numbers.
        horizon_laps: Optional horizon; if set, ignore pits beyond current_lap + horizon_laps.

    Returns:
        Next pit lap, or None if none exists in range.
    """
    candidates = [lap for lap in pit_laps if lap > current_lap]
    if horizon_laps is not None:
        max_lap = current_lap + horizon_laps
        candidates = [lap for lap in candidates if lap <= max_lap]

    if not candidates:
        return None

    return min(candidates)


def make_pit_window_label(
    current_lap: int,
    pit_laps: Sequence[int],
    window_half_width: int = 0,
    horizon_laps: Optional[int] = None,
) -> PitWindowLabel:
    """Create a pit window label.

    MVP behavior:
        - center_lap := next pit lap
        - start_lap := center_lap - window_half_width (clamped to future)
        - end_lap := center_lap + window_half_width

    Args:
        current_lap: Current lap (1-indexed).
        pit_laps: Pit lap numbers.
        window_half_width: Half-width of symmetric window around center.
        horizon_laps: Optional prediction horizon.

    Returns:
        PitWindowLabel with optional start/end/center.
    """
    if window_half_width < 0:
        raise ValueError("window_half_width must be non-negative")

    center = next_pit_lap(
        current_lap=current_lap,
        pit_laps=pit_laps,
        horizon_laps=horizon_laps)
    if center is None:
        return PitWindowLabel(start_lap=None, end_lap=None, center_lap=None)

    start = max(current_lap + 1, center - window_half_width)
    end = max(start, center + window_half_width)

    return PitWindowLabel(start_lap=start, end_lap=end, center_lap=center)
