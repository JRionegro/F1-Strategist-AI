"""Track map dashboard utilities for the Dash front-end."""
from __future__ import annotations

import math
from numbers import Real
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

FOCUS_OUTLINE_COLOR = "#e10600"
FOCUS_ALT_OUTLINE_COLOR = "#f5ff00"


class TrackMapDashboard:
    """Expose helper methods to build the circuit map and driver overlays."""

    def __init__(self, cache_dir: str = "./cache") -> None:
        self.provider = FastF1PositionProvider(cache_dir=cache_dir)
        self.circuit_outline: Optional[Dict[str, pd.DataFrame]] = None
        self.session_loaded: bool = False
        self._base_figure: Optional[go.Figure] = None
        self._axis_ranges: Optional[Tuple[Tuple[float,
                                                float], Tuple[float, float]]] = None
        self._load_failed: bool = False
        self._last_session_key: Optional[Tuple[int, str, str]] = None
        logger.info("TrackMapDashboard initialized")

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> Optional[Tuple[int, int, int]]:
        """Convert hex color to RGB tuple."""
        if not isinstance(hex_color, str):
            return None

        value = hex_color.strip().lstrip("#")
        if len(value) == 3:
            value = "".join(ch * 2 for ch in value)
        if len(value) != 6:
            return None

        try:
            r = int(value[0:2], 16)
            g = int(value[2:4], 16)
            b = int(value[4:6], 16)
        except ValueError:
            return None
        return r, g, b

    @classmethod
    def _should_use_dark_text(cls, hex_color: str) -> bool:
        """Return True when the foreground should be dark for contrast."""
        rgb = cls._hex_to_rgb(hex_color)
        if rgb is None:
            return False

        r, g, b = rgb
        brightness = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
        return brightness >= 0.68

    @classmethod
    def _is_red_hue(cls, hex_color: str) -> bool:
        """Return True when the provided color is strongly red."""
        rgb = cls._hex_to_rgb(hex_color)
        if rgb is None:
            return False

        r, g, b = rgb
        return r >= 200 and g <= 90 and b <= 90

    @classmethod
    def resolve_marker_style(cls, driver: Dict[str, Any]) -> Dict[str, Any]:
        """Return marker styling based on team color and focus state."""
        team = driver.get("team_name", "Unknown")
        fill_color = TEAM_COLORS.get(team, TEAM_COLORS["Unknown"])
        text_color = "#000000" if cls._should_use_dark_text(
            fill_color) else "#FFFFFF"
        is_focus = bool(driver.get("is_focus_driver"))
        is_retired = bool(driver.get("retired"))

        if is_retired:
            fill_color = "#3b3b3b"
            text_color = "#ffdddd"
            outline_color = "#ff4d4f" if not is_focus else FOCUS_ALT_OUTLINE_COLOR
            outline_width = 3 if is_focus else 2
        else:
            outline_color = FOCUS_OUTLINE_COLOR if is_focus else "white"
            if is_focus and cls._is_red_hue(fill_color):
                outline_color = FOCUS_ALT_OUTLINE_COLOR
            outline_width = 3 if is_focus else 2
        return {
            "fill_color": fill_color,
            "text_color": text_color,
            "outline_color": outline_color,
            "outline_width": outline_width,
        }

    @staticmethod
    def _build_customdata(
        driver_number: int,
        position: Dict[str, Any],
        fallback_lap: int = 1,
    ) -> List[List[float]]:
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
        lap_raw = position.get("lap_number")
        if isinstance(lap_raw, Real):
            lap_value = float(lap_raw)
            if math.isfinite(lap_value) and lap_value >= 1.0:
                lap_number = lap_value
            else:
                lap_number = float(max(fallback_lap, 1))
        else:
            lap_number = float(max(fallback_lap, 1))

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
            lap_number,
        ]]

    @staticmethod
    def build_hovertemplate(driver: Dict[str, Any], team: str) -> str:
        """Return hovertemplate string for a driver marker."""
        driver_label = driver.get("driver_name") or driver.get(
            "driver_number") or "Driver"
        lines = [
            f"<b>{driver_label}</b>",
            f"Team: {team}",
            "Lap %{customdata[9]:.0f}",
        ]

        if driver.get("retired"):
            status_text = str(driver.get("retired_status") or "Retired")
            retired_lap = driver.get("retired_lap")
            if isinstance(retired_lap, int) and retired_lap >= 1:
                lines.append(f"Status: {status_text} (Lap {retired_lap})")
            else:
                lines.append(f"Status: {status_text}")

        return "<br>".join(lines) + "<extra></extra>"

    def get_retirement_marker_position(
            self, order_index: int) -> Tuple[float, float]:
        """Return off-track coordinates to display retired drivers consistently."""
        if self._axis_ranges is None:
            base_x = 4800.0
            base_y = 4800.0
            step_y = 180.0
            return base_x, base_y - (order_index + 1) * step_y

        (x_min, x_max), (y_min, y_max) = self._axis_ranges
        x_span = x_max - x_min
        y_span = y_max - y_min
        x_offset = max(250.0, x_span * 0.12)
        y_step = max(160.0, y_span * 0.08)
        anchor_x = x_max + x_offset
        anchor_y = y_max - (order_index + 1) * y_step
        return float(anchor_x), float(anchor_y)

    def get_axis_ranges(
            self) -> Optional[Tuple[Tuple[float, float], Tuple[float, float]]]:
        """Expose cached axis ranges for zoom resets."""
        return self._axis_ranges

    def load_session(
            self,
            year: int,
            country: str,
            session_type: str = "R") -> bool:
        """Load FastF1 telemetry and cache the circuit outline."""
        session_key = (year, country, session_type)
        if self._last_session_key == session_key and self.session_loaded:
            logger.info("Track map session already loaded: %s", session_key)
            return True

        self.session_loaded = False
        self._load_failed = False
        self._last_session_key = session_key

        logger.info(
            "Loading track map session: %s %s %s",
            year,
            country,
            session_type)
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
            left_pad = x_pad * 0.6
            right_pad = x_pad * 1.6
            x_range = (
                float(x_vals.min() - left_pad),
                float(x_vals.max() + right_pad),
            )
            y_range = (
                float(
                    y_vals.min() -
                    y_pad),
                float(
                    y_vals.max() +
                    y_pad))
        else:
            x_range = (-5000.0, 5000.0)
            y_range = (-5000.0, 5000.0)

        extra_x = max(250.0, (x_range[1] - x_range[0]) * 0.12)
        extra_y = max(120.0, (y_range[1] - y_range[0]) * 0.06)
        expanded_x_range = (float(x_range[0]), float(x_range[1] + extra_x))
        expanded_y_range = (float(y_range[0]), float(y_range[1] + extra_y))

        self._axis_ranges = (expanded_x_range, expanded_y_range)

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
                range=list(expanded_x_range),
            ),
            yaxis=dict(
                title="",
                showgrid=False,
                showticklabels=False,
                zeroline=False,
                range=list(expanded_y_range),
            ),
            plot_bgcolor="#1a1a1a",
            paper_bgcolor="#0d0d0d",
            font=dict(color="white"),
            hovermode="closest",
            margin=dict(l=28, r=10, t=10, b=70),
            autosize=True,
            legend=dict(
                title=None,
                orientation="h",
                x=0.02,
                y=-0.16,
                xanchor="left",
                yanchor="top",
                bgcolor="rgba(0,0,0,0.35)",
                bordercolor="white",
                borderwidth=1,
                font=dict(size=9),
                entrywidthmode="fraction",
                entrywidth=0.24,
                itemsizing="constant",
                tracegroupgap=0,
                itemclick=False,
                itemdoubleclick=False,
                traceorder="normal",
            ),
            uirevision="track-map-constant",
        )

    def create_figure(
        self,
        current_lap: int,
        driver_data: List[Dict[str, Any]],
        elapsed_time: Optional[float] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        lap_filter: Optional[int] = None,
    ) -> go.Figure:
        """Return full circuit figure with markers."""
        if not self.session_loaded or self._base_figure is None:
            return self._create_error_figure(
                "Session not loaded. Track map unavailable.",
                width,
                height,
            )

        fig = go.Figure(self._base_figure.to_dict())
        layout_updates: Dict[str, Any] = {
            "title": dict(text=""),
            "uirevision": "track-map-constant",
            "transition": dict(duration=600, easing="linear"),
            "autosize": True,
            "margin": dict(l=30, r=30, t=20, b=90),
            "height": 560,
        }
        if width is not None:
            layout_updates["width"] = width
        if height is not None:
            layout_updates["height"] = height

        fig.update_layout(**layout_updates)

        if self._axis_ranges is not None:
            fig.update_xaxes(range=list(self._axis_ranges[0]))
            fig.update_yaxes(range=list(self._axis_ranges[1]))

        sorted_drivers = sorted(driver_data,
                                key=lambda item: item["driver_number"])
        driver_numbers = [entry["driver_number"] for entry in sorted_drivers]
        positions = self.provider.get_all_driver_positions(
            lap_number=lap_filter,
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
            position = positions.get(driver_number)
            is_retired = bool(driver.get("retired"))
            if position is None and not is_retired:
                continue

            position_payload: Dict[str, Any] = position.copy(
            ) if isinstance(position, dict) else {}
            team = driver.get("team_name", "Unknown")
            styles = self.resolve_marker_style(driver)
            lap_hint = driver.get("lap_fallback") if isinstance(
                driver.get("lap_fallback"), int) else None
            fallback_lap = int(lap_hint) if isinstance(
                lap_hint, int) and lap_hint >= 1 else current_lap

            if is_retired:
                order_index = int(driver.get("retired_order") or 0)
                anchor_x, anchor_y = self.get_retirement_marker_position(
                    order_index)
                position_payload.update({
                    "x": anchor_x,
                    "y": anchor_y,
                    "time": position_payload.get("time", float("nan")),
                    "query_time": position_payload.get("query_time", float("nan")),
                    "previous_sample": position_payload.get("previous_sample") or {},
                    "next_sample": position_payload.get("next_sample") or {},
                    "lap_number": driver.get("retired_lap", fallback_lap),
                })
                fallback_lap = driver.get("retired_lap") or fallback_lap
                point_x = anchor_x
                point_y = anchor_y
            else:
                pos_x = position_payload.get("x")
                pos_y = position_payload.get("y")
                point_x = float(pos_x) if isinstance(
                    pos_x, (int, float)) else 0.0
                point_y = float(pos_y) if isinstance(
                    pos_y, (int, float)) else 0.0

            custom_data = self._build_customdata(
                driver_number, position_payload, fallback_lap=fallback_lap)
            hover_template = self.build_hovertemplate(driver, team)
            fig.add_trace(
                go.Scatter(
                    x=[point_x],
                    y=[point_y],
                    mode="markers+text",
                    marker=dict(
                        size=20,
                        color=styles["fill_color"],
                        line=dict(
                            color=styles["outline_color"],
                            width=styles["outline_width"]),
                    ),
                    text=[
                        str(driver_number)],
                    textposition="middle center",
                    textfont=dict(
                        color=styles["text_color"],
                        size=10,
                        family="Arial Black"),
                    name=team if not seen_teams.get(team) else None,
                    legendgroup=team,
                    showlegend=team not in seen_teams,
                    hovertemplate=hover_template,
                    customdata=custom_data,
                    uid=str(driver_number),
                ))
            seen_teams[team] = True

        return fig

    def _create_error_figure(
        self,
        message: str,
        width: Optional[int],
        height: Optional[int],
    ) -> go.Figure:
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
        layout_updates: Dict[str, Any] = {
            "title": "Track Map",
            "plot_bgcolor": "#1a1a1a",
            "paper_bgcolor": "#0d0d0d",
            "font": dict(color="white"),
            "xaxis": dict(visible=False),
            "yaxis": dict(visible=False),
            "autosize": True,
        }
        if width is not None:
            layout_updates["width"] = width
        if height is not None:
            layout_updates["height"] = height

        fig.update_layout(**layout_updates)
        return fig

    def create_loading_figure(
        self,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> go.Figure:
        """Return loading placeholder."""
        return self._create_error_figure(
            "⏳ Loading track map session...", width, height)

    def create_no_data_figure(
        self,
        lap_number: int,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> go.Figure:
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

        sorted_drivers = sorted(driver_data,
                                key=lambda item: item["driver_number"])
        driver_numbers = [entry["driver_number"] for entry in sorted_drivers]
        positions = self.provider.get_all_driver_positions(
            lap_number=current_lap,
            driver_numbers=driver_numbers,
            elapsed_time=elapsed_time,
        )

        fig = go.Figure()
        for driver in sorted_drivers:
            driver_number = driver["driver_number"]
            position = positions.get(driver_number)
            is_retired = bool(driver.get("retired"))
            if position is None and not is_retired:
                continue

            position_payload: Dict[str, Any] = position.copy(
            ) if isinstance(position, dict) else {}
            team = driver.get("team_name", "Unknown")
            styles = self.resolve_marker_style(driver)
            lap_hint = driver.get("lap_fallback") if isinstance(
                driver.get("lap_fallback"), int) else None
            fallback_lap = int(lap_hint) if isinstance(
                lap_hint, int) and lap_hint >= 1 else current_lap

            if is_retired:
                order_index = int(driver.get("retired_order") or 0)
                anchor_x, anchor_y = self.get_retirement_marker_position(
                    order_index)
                position_payload.update({
                    "x": anchor_x,
                    "y": anchor_y,
                    "time": position_payload.get("time", float("nan")),
                    "query_time": position_payload.get("query_time", float("nan")),
                    "previous_sample": position_payload.get("previous_sample") or {},
                    "next_sample": position_payload.get("next_sample") or {},
                    "lap_number": driver.get("retired_lap", fallback_lap),
                })
                fallback_lap = driver.get("retired_lap") or fallback_lap
                point_x = anchor_x
                point_y = anchor_y
            else:
                pos_x = position_payload.get("x")
                pos_y = position_payload.get("y")
                point_x = float(pos_x) if isinstance(
                    pos_x, (int, float)) else 0.0
                point_y = float(pos_y) if isinstance(
                    pos_y, (int, float)) else 0.0

            custom_data = self._build_customdata(
                driver_number, position_payload, fallback_lap=fallback_lap)
            hover_template = self.build_hovertemplate(driver, team)

            fig.add_trace(
                go.Scatter(
                    x=[point_x],
                    y=[point_y],
                    mode="markers+text",
                    marker=dict(
                        size=20,
                        color=styles["fill_color"],
                        line=dict(
                            color=styles["outline_color"],
                            width=styles["outline_width"]),
                    ),
                    text=[
                        str(driver_number)],
                    textposition="middle center",
                    textfont=dict(
                        color=styles["text_color"],
                        size=10,
                        family="Arial Black"),
                    name=driver.get(
                        "driver_name",
                        str(driver_number)),
                    hovertext=f"{
                        driver.get(
                            'driver_name',
                            driver_number)} ({team})",
                    hoverinfo="text",
                    customdata=custom_data,
                    uid=str(driver_number),
                    hovertemplate=hover_template,
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
