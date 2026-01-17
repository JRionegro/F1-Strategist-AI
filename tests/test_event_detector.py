"""Tests for proactive race event detector."""

from datetime import UTC, datetime

import pandas as pd

from src.data.openf1_data_provider import OpenF1DataProvider
from src.session.event_detector import RaceEventDetector


class _FakeProvider(OpenF1DataProvider):
    """Minimal OpenF1 provider stub for pit window tests."""

    def __init__(self) -> None:
        super().__init__(rate_limit_delay=0.0, verify_ssl=True)

    @staticmethod
    def get_stints(session_key: int, driver_number: int) -> pd.DataFrame:  # noqa: D401
        """Return predefined stint data for the requested driver."""
        _ = session_key  # Explicitly unused in stub
        _ = driver_number
        data = [
            {
                "DriverNumber": 4,
                "StintNumber": 1,
                "StintStart": 1,
                "StintEnd": 12,
                "Compound": "SOFT",
                "TyreAge": 0,
            },
            {
                "DriverNumber": 4,
                "StintNumber": 2,
                "StintStart": 13,
                "StintEnd": 28,
                "Compound": "MEDIUM",
                "TyreAge": 2,
            },
            {
                "DriverNumber": 4,
                "StintNumber": 3,
                "StintStart": 29,
                "StintEnd": None,
                "Compound": "HARD",
                "TyreAge": 0,
            },
        ]
        return pd.DataFrame(data)


def test_pit_window_alert_uses_active_stint_compound() -> None:
    """Ensure pit window alerts reference the active tire compound."""
    provider = _FakeProvider()
    detector = RaceEventDetector(
        provider,
        tire_windows={
            "SOFT": {"min": 1, "optimal": 5, "max": 8},
            "MEDIUM": {"min": 4, "optimal": 10, "max": 15},
            "HARD": {"min": 8, "optimal": 18, "max": 25},
        },
    )

    event = detector._check_pit_window(  # pylint: disable=protected-access
        session_key=123,
        current_time=datetime.now(UTC),
        current_lap=16,
        driver_number=4,
        total_laps=57,
    )

    assert event is not None, "Expected pit window event to be generated"
    assert "MEDIUM" in event.message
    assert event.data["compound"] == "MEDIUM"
    assert event.data["stint_age"] == 5


def test_stint_age_respects_tyre_age_offset() -> None:
    """Stint age should include tyre age at stint start."""
    provider = _FakeProvider()
    detector = RaceEventDetector(
        provider,
        tire_windows={
            "SOFT": {"min": 1, "optimal": 5, "max": 8},
            "MEDIUM": {"min": 4, "optimal": 10, "max": 15},
            "HARD": {"min": 8, "optimal": 18, "max": 25},
        },
    )

    event = detector._check_pit_window(  # pylint: disable=protected-access
        session_key=123,
        current_time=datetime.now(UTC),
        current_lap=20,
        driver_number=4,
        total_laps=57,
    )

    assert event is not None
    # Medium stint starts lap 13 with tyre age 2 -> (20-13)=7 -> total 9
    assert event.data["stint_age"] == 9
