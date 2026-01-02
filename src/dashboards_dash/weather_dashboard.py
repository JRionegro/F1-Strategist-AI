"""
Weather Dashboard - Phase 1 MVP

Displays current weather conditions and temperature evolution for F1 sessions.
Uses OpenF1 API data exclusively in this MVP phase.

Features:
- Current weather conditions panel (temp, humidity, wind, pressure)
- Temperature evolution graph (air + track temperature over time)
- Basic Weather Agent integration for strategy impact analysis
- Simulation mode: Historical weather conditions
- Live mode: Real-time updates every 1-2 minutes

Future Phases:
- Phase 2: Satellite rain radar (RainViewer API), forecasts
- Phase 3: Wind by sector, AI predictions, automatic alerts
"""

import logging
from typing import Optional, Any

import pandas as pd
import plotly.graph_objects as go
from dash import dcc, html
import dash_bootstrap_components as dbc
from plotly.subplots import make_subplots

logger = logging.getLogger(__name__)


def _degrees_to_cardinal(degrees: float) -> str:
    """Convert wind direction in degrees to cardinal direction."""
    directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
    index = round(degrees / 45) % 8
    return directions[index]


def _degrees_to_arrow(degrees: float) -> str:
    """Convert wind direction in degrees to arrow character."""
    # Arrows point in the direction the wind is GOING TO
    # Wind from N (0°) blows south, so arrow points down
    arrows = ['↓', '↙', '←', '↖', '↑', '↗', '→', '↘']
    index = round(degrees / 45) % 8
    return arrows[index]


def create_weather_dashboard() -> html.Div:
    """
    Create compact Weather dashboard layout (Phase 1 MVP).

    Returns:
        Dash HTML component with weather dashboard layout
    """
    return html.Div(
        [
            # Current Conditions Panel (compact)
            dbc.Card(
                [
                    dbc.CardHeader([
                        html.H5("☁️ Weather", className="mb-0", style={"fontSize": "1.2rem"})
                    ], className="py-1"),
                    dbc.CardHeader(
                        id="weather-conditions-header",
                        className="text-white py-1",
                        style={"fontSize": "0.9rem", "backgroundColor": "#1e1e1e", "display": "flex", "justifyContent": "space-between", "alignItems": "center"}
                    ),
                    dbc.CardBody(
                        id="weather-conditions-panel",
                        className="text-white p-2",
                        style={"backgroundColor": "#1e1e1e"}
                    ),
                ],
                className="mb-2 border border-secondary",
                style={"backgroundColor": "#1e1e1e"}
            ),
            # Temperature Graph (compact)
            dbc.Card(
                [
                    dbc.CardHeader(
                        "🌡️ Temperature",
                        className="text-white py-1",
                        style={"fontSize": "0.9rem", "backgroundColor": "#1e1e1e"}
                    ),
                    dbc.CardBody(
                        [
                            dcc.Graph(
                                id="weather-temperature-graph",
                                config={"responsive": True, "displayModeBar": False},
                                style={"height": "198px"}
                            ),
                        ],
                        className="p-1",
                        style={"backgroundColor": "#1e1e1e"}
                    ),
                ],
                className="mb-2 border border-secondary",
                style={"backgroundColor": "#1e1e1e"}
            ),
            # Strategy Impact Panel (compact)
            dbc.Card(
                [
                    dbc.CardHeader(
                        "⚠️ Strategy Impact",
                        className="text-white py-1",
                        style={"fontSize": "0.9rem", "backgroundColor": "#1e1e1e"}
                    ),
                    dbc.CardBody(
                        id="weather-strategy-panel",
                        className="text-white p-2",
                        style={"backgroundColor": "#1e1e1e"}
                    ),
                ],
                className="mb-2 border border-secondary",
                style={"backgroundColor": "#1e1e1e"}
            ),
            # Hidden div to store weather data
            html.Div(
                id="weather-data-store",
                style={"display": "none"}
            ),
        ],
        className="p-2"
    )


def create_weather_conditions_panel(
    weather_df: Optional[pd.DataFrame]
) -> tuple[html.Div, str] | html.Div:
    """
    Create current weather conditions display panel.

    Args:
        weather_df: Weather data DataFrame from OpenF1

    Returns:
        Tuple of (Dash HTML component with weather metrics, timestamp string)
        or just Dash HTML component if no data
    """
    if weather_df is None or weather_df.empty:
        return html.Div(
            [
                html.P(
                    "Weather data unavailable",
                    className="text-muted text-center my-4"
                ),
                html.Small(
                    (
                        "Weather data is available for sessions from 2023 "
                        "onwards"
                    ),
                    className="text-muted"
                ),
            ]
        )

    # Get latest weather reading
    latest = weather_df.iloc[-1]

    # Get wind direction and convert to cardinal + arrow
    wind_dir = latest.get('WindDirection', 0) or 0
    cardinal = _degrees_to_cardinal(wind_dir)
    arrow = _degrees_to_arrow(wind_dir)

    # Create ultra-compact weather metrics for single line
    metrics = [
        ("🌡️", f"{latest['AirTemp']:.0f}°C", "Air"),
        ("🛣️", f"{latest['TrackTemp']:.0f}°C", "Track"),
        ("💧", f"{latest['Humidity']:.0f}%", "Hum"),
        ("🌪️", f"{latest['WindSpeed']:.0f} {arrow}{cardinal}", "Wind"),
        ("🌧️", "Y" if latest['Rainfall'] else "N", "Rain"),
    ]

    # Create ultra-compact metric display (single line)
    metric_items = []
    for icon, value, label in metrics:
        metric_items.append(
            html.Span(
                [
                    html.Span(icon, style={"fontSize": "0.9rem", "marginRight": "2px"}),
                    html.Strong(value, className="text-info", style={"fontSize": "0.75rem"}),
                    html.Span(f" {label}", className="text-muted", style={"fontSize": "0.65rem"}),
                ],
                className="me-2",
                style={"whiteSpace": "nowrap"}
            )
        )

    # Return tuple: (conditions_content, timestamp)
    conditions_content = html.Div(
        [
            html.Div(
                metric_items,
                style={"display": "flex", "flexWrap": "nowrap", "overflowX": "auto"}
            ),
        ]
    )
    
    timestamp = latest['Time'].strftime('%H:%M')
    
    return (conditions_content, timestamp)


def create_temperature_graph(
    weather_df: Optional[pd.DataFrame],
    current_time: Optional[Any] = None
) -> go.Figure:
    """
    Create temperature evolution graph (air + track temperature).

    Args:
        weather_df: Weather data DataFrame from OpenF1
        current_time: Current simulation time to mark on the graph

    Returns:
        Plotly Figure with temperature evolution
    """
    if weather_df is None or weather_df.empty:
        # Return empty figure with message
        fig = go.Figure()
        fig.add_annotation(
            text="Weather data unavailable",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font={"size": 16, "color": "gray"}
        )
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0d1117",
            plot_bgcolor="#161b22",
            height=400
        )
        return fig

    # Create figure with secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": False}]])

    # Add air temperature trace
    fig.add_trace(
        go.Scatter(
            x=weather_df["Time"],
            y=weather_df["AirTemp"],
            name="Air Temperature",
            mode="lines",
            line={"color": "#17a2b8", "width": 2},
            hovertemplate=(
                "<b>Air Temp</b><br>"
                "%{y:.1f}°C<br>"
                "%{x|%H:%M:%S}<br>"
                "<extra></extra>"
            )
        )
    )

    # Add track temperature trace
    fig.add_trace(
        go.Scatter(
            x=weather_df["Time"],
            y=weather_df["TrackTemp"],
            name="Track Temperature",
            mode="lines",
            line={"color": "#dc3545", "width": 2},
            hovertemplate=(
                "<b>Track Temp</b><br>"
                "%{y:.1f}°C<br>"
                "%{x|%H:%M:%S}<br>"
                "<extra></extra>"
            )
        )
    )

    # Add current time marker if provided
    if current_time is not None:
        try:
            # Convert current_time to datetime if needed
            if isinstance(current_time, str):
                from datetime import datetime
                current_time = datetime.fromisoformat(current_time.replace('Z', '+00:00'))
            
            # Add vertical line at current simulation time
            fig.add_vline(
                x=current_time,
                line_dash="dash",
                line_color="#ffc107",
                line_width=2,
                annotation_text="Now",
                annotation_position="top",
                annotation_font_size=9,
                annotation_font_color="#ffc107"
            )
        except Exception as e:
            logger.warning(f"Could not add current time marker: {e}")
    
    # Update layout (compact) - legend above graph area
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0d1117",
        plot_bgcolor="#161b22",
        hovermode="x unified",
        showlegend=True,
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
            "font": {"size": 8},
            "bgcolor": "rgba(0,0,0,0)"
        },
        xaxis={
            "title": None,
            "gridcolor": "#30363d",
            "showgrid": False,
            "tickfont": {"size": 8}
        },
        yaxis={
            "title": "°C",
            "gridcolor": "#30363d",
            "showgrid": True,
            "tickfont": {"size": 8}
        },
        height=200,
        margin={"l": 30, "r": 5, "t": 25, "b": 25}
    )

    return fig


def create_weather_strategy_panel(
    weather_df: Optional[pd.DataFrame],
    session_type: str
) -> html.Div:
    """
    Create weather strategy impact panel with basic analysis.

    Args:
        weather_df: Weather data DataFrame from OpenF1
        session_type: Type of session (Race, Qualifying, etc.)

    Returns:
        Dash HTML component with strategy impact information
    """
    if weather_df is None or weather_df.empty:
        return html.Div(
            [
                html.P(
                    "Weather analysis unavailable",
                    className="text-muted text-center my-4"
                ),
            ]
        )

    latest = weather_df.iloc[-1]

    # Basic strategy insights based on conditions
    insights = []

    # Temperature analysis
    if latest["TrackTemp"] > 45:
        insights.append({
            "icon": "🔥",
            "title": "High Track Temperature",
            "text": (
                f"Track temperature at {latest['TrackTemp']:.1f}°C. "
                "Expect higher tire degradation, especially on soft "
                "compounds. Consider shorter stint lengths."
            ),
            "color": "danger"
        })
    elif latest["TrackTemp"] < 25:
        insights.append({
            "icon": "❄️",
            "title": "Low Track Temperature",
            "text": (
                f"Track temperature at {latest['TrackTemp']:.1f}°C. "
                "Tire warm-up may be challenging. Softer compounds "
                "recommended for better grip."
            ),
            "color": "info"
        })

    # Wind analysis
    if latest["WindSpeed"] > 30:
        insights.append({
            "icon": "💨",
            "title": "Strong Wind Conditions",
            "text": (
                f"Wind speed at {latest['WindSpeed']:.1f} km/h from "
                f"{latest['WindDirection']:.0f}°. Expect impact on "
                "braking zones and high-speed corners. Adjust "
                "downforce settings."
            ),
            "color": "warning"
        })

    # Rainfall analysis
    if latest["Rainfall"]:
        insights.append({
            "icon": "🌧️",
            "title": "Rain Detected",
            "text": (
                "Rain is falling at the circuit. Intermediate or wet "
                "tires required. Monitor track evolution closely for "
                "optimal crossover timing to slicks."
            ),
            "color": "primary"
        })
    else:
        insights.append({
            "icon": "☀️",
            "title": "Dry Conditions",
            "text": (
                "Track is dry. Slick tires optimal. Focus on tire "
                "management and degradation patterns."
            ),
            "color": "success"
        })

    # Humidity analysis
    if latest["Humidity"] > 70:
        insights.append({
            "icon": "💧",
            "title": "High Humidity",
            "text": (
                f"Humidity at {latest['Humidity']:.1f}%. May affect "
                "brake cooling and engine performance. Monitor "
                "component temperatures."
            ),
            "color": "info"
        })

    # Create compact insight badges
    insight_badges = []
    for insight in insights:
        insight_badges.append(
            html.Div(
                [
                    html.Span(insight["icon"], style={"fontSize": "1rem", "marginRight": "4px"}),
                    html.Small(
                        [
                            html.Strong(f"{insight['title']}: ", style={"fontSize": "0.75rem"}),
                            html.Span(insight["text"], style={"fontSize": "0.7rem"}),
                        ],
                        className=f"text-{insight['color']}"
                    ),
                ],
                className="mb-1 p-1 border-bottom border-secondary"
            )
        )

    return html.Div(
        [
            html.Div(insight_badges),
            html.Small(
                "💡 For AI analysis, use Weather Agent",
                className="text-muted",
                style={"fontSize": "0.65rem"}
            ),
        ]
    )


def get_weather_data(
    session_key: Optional[int],
    data_provider: Optional[Any] = None
) -> Optional[pd.DataFrame]:
    """
    Fetch weather data for the current session.

    Args:
        session_key: OpenF1 session key
        data_provider: OpenF1DataProvider instance (if None, attempts to import)

    Returns:
        Weather DataFrame or None if unavailable
    """
    if session_key is None:
        logger.warning("No session key provided for weather data")
        return None

    try:
        # If no provider given, try to import from app context
        if data_provider is None:
            try:
                from src.data.openf1_data_provider import OpenF1DataProvider
                data_provider = OpenF1DataProvider()
            except ImportError:
                logger.error("Could not import OpenF1DataProvider")
                return None

        weather_df = data_provider.get_weather(session_key)

        if weather_df is None or weather_df.empty:
            logger.warning(
                f"No weather data available for session {session_key}"
            )
            return None

        logger.info(
            f"Loaded {len(weather_df)} weather records for session "
            f"{session_key}"
        )
        return weather_df

    except Exception as e:
        logger.error(f"Error fetching weather data: {e}", exc_info=True)
        return None


# Export functions for use in callbacks
__all__ = [
    "create_weather_dashboard",
    "create_weather_conditions_panel",
    "create_temperature_graph",
    "create_weather_strategy_panel",
    "get_weather_data",
    "render_weather_content",
]


def render_weather_content(session_key: Optional[int] = None, simulation_time: Optional[float] = None) -> dbc.Card:
    """
    Render complete Weather dashboard content with live data.
    
    This function generates all weather dashboard components in one go,
    similar to how race_overview_dashboard.render() works.
    
    Args:
        session_key: OpenF1 session key (integer)
        simulation_time: Current simulation time in seconds (optional)
    
    Returns:
        Complete Weather dashboard Card component
    """
    try:
        # Get weather data
        weather_df = get_weather_data(session_key)
        
        if weather_df is None or weather_df.empty:
            logger.warning(f"No weather data for session {session_key}")
            return dbc.Card([
                dbc.CardHeader([
                    html.H4([
                        "☁️ Weather"
                    ], className="mb-0", style={"fontSize": "0.9rem"})
                ]),
                dbc.CardBody([
                    html.P("No weather data available for this session", 
                           className="text-muted text-center p-3")
                ])
            ], className="mb-3", style={"height": "650px"})
        
        # Filter data by simulation time if provided
        filtered_weather_df = weather_df
        if simulation_time is not None and not weather_df.empty:
            try:
                from datetime import timedelta
                # Get session start time from weather data
                session_start = weather_df['Time'].min()
                # Calculate current datetime from elapsed seconds
                current_time_dt = session_start + timedelta(seconds=simulation_time)
                
                # Filter weather data up to current simulation time
                filtered_weather_df = weather_df[weather_df['Time'] <= current_time_dt].copy()
                
                # If no data before current time, use all data (edge case at start)
                if filtered_weather_df.empty:
                    filtered_weather_df = weather_df
                    logger.debug("No weather data before current time, using all data")
                else:
                    logger.debug(
                        f"Filtered weather: {len(filtered_weather_df)}/{len(weather_df)} records"
                    )
                    
            except Exception as e:
                logger.warning(f"Could not filter weather by simulation time: {e}")
                filtered_weather_df = weather_df
        
        # Generate all components with filtered data
        conditions_result = create_weather_conditions_panel(filtered_weather_df)
        
        # Unpack result - returns tuple (content, timestamp) or just content
        if isinstance(conditions_result, tuple):
            conditions_panel, timestamp = conditions_result
            conditions_header = html.Div(
                [
                    html.Span("🌤️ Conditions"),
                    html.Span(
                        f"{timestamp}",
                        style={"fontSize": "0.75rem", "opacity": "0.8"}
                    )
                ],
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "alignItems": "center",
                    "width": "100%"
                }
            )
        else:
            conditions_panel = conditions_result
            conditions_header = html.Span("🌤️ Conditions")
        
        temperature_graph = create_temperature_graph(filtered_weather_df)
        strategy_panel = create_weather_strategy_panel(filtered_weather_df, "Race")
        
        # Return complete layout with proper title structure (similar to AI Assistant)
        return dbc.Card([
            dbc.CardHeader([
                html.H5(
                    "☁️ Weather",
                    className="mb-0",
                    style={"fontSize": "1.2rem"}
                )
            ], className="py-1"),
            dbc.CardBody([
                # Current Conditions Panel
                dbc.Card([
                    dbc.CardHeader(
                        conditions_header,
                        className="text-white py-1",
                        style={"fontSize": "0.9rem", "backgroundColor": "#1e1e1e"}
                    ),
                    dbc.CardBody(
                        conditions_panel,
                        className="text-white p-2",
                        style={"backgroundColor": "#1e1e1e"}
                    ),
                ], className="mb-2 border border-secondary", style={"backgroundColor": "#1e1e1e"}),
                
                # Temperature Graph
                dbc.Card([
                    dbc.CardHeader(
                        "🌡️ Temperature",
                        className="text-white py-1",
                        style={"fontSize": "0.9rem", "backgroundColor": "#1e1e1e"}
                    ),
                    dbc.CardBody([
                        dcc.Graph(
                            figure=temperature_graph,
                            config={"responsive": True, "displayModeBar": False},
                            style={"height": "198px"}
                        ),
                    ], className="p-1", style={"backgroundColor": "#1e1e1e"}),
                ], className="mb-2 border border-secondary", style={"backgroundColor": "#1e1e1e"}),
                
                # Strategy Impact Panel
                dbc.Card([
                    dbc.CardHeader(
                        "⚠️ Strategy Impact",
                        className="text-white py-1",
                        style={"fontSize": "0.9rem", "backgroundColor": "#1e1e1e"}
                    ),
                    dbc.CardBody(
                        strategy_panel,
                        className="text-white p-2",
                        style={"backgroundColor": "#1e1e1e"}
                    ),
                ], className="mb-2 border border-secondary", style={"backgroundColor": "#1e1e1e"}),
            ])
        ], className="mb-3", style={"height": "620px", "overflow": "auto"})
        
    except Exception as e:
        logger.error(f"Error rendering weather content: {e}", exc_info=True)
        return dbc.Card([
            dbc.CardHeader([
                html.H4([
                    "☁️ Weather"
                ], className="mb-0", style={"fontSize": "0.9rem"})
            ]),
            dbc.CardBody([
                html.P(f"Error loading weather: {str(e)}", className="text-danger text-center p-3")
            ])
        ], className="mb-3", style={"height": "650px"})
