"""Lightweight tests that guard regression in the track map dashboard helpers."""
from __future__ import annotations

from typing import Any, Dict, Sequence, cast

import plotly.graph_objects as go

from src.dashboards_dash.track_map_dashboard import TrackMapDashboard


def _build_fake_driver(driver_number: int) -> Dict[str, Any]:
    return {
        "driver_number": driver_number,
        "driver_name": f"Driver {driver_number}",
        "team_name": "Unknown",
    }


def test_create_drivers_only_figure_without_positions_returns_empty() -> None:
    """When no telemetry is available the helper should return an empty layout."""
    dashboard = TrackMapDashboard()
    dashboard.session_loaded = False
    dashboard.provider.positions_df = None

    fig = dashboard.create_drivers_only_figure(1, [_build_fake_driver(1)], elapsed_time=None)
    assert isinstance(fig, go.Figure)
    traces: Sequence[Any] = cast(Sequence[Any], fig.data)
    assert len(traces) == 0


def test_get_circuit_figure_returns_loading_placeholder_when_not_ready() -> None:
    """Ensure the loading placeholder is returned while the base figure is missing."""
    dashboard = TrackMapDashboard()
    circuit_fig = dashboard.get_circuit_figure()
    assert isinstance(circuit_fig, go.Figure)
    circuit_traces: Sequence[Any] = cast(Sequence[Any], circuit_fig.data)
    assert len(circuit_traces) == 0
    annotations = list(getattr(circuit_fig.layout, "annotations", []))
    assert any("Loading" in str(getattr(annotation, "text", "")) for annotation in annotations)
