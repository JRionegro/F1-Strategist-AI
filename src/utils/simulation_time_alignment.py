"""Helpers to align simulation time across dashboard data sources."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

import pandas as pd


def resolve_race_control_offset_seconds(session_data: Optional[Dict[str, Any]]) -> float:
    """Return the race-control offset inferred from loaded session metadata."""
    if not isinstance(session_data, dict):
        return 0.0

    track_map_payload = session_data.get("track_map")
    offset_value: Any = None
    if isinstance(track_map_payload, dict):
        offset_value = track_map_payload.get("formation_offset_seconds")

    # Backward/alternate payload shapes used in callbacks/store snapshots.
    if offset_value is None:
        offset_value = session_data.get("formation_offset_seconds")

    if isinstance(offset_value, str):
        try:
            offset_value = float(offset_value.strip())
        except (TypeError, ValueError):
            return 0.0

    if not isinstance(offset_value, (int, float)):
        return 0.0

    return max(float(offset_value), 0.0)


def apply_race_control_time_offset(
    simulation_time_seconds: float,
    session_data: Optional[Dict[str, Any]],
) -> float:
    """Return race-control effective simulation seconds.

    The simulation controller start time is already aligned to race start.
    Race control must therefore use raw elapsed simulation seconds to avoid
    double-applying formation offsets and delaying SC/VSC events.

    The ``session_data`` argument is intentionally accepted for API
    compatibility with callers and for future diagnostics.
    """
    _ = session_data
    return float(simulation_time_seconds)


def resolve_race_control_session_start_time(
    controller_start_time: datetime | pd.Timestamp,
    session_data: Optional[Dict[str, Any]],
) -> pd.Timestamp:
    """Return the session start timestamp for race-control filtering.

    The simulation controller rebases lap timing so elapsed=0 equals
    lap-1 start, but ``controller.start_time`` only includes the
    formation-lap offset (small, ~200 s) rather than the full gap
    between ``session.date`` and lap-1 in FastF1's timeline (~3500 s).

    Track Map compensates via ``provider.clamp_session_time()``; Race
    Control must compensate here by adding the remaining gap so that
    ``start + elapsed`` always equals the real UTC instant of the
    corresponding race moment.
    """
    start_timestamp = pd.Timestamp(controller_start_time)

    if not isinstance(session_data, dict):
        return start_timestamp

    track_map = session_data.get("track_map")
    if not isinstance(track_map, dict):
        return start_timestamp

    shift = track_map.get("race_clock_start_shift_seconds")
    offset = track_map.get("formation_offset_seconds")

    if not isinstance(shift, (int, float)):
        return start_timestamp
    if not isinstance(offset, (int, float)):
        offset = 0.0

    extra = float(shift) - float(offset)
    if extra > 0:
        start_timestamp = start_timestamp + pd.Timedelta(
            seconds=extra
        )

    return start_timestamp
