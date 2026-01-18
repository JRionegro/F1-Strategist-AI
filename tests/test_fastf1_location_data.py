"""Unit tests for the FastF1 position provider integration."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.data.fastf1_position_provider import FastF1PositionProvider
from src.dashboards_dash.track_map_dashboard import TrackMapDashboard


@pytest.fixture
def provider(tmp_path: Path) -> FastF1PositionProvider:
    """Return a provider wired to a temporary cache directory."""
    cache_dir = tmp_path / "fastf1"
    cache_dir.mkdir()
    return FastF1PositionProvider(cache_dir=str(cache_dir))


def test_translate_openf1_session_defaults_to_race() -> None:
    """Ensure the OpenF1 translation keeps defaults sensible."""
    session = {
        "meeting_name": "Bahrain Grand Prix",
        "session_name": "Race",
        "date_start": "2024-03-02T18:00:00Z",
    }
    result = FastF1PositionProvider.translate_openf1_session(session)
    assert result["identifier"] == "R"
    assert result["round"] == "Bahrain"
    assert result["year"] == 2024


def test_cache_path_isolated_per_year(provider: FastF1PositionProvider) -> None:
    """Cache path should reside inside the configured directory."""
    cache_path = provider._get_positions_cache_path(2024, "Bahrain", "R")  # pylint: disable=protected-access
    assert cache_path.parent.name == "2024"
    assert cache_path.name == "Bahrain_R_positions.pkl"


def test_customdata_payload_contains_expected_fields() -> None:
    """Validate shape of customdata payload consumed by Plotly tween helper."""
    dashboard = TrackMapDashboard()
    payload = dashboard._build_customdata(1, {  # pylint: disable=protected-access
        "x": 1.0,
        "y": 2.0,
        "time": 5.0,
        "query_time": 6.0,
        "previous_sample": {"time": 4.5, "x": 0.0, "y": 1.0},
        "next_sample": {"time": 6.5, "x": 2.0, "y": 3.0},
    })
    assert isinstance(payload, list)
    assert len(payload) == 1
    assert pytest.approx(payload[0][0]) == 1.0
    assert pytest.approx(payload[0][1]) == 4.5
    assert pytest.approx(payload[0][4]) == 6.5
