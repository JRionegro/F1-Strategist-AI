"""
Telemetry Dashboard - Driver telemetry visualization.

Shows speed, throttle, brake, gear, and DRS data for the focus driver
on their last completed lap, with comparison support for up to 2 drivers.

Features:
- Speed chart with DRS zones overlay (colored bands)
- Throttle percentage chart
- Brake percentage chart  
- Gear chart
- X-axis: Distance (meters) for accurate lap comparison
- Downsampled to ~500 points for smooth rendering
- Simulation mode: Historical telemetry synced to simulation time
- Live mode: Real-time telemetry updates
"""

import logging
from typing import Optional, List, Any
from datetime import timedelta

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import dcc, html
import dash_bootstrap_components as dbc
import fastf1

logger = logging.getLogger(__name__)

# Team colors for driver traces (2025 season)
TEAM_COLORS = {
    'Red Bull Racing': '#3671C6',
    'Ferrari': '#E8002D',
    'Mercedes': '#27F4D2',
    'McLaren': '#FF8000',
    'Aston Martin': '#229971',
    'Alpine': '#FF87BC',
    'Williams': '#64C4FF',
    'RB': '#6692FF',
    'Kick Sauber': '#52E252',
    'Haas F1 Team': '#B6BABD',
}

# Default colors for comparison drivers
DEFAULT_COLORS = ['#FF6B6B', '#4ECDC4', '#45B7D1']

# Enable FastF1 cache
fastf1.Cache.enable_cache('./cache')


class TelemetryDashboard:
    """Telemetry dashboard for driver comparison."""

    # Cache of sessions where car_data failed to avoid repeated timeouts
    _failed_car_data_sessions: set = set()

    def __init__(self, openf1_provider):
        """
        Initialize Telemetry Dashboard.

        Args:
            openf1_provider: OpenF1DataProvider instance
        """
        self.provider = openf1_provider
        self._cached_session_key = None
        self._cached_car_data = None
        self._cached_laps = None
        self._cached_drivers = None
        self._car_data_load_attempted = False

    def render(
        self,
        session_key: Optional[int] = None,
        simulation_time: Optional[float] = None,
        session_start_time: Optional[pd.Timestamp] = None,
        focused_driver: Optional[str] = None,
        comparison_drivers: Optional[List[str]] = None,
        current_lap: Optional[int] = None,
        driver_options: Optional[List[Any]] = None
    ) -> dbc.Card:
        """
        Render the Telemetry Dashboard.

        Args:
            session_key: OpenF1 session key
            simulation_time: Current simulation time in seconds
            session_start_time: Session start timestamp
            focused_driver: Driver number as string (focus driver)
            comparison_drivers: List of driver numbers for comparison
            current_lap: Current lap number from simulation
            driver_options: List of driver options for dropdowns

        Returns:
            Dash Card component with telemetry visualization
        """
        if session_key is None:
            return self._render_placeholder()

        if not focused_driver:
            return self._render_no_driver_selected()

        try:
            # Load and cache data
            logger.info(
                f"Telemetry render: session_key={session_key}, "
                f"focused_driver={focused_driver}"
            )
            self._load_data(session_key)

            if self._cached_car_data is None or self._cached_car_data.empty:
                logger.warning(f"No car data available for session {session_key}")
                return self._render_no_data()

            # Get the last completed lap for focus driver
            try:
                focus_driver_num = int(focused_driver)
            except (ValueError, TypeError) as e:
                logger.error(
                    f"Invalid focused_driver format: {focused_driver}, "
                    f"error: {e}"
                )
                return self._render_error(f"Invalid driver: {focused_driver}")

            lap_data = self._get_driver_last_lap(
                focus_driver_num,
                simulation_time,
                session_start_time,
                current_lap
            )

            if lap_data is None:
                return self._render_no_lap_data(focused_driver)

            # Get telemetry for focus driver
            telemetry_data = self._get_lap_telemetry(
                focus_driver_num,
                lap_data
            )

            if telemetry_data.empty:
                return self._render_no_telemetry(focused_driver)

            # Build driver list for visualization
            drivers_to_plot = [(focus_driver_num, telemetry_data)]
            
            # Add comparison drivers if specified
            if comparison_drivers:
                for comp_driver in comparison_drivers[:2]:
                    if comp_driver and comp_driver != focused_driver:
                        comp_driver_num = int(comp_driver)
                        comp_lap = self._get_driver_last_lap(
                            comp_driver_num,
                            simulation_time,
                            session_start_time,
                            current_lap
                        )
                        if comp_lap is not None:
                            comp_telemetry = self._get_lap_telemetry(
                                comp_driver_num,
                                comp_lap
                            )
                            if not comp_telemetry.empty:
                                drivers_to_plot.append(
                                    (comp_driver_num, comp_telemetry)
                                )

            # Create visualization
            fig = self._create_telemetry_figure(drivers_to_plot)

            # Get driver info for display
            driver_info = self._get_driver_info(focus_driver_num)
            driver_name = driver_info.get('name', f"Driver {focus_driver_num}")
            lap_number = lap_data.get('LapNumber', 'N/A')

            return dbc.Card(
                [
                    dbc.CardHeader(
                        [
                            html.Div(
                                [
                                    html.H5(
                                        "📊 Telemetry",
                                        className="mb-0 d-inline",
                                        style={"fontSize": "1.2rem"}
                                    ),
                                    html.Span(
                                        f" - {driver_name} (Lap {lap_number})",
                                        className="text-muted ms-2",
                                        style={"fontSize": "0.9rem"}
                                    ),
                                ],
                                className="d-flex align-items-center"
                            )
                        ],
                        className="py-1"
                    ),
                    dbc.CardBody(
                        [
                            # Comparison driver info (dropdowns are in layout)
                            html.Div(
                                [
                                    html.Span(
                                        "Compare with: ",
                                        className="text-muted small me-2"
                                    ),
                                    html.Span(
                                        (
                                            ", ".join([
                                                d for d in (comparison_drivers or [])
                                                if d
                                            ]) or "None"
                                        ),
                                        className="small text-info"
                                    ),
                                    html.Span(
                                        " (use sidebar dropdowns)",
                                        className="text-muted small ms-1"
                                    ),
                                ],
                                className="mb-2 d-flex align-items-center"
                            ),
                            # Telemetry graph
                            dcc.Graph(
                                figure=fig,
                                config={
                                    "responsive": True,
                                    "displayModeBar": False
                                },
                                style={"height": "520px"}
                            ),
                        ],
                        className="p-2",
                        style={"backgroundColor": "#1e1e1e"}
                    ),
                ],
                className="mb-3 border border-secondary",
                style={"height": "620px", "backgroundColor": "#1e1e1e"}
            )

        except Exception as e:
            logger.error(f"Error rendering telemetry dashboard: {e}")
            return self._render_error(str(e))

    def _load_data(self, session_key: int) -> None:
        """Load and cache session data."""
        if self._cached_session_key != session_key:
            logger.info(f"Loading telemetry data for session {session_key}")
            
            # Check if this session previously failed for car_data
            if session_key in TelemetryDashboard._failed_car_data_sessions:
                logger.info(
                    f"Session {session_key} in failed cache, "
                    "skipping car_data request"
                )
                self._cached_car_data = pd.DataFrame()
                self._cached_session_key = session_key
                self._car_data_load_attempted = True
                # Still try to load laps and drivers (they usually work)
                try:
                    self._cached_laps = self.provider.get_laps(
                        session_key=session_key
                    )
                    self._cached_drivers = self.provider.get_drivers(
                        session_key=session_key
                    )
                except Exception as e:
                    logger.error(f"Error loading laps/drivers: {e}")
                    self._cached_laps = pd.DataFrame()
                    self._cached_drivers = pd.DataFrame()
                return
            
            try:
                # Try to get car_data with shorter timeout
                self._cached_car_data = self._get_car_data_with_short_timeout(
                    session_key
                )
                self._cached_laps = self.provider.get_laps(
                    session_key=session_key
                )
                self._cached_drivers = self.provider.get_drivers(
                    session_key=session_key
                )
                self._cached_session_key = session_key
                self._car_data_load_attempted = True
                
                if self._cached_car_data is not None:
                    logger.info(
                        f"Cached {len(self._cached_car_data)} car data records"
                    )
                else:
                    logger.warning(
                        f"No car data for session {session_key}"
                    )
            except Exception as e:
                logger.error(f"Error loading telemetry data: {e}")
                self._cached_car_data = pd.DataFrame()
                self._cached_laps = pd.DataFrame()
                self._cached_drivers = pd.DataFrame()

    def _get_car_data_with_short_timeout(
        self,
        session_key: int
    ) -> pd.DataFrame:
        """
        Get car data with a short timeout to avoid blocking UI.
        
        This uses a reduced timeout (5s) and no retries to prevent
        UI freezing when the OpenF1 car_data endpoint is unavailable.
        """
        import requests
        
        url = f"{self.provider.base_url}/car_data"
        params = {"session_key": session_key}
        
        try:
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    df = pd.DataFrame(data)
                    if "date" in df.columns:
                        df["date"] = pd.to_datetime(df["date"], format='mixed')
                    
                    column_mapping = {
                        "driver_number": "DriverNumber",
                        "date": "Timestamp",
                        "speed": "Speed",
                        "rpm": "RPM",
                        "n_gear": "Gear",
                        "throttle": "Throttle",
                        "brake": "Brake",
                        "drs": "DRS"
                    }
                    df = df.rename(
                        columns={
                            k: v for k, v in column_mapping.items()
                            if k in df.columns
                        }
                    )
                    logger.info(
                        f"Loaded {len(df)} car data records "
                        f"for session {session_key}"
                    )
                    return df
                else:
                    logger.warning(
                        f"No car data available for session {session_key}"
                    )
                    TelemetryDashboard._failed_car_data_sessions.add(
                        session_key
                    )
                    return pd.DataFrame()
            else:
                logger.warning(
                    f"Car data request failed with status "
                    f"{response.status_code} for session {session_key}"
                )
                TelemetryDashboard._failed_car_data_sessions.add(session_key)
                return pd.DataFrame()
                
        except requests.Timeout:
            logger.warning(
                f"Car data request timed out for session {session_key}"
            )
            TelemetryDashboard._failed_car_data_sessions.add(session_key)
            return pd.DataFrame()
        except requests.RequestException as e:
            logger.warning(f"Car data request failed: {e}")
            TelemetryDashboard._failed_car_data_sessions.add(session_key)
            return pd.DataFrame()

    def _get_driver_last_lap(
        self,
        driver_number: int,
        simulation_time: Optional[float],
        session_start_time: Optional[pd.Timestamp],
        current_lap: Optional[int]
    ) -> Optional[dict]:
        """Get the last completed lap for a driver."""
        if self._cached_laps is None or self._cached_laps.empty:
            return None

        driver_laps = self._cached_laps[
            self._cached_laps['DriverNumber'] == driver_number
        ].copy()

        if driver_laps.empty:
            return None

        # Filter by simulation time if available
        if simulation_time is not None and session_start_time is not None:
            current_time = session_start_time + timedelta(seconds=simulation_time)
            
            # Filter to laps that have ended before current simulation time
            if 'LapEndTime' in driver_laps.columns:
                completed_laps = driver_laps[
                    pd.notna(driver_laps['LapEndTime']) &
                    (driver_laps['LapEndTime'] <= current_time)
                ]
                if not completed_laps.empty:
                    driver_laps = completed_laps

        # Get the last lap
        if 'LapNumber' in driver_laps.columns:
            driver_laps = driver_laps.sort_values('LapNumber', ascending=False)

        last_lap = driver_laps.iloc[0]
        return last_lap.to_dict()

    def _get_lap_telemetry(
        self,
        driver_number: int,
        lap_data: dict
    ) -> pd.DataFrame:
        """Get telemetry data for a specific lap."""
        if self._cached_car_data is None or self._cached_car_data.empty:
            return pd.DataFrame()

        # Filter by driver
        driver_telemetry = self._cached_car_data[
            self._cached_car_data['DriverNumber'] == driver_number
        ].copy()

        if driver_telemetry.empty:
            return pd.DataFrame()

        # Filter by lap time range
        lap_start = lap_data.get('LapStartTime')
        lap_end = lap_data.get('LapEndTime')

        if pd.notna(lap_start) and pd.notna(lap_end):
            if 'Timestamp' in driver_telemetry.columns:
                driver_telemetry = driver_telemetry[
                    (driver_telemetry['Timestamp'] >= lap_start) &
                    (driver_telemetry['Timestamp'] <= lap_end)
                ]
        elif pd.notna(lap_start):
            # Only start time available, get next ~2 minutes of data
            if 'Timestamp' in driver_telemetry.columns:
                lap_end_approx = lap_start + timedelta(minutes=2)
                driver_telemetry = driver_telemetry[
                    (driver_telemetry['Timestamp'] >= lap_start) &
                    (driver_telemetry['Timestamp'] <= lap_end_approx)
                ]

        if driver_telemetry.empty:
            return pd.DataFrame()

        # Calculate distance from timestamps (approximate)
        driver_telemetry = self._calculate_distance(driver_telemetry)

        # Downsample to ~500 points for smooth rendering
        driver_telemetry = self._downsample(driver_telemetry, target_points=500)

        return driver_telemetry

    def _calculate_distance(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate cumulative distance from speed and time."""
        if df.empty or 'Speed' not in df.columns:
            return df

        df = df.sort_values('Timestamp').reset_index(drop=True)

        if 'Timestamp' in df.columns and len(df) > 1:
            # Calculate time differences in seconds
            timestamps = pd.to_datetime(df['Timestamp'])
            time_diff_td = timestamps.diff()
            time_diff = time_diff_td.dt.total_seconds().fillna(0)
            
            # Calculate distance: speed (km/h) * time (s) / 3.6 = meters
            speed_ms = df['Speed'] / 3.6  # Convert km/h to m/s
            distances = speed_ms * time_diff
            
            # Cumulative distance
            df['Distance'] = distances.cumsum()
        else:
            # Fallback: use index as distance proxy
            df['Distance'] = df.index * 10  # Approximate 10m per sample

        return df

    def _downsample(
        self,
        df: pd.DataFrame,
        target_points: int = 500
    ) -> pd.DataFrame:
        """Downsample DataFrame to target number of points."""
        if len(df) <= target_points:
            return df

        # Calculate step size
        step = len(df) // target_points
        if step < 1:
            step = 1

        # Sample every nth row
        return df.iloc[::step].reset_index(drop=True)

    def _get_driver_info(self, driver_number: int) -> dict:
        """Get driver information."""
        if self._cached_drivers is None or self._cached_drivers.empty:
            return {'name': f"#{driver_number}", 'team': 'Unknown'}

        driver_row = self._cached_drivers[
            self._cached_drivers['DriverNumber'] == driver_number
        ]

        if driver_row.empty:
            return {'name': f"#{driver_number}", 'team': 'Unknown'}

        row = driver_row.iloc[0]
        name = row.get('Abbreviation', f"#{driver_number}")
        team = row.get('TeamName', 'Unknown')
        full_name = row.get('FullName', name)

        return {
            'name': name,
            'full_name': full_name,
            'team': team,
            'color': TEAM_COLORS.get(team, DEFAULT_COLORS[0])
        }

    def _create_telemetry_figure(
        self,
        drivers_data: List[tuple]
    ) -> go.Figure:
        """
        Create telemetry visualization with stacked charts.

        Args:
            drivers_data: List of (driver_number, telemetry_df) tuples
        """
        # Create subplots: Speed, Throttle, Brake, Gear
        fig = make_subplots(
            rows=4, cols=1,
            shared_xaxis=True,
            vertical_spacing=0.03,
            row_heights=[0.35, 0.22, 0.22, 0.21],
            subplot_titles=None
        )

        # Add traces for each driver
        for idx, (driver_num, telemetry) in enumerate(drivers_data):
            if telemetry.empty:
                continue

            driver_info = self._get_driver_info(driver_num)
            color = driver_info.get('color', DEFAULT_COLORS[idx % 3])
            name = driver_info.get('name', f"#{driver_num}")

            # Check required columns
            if 'Distance' not in telemetry.columns:
                continue

            x_data = telemetry['Distance']

            # Speed trace
            if 'Speed' in telemetry.columns:
                fig.add_trace(
                    go.Scatter(
                        x=x_data,
                        y=telemetry['Speed'],
                        name=name,
                        line=dict(color=color, width=2),
                        legendgroup=name,
                        showlegend=True
                    ),
                    row=1, col=1
                )

                # Add DRS zones as colored bands (only for first driver)
                if idx == 0 and 'DRS' in telemetry.columns:
                    self._add_drs_zones(fig, telemetry, x_data)

            # Throttle trace
            if 'Throttle' in telemetry.columns:
                fig.add_trace(
                    go.Scatter(
                        x=x_data,
                        y=telemetry['Throttle'],
                        name=name,
                        line=dict(color=color, width=2),
                        legendgroup=name,
                        showlegend=False
                    ),
                    row=2, col=1
                )

            # Brake trace
            if 'Brake' in telemetry.columns:
                fig.add_trace(
                    go.Scatter(
                        x=x_data,
                        y=telemetry['Brake'],
                        name=name,
                        line=dict(color=color, width=2),
                        legendgroup=name,
                        showlegend=False
                    ),
                    row=3, col=1
                )

            # Gear trace
            if 'Gear' in telemetry.columns:
                fig.add_trace(
                    go.Scatter(
                        x=x_data,
                        y=telemetry['Gear'],
                        name=name,
                        line=dict(color=color, width=2),
                        legendgroup=name,
                        showlegend=False,
                        mode='lines'
                    ),
                    row=4, col=1
                )

        # Update layout
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#1e1e1e",
            plot_bgcolor="#161b22",
            height=500,
            margin=dict(l=50, r=20, t=30, b=40),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5,
                font=dict(size=10)
            ),
            hovermode='x unified'
        )

        # Update y-axes
        fig.update_yaxes(
            title_text="Speed (km/h)",
            row=1, col=1,
            title_font=dict(size=10),
            tickfont=dict(size=9),
            gridcolor='#333'
        )
        fig.update_yaxes(
            title_text="Throttle (%)",
            row=2, col=1,
            range=[0, 105],
            title_font=dict(size=10),
            tickfont=dict(size=9),
            gridcolor='#333'
        )
        fig.update_yaxes(
            title_text="Brake (%)",
            row=3, col=1,
            range=[0, 105],
            title_font=dict(size=10),
            tickfont=dict(size=9),
            gridcolor='#333'
        )
        fig.update_yaxes(
            title_text="Gear",
            row=4, col=1,
            range=[0, 9],
            dtick=1,
            title_font=dict(size=10),
            tickfont=dict(size=9),
            gridcolor='#333'
        )

        # Update x-axis (only show on bottom)
        fig.update_xaxes(
            title_text="Distance (m)",
            row=4, col=1,
            title_font=dict(size=10),
            tickfont=dict(size=9),
            gridcolor='#333'
        )
        for row in [1, 2, 3]:
            fig.update_xaxes(
                showticklabels=False,
                row=row, col=1,
                gridcolor='#333'
            )

        return fig

    def _add_drs_zones(
        self,
        fig: go.Figure,
        telemetry: pd.DataFrame,
        x_data: pd.Series
    ) -> None:
        """Add DRS activation zones as colored bands on speed chart."""
        if 'DRS' not in telemetry.columns:
            return

        # Find DRS activation zones (DRS > 0 or DRS >= 10 depending on API)
        drs_active = telemetry['DRS'] >= 10  # DRS >= 10 means open

        if not drs_active.any():
            return

        # Find start and end of each DRS zone
        drs_changes = drs_active.astype(int).diff().fillna(0)
        starts = x_data[drs_changes == 1].tolist()
        ends = x_data[drs_changes == -1].tolist()

        # Handle edge cases
        if drs_active.iloc[0]:
            starts.insert(0, x_data.iloc[0])
        if drs_active.iloc[-1]:
            ends.append(x_data.iloc[-1])

        # Add shapes for DRS zones (on first subplot only)
        for start, end in zip(starts, ends):
            fig.add_shape(
                type="rect",
                x0=start,
                x1=end,
                y0=0,
                y1=1,
                yref="paper",
                fillcolor="rgba(0, 255, 0, 0.15)",
                layer="below",
                line_width=0,
                row=1, col=1
            )

    def _render_placeholder(self) -> dbc.Card:
        """Render placeholder when no session loaded."""
        return dbc.Card(
            [
                dbc.CardHeader(
                    html.H5("📊 Telemetry", className="mb-0"),
                    className="py-2"
                ),
                dbc.CardBody(
                    [
                        html.Div(
                            [
                                html.I(
                                    className="fas fa-chart-line fa-3x mb-3",
                                    style={"color": "#666"}
                                ),
                                html.H5(
                                    "No session loaded",
                                    className="text-muted"
                                ),
                                html.P(
                                    "Select a race session to view telemetry",
                                    className="small text-muted"
                                ),
                            ],
                            className="text-center p-5"
                        )
                    ],
                    style={"backgroundColor": "#1e1e1e"}
                ),
            ],
            className="mb-3",
            style={"height": "620px", "backgroundColor": "#1e1e1e"}
        )

    def _render_no_driver_selected(self) -> dbc.Card:
        """Render when no focus driver selected."""
        return dbc.Card(
            [
                dbc.CardHeader(
                    html.H5("📊 Telemetry", className="mb-0"),
                    className="py-2"
                ),
                dbc.CardBody(
                    [
                        html.Div(
                            [
                                html.I(
                                    className="fas fa-user fa-3x mb-3",
                                    style={"color": "#666"}
                                ),
                                html.H5(
                                    "No driver selected",
                                    className="text-muted"
                                ),
                                html.P(
                                    "Select a Focus Driver in the sidebar",
                                    className="small text-muted"
                                ),
                            ],
                            className="text-center p-5"
                        )
                    ],
                    style={"backgroundColor": "#1e1e1e"}
                ),
            ],
            className="mb-3",
            style={"height": "620px", "backgroundColor": "#1e1e1e"}
        )

    def _render_no_data(self) -> dbc.Card:
        """Render when no telemetry data available."""
        return dbc.Card(
            [
                dbc.CardHeader(
                    html.H5("📊 Telemetry", className="mb-0"),
                    className="py-2"
                ),
                dbc.CardBody(
                    [
                        html.Div(
                            [
                                html.I(
                                    className="fas fa-database fa-3x mb-3",
                                    style={"color": "#666"}
                                ),
                                html.H5(
                                    "No telemetry data",
                                    className="text-muted"
                                ),
                                html.P(
                                    "Telemetry data is not available",
                                    className="small text-muted"
                                ),
                            ],
                            className="text-center p-5"
                        )
                    ],
                    style={"backgroundColor": "#1e1e1e"}
                ),
            ],
            className="mb-3",
            style={"height": "620px", "backgroundColor": "#1e1e1e"}
        )

    def _render_no_lap_data(self, driver: str) -> dbc.Card:
        """Render when no lap data for driver."""
        return dbc.Card(
            [
                dbc.CardHeader(
                    html.H5("📊 Telemetry", className="mb-0"),
                    className="py-2"
                ),
                dbc.CardBody(
                    [
                        html.Div(
                            [
                                html.I(
                                    className="fas fa-flag fa-3x mb-3",
                                    style={"color": "#666"}
                                ),
                                html.H5(
                                    f"No lap data for driver #{driver}",
                                    className="text-muted"
                                ),
                                html.P(
                                    "Waiting for lap completion...",
                                    className="small text-muted"
                                ),
                            ],
                            className="text-center p-5"
                        )
                    ],
                    style={"backgroundColor": "#1e1e1e"}
                ),
            ],
            className="mb-3",
            style={"height": "620px", "backgroundColor": "#1e1e1e"}
        )

    def _render_no_telemetry(self, driver: str) -> dbc.Card:
        """Render when no telemetry for driver's lap."""
        return dbc.Card(
            [
                dbc.CardHeader(
                    html.H5("📊 Telemetry", className="mb-0"),
                    className="py-2"
                ),
                dbc.CardBody(
                    [
                        html.Div(
                            [
                                html.I(
                                    className="fas fa-wave-square fa-3x mb-3",
                                    style={"color": "#666"}
                                ),
                                html.H5(
                                    f"No telemetry for #{driver}",
                                    className="text-muted"
                                ),
                                html.P(
                                    "Car data not available for this lap",
                                    className="small text-muted"
                                ),
                            ],
                            className="text-center p-5"
                        )
                    ],
                    style={"backgroundColor": "#1e1e1e"}
                ),
            ],
            className="mb-3",
            style={"height": "620px", "backgroundColor": "#1e1e1e"}
        )

    def _render_error(self, error_msg: str) -> dbc.Card:
        """Render error state."""
        return dbc.Card(
            [
                dbc.CardHeader(
                    html.H5("📊 Telemetry", className="mb-0"),
                    className="py-2"
                ),
                dbc.CardBody(
                    [
                        html.Div(
                            [
                                html.I(
                                    className="fas fa-exclamation-triangle fa-3x mb-3",
                                    style={"color": "#dc3545"}
                                ),
                                html.H5("Error loading telemetry"),
                                html.P(
                                    error_msg,
                                    className="small text-danger"
                                ),
                            ],
                            className="text-center p-5"
                        )
                    ],
                    style={"backgroundColor": "#1e1e1e"}
                ),
            ],
            className="mb-3",
            style={"height": "620px", "backgroundColor": "#1e1e1e"}
        )
