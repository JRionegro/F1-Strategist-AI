"""
AI Assistant Dashboard - Dash Version.

Proactive multi-agent conversational interface for F1 strategy.
Provides automatic alerts (pit window, safety car, undercut risk)
and allows user questions.

CRITICAL: In simulation mode, AI does NOT know the future.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from dash import html, dcc
import dash_bootstrap_components as dbc

logger = logging.getLogger(__name__)


class AIAssistantDashboard:
    """
    Proactive AI Assistant Dashboard with multi-agent chat interface.
    
    Features:
    - Automatic strategy alerts (pit window, safety car, undercut)
    - User questions routed to 5 specialized agents
    - Persistent chat history (survives simulation updates)
    - Visual distinction: user (blue), AI response (gray), alerts (amber)
    """

    @staticmethod
    def create_layout(
        focused_driver: Optional[str] = None,
        race_name: str = "Race",
        session_type: str = "Race",
        messages: Optional[List[Dict]] = None
    ):
        """
        Create the AI Assistant dashboard layout.
        
        Args:
            focused_driver: Currently focused driver code
            race_name: Current race name for display
            session_type: Session type (Race, Qualifying, etc.)
            messages: List of message dicts to render
            
        Returns:
            Dash component tree
        """
        # Render messages from store
        rendered_messages = AIAssistantDashboard.render_messages(messages or [])
        
        return dbc.Card([
            dbc.CardHeader([
                html.Div([
                    html.H4([
                        "🤖 AI Strategist"
                    ], className="mb-0 d-inline", style={"fontSize": "1.1rem"}),
                    dbc.Badge(
                        "PROACTIVE",
                        color="warning",
                        className="ms-2",
                        style={"fontSize": "0.65rem"}
                    )
                ])
            ], className="py-1"),
            dbc.CardBody([
                # Context badges - compact row
                html.Div([
                    dbc.Badge(
                        race_name[:20] if len(race_name) > 20 else race_name,
                        color="primary",
                        className="me-1",
                        style={"fontSize": "0.7rem"}
                    ),
                    dbc.Badge(
                        session_type,
                        color="success",
                        className="me-1",
                        style={"fontSize": "0.7rem"}
                    ),
                    dbc.Badge(
                        f"#{focused_driver}" if focused_driver else "No focus",
                        color="warning" if focused_driver else "secondary",
                        style={"fontSize": "0.7rem"}
                    )
                ], className="mb-2"),
                
                # Chat messages area - renders from store
                html.Div(
                    id='chat-messages-container',
                    children=rendered_messages,
                    style={
                        'overflow-y': 'auto',
                        'padding': '8px',
                        'background-color': '#1a1a1a',
                        'border-radius': '5px',
                        'margin-bottom': '8px',
                        'height': '320px'
                    }
                ),
                
                # Input area
                dbc.InputGroup([
                    dbc.Input(
                        id='chat-input',
                        placeholder="Ask about strategy, gaps, weather...",
                        style={'fontSize': '0.85rem'},
                        type="text",
                        debounce=True
                    ),
                    dbc.Button(
                        [html.I(className="bi bi-send-fill")],
                        id='chat-send-btn',
                        color="primary",
                        n_clicks=0
                    )
                ], className="mb-2", size="sm"),
                
                # Quick action buttons
                html.Div([
                    dbc.ButtonGroup([
                        dbc.Button(
                            "🔧 Pit",
                            id='quick-pit-btn',
                            size="sm",
                            outline=True,
                            color="info",
                            n_clicks=0
                        ),
                        dbc.Button(
                            "🌤️ Weather",
                            id='quick-weather-btn',
                            size="sm",
                            outline=True,
                            color="info",
                            n_clicks=0
                        ),
                        dbc.Button(
                            "📊 Gaps",
                            id='quick-gap-btn',
                            size="sm",
                            outline=True,
                            color="info",
                            n_clicks=0
                        )
                    ], size="sm", className="me-2"),
                    dbc.Button(
                        [html.I(className="bi bi-trash me-1"), "Clear"],
                        id='clear-chat-btn',
                        color="danger",
                        size="sm",
                        outline=True,
                        n_clicks=0
                    )
                ], className="d-flex justify-content-between")
            ], style={"padding": "0.5rem"})
        ], className="mb-3", style={"height": "560px", "overflow": "hidden"})
    
    @staticmethod
    def render_messages(messages: List[Dict]) -> List[html.Div]:
        """
        Render list of messages to Dash components.
        
        Args:
            messages: List of message dicts with keys:
                - type: 'user', 'assistant', 'alert'
                - content: Message text
                - timestamp: ISO timestamp string
                - metadata: Optional dict with confidence, agents_used, etc.
                - priority: For alerts, 1-5 urgency level
                
        Returns:
            List of rendered message components (newest first)
        """
        if not messages:
            return [
                html.Div([
                    html.P([
                        html.I(className="bi bi-info-circle me-2"),
                        "AI will send proactive alerts during the race. ",
                        "You can also ask questions anytime."
                    ], className="text-muted small text-center mb-0")
                ], style={"padding": "20px"})
            ]
        
        rendered = []
        # Reverse order: newest messages first (at top)
        for msg in reversed(messages):
            msg_type = msg.get('type', 'assistant')
            content = msg.get('content', '')
            timestamp = msg.get('timestamp', '')
            metadata = msg.get('metadata', {})
            priority = msg.get('priority', 0)
            
            if msg_type == 'user':
                rendered.append(
                    AIAssistantDashboard.create_user_message(content, timestamp)
                )
            elif msg_type == 'alert':
                rendered.append(
                    AIAssistantDashboard.create_alert_message(
                        content, timestamp, priority
                    )
                )
            else:
                rendered.append(
                    AIAssistantDashboard.create_assistant_message(
                        content, timestamp, metadata
                    )
                )
        
        return rendered
    
    @staticmethod
    def create_user_message(
        content: str,
        timestamp: str = ""
    ) -> html.Div:
        """Create a user message bubble (blue, right-aligned)."""
        time_str = timestamp[-8:-3] if len(timestamp) > 8 else datetime.now().strftime("%H:%M")
        
        return html.Div([
            html.Div([
                html.Div(
                    content,
                    style={
                        'background': 'linear-gradient(135deg, #0d6efd, #0a58ca)',
                        'color': 'white',
                        'padding': '8px 12px',
                        'borderRadius': '12px 12px 0 12px',
                        'maxWidth': '85%',
                        'marginLeft': 'auto',
                        'fontSize': '0.85rem'
                    }
                ),
                html.Small(
                    time_str,
                    className="text-muted",
                    style={'float': 'right', 'marginTop': '2px'}
                )
            ])
        ], className="mb-2", style={'clear': 'both'})
    
    @staticmethod
    def create_assistant_message(
        content: str,
        timestamp: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> html.Div:
        """Create an assistant message bubble (gray, left-aligned)."""
        time_str = timestamp[-8:-3] if len(timestamp) > 8 else datetime.now().strftime("%H:%M")
        
        # Build metadata footer
        footer_items = []
        if metadata:
            if 'confidence' in metadata:
                conf = metadata['confidence']
                footer_items.append(
                    html.Span(f"📊 {conf:.0%}", className="me-2")
                )
            if 'agents_used' in metadata and metadata['agents_used']:
                agents = ", ".join(metadata['agents_used'][:2])
                footer_items.append(
                    html.Span(f"🤖 {agents}", className="me-2")
                )
        
        return html.Div([
            html.Div([
                html.Div(
                    content,
                    style={
                        'background': '#2d2d2d',
                        'color': '#e0e0e0',
                        'padding': '8px 12px',
                        'borderRadius': '12px 12px 12px 0',
                        'maxWidth': '85%',
                        'fontSize': '0.85rem'
                    }
                ),
                html.Div([
                    html.Small(time_str, className="text-muted me-2"),
                    html.Small(footer_items, className="text-muted")
                ], style={'marginTop': '2px'})
            ])
        ], className="mb-2", style={'clear': 'both'})
    
    @staticmethod
    def create_alert_message(
        content: str,
        timestamp: str = "",
        priority: int = 3
    ) -> html.Div:
        """
        Create a proactive alert message bubble (amber/orange).
        
        Priority colors:
        - 5 (highest): red background
        - 4: orange background  
        - 3: amber/yellow background
        - 1-2: muted background
        """
        time_str = timestamp[-8:-3] if len(timestamp) > 8 else datetime.now().strftime("%H:%M")
        
        # Color based on priority
        if priority >= 5:
            bg_color = 'linear-gradient(135deg, #dc3545, #b02a37)'
            text_color = 'white'
            border = 'none'
        elif priority >= 4:
            bg_color = 'linear-gradient(135deg, #fd7e14, #e66a00)'
            text_color = 'white'
            border = 'none'
        elif priority >= 3:
            bg_color = 'linear-gradient(135deg, #ffc107, #e0a800)'
            text_color = '#1a1a1a'
            border = 'none'
        else:
            bg_color = '#3d3d3d'
            text_color = '#e0e0e0'
            border = '1px solid #ffc107'
        
        return html.Div([
            html.Div([
                html.Div([
                    html.Span("⚡ ALERT", style={
                        'fontSize': '0.7rem',
                        'fontWeight': 'bold',
                        'opacity': '0.8',
                        'display': 'block',
                        'marginBottom': '4px'
                    }),
                    html.Span(content)
                ], style={
                    'background': bg_color,
                    'color': text_color,
                    'padding': '10px 14px',
                    'borderRadius': '8px',
                    'border': border,
                    'fontSize': '0.85rem',
                    'boxShadow': '0 2px 8px rgba(0,0,0,0.3)'
                }),
                html.Small(
                    f"🔔 {time_str}",
                    className="text-warning",
                    style={'marginTop': '2px', 'display': 'block'}
                )
            ])
        ], className="mb-2", style={'clear': 'both'})
    
    @staticmethod
    def create_thinking_indicator() -> html.Div:
        """Create a thinking/loading indicator."""
        return html.Div([
            html.Div([
                dbc.Spinner(
                    size="sm",
                    color="primary"
                ),
                html.Span(
                    " Analyzing...",
                    className="text-muted ms-2",
                    style={'fontSize': '0.85rem'}
                )
            ], style={
                'background': '#2d2d2d',
                'padding': '10px 14px',
                'borderRadius': '12px 12px 12px 0',
                'display': 'inline-block'
            })
        ], className="mb-2")
