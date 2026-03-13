"""Default tire compound thresholds with optional overrides."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Mapping, Optional


TireWindow = Dict[str, int]


DEFAULT_TIRE_WINDOWS: Dict[str, TireWindow] = {
    "SOFT": {"min": 8, "optimal": 12, "max": 18},
    "MEDIUM": {"min": 15, "optimal": 22, "max": 30},
    "HARD": {"min": 25, "optimal": 35, "max": 45},
    "INTERMEDIATE": {"min": 10, "optimal": 20, "max": 35},
    "WET": {"min": 15, "optimal": 30, "max": 50},
}


def resolve_tire_windows(
    overrides: Mapping[str, Mapping[str, int]] | None
) -> Dict[str, TireWindow]:
    """Merge optional overrides into default tire windows.

    Args:
        overrides: Mapping of compound -> window values. Missing keys
            fall back to defaults.

    Returns:
        Merged dictionary with normalized compound keys.
    """

    resolved: Dict[str, TireWindow] = {compound: window.copy(
    ) for compound, window in DEFAULT_TIRE_WINDOWS.items()}

    if not overrides:
        return resolved

    for compound, window in overrides.items():
        key = str(compound).upper()
        if key not in resolved:
            resolved[key] = {}
        for field, value in window.items():
            resolved[key][field] = int(value)

    return resolved


def extract_tire_windows_from_text(text: str) -> Dict[str, TireWindow]:
    """Extract tire window overrides from free-form strategy text.

    This parser scans each line for compound names and uses the first three
    integers as min/optimal/max in that order.
    """

    overrides: Dict[str, TireWindow] = {}
    compounds = ["SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"]

    for line in text.splitlines():
        upper = line.upper()
        for compound in compounds:
            if compound not in upper:
                continue
            numbers = [int(x) for x in re.findall(r"\d+", line)]
            if len(numbers) < 3:
                continue
            overrides[compound] = {
                "min": numbers[0],
                "optimal": numbers[1],
                "max": numbers[2],
            }
    return overrides


def load_tire_window_overrides_from_path(
    path: str | Path,
) -> Optional[Dict[str, TireWindow]]:
    """Load tire window overrides from a strategy document path.

    Returns None if the file is missing or no overrides are detected.
    """

    path = Path(path)
    if not path.exists():
        return None

    content = path.read_text(encoding="utf-8", errors="ignore")
    overrides = extract_tire_windows_from_text(content)
    return overrides or None


__all__ = [
    "DEFAULT_TIRE_WINDOWS",
    "resolve_tire_windows",
    "extract_tire_windows_from_text",
    "load_tire_window_overrides_from_path",
]
