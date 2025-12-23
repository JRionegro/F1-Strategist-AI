"""
Circuit Map Dashboard for F1 Strategist AI.

Displays circuit layout with real-time driver positions.
"""

import logging
from typing import Optional
import plotly.graph_objects as go
from dash import html, dcc
import dash_bootstrap_components as dbc

logger = logging.getLogger(__name__)


# Team colors (2025 season)
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


class CircuitMapDashboard:
    """Circuit map visualization dashboard."""
    
    @staticmethod
    def create_layout(session_obj=None, current_time=None):
        """
        Create circuit map dashboard layout.
        
        Args:
            session_obj: FastF1 session object
            current_time: Current simulation time (for position updates)
            
        Returns:
            Dash component with circuit map
        """
        if session_obj is None:
            return dbc.Card([
                dbc.CardHeader(html.H5("🗺️ Circuit Map & Positions")),
                dbc.CardBody([
                    html.P(
                        "Select a session to view circuit map",
                        className="text-center text-muted mt-5"
                    )
                ])
            ], className="mb-3")
        
        # Create circuit map figure
        fig = CircuitMapDashboard._create_circuit_figure(session_obj, current_time)
        
        return dbc.Card([
            dbc.CardHeader([
                html.H5("🗺️ Circuit Map & Positions", className="d-inline"),
                html.Span(
                    f" - {session_obj.event['EventName']} ({session_obj.event.year})",
                    className="text-muted small"
                )
            ]),
            dbc.CardBody([
                dcc.Graph(
                    id='circuit-map-graph',
                    figure=fig,
                    config={'displayModeBar': False},
                    style={'height': '600px'}
                )
            ])
        ], className="mb-3")
    
    @staticmethod
    def _create_circuit_figure(session_obj, current_time=None):
        """
        Create Plotly figure with circuit layout and driver positions.
        
        Args:
            session_obj: FastF1 session object
            current_time: Current simulation time for position updates
            
        Returns:
            Plotly Figure object
        """
        fig = go.Figure()
        
        try:
            # Get position data for all laps
            laps = session_obj.laps
            
            if laps.empty:
                logger.warning("No lap data available for circuit map")
                return CircuitMapDashboard._create_empty_figure(
                    "No lap data available"
                )
            
            # Draw circuit outline using first driver's telemetry
            first_driver = laps['DriverNumber'].iloc[0]
            first_lap = laps[laps['DriverNumber'] == first_driver].iloc[0]
            
            try:
                telemetry = first_lap.get_telemetry()
                
                if not telemetry.empty and 'X' in telemetry.columns and 'Y' in telemetry.columns:
                    # Circuit outline
                    fig.add_trace(go.Scatter(
                        x=telemetry['X'],
                        y=telemetry['Y'],
                        mode='lines',
                        line=dict(color='white', width=2),
                        name='Circuit',
                        hoverinfo='skip',
                        showlegend=False
                    ))
                    
                    # Add start/finish line marker
                    fig.add_trace(go.Scatter(
                        x=[telemetry['X'].iloc[0]],
                        y=[telemetry['Y'].iloc[0]],
                        mode='markers+text',
                        marker=dict(size=15, color='lime', symbol='square'),
                        text=['START'],
                        textposition='top center',
                        textfont=dict(color='lime', size=10),
                        name='Start/Finish',
                        hoverinfo='skip'
                    ))
            except Exception as e:
                logger.warning(f"Could not load telemetry for circuit outline: {e}")
            
            # Add driver positions
            CircuitMapDashboard._add_driver_positions(
                fig, session_obj, laps, current_time
            )
            
            # Update layout
            fig.update_layout(
                plot_bgcolor='#0a0a0a',
                paper_bgcolor='#1a1a1a',
                font=dict(color='white'),
                xaxis=dict(
                    showgrid=False,
                    zeroline=False,
                    showticklabels=False,
                    scaleanchor='y',
                    scaleratio=1
                ),
                yaxis=dict(
                    showgrid=False,
                    zeroline=False,
                    showticklabels=False
                ),
                hovermode='closest',
                margin=dict(l=10, r=10, t=10, b=10),
                showlegend=True,
                legend=dict(
                    orientation='h',
                    yanchor='top',
                    y=-0.05,
                    xanchor='center',
                    x=0.5,
                    bgcolor='rgba(0,0,0,0.5)'
                )
            )
            
        except Exception as e:
            logger.error(f"Error creating circuit map: {e}")
            return CircuitMapDashboard._create_empty_figure(f"Error: {str(e)}")
        
        return fig
    
    @staticmethod
    def _add_driver_positions(fig, session_obj, laps, current_time=None):
        """
        Add driver position markers to the circuit map.
        
        Args:
            fig: Plotly Figure object
            session_obj: FastF1 session object
            laps: Laps dataframe
            current_time: Current simulation time
        """
        try:
            # Get latest positions for each driver
            drivers = session_obj.drivers
            results = session_obj.results
            
            for driver_num in drivers:
                try:
                    # Get driver info
                    driver_info = results[results['DriverNumber'] == str(driver_num)].iloc[0]
                    abbr = driver_info['Abbreviation']
                    team = driver_info['TeamName']
                    color = TEAM_COLORS.get(team, '#FFFFFF')
                    
                    # Get driver's laps
                    driver_laps = laps[laps['DriverNumber'] == driver_num]
                    if driver_laps.empty:
                        continue
                    
                    # Find appropriate lap based on current_time
                    if current_time is not None and 'Time' in driver_laps.columns:
                        # Try to find lap based on Time column
                        try:
                            # Filter laps where Time is before or at current_time
                            import pandas as pd
                            valid_laps = driver_laps[
                                pd.notna(driver_laps['Time']) & 
                                (driver_laps['Time'] <= current_time)
                            ]
                            if not valid_laps.empty:
                                # Use the last lap that started before current_time
                                current_lap = valid_laps.iloc[-1]
                            else:
                                # Use first lap if no lap started yet
                                current_lap = driver_laps.iloc[0]
                        except Exception as e:
                            logger.debug(f"Error filtering laps for driver {driver_num}: {e}")
                            # Fallback to first lap
                            current_lap = driver_laps.iloc[0]
                    else:
                        # Use first lap if no time specified (to show all drivers at start)
                        current_lap = driver_laps.iloc[0]
                    
                    telemetry = current_lap.get_telemetry()
                    
                    if not telemetry.empty and 'X' in telemetry.columns and 'Y' in telemetry.columns:
                        # Calculate position within the lap based on current_time
                        if current_time is not None and 'Time' in telemetry.columns:
                            try:
                                # Find closest telemetry point to current_time
                                import pandas as pd
                                valid_telem = telemetry[pd.notna(telemetry['Time'])]
                                if not valid_telem.empty:
                                    time_diffs = (valid_telem['Time'] - current_time).abs()
                                    closest_idx = time_diffs.idxmin()
                                    x_pos = telemetry.loc[closest_idx, 'X']
                                    y_pos = telemetry.loc[closest_idx, 'Y']
                                else:
                                    # Fallback to first position
                                    x_pos = telemetry['X'].iloc[0]
                                    y_pos = telemetry['Y'].iloc[0]
                            except Exception as e:
                                logger.debug(f"Error calculating position for driver {driver_num}: {e}")
                                # Fallback to first position
                                x_pos = telemetry['X'].iloc[0]
                                y_pos = telemetry['Y'].iloc[0]
                        else:
                            # Default to first position (start/finish line)
                            x_pos = telemetry['X'].iloc[0]
                            y_pos = telemetry['Y'].iloc[0]
                        
                        # Add driver marker
                        fig.add_trace(go.Scatter(
                            x=[x_pos],
                            y=[y_pos],
                            mode='markers+text',
                            marker=dict(
                                size=12,
                                color=color,
                                line=dict(color='white', width=1)
                            ),
                            text=[abbr],
                            textposition='middle center',
                            textfont=dict(size=8, color='black'),
                            name=f"{abbr} ({team})",
                            hovertemplate=(
                                f"<b>{abbr}</b><br>"
                                f"Team: {team}<br>"
                                f"<extra></extra>"
                            )
                        ))
                        
                except Exception as e:
                    logger.debug(f"Could not add position for driver {driver_num}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error adding driver positions: {e}")
    
    @staticmethod
    def _create_empty_figure(message: str):
        """Create empty figure with message."""
        fig = go.Figure()
        fig.add_annotation(
            text=message,
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="gray")
        )
        fig.update_layout(
            plot_bgcolor='#0a0a0a',
            paper_bgcolor='#1a1a1a',
            xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
            yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
            height=600
        )
        return fig
