"""Track map dashboard utilities for the Dash front-end."""
from __future__ import annotations

import logging
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import plotly.graph_objects as go

from src.data.fastf1_position_provider import FastF1PositionProvider
from src.utils.logging_config import LogCategory, get_logger

logger = get_logger(LogCategory.DASHBOARD)


TEAM_COLORS: Dict[str, str] = {
    "Red Bull Racing": "#3671C6",
    "Ferrari": "#E8002D",
    "Mercedes": "#27F4D2",
    "McLaren": "#FF8000",
    "Aston Martin": "#229971",
    "Alpine": "#FF87BC",
    "Williams": "#64C4FF",
    "Haas F1 Team": "#B6BABD",
    "RB": "#6692FF",
    "Kick Sauber": "#52E252",
    "Unknown": "#FFFFFF",
}


class TrackMapDashboard:
    """Expose helper methods to build the circuit map and driver overlays."""

    def __init__(self, cache_dir: str = "./cache") -> None:
        self.provider = FastF1PositionProvider(cache_dir=cache_dir)
        self.circuit_outline: Optional[Dict[str, pd.DataFrame]] = None
        self.session_loaded: bool = False
        self._base_figure: Optional[go.Figure] = None
        self._axis_ranges: Optional[Tuple[Tuple[float, float], Tuple[float, float]]] = None
        self._load_failed: bool = False
        self._last_session_key: Optional[Tuple[int, str, str]] = None
        logger.info("TrackMapDashboard initialized")

    @staticmethod
    def _build_customdata(driver_number: int, position: Dict[str, Any]) -> List[List[float]]:
        """Return customdata payload used by the tween helper."""
        prev_sample = position.get("previous_sample") or {}
        next_sample = position.get("next_sample") or {}
        current_time = float(position.get("time", 0.0))
        query_time = float(position.get("query_time", current_time))
        prev_time = float(prev_sample.get("time", current_time))
        next_time = float(next_sample.get("time", current_time))
        prev_x = float(prev_sample.get("x", position.get("x", 0.0)))
        prev_y = float(prev_sample.get("y", position.get("y", 0.0)))
        next_x = float(next_sample.get("x", position.get("x", 0.0)))
        next_y = float(next_sample.get("y", position.get("y", 0.0)))

        return [[
            float(driver_number),
            prev_time,
            prev_x,
            prev_y,
            next_time,
            next_x,
            next_y,
            query_time,
            current_time,
        ]]

    def load_session(self, year: int, country: str, session_type: str = "R") -> bool:
        """Load FastF1 telemetry and cache the circuit outline."""
        session_key = (year, country, session_type)
        if self._last_session_key == session_key and self.session_loaded:
            logger.info("Track map session already loaded: %s", session_key)
            return True

        self.session_loaded = False
        self._load_failed = False
        self._last_session_key = session_key

        logger.info("Loading track map session: %s %s %s", year, country, session_type)
        if not self.provider.load_session(year, country, session_type):
            self._load_failed = True
            return False

        self.circuit_outline = self.provider.get_circuit_outline()
        if self.circuit_outline is None:
            logger.warning("Unable to build circuit outline")
            self._load_failed = True
            return False

        self._create_base_figure()
        self.session_loaded = True
        logger.info("Track map session ready")
        return True

    def _create_base_figure(self) -> None:
        """Populate the static circuit figure and cache axis ranges."""
        outline = self.circuit_outline
        if outline is None:
            return

        self._base_figure = go.Figure()

        if "center" in outline and not outline["center"].empty:
            center_df = outline["center"].astype(float)
            x_vals = center_df["X"].to_numpy()
            y_vals = center_df["Y"].to_numpy()
            x_span = float(x_vals.max() - x_vals.min()) if x_vals.size else 0.0
            y_span = float(y_vals.max() - y_vals.min()) if y_vals.size else 0.0
            padding = 0.05
            x_pad = max(200.0, x_span * padding)
            y_pad = max(200.0, y_span * padding)
            x_range = (float(x_vals.min() - x_pad), float(x_vals.max() + x_pad))
            y_range = (float(y_vals.min() - y_pad), float(y_vals.max() + y_pad))
        else:
            x_range = (-5000.0, 5000.0)
            y_range = (-5000.0, 5000.0)

        self._axis_ranges = (x_range, y_range)

        self._base_figure.add_trace(go.Scatter(
            x=outline["outer"]["X"],
            y=outline["outer"]["Y"],
            mode="lines",
            line=dict(color="#666666", width=2),
            name="Track Edge",
            hoverinfo="skip",
            showlegend=False,
        ))

        self._base_figure.add_trace(go.Scatter(
            x=outline["inner"]["X"],
            y=outline["inner"]["Y"],
            mode="lines",
            line=dict(color="#666666", width=2),
            name="Track Edge",
            hoverinfo="skip",
            showlegend=False,
        ))

        self._base_figure.update_layout(
            xaxis=dict(
                title="",
                showgrid=False,
                showticklabels=False,
                zeroline=False,
                scaleanchor="y",
                scaleratio=1,
                range=list(x_range),
            ),
            yaxis=dict(
                title="",
                showgrid=False,
                showticklabels=False,
                zeroline=False,
                range=list(y_range),
            ),
            plot_bgcolor="#1a1a1a",
            paper_bgcolor="#0d0d0d",
            font=dict(color="white"),
            hovermode="closest",
            margin=dict(l=10, r=10, t=10, b=10),
            autosize=True,
            legend=dict(
                title="Teams",
                orientation="v",
                x=1.02,
                y=1,
                bgcolor="rgba(0,0,0,0.5)",
                bordercolor="white",
                borderwidth=1,
            ),
            uirevision="track-map-constant",
        )

    def create_figure(
        self,
        current_lap: int,
        driver_data: List[Dict[str, Any]],
        elapsed_time: Optional[float] = None,
        width: int = 1200,
        height: int = 800,
    ) -> go.Figure:
        """Return full circuit figure with markers."""
        if not self.session_loaded or self._base_figure is None:
            return self._create_error_figure(
                "Session not loaded. Track map unavailable.",
                width,
                height,
            )

        fig = go.Figure(self._base_figure.to_dict())
        fig.update_layout(
            title=dict(
                text=f"Track Positions - Lap {current_lap}",
                font=dict(size=20, color="white"),
            ),
            width=width,
            height=height,
            uirevision="track-map-constant",
            transition=dict(duration=600, easing="linear"),
        )

        if self._axis_ranges is not None:
            fig.update_xaxes(range=list(self._axis_ranges[0]))
            fig.update_yaxes(range=list(self._axis_ranges[1]))

        sorted_drivers = sorted(driver_data, key=lambda item: item["driver_number"])
        driver_numbers = [entry["driver_number"] for entry in sorted_drivers]
        positions = self.provider.get_all_driver_positions(
            lap_number=current_lap,
            driver_numbers=driver_numbers,
            elapsed_time=elapsed_time,
        )

        if not positions:
            fig.add_annotation(
                text=f"No position data available for lap {current_lap}",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=16, color="orange"),
            )
            return fig

        seen_teams: Dict[str, bool] = {}
        for driver in sorted_drivers:
            driver_number = driver["driver_number"]
            if driver_number not in positions:
                continue

            position = positions[driver_number]
            team = driver.get("team_name", "Unknown")
            color = TEAM_COLORS.get(team, TEAM_COLORS["Unknown"])
            custom_data = self._build_customdata(driver_number, position)

            fig.add_trace(go.Scatter(
                x=[position["x"]],
                y=[position["y"]],
                mode="markers+text",
                marker=dict(
                    size=20,
                    color=color,
                    line=dict(color="white", width=2),
                ),
                text=[str(driver_number)],
                textposition="middle center",
                textfont=dict(color="white", size=10, family="Arial Black"),
                name=team if not seen_teams.get(team) else None,
                legendgroup=team,
                showlegend=team not in seen_teams,
                hovertemplate=(
                    f"<b>{driver.get('driver_name', driver_number)}</b><br>"
                    f"Team: {team}<br>Lap {current_lap}<extra></extra>"
                ),
                customdata=custom_data,
                uid=str(driver_number),
            ))
            seen_teams[team] = True

        return fig

    def _create_error_figure(self, message: str, width: int, height: int) -> go.Figure:
        """Return fallback figure with an error message."""
        fig = go.Figure()
        fig.add_annotation(
            text=message,
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=18, color="red"),
        )
        fig.update_layout(
            title="Track Map",
            plot_bgcolor="#1a1a1a",
            paper_bgcolor="#0d0d0d",
            font=dict(color="white"),
            width=width,
            height=height,
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
        )
        return fig

    def create_loading_figure(self, width: int = 1200, height: int = 800) -> go.Figure:
        """Return loading placeholder."""
        return self._create_error_figure("⏳ Loading track map session...", width, height)

    def create_no_data_figure(self, lap_number: int, width: int = 1200, height: int = 800) -> go.Figure:
        """Return placeholder when telemetry is unavailable."""
        return self._create_error_figure(
            f"No position data for lap {lap_number}",
            width,
            height,
        )

    def get_session_info(self) -> Optional[Dict[str, Any]]:
        """Expose provider session info."""
        return self.provider.get_session_info()

    def clear_cache(self) -> None:
        """Clear position cache from memory."""
        self.provider.clear_cache()

    def get_circuit_figure(self) -> go.Figure:
        """Return cached circuit layer or loading placeholder."""
        return self._base_figure if self._base_figure is not None else self.create_loading_figure()

    def create_drivers_only_figure(
        self,
        current_lap: int,
        driver_data: List[Dict[str, Any]],
        elapsed_time: Optional[float] = None,
    ) -> go.Figure:
        """Return transparent figure containing driver markers only."""
        if not self.session_loaded:
            positions_ready = (
                self.provider.positions_df is not None
                and not self.provider.positions_df.empty
            )
            if not positions_ready:
                return self.create_empty_drivers_figure()

        if self._axis_ranges is not None:
            x_range = list(self._axis_ranges[0])
            y_range = list(self._axis_ranges[1])
        else:
            x_range = [-5000.0, 5000.0]
            y_range = [-5000.0, 5000.0]

        sorted_drivers = sorted(driver_data, key=lambda item: item["driver_number"])
        driver_numbers = [entry["driver_number"] for entry in sorted_drivers]
        positions = self.provider.get_all_driver_positions(
            lap_number=current_lap,
            driver_numbers=driver_numbers,
            elapsed_time=elapsed_time,
        )

        fig = go.Figure()
        for driver in sorted_drivers:
            driver_number = driver["driver_number"]
            if driver_number not in positions:
                continue

            position = positions[driver_number]
            team = driver.get("team_name", "Unknown")
            color = TEAM_COLORS.get(team, TEAM_COLORS["Unknown"])
            custom_data = self._build_customdata(driver_number, position)

            fig.add_trace(go.Scatter(
                x=[position["x"]],
                y=[position["y"]],
                mode="markers+text",
                marker=dict(
                    size=20,
                    color=color,
                    line=dict(color="white", width=2),
                ),
                text=[str(driver_number)],
                textposition="middle center",
                textfont=dict(color="white", size=10, family="Arial Black"),
                name=driver.get("driver_name", str(driver_number)),
                hovertext=f"{driver.get('driver_name', driver_number)} ({team})",
                hoverinfo="text",
                customdata=custom_data,
                uid=str(driver_number),
            ))

        fig.update_layout(
            xaxis=dict(
                range=x_range,
                showgrid=False,
                showticklabels=False,
                zeroline=False,
                scaleanchor="y",
                scaleratio=1,
            ),
            yaxis=dict(
                range=y_range,
                showgrid=False,
                showticklabels=False,
                zeroline=False,
            ),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            margin=dict(l=10, r=10, t=10, b=10),
            autosize=True,
            hovermode="closest",
            uirevision="drivers-constant",
            transition=dict(duration=600, easing="linear"),
        )

        return fig

    def create_empty_drivers_figure(self) -> go.Figure:
        """Return empty transparent figure."""
        fig = go.Figure()
        fig.update_layout(
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            margin=dict(l=0, r=0, t=0, b=0),
        )
        return fig


_TRACK_MAP_DASHBOARD: Optional[TrackMapDashboard] = None
_TRACK_MAP_LOCK: Lock = Lock()


def get_track_map_dashboard(cache_dir: str = "./cache") -> TrackMapDashboard:
    """Return singleton TrackMapDashboard instance."""
    global _TRACK_MAP_DASHBOARD
    with _TRACK_MAP_LOCK:
        if _TRACK_MAP_DASHBOARD is None:
            _TRACK_MAP_DASHBOARD = TrackMapDashboard(cache_dir=cache_dir)
            logger.info("Track map dashboard singleton created")
        return _TRACK_MAP_DASHBOARD
