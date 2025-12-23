"""
Race Overview Dashboard - Hybrid layout combining Leaderboard + Circuit Map.

Left side: Real-time leaderboard with positions, gaps, tire compounds
Right side: Circuit map with driver positions (static for now, animated in future)
"""

import logging
from typing import Optional

import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
from dash import dash_table, dcc, html

logger = logging.getLogger(__name__)

# 2025 F1 Team Colors
TEAM_COLORS = {
    "Red Bull Racing": "#3671C6",
    "Mercedes": "#27F4D2",
    "Ferrari": "#E8002D",
    "McLaren": "#FF8000",
    "Aston Martin": "#229971",
    "Alpine": "#FF87BC",
    "Williams": "#64C4FF",
    "RB": "#6692FF",
    "Kick Sauber": "#52E252",
    "Haas F1 Team": "#B6BABD",
}


class RaceOverviewDashboard:
    """Hybrid dashboard showing leaderboard table + circuit map."""

    @staticmethod
    def render(session_obj=None, focused_driver=None):
        """
        Render the Race Overview Dashboard with two-column layout.

        Args:
            session_obj: FastF1 session object with loaded data
            focused_driver: Driver number to highlight (optional)

        Returns:
            Dash component tree for the dashboard
        """
        if session_obj is None:
            return html.Div(
                "No session loaded. Please select a race session.",
                className="text-center text-muted p-5",
            )

        try:
            # Get session data
            laps = session_obj.laps
            results = session_obj.results

            # Build leaderboard table
            leaderboard_table = RaceOverviewDashboard._build_leaderboard(
                session_obj, laps, results
            )

            # Build circuit map
            circuit_map = RaceOverviewDashboard._build_circuit_map(
                session_obj, laps, results
            )

            # Two-column layout
            return dbc.Row(
                [
                    # Left column - Leaderboard (40%)
                    dbc.Col(
                        [
                            html.H4(
                                "Race Leaderboard",
                                className="mb-3 text-center",
                                style={"color": "#e10600"},
                            ),
                            html.Div(id="leaderboard-container", children=leaderboard_table),
                        ],
                        width=5,
                        className="pe-3",
                    ),
                    # Right column - Circuit Map (60%)
                    dbc.Col(
                        [
                            html.H4(
                                "Circuit Map",
                                className="mb-3 text-center",
                                style={"color": "#e10600"},
                            ),
                            html.Div(id="circuit-map-container", children=circuit_map),
                        ],
                        width=7,
                        className="ps-3",
                    ),
                ],
                className="g-0",
            )

        except Exception as e:
            logger.error(f"Error rendering Race Overview Dashboard: {e}")
            return html.Div(
                f"Error loading dashboard: {str(e)}",
                className="text-center text-danger p-5",
            )

    @staticmethod
    def _build_leaderboard(session_obj, laps, results, elapsed_seconds=None):
        """
        Build leaderboard DataTable with positions, gaps, tire info.

        Args:
            session_obj: FastF1 session object
            laps: Session laps dataframe
            results: Session results dataframe
            elapsed_seconds: Elapsed simulation seconds from start (for filtering laps)

        Returns:
            dash_table.DataTable component
        """
        try:
            logger.info("_build_leaderboard: Starting...")
            # OPTIMIZED: Use vectorized operations instead of loops
            
            # Filter laps by simulation time using LapNumber
            if elapsed_seconds is not None:
                logger.info(f"_build_leaderboard: Simulation at {elapsed_seconds:.1f}s from start")
                
                # Filter using lap completion time (LapStartTime + LapTime)
                if 'LapStartTime' in laps.columns and 'LapTime' in laps.columns:
                    laps_copy = laps[
                        pd.notna(laps['LapStartTime']) & pd.notna(laps['LapTime'])
                    ].copy()
                    
                    # Convert to seconds
                    laps_copy['LapStartTime_seconds'] = laps_copy['LapStartTime'].dt.total_seconds()
                    laps_copy['LapTime_seconds'] = laps_copy['LapTime'].dt.total_seconds()
                    
                    # Calculate when lap ENDS (start + duration)
                    laps_copy['LapEndTime_seconds'] = (
                        laps_copy['LapStartTime_seconds'] + laps_copy['LapTime_seconds']
                    )
                    
                    # DEBUG: Log first few lap end times
                    if not laps_copy.empty:
                        min_end = laps_copy['LapEndTime_seconds'].min()
                        max_end = laps_copy['LapEndTime_seconds'].max()
                        logger.info(f"_build_leaderboard: DEBUG - LapEndTime range: {min_end:.1f}s to {max_end:.1f}s")
                        sample_data = laps_copy[['DriverNumber', 'LapNumber', 'LapStartTime_seconds', 'LapTime_seconds', 'LapEndTime_seconds']].head(3)
                        logger.info(f"_build_leaderboard: DEBUG - Sample laps:\n{sample_data.to_string()}")
                    
                    # Filter laps that FINISHED before elapsed_seconds
                    completed_laps = laps_copy[
                        laps_copy['LapEndTime_seconds'] <= elapsed_seconds
                    ].copy()
                    logger.info(f"_build_leaderboard: Filtered to {len(completed_laps)} laps (LapEndTime <= {elapsed_seconds:.1f}s)")
                else:
                    completed_laps = laps.copy()
                    logger.info("_build_leaderboard: No LapStartTime column, using all laps")
            else:
                completed_laps = laps.copy()
                logger.info(f"_build_leaderboard: No elapsed_seconds filter, using all {len(completed_laps)} laps")

            if completed_laps.empty:
                logger.warning("_build_leaderboard: No laps found")
                return dash_table.DataTable(
                    id="leaderboard-table",
                    columns=[{"name": "No Data", "id": "no_data"}],
                    data=[{"no_data": "No lap data available"}],
                    style_table={"overflowX": "auto"},
                )

            # Vectorized cumulative time calculation
            logger.info("_build_leaderboard: Calculating cumulative times...")
            
            # Only convert LapTime_seconds if not already present
            if 'LapTime_seconds' not in completed_laps.columns:
                completed_laps["LapTime_seconds"] = completed_laps["LapTime"].apply(
                    lambda x: x.total_seconds() if pd.notna(x) else 0
                )
            
            # Group by driver and get last lap info + cumulative time
            logger.info("_build_leaderboard: Grouping by driver...")
            driver_stats = completed_laps.groupby("DriverNumber", as_index=False).agg({
                "LapTime": "last",
                "Compound": "last",
                "LapTime_seconds": "sum",  # Sum all completed lap times
                "LapNumber": "max",  # Last completed lap number
                "LapEndTime_seconds": "max"  # When last lap ended
            })
            
            # Add interpolated time if simulation is past last completed lap
            if elapsed_seconds is not None:
                # Calculate time spent in current (incomplete) lap
                driver_stats['TimeInCurrentLap'] = elapsed_seconds - driver_stats['LapEndTime_seconds']
                # Only add if positive (driver is in a new lap)
                driver_stats['TimeInCurrentLap'] = driver_stats['TimeInCurrentLap'].clip(lower=0)
                
                # Add interpolated time to cumulative time
                driver_stats['CumulativeTime_seconds'] = (
                    driver_stats['LapTime_seconds'] + driver_stats['TimeInCurrentLap']
                )
            else:
                driver_stats['CumulativeTime_seconds'] = driver_stats['LapTime_seconds']
            
            logger.info(f"_build_leaderboard: Processed {len(driver_stats)} drivers")

            # Merge with results to get driver info
            logger.info("_build_leaderboard: Merging with results...")
            leaderboard_df = results.merge(
                driver_stats,
                on="DriverNumber",
                how="inner"
            )
            logger.info(f"_build_leaderboard: Merged, got {len(leaderboard_df)} entries")

            if leaderboard_df.empty:
                return dash_table.DataTable(
                    id="leaderboard-table",
                    columns=[{"name": "No Data", "id": "no_data"}],
                    data=[{"no_data": "No driver data available"}],
                    style_table={"overflowX": "auto"},
                )

            # Sort by cumulative time (fastest first)
            leaderboard_df = leaderboard_df.sort_values("CumulativeTime_seconds").reset_index(drop=True)

            # Build data list with formatted values
            leaderboard_data = []
            for idx, row in leaderboard_df.iterrows():
                abbr = row.get("Abbreviation", "???")
                team = row.get("TeamName", "Unknown")
                team_color = TEAM_COLORS.get(team, "#FFFFFF")
                
                # Format lap time
                lap_time = row.get("LapTime")
                if pd.notna(lap_time):
                    lap_time_str = str(lap_time).split(" ")[-1][:10]
                else:
                    lap_time_str = "-"
                
                leaderboard_data.append({
                    "Pos": 0,  # Will be set below
                    "Driver": abbr,
                    "TeamColor": team_color,
                    "CumulativeTime_seconds": row["CumulativeTime_seconds"],
                    "DriverNumber": row["DriverNumber"],
                    "LastLap": lap_time_str,
                    "Tire": row.get("Compound", "Unknown"),
                })
            
            # Recalculate positions and gaps after sorting
            leader_time_seconds = leaderboard_data[0]["CumulativeTime_seconds"] if leaderboard_data else 0
            
            # DEBUG: Log leader time
            logger.info(f"_build_leaderboard: DEBUG - Leader time: {leader_time_seconds:.3f}s")
            
            for i, entry in enumerate(leaderboard_data):
                entry["Pos"] = i + 1
                
                # Calculate gap to car ahead
                if i == 0:
                    entry["GapAhead"] = "LEADER"
                else:
                    gap_seconds = entry["CumulativeTime_seconds"] - leaderboard_data[i-1]["CumulativeTime_seconds"]
                    if gap_seconds < 0.1:
                        entry["GapAhead"] = "-"
                    else:
                        entry["GapAhead"] = f"+{gap_seconds:.3f}s"
                
                # Calculate gap to leader
                if i == 0:
                    entry["GapLeader"] = "-"
                else:
                    gap_seconds = entry["CumulativeTime_seconds"] - leader_time_seconds
                    if gap_seconds < 0.1:
                        entry["GapLeader"] = "-"
                    else:
                        entry["GapLeader"] = f"+{gap_seconds:.3f}s"
            
            # DEBUG: Log first 3 drivers
            if len(leaderboard_data) >= 3:
                logger.info(f"_build_leaderboard: DEBUG - P1: {leaderboard_data[0]['Driver']} {leaderboard_data[0]['CumulativeTime_seconds']:.3f}s")
                logger.info(f"_build_leaderboard: DEBUG - P2: {leaderboard_data[1]['Driver']} {leaderboard_data[1]['CumulativeTime_seconds']:.3f}s Gap={leaderboard_data[1]['GapLeader']}")
                logger.info(f"_build_leaderboard: DEBUG - P3: {leaderboard_data[2]['Driver']} {leaderboard_data[2]['CumulativeTime_seconds']:.3f}s Gap={leaderboard_data[2]['GapLeader']}")

            logger.info("_build_leaderboard: Creating DataTable...")
            
            # Create DataTable with simplified styling (no per-row conditionals for performance)
            return dash_table.DataTable(
                id="leaderboard-table",
                columns=[
                    {"name": "Pos", "id": "Pos"},
                    {"name": "Driver", "id": "Driver"},
                    {"name": "Interval", "id": "GapAhead"},
                    {"name": "Gap", "id": "GapLeader"},
                    {"name": "Last Lap", "id": "LastLap"},
                    {"name": "Tire", "id": "Tire"},
                ],
                data=leaderboard_data,
                style_table={
                    "overflowY": "auto",
                    "maxHeight": "600px",
                },
                style_header={
                    "backgroundColor": "#1e1e1e",
                    "color": "#e10600",
                    "fontWeight": "bold",
                    "textAlign": "center",
                    "border": "1px solid #333",
                    "fontSize": "12px",
                },
                style_cell={
                    "backgroundColor": "#2b2b2b",
                    "color": "white",
                    "textAlign": "center",
                    "padding": "6px",
                    "border": "1px solid #333",
                    "fontSize": "13px",
                },
                style_cell_conditional=[  # type: ignore
                    {"if": {"column_id": "Pos"}, "width": "50px"},
                    {"if": {"column_id": "Driver"}, "width": "70px", "fontWeight": "bold"},
                    {"if": {"column_id": "GapAhead"}, "width": "90px"},
                    {"if": {"column_id": "GapLeader"}, "width": "90px"},
                    {"if": {"column_id": "LastLap"}, "width": "100px"},
                    {"if": {"column_id": "Tire"}, "width": "70px"},
                ],
                style_data={
                    "border": "1px solid #444",
                },
            )

        except Exception as e:
            logger.error(f"Error building leaderboard: {e}")
            return html.Div(
                f"Error loading leaderboard: {str(e)}",
                className="text-danger text-center p-3",
            )

    @staticmethod
    def _build_circuit_map(session_obj, laps, results, current_time=None):
        """
        Build circuit map with driver positions.
        
        NOTE: Circuit map disabled - OpenF1 API does not provide X/Y telemetry
        data required for track visualization. FastF1 telemetry would be needed.

        Args:
            session_obj: FastF1 session object
            laps: Session laps dataframe
            results: Session results dataframe
            current_time: Current simulation time (for driver positions)

        Returns:
            dcc.Graph component with circuit map
        """
        try:
            # OpenF1 does not provide X/Y telemetry - return placeholder
            logger.warning(
                "Circuit map unavailable: OpenF1 API does not provide "
                "position telemetry (X/Y coordinates)"
            )
            return html.Div(
                [
                    html.H5(
                        "Circuit Map",
                        className="text-center text-light mb-3"
                    ),
                    html.P(
                        "Circuit visualization unavailable with OpenF1 data source. "
                        "Position telemetry (X/Y coordinates) not provided by API.",
                        className="text-center text-muted",
                        style={"fontSize": "14px", "padding": "20px"}
                    )
                ],
                className="border border-secondary rounded p-3",
                style={
                    "backgroundColor": "#1e1e1e",
                    "minHeight": "400px",
                    "display": "flex",
                    "flexDirection": "column",
                    "justifyContent": "center"
                }
            )
            
            # Original FastF1 code kept for reference but unreachable:
            # Get reference lap for circuit outline (first driver, first lap)
            first_driver = session_obj.drivers[0]
            driver_laps = laps[laps["DriverNumber"] == first_driver]
            if driver_laps.empty:
                raise ValueError("No laps found for circuit outline")

            reference_lap = driver_laps.iloc[0]
            telemetry = reference_lap.get_telemetry()

            if telemetry.empty or "X" not in telemetry.columns:
                raise ValueError("No telemetry data available")

            # Create figure
            fig = go.Figure()

            # Circuit outline (Trace 0)
            fig.add_trace(
                go.Scatter(
                    x=telemetry["X"],
                    y=telemetry["Y"],
                    mode="lines",
                    line=dict(color="white", width=2),
                    name="Circuit",
                    hoverinfo="skip",
                    showlegend=False,
                )
            )

            # Start/Finish marker (Trace 1)
            fig.add_trace(
                go.Scatter(
                    x=[telemetry["X"].iloc[0]],
                    y=[telemetry["Y"].iloc[0]],
                    mode="markers+text",
                    marker=dict(size=15, color="lime", symbol="square"),
                    text=["START"],
                    textposition="top center",
                    textfont=dict(color="lime", size=10),
                    name="Start/Finish",
                    hoverinfo="skip",
                    showlegend=False,
                )
            )

            # Add driver positions (Traces 2+)
            RaceOverviewDashboard._add_driver_positions(
                fig, session_obj, laps, current_time
            )

            # Configure layout
            fig.update_layout(
                plot_bgcolor="#0e1117",
                paper_bgcolor="#0e1117",
                xaxis=dict(
                    showgrid=False,
                    showticklabels=False,
                    zeroline=False,
                    scaleanchor="y",
                    scaleratio=1,
                ),
                yaxis=dict(
                    showgrid=False, showticklabels=False, zeroline=False
                ),
                margin=dict(l=10, r=10, t=10, b=10),
                height=600,
                hovermode="closest",
                showlegend=False,
            )

            return dcc.Graph(
                id="circuit-map-graph",
                figure=fig,
                config={"displayModeBar": False},
                style={"height": "600px"},
            )

        except Exception as e:
            logger.error(f"Error building circuit map: {e}")
            return html.Div(
                f"Error loading circuit map: {str(e)}",
                className="text-danger text-center p-3",
            )

    @staticmethod
    def _add_driver_positions(fig, session_obj, laps, current_time=None):
        """
        Add driver position markers to the circuit map.

        Args:
            fig: Plotly figure object
            session_obj: FastF1 session object
            laps: Session laps dataframe
            current_time: Current simulation time (for position calculation)
        """
        try:
            drivers = session_obj.drivers
            results = session_obj.results

            for driver_num in drivers:
                try:
                    driver_info = results[
                        results["DriverNumber"] == str(driver_num)
                    ].iloc[0]
                    abbr = driver_info["Abbreviation"]
                    team = driver_info["TeamName"]
                    color = TEAM_COLORS.get(team, "#FFFFFF")

                    # Get driver's laps
                    driver_laps = laps[laps["DriverNumber"] == driver_num]
                    if driver_laps.empty:
                        continue

                    # Find appropriate lap based on current_time
                    if (
                        current_time is not None
                        and "Time" in driver_laps.columns
                    ):
                        valid_laps = driver_laps[
                            pd.notna(driver_laps["Time"])
                            & (driver_laps["Time"] <= current_time)
                        ]
                        if not valid_laps.empty:
                            current_lap = valid_laps.iloc[-1]
                        else:
                            current_lap = driver_laps.iloc[0]
                    else:
                        # Default to first lap (grid positions)
                        current_lap = driver_laps.iloc[0]

                    telemetry = current_lap.get_telemetry()

                    if (
                        not telemetry.empty
                        and "X" in telemetry.columns
                        and "Y" in telemetry.columns
                    ):
                        if (
                            current_time is not None
                            and "Time" in telemetry.columns
                        ):
                            # Find closest telemetry point by time
                            valid_telem = telemetry[
                                pd.notna(telemetry["Time"])
                            ]
                            if not valid_telem.empty:
                                time_diffs = (
                                    valid_telem["Time"] - current_time
                                ).abs()
                                closest_idx = time_diffs.idxmin()
                                x_pos = telemetry.loc[closest_idx, "X"]
                                y_pos = telemetry.loc[closest_idx, "Y"]
                            else:
                                x_pos = telemetry["X"].iloc[0]
                                y_pos = telemetry["Y"].iloc[0]
                        else:
                            # Default to start/finish line
                            x_pos = telemetry["X"].iloc[0]
                            y_pos = telemetry["Y"].iloc[0]

                        # Add driver marker (Traces 2+ for drivers)
                        fig.add_trace(
                            go.Scatter(
                                x=[x_pos],
                                y=[y_pos],
                                mode="markers+text",
                                marker=dict(
                                    size=12,
                                    color=color,
                                    line=dict(color="white", width=1),
                                ),
                                text=[abbr],
                                textposition="middle center",
                                textfont=dict(size=8, color="black"),
                                name=f"{abbr} ({team})",
                                hovertemplate=(
                                    f"<b>{abbr}</b><br>Team: {team}<extra></extra>"
                                ),
                            )
                        )

                except Exception as e:
                    logger.debug(f"Error processing driver {driver_num}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error adding driver positions: {e}")
