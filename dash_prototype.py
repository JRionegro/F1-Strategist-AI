"""
Dash Prototype - F1 Strategist AI
Compare layout flexibility with Streamlit version.
"""

from dash import Dash, html, dcc, Input, Output, callback
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

# Initialize Dash app with Bootstrap theme
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG],  # F1 dark theme
    suppress_callback_exceptions=True
)

# Mock data for demo
def create_telemetry_chart():
    """Sample telemetry chart."""
    laps = np.arange(1, 58)
    speed = 280 + np.random.randn(57) * 15
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=laps, y=speed,
        mode='lines',
        name='Speed',
        line=dict(color='#e10600', width=2)
    ))
    fig.update_layout(
        title='Speed per Lap',
        xaxis_title='Lap',
        yaxis_title='Speed (km/h)',
        template='plotly_dark',
        height=300,
        margin=dict(l=40, r=20, t=40, b=30)
    )
    return fig


def create_circuit_map():
    """Sample circuit map."""
    theta = np.linspace(0, 2*np.pi, 100)
    x = np.cos(theta) * 100
    y = np.sin(theta) * 100
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=y,
        mode='lines',
        line=dict(color='white', width=3),
        name='Track'
    ))
    # Add car position
    fig.add_trace(go.Scatter(
        x=[100], y=[0],
        mode='markers',
        marker=dict(size=15, color='#e10600'),
        name='VER'
    ))
    fig.update_layout(
        title='Circuit Map - Abu Dhabi',
        template='plotly_dark',
        height=400,
        showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=dict(l=20, r=20, t=40, b=20)
    )
    return fig


def create_tire_strategy():
    """Sample tire strategy chart."""
    drivers = ['VER', 'HAM', 'LEC', 'NOR', 'PIA']
    df = pd.DataFrame({
        'Driver': drivers,
        'Soft': np.random.randint(5, 15, 5),
        'Medium': np.random.randint(10, 25, 5),
        'Hard': np.random.randint(15, 30, 5)
    })
    
    fig = go.Figure()
    fig.add_trace(go.Bar(name='Soft', x=df['Driver'], y=df['Soft'], 
                         marker_color='#e10600'))
    fig.add_trace(go.Bar(name='Medium', x=df['Driver'], y=df['Medium'],
                         marker_color='#ffd700'))
    fig.add_trace(go.Bar(name='Hard', x=df['Driver'], y=df['Hard'],
                         marker_color='white'))
    
    fig.update_layout(
        title='Tire Strategy',
        barmode='stack',
        template='plotly_dark',
        height=300,
        margin=dict(l=40, r=20, t=40, b=30)
    )
    return fig


def create_positions_chart():
    """Sample positions chart."""
    laps = list(range(1, 58))
    positions = [1 + np.random.randint(-1, 2) for _ in laps]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=laps, y=positions,
        mode='lines+markers',
        name='VER',
        line=dict(color='#e10600', width=2)
    ))
    fig.update_layout(
        title='Position History',
        xaxis_title='Lap',
        yaxis_title='Position',
        template='plotly_dark',
        height=250,
        yaxis=dict(autorange='reversed'),
        margin=dict(l=40, r=20, t=40, b=30)
    )
    return fig


def create_weather_chart():
    """Sample weather chart."""
    time = pd.date_range('2025-12-22 14:00', periods=60, freq='min')
    temp = 28 + np.random.randn(60) * 2
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=time, y=temp,
        mode='lines',
        fill='tozeroy',
        name='Temperature',
        line=dict(color='#ff6b35', width=2)
    ))
    fig.update_layout(
        title='Weather Forecast',
        xaxis_title='Time',
        yaxis_title='Temperature (°C)',
        template='plotly_dark',
        height=250,
        margin=dict(l=40, r=20, t=40, b=30)
    )
    return fig


# Sidebar content
sidebar = dbc.Col([
    html.Div([
        html.H2("🏎️ F1 Strategist", className="text-center mb-4"),
        
        # Mode selector
        html.H6("🎮 Mode", className="mb-2"),
        dbc.RadioItems(
            id="mode-selector",
            options=[
                {"label": "🔴 Live", "value": "live"},
                {"label": "⏯️ Simulation", "value": "sim"}
            ],
            value="sim",
            className="mb-3"
        ),
        
        html.Hr(),
        
        # Context selector (collapsed)
        dbc.Accordion([
            dbc.AccordionItem([
                dbc.Label("Year"),
                dcc.Dropdown(
                    id='year-selector',
                    options=[{'label': str(y), 'value': y} for y in range(2023, 2026)],
                    value=2025,
                    className="mb-2"
                ),
                dbc.Label("Circuit"),
                dcc.Dropdown(
                    id='circuit-selector',
                    options=[
                        {'label': 'Abu Dhabi', 'value': 'abu_dhabi'},
                        {'label': 'Monaco', 'value': 'monaco'},
                        {'label': 'Monza', 'value': 'monza'}
                    ],
                    value='abu_dhabi',
                    className="mb-2"
                ),
                dbc.Label("Driver"),
                dcc.Dropdown(
                    id='driver-selector',
                    options=[
                        {'label': d, 'value': d} 
                        for d in ['VER', 'HAM', 'LEC', 'NOR', 'PIA']
                    ],
                    value='VER'
                )
            ], title="📍 Context", className="mb-3")
        ], start_collapsed=True),
        
        html.Hr(),
        
        # Dashboard selector
        html.H6("📊 Dashboards", className="mb-2"),
        dbc.Checklist(
            id="dashboard-selector",
            options=[
                {"label": "Telemetry", "value": "telemetry"},
                {"label": "Circuit & Positions", "value": "circuit"},
                {"label": "Tire Strategy", "value": "tires"},
                {"label": "Weather", "value": "weather"},
                {"label": "AI Assistant", "value": "ai"}
            ],
            value=["telemetry", "circuit", "tires", "weather"],
            className="mb-3"
        ),
        
        html.Hr(),
        
        # Simulation controls
        dbc.Accordion([
            dbc.AccordionItem([
                dbc.Row([
                    dbc.Col([
                        dbc.Button("▶️", id="play-btn", color="success", 
                                   className="w-100")
                    ], width=6),
                    dbc.Col([
                        dbc.Button("⏮️", id="restart-btn", color="secondary",
                                   className="w-100")
                    ], width=6)
                ], className="mb-2"),
                
                dbc.Label("Speed"),
                dcc.Slider(
                    id='speed-slider',
                    min=1, max=10, step=1, value=1,
                    marks={i: f'{i}x' for i in [1, 5, 10]}
                ),
                
                html.Div("⏱️ Lap 15/57 | ⏳ 45m left", 
                         className="text-center mt-3 small")
            ], title="⏯️ Playback", className="mb-3")
        ], start_collapsed=True)
        
    ], className="p-3", style={'height': '100vh', 'overflow-y': 'auto'})
], width=3, className="bg-dark border-end")


# Main content with flexible grid layout
main_content = dbc.Col([
    html.Div([
        # FLEXIBLE 3-COLUMN GRID - Easy to customize widths
        dbc.Row([
            # LEFT COLUMN (narrow) - 25% width
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        dcc.Graph(
                            id='telemetry-chart',
                            figure=create_telemetry_chart(),
                            config={'displayModeBar': False}
                        )
                    ])
                ], className="mb-3"),
                
                dbc.Card([
                    dbc.CardBody([
                        dcc.Graph(
                            id='tire-chart',
                            figure=create_tire_strategy(),
                            config={'displayModeBar': False}
                        )
                    ])
                ], className="mb-3")
            ], width=3),  # 25% width
            
            # CENTER COLUMN (wider) - 50% width
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        dcc.Graph(
                            id='circuit-map',
                            figure=create_circuit_map(),
                            config={'displayModeBar': False}
                        )
                    ])
                ], className="mb-3"),
                
                dbc.Card([
                    dbc.CardBody([
                        html.H5("💬 AI Assistant", className="mb-3"),
                        dbc.Textarea(
                            placeholder="Ask about race strategy...",
                            className="mb-2",
                            style={'height': '100px'}
                        ),
                        dbc.Button("Send", color="primary", size="sm")
                    ])
                ], className="mb-3")
            ], width=6),  # 50% width
            
            # RIGHT COLUMN (narrow) - 25% width
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        dcc.Graph(
                            id='positions-chart',
                            figure=create_positions_chart(),
                            config={'displayModeBar': False}
                        )
                    ])
                ], className="mb-3"),
                
                dbc.Card([
                    dbc.CardBody([
                        dcc.Graph(
                            id='weather-chart',
                            figure=create_weather_chart(),
                            config={'displayModeBar': False}
                        )
                    ])
                ], className="mb-3")
            ], width=3)  # 25% width
        ])
    ], className="p-3")
], width=9)


# App layout
app.layout = dbc.Container([
    dbc.Row([
        sidebar,
        main_content
    ], className="g-0")
], fluid=True, className="vh-100")


# Callbacks for interactivity (optional, for demo)
@callback(
    Output('telemetry-chart', 'figure'),
    Input('driver-selector', 'value')
)
def update_telemetry(driver):
    """Update telemetry chart when driver changes."""
    return create_telemetry_chart()


if __name__ == '__main__':
    print("\n" + "="*60)
    print("🏎️  F1 STRATEGIST AI - DASH PROTOTYPE")
    print("="*60)
    print("\nStarting Dash application...")
    print("Open: http://localhost:8050")
    print("\nPress Ctrl+C to stop\n")
    
    app.run(debug=True, port=8050)
