"""Integration regression test for Qatar 2025 race-control timing.

This validates the full path from simulation-time alignment helper to
RaceControlDashboard time filtering/status extraction.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.dashboards_dash.race_control_dashboard import RaceControlDashboard
from src.utils.simulation_time_alignment import (
    apply_race_control_time_offset,
    resolve_race_control_session_start_time,
)


class MockOpenF1Provider:
    """Minimal provider used by RaceControlDashboard in this integration test."""

    def __init__(self, messages: pd.DataFrame) -> None:
        self._messages = messages

    def get_race_control_messages(self, session_key: int) -> pd.DataFrame:
        """Return race-control messages for the requested session."""
        _ = session_key
        return self._messages.copy()

    def get_drivers(self, session_key: int) -> pd.DataFrame:
        """Return lightweight driver data for dashboard internals."""
        _ = session_key
        return pd.DataFrame(
            [
                {"DriverNumber": "1", "Abbreviation": "VER"},
            ]
        )


def _build_qatar_like_messages(race_start: pd.Timestamp) -> pd.DataFrame:
    """Create a tiny OpenF1-like race-control timeline around SC deployment."""
    return pd.DataFrame(
        [
            {
                "Time": race_start + pd.Timedelta(seconds=560.0),
                "Category": "Info",
                "Message": "TRACK CLEAR",
            },
            {
                "Time": race_start + pd.Timedelta(seconds=573.828),
                "Category": "SafetyCar",
                "Message": "SAFETY CAR DEPLOYED",
            },
        ]
    )


@pytest.mark.integration
def test_qatar_sc_appears_at_expected_elapsed_time_without_double_offset() -> None:
    """SC must be visible at deployment time using controller-aligned elapsed seconds."""
    session_key = 9850
    race_start = pd.Timestamp("2025-11-30 16:03:27.172", tz="UTC")
    session_data = {"track_map": {"formation_offset_seconds": 207.172}}

    dashboard = RaceControlDashboard(MockOpenF1Provider(_build_qatar_like_messages(race_start)))

    messages, _ = dashboard._get_messages_and_drivers(session_key)
    assert messages is not None
    assert len(messages) == 2

    pre_sc_elapsed = apply_race_control_time_offset(573.0, session_data)
    pre_sc_status = dashboard.get_status_summary(
        session_key=session_key,
        simulation_time=pre_sc_elapsed,
        session_start_time=race_start,
        current_lap=7,
    )
    assert pre_sc_status["safety_car"] is False
    assert pre_sc_status["flag"] == "GREEN"

    sc_elapsed = apply_race_control_time_offset(573.828, session_data)
    sc_status = dashboard.get_status_summary(
        session_key=session_key,
        simulation_time=sc_elapsed,
        session_start_time=race_start,
        current_lap=7,
    )
    assert sc_status["safety_car"] is True
    assert sc_status["flag"] == "SC"


@pytest.mark.integration
def test_qatar_sc_is_on_time_when_controller_start_is_shifted() -> None:
    """SC must still appear on time when controller start includes formation offset."""
    session_key = 9850
    race_start = pd.Timestamp("2025-11-30 16:03:27.172", tz="UTC")
    session_data = {"track_map": {"formation_offset_seconds": 207.172}}
    shifted_controller_start = race_start + pd.Timedelta(seconds=207.172)

    dashboard = RaceControlDashboard(MockOpenF1Provider(_build_qatar_like_messages(race_start)))
    messages, _ = dashboard._get_messages_and_drivers(session_key)
    assert messages is not None

    corrected_start = resolve_race_control_session_start_time(
        shifted_controller_start,
        session_data,
    )

    status = dashboard.get_status_summary(
        session_key=session_key,
        simulation_time=apply_race_control_time_offset(573.828, session_data),
        session_start_time=corrected_start,
        current_lap=7,
    )
    assert status["safety_car"] is True
    assert status["flag"] == "SC"
