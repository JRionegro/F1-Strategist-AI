"""Tests for simulation timeline alignment helpers."""

from __future__ import annotations

import pandas as pd

from src.utils.simulation_time_alignment import (
    apply_race_control_time_offset,
    resolve_race_control_session_start_time,
    resolve_race_control_offset_seconds,
)


def test_resolve_race_control_offset_from_session_data() -> None:
    """Offset should be read from session track-map metadata."""
    session_data = {
        "track_map": {
            "formation_offset_seconds": 207.172,
        }
    }

    offset = resolve_race_control_offset_seconds(session_data)
    assert offset == 207.172


def test_resolve_race_control_offset_ignores_invalid_payload() -> None:
    """Invalid or missing values should safely return zero offset."""
    assert resolve_race_control_offset_seconds(None) == 0.0
    assert resolve_race_control_offset_seconds({}) == 0.0
    assert resolve_race_control_offset_seconds({"track_map": {}}) == 0.0
    assert resolve_race_control_offset_seconds({"track_map": {"formation_offset_seconds": -5}}) == 0.0


def test_apply_race_control_time_offset_keeps_controller_elapsed_time() -> None:
    """Race control should use controller elapsed time without adding offset."""
    session_data = {
        "track_map": {
            "formation_offset_seconds": 180.0,
        }
    }

    aligned = apply_race_control_time_offset(540.0, session_data)
    assert aligned == 540.0


def test_qatar_guard_prevents_two_lap_delay_from_double_offset() -> None:
    """Protect against adding formation offset twice in race-control filters."""
    formation_offset = 207.172
    lap_duration_reference = 89.0
    # Controller-aligned elapsed seconds when SC is deployed in Qatar sample.
    sc_elapsed_seconds = 573.828

    wrong_double_offset = sc_elapsed_seconds + formation_offset
    lap_delay = (wrong_double_offset - sc_elapsed_seconds) / lap_duration_reference

    assert lap_delay > 2.0
    assert apply_race_control_time_offset(
        sc_elapsed_seconds,
        {"track_map": {"formation_offset_seconds": formation_offset}},
    ) == sc_elapsed_seconds


def test_resolve_race_control_session_start_time_without_shift() -> None:
    """Start time unchanged when only formation offset is present.

    The function only adjusts when ``race_clock_start_shift_seconds``
    is provided.  With just ``formation_offset_seconds`` it returns the
    controller start unchanged so race-control events are not delayed.
    """
    controller_start = pd.Timestamp("2025-11-30 16:06:54.344", tz="UTC")
    session_data = {"track_map": {"formation_offset_seconds": 207.172}}

    resolved = resolve_race_control_session_start_time(
        controller_start, session_data
    )

    assert resolved == controller_start
