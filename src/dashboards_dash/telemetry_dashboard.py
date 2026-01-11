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
import time
from typing import Optional, List, Any, Dict, Sequence
from datetime import timedelta

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import dcc, html
import dash_bootstrap_components as dbc
import fastf1

logger = logging.getLogger(__name__)

# TTL for failed sessions cache (5 minutes)
FAILED_SESSION_TTL_SECONDS = 300

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

    # Cache of (session_key, driver_number, lap_number) that failed
    # Value is timestamp for TTL
    _failed_lap_requests: Dict[tuple, float] = {}

    def __init__(self, openf1_provider):
        """
        Initialize Telemetry Dashboard.

        Args:
            openf1_provider: OpenF1DataProvider instance
        """
        self.provider = openf1_provider
        self._cached_session_key = None
        self._cached_laps = None
        self._cached_drivers = None
        # Cache for lap telemetry: {(session, driver, lap): DataFrame}
        self._lap_telemetry_cache: Dict[tuple, pd.DataFrame] = {}

    def render(
        self,
        session_key: Optional[int] = None,
        simulation_time: Optional[float] = None,
        session_start_time: Optional[pd.Timestamp] = None,
        focused_driver: Optional[str] = None,
        comparison_driver: Optional[str] = None,
        current_lap: Optional[int] = None,
        driver_options: Optional[List[Dict[str, Any]]] = None
    ) -> dbc.Card:
        """
        Render the Telemetry Dashboard.

        Args:
            session_key: OpenF1 session key
            simulation_time: Current simulation time in seconds
            session_start_time: Session start timestamp
            focused_driver: Driver number as string (focus driver)
            comparison_driver: Driver to compare against (single driver)
            current_lap: Current lap number from simulation
            driver_options: List of driver options for comparison dropdown

        Returns:
            Dash Card component with telemetry visualization
        """
        if session_key is None:
            return self._render_placeholder()

        if not focused_driver:
            return self._render_no_driver_selected()

        try:
            # Parse focused_driver - can be "CODE_YEAR_NUMBER" or just number
            focus_driver_num = self._parse_driver_number(focused_driver)
            if focus_driver_num is None:
                return self._render_error(f"Invalid driver: {focused_driver}")

            # Load laps and drivers (lightweight)
            logger.info(
                f"Telemetry render: session_key={session_key}, "
                f"focused_driver={focused_driver} (#{focus_driver_num})"
            )
            self._load_session_metadata(session_key)

            # Get the last lap info for the driver
            lap_data = self._get_driver_last_lap(
                focus_driver_num,
                simulation_time,
                session_start_time,
                current_lap
            )

            if lap_data is None:
                return self._render_no_lap_data(focused_driver)

            # Fetch telemetry ONLY for this specific lap (optimized)
            telemetry_data = self._fetch_lap_telemetry(
                session_key,
                focus_driver_num,
                lap_data
            )

            if telemetry_data is None or telemetry_data.empty:
                return self._render_no_telemetry(focused_driver)

            # Build driver list for visualization
            drivers_to_plot = [(focus_driver_num, telemetry_data)]
            
            # Add comparison driver if specified
            comparison_driver_info = None
            if comparison_driver and comparison_driver != focused_driver:
                comp_driver_num = self._parse_driver_number(comparison_driver)
                if comp_driver_num is not None:
                    comp_lap = self._get_driver_last_lap(
                        comp_driver_num,
                        simulation_time,
                        session_start_time,
                        current_lap
                    )
                    if comp_lap is not None:
                        comp_telemetry = self._fetch_lap_telemetry(
                            session_key,
                            comp_driver_num,
                            comp_lap
                        )
                        if (
                            comp_telemetry is not None and
                            not comp_telemetry.empty
                        ):
                            drivers_to_plot.append(
                                (comp_driver_num, comp_telemetry)
                            )
                            comparison_driver_info = self._get_driver_info(
                                comp_driver_num
                            )

            # Get driver info for display
            driver_info = self._get_driver_info(focus_driver_num)
            driver_name = driver_info.get('name', f"Driver {focus_driver_num}")
            # Convert OpenF1 lap to racing lap (OpenF1 lap 3 = racing lap 1)
            openf1_lap = lap_data.get('LapNumber', 3)
            racing_lap = max(1, openf1_lap - 2) if openf1_lap else 1

            # Create visualization (pass racing_lap for DRS rule validation)
            fig = self._create_telemetry_figure(drivers_to_plot, racing_lap)

            # Build comparison dropdown options (exclude focus driver)
            comparison_options = []
            if driver_options:
                comparison_options = [
                    opt for opt in driver_options
                    if opt.get('value') != focused_driver
                ]

            # Build subtitle with comparison info
            subtitle_text = f" - {driver_name} (Lap {racing_lap})"
            if comparison_driver_info:
                comp_name = comparison_driver_info.get(
                    'name', f"Driver {comparison_driver}"
                )
                subtitle_text += f" vs {comp_name}"

            return dbc.Card(
                [
                    dbc.CardHeader(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        html.H4(
                                            [
                                                "📊 Telemetry",
                                                html.Span(
                                                    subtitle_text,
                                                    className="text-muted ms-2",
                                                    style={"fontSize": "0.8rem"}
                                                ),
                                            ],
                                            className="mb-0",
                                            style={"fontSize": "0.9rem"}
                                        ),
                                        width="auto",
                                        className="d-flex align-items-center"
                                    ),
                                    dbc.Col(
                                        dcc.Dropdown(
                                            id='telemetry-comparison-driver',
                                            options=comparison_options,  # type: ignore[arg-type]
                                            value=comparison_driver,
                                            placeholder="Compare with...",
                                            clearable=True,
                                            style={
                                                'fontSize': '11px',
                                                'fontFamily': 'monospace',
                                                'minWidth': '180px',
                                                'backgroundColor': '#2d2d2d',
                                            },
                                            className="dash-dropdown-dark"
                                        ),
                                        width="auto",
                                        className="ms-auto"
                                    ),
                                ],
                                className="g-0 align-items-center",
                                style={"flexWrap": "nowrap"}
                            )
                        ],
                        style={"padding": "0.5rem 1rem"}
                    ),
                    dbc.CardBody(
                        [
                            # Telemetry graph
                            dcc.Graph(
                                figure=fig,
                                config={
                                    "responsive": True,
                                    "displayModeBar": False
                                },
                                style={"height": "560px"}
                            ),
                        ],
                        className="p-0",
                        style={"backgroundColor": "#1e1e1e"}
                    ),
                ],
                className="mb-2 border border-secondary",
                style={"height": "620px", "backgroundColor": "#1e1e1e"}
            )

        except Exception as e:
            logger.error(f"Error rendering telemetry dashboard: {e}")
            return self._render_error(str(e))

    def _parse_driver_number(self, focused_driver: str) -> Optional[int]:
        """
        Parse driver number from focused_driver string.

        Handles formats:
        - "CODE_YEAR_NUMBER" (e.g., "RUS_2025_63")
        - Plain number as string (e.g., "63")
        """
        if not focused_driver:
            return None

        try:
            # Try format CODE_YEAR_NUMBER
            parts = focused_driver.split('_')
            if len(parts) >= 3:
                return int(parts[2])
            # Try plain number
            return int(focused_driver)
        except (ValueError, TypeError, IndexError) as e:
            logger.error(
                f"Invalid focused_driver format: {focused_driver}, error: {e}"
            )
            return None

    def _load_session_metadata(self, session_key: int) -> None:
        """
        Load and cache lightweight session metadata (laps and drivers only).
        
        Car telemetry is loaded on-demand per lap to optimize API calls.
        """
        if self._cached_session_key != session_key:
            logger.info(f"Loading session metadata for {session_key}")
            # Clear lap telemetry cache when session changes
            self._lap_telemetry_cache.clear()
            
            try:
                self._cached_laps = self.provider.get_laps(
                    session_key=session_key
                )
                self._cached_drivers = self.provider.get_drivers(
                    session_key=session_key
                )
                self._cached_session_key = session_key
                
                logger.info(
                    f"Loaded {len(self._cached_laps)} laps, "
                    f"{len(self._cached_drivers)} drivers"
                )
            except Exception as e:
                logger.error(f"Error loading session metadata: {e}")
                self._cached_laps = pd.DataFrame()
                self._cached_drivers = pd.DataFrame()

    def _fetch_lap_telemetry(
        self,
        session_key: int,
        driver_number: int,
        lap_data: dict
    ) -> Optional[pd.DataFrame]:
        """
        Fetch telemetry for a specific lap using time window filtering.
        
        This is much more efficient than loading all session telemetry.
        Typical reduction: 32K records -> ~500-1000 records per lap.
        """
        lap_number = lap_data.get('LapNumber')
        cache_key = (session_key, driver_number, lap_number)
        
        # Check cache first
        if cache_key in self._lap_telemetry_cache:
            return self._lap_telemetry_cache[cache_key]
        
        # TEMPORARILY DISABLED - Check if this request previously failed
        # if cache_key in TelemetryDashboard._failed_lap_requests:
        #     failed_time = TelemetryDashboard._failed_lap_requests[cache_key]
        #     elapsed = time.time() - failed_time
        #     if elapsed < FAILED_SESSION_TTL_SECONDS:
        #         remaining = FAILED_SESSION_TTL_SECONDS - elapsed
        #         print(
        #             f"⏳ TELEMETRY DEBUG: {cache_key} in failed cache "
        #             f"(retry in {remaining:.0f}s)",
        #             flush=True
        #         )
        #         return None
        #     else:
        #         print(
        #             f"🔄 TELEMETRY DEBUG: TTL expired for {cache_key}",
        #             flush=True
        #         )
        #         del TelemetryDashboard._failed_lap_requests[cache_key]
        
        # Get lap time window
        lap_start = lap_data.get('LapStartTime')
        lap_end = lap_data.get('LapEndTime')
        
        print(
            f"📊 TELEMETRY DEBUG: Lap {lap_number} start={lap_start}, "
            f"end={lap_end}",
            flush=True
        )
        
        if pd.isna(lap_start):
            logger.warning(f"⚠️ No LapStartTime for lap {lap_number}")
            return None
        
        # Convert to ISO format for API (without timezone or milliseconds -
        # OpenF1 API returns 500 errors with timezone suffix or milliseconds)
        def to_iso_no_tz(ts: pd.Timestamp) -> str:
            """Convert timestamp to ISO format without timezone or ms."""
            # Remove timezone info to get naive datetime, then format
            if ts.tzinfo is not None:
                ts = ts.tz_localize(None)
            # NO milliseconds - OpenF1 API doesn't accept them
            return ts.strftime('%Y-%m-%dT%H:%M:%S')
        
        if isinstance(lap_start, pd.Timestamp):
            date_start = to_iso_no_tz(lap_start)
        else:
            date_start = str(lap_start).replace('+00:00', '')
        
        # If lap_end is NaT (lap in progress), use lap_start + 2 minutes
        if pd.isna(lap_end):
            # Assume max lap time of 2 minutes
            estimated_end = lap_start + timedelta(minutes=2)
            date_end = to_iso_no_tz(estimated_end)
        else:
            if isinstance(lap_end, pd.Timestamp):
                date_end = to_iso_no_tz(lap_end)
            else:
                date_end = str(lap_end).replace('+00:00', '')
        
        print(
            f"🌐 TELEMETRY API: Fetching driver {driver_number}, "
            f"lap {lap_number}: {date_start} to {date_end}",
            flush=True
        )
        
        try:
            car_data = self.provider.get_car_data(
                session_key=session_key,
                driver_number=driver_number,
                date_start=date_start,
                date_end=date_end
            )
            
            if car_data is None or car_data.empty:
                print(
                    f"❌ TELEMETRY API: No data returned for driver "
                    f"{driver_number} lap {lap_number}",
                    flush=True
                )
                TelemetryDashboard._failed_lap_requests[cache_key] = time.time()
                return None
            
            # Debug: Check DRS data
            if 'DRS' in car_data.columns:
                drs_active_count = (car_data['DRS'] >= 10).sum()
                print(
                    f"✅ TELEMETRY API: Got {len(car_data)} points for "
                    f"lap {lap_number} | DRS active: {drs_active_count} points",
                    flush=True
                )
            else:
                print(
                    f"✅ TELEMETRY API: Got {len(car_data)} points for "
                    f"lap {lap_number} | ⚠️ No DRS column",
                    flush=True
                )
            
            # Process data: calculate distance and downsample
            car_data = self._calculate_distance(car_data)
            car_data = self._downsample(car_data, target_points=500)
            
            # Cache the processed result
            self._lap_telemetry_cache[cache_key] = car_data
            return car_data
            
        except Exception as e:
            logger.error(f"Error fetching lap telemetry: {e}")
            TelemetryDashboard._failed_lap_requests[cache_key] = time.time()
            return None

    def _get_driver_last_lap(
        self,
        driver_number: int,
        simulation_time: Optional[float],
        session_start_time: Optional[pd.Timestamp],
        current_lap: Optional[int]
    ) -> Optional[dict]:
        """Get the last completed lap for a driver."""
        if self._cached_laps is None or self._cached_laps.empty:
            print(f"🚫 TELEMETRY DEBUG: No cached laps available", flush=True)
            return None

        driver_laps = self._cached_laps[
            self._cached_laps['DriverNumber'] == driver_number
        ].copy()

        if driver_laps.empty:
            print(
                f"🚫 TELEMETRY DEBUG: No laps for driver {driver_number}",
                flush=True
            )
            return None
        
        print(
            f"📋 TELEMETRY DEBUG: Driver {driver_number} has "
            f"{len(driver_laps)} laps",
            flush=True
        )

        # Filter by simulation time if available
        if simulation_time is not None and session_start_time is not None:
            current_time = session_start_time + timedelta(seconds=simulation_time)
            
            # Filter to laps that have ended before current simulation time
            if 'LapEndTime' in driver_laps.columns:
                completed_laps = driver_laps[
                    pd.notna(driver_laps['LapEndTime']) &
                    (driver_laps['LapEndTime'] <= current_time)
                ]
                print(
                    f"📋 TELEMETRY DEBUG: Completed laps: {len(completed_laps)}",
                    flush=True
                )
                if not completed_laps.empty:
                    driver_laps = completed_laps

        # Get the last lap
        if 'LapNumber' in driver_laps.columns:
            driver_laps = driver_laps.sort_values('LapNumber', ascending=False)

        last_lap = driver_laps.iloc[0]
        lap_dict = last_lap.to_dict()
        print(
            f"✅ TELEMETRY DEBUG: Using lap {lap_dict.get('LapNumber')}",
            flush=True
        )
        return lap_dict

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
        drivers_data: List[tuple],
        racing_lap: int = 1
    ) -> go.Figure:
        """
        Create telemetry visualization with stacked charts.

        Args:
            drivers_data: List of (driver_number, telemetry_df) tuples
            racing_lap: Current racing lap number (1-based, excludes formation)
        """
        # Create subplots: Speed, Throttle, Brake, Gear
        fig = make_subplots(
            rows=4, cols=1,
            shared_xaxes=True,
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
                # F1 Rule: DRS is enabled after completing 2 racing laps
                if idx == 0 and 'DRS' in telemetry.columns:
                    self._add_drs_zones(fig, telemetry, x_data, racing_lap)

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
            height=490,
            margin=dict(l=50, r=20, t=10, b=50),
            legend=dict(
                orientation="h",
                yanchor="top",
                y=0.99,
                xanchor="right",
                x=0.99,
                font=dict(size=9),
                bgcolor="rgba(30,30,30,0.8)"
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
        x_data: pd.Series,
        racing_lap: int = 1
    ) -> None:
        """Add DRS activation zones as colored bands on speed chart.
        
        F1 Rule: DRS is enabled after completing 2 racing laps.
        
        OpenF1 DRS values:
        - 0, 1: DRS off
        - 8: Detected, eligible once in activation zone
        - 10, 12, 14: DRS on (wing open)
        
        Args:
            racing_lap: Current racing lap (1-based). DRS shown only if lap >= 3.
        """
        if 'DRS' not in telemetry.columns:
            logger.debug("DRS column not found in telemetry data")
            return

        # F1 Rule: DRS is NOT enabled in the first 2 racing laps
        # (formation lap doesn't count, so racing laps 1-2 have no DRS)
        if racing_lap < 3:
            logger.info(
                f"🚫 DRS disabled: Racing lap {racing_lap} < 3 "
                "(F1 rule: DRS enabled after 2 completed laps)"
            )
            return

        # Debug: log DRS values
        drs_values = telemetry['DRS'].unique()
        drs_count = (telemetry['DRS'] >= 10).sum()
        logger.info(f"🔍 DRS DEBUG: Racing lap {racing_lap}, "
                    f"Unique values={sorted(drs_values)}, "
                    f"Count>=10: {drs_count}/{len(telemetry)}")

        # Find DRS activation zones (DRS >= 10 means wing open)
        drs_active = telemetry['DRS'] >= 10

        if not drs_active.any():
            logger.info("🔍 DRS DEBUG: No DRS activation (all False)")
            return

        # Find start and end of each DRS zone
        drs_changes = drs_active.astype(int).diff().fillna(0)
        starts = x_data[drs_changes == 1].tolist()
        ends = x_data[drs_changes == -1].tolist()

        logger.info(f"🔍 DRS DEBUG: diff found {len(starts)} starts, "
                    f"{len(ends)} ends")
        logger.info(f"🔍 DRS DEBUG: drs_active.iloc[0]={drs_active.iloc[0]}, "
                    f"drs_active.iloc[-1]={drs_active.iloc[-1]}")

        # Handle edge cases
        if drs_active.iloc[0]:
            starts.insert(0, x_data.iloc[0])
            logger.info("🔍 DRS DEBUG: Added start at beginning (edge case)")
        if drs_active.iloc[-1]:
            ends.append(x_data.iloc[-1])
            logger.info("🔍 DRS DEBUG: Added end at end (edge case)")

        logger.info(f"Adding {len(starts)} DRS zones to telemetry chart")

        # Get the y-axis range for speed (first subplot)
        speed_data = telemetry['Speed']
        y_min = speed_data.min() * 0.95 if not speed_data.empty else 0
        y_max = speed_data.max() * 1.05 if not speed_data.empty else 350

        # Add shapes for DRS zones (on first subplot - Speed)
        for i, (start, end) in enumerate(zip(starts, ends)):
            # Green band covering full height of speed chart
            fig.add_shape(
                type="rect",
                x0=start,
                x1=end,
                y0=y_min,
                y1=y_max,
                xref="x",
                yref="y",
                fillcolor="rgba(0, 200, 83, 0.25)",
                layer="below",
                line=dict(color="rgba(0, 200, 83, 0.6)", width=1),
            )

            # Add "DRS" label annotation at the center of each zone
            zone_center = (start + end) / 2
            fig.add_annotation(
                x=zone_center,
                y=y_max * 0.95,
                xref="x",
                yref="y",
                text="DRS",
                showarrow=False,
                font=dict(size=10, color="#00C853", family="Arial Black"),
                bgcolor="rgba(0, 0, 0, 0.6)",
                bordercolor="#00C853",
                borderwidth=1,
                borderpad=3,
            )

        # Add legend entry for DRS zones (Focus Driver only)
        # Using a dummy scatter trace with matching color
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode='markers',
                marker=dict(
                    size=12,
                    color="rgba(0, 200, 83, 0.5)",
                    symbol="square",
                    line=dict(color="#00C853", width=1)
                ),
                name="DRS (Focus)",
                showlegend=True,
                legendgroup="drs_legend"
            ),
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
