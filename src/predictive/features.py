"""Feature utilities for predictive AI.

This starter keeps feature computation:
- deterministic
- side-effect free
- independent from the running Dash app

Later phases will add adapters that build these features from session objects.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Optional


def compute_stint_lap(lap_number: int, last_pit_lap: Optional[int]) -> int:
    """Compute stint lap index.

    Args:
        lap_number: Current lap number (1-indexed).
        last_pit_lap: Lap number of the most recent pit stop, if known.

    Returns:
        Stint lap index (0 if unknown).
    """
    if last_pit_lap is None:
        return 0
    if last_pit_lap < 0:
        return 0
    if lap_number <= last_pit_lap:
        return 0
    return lap_number - last_pit_lap


def rolling_mean(values: Sequence[float], window: int) -> Optional[float]:
    """Compute a simple rolling mean on the tail of a sequence.

    Args:
        values: Sequence of numeric values.
        window: Window size.

    Returns:
        Rolling mean over the last `window` values, or None if unavailable.
    """
    if window <= 0:
        raise ValueError("window must be positive")
    if not values:
        return None

    tail = list(values)[-window:]
    if not tail:
        return None

    return sum(tail) / float(len(tail))
