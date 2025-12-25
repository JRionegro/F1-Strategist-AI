"""
AI Assistant Dashboard - Dash Version.

Multi-agent conversational interface for F1 strategy queries.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any

from dash import html, dcc
import dash_bootstrap_components as dbc

logger = logging.getLogger(__name__)


class AIAssistantDashboard:
    """
    AI Assistant Dashboard with multi-agent chat interface.
    
    Provides conversational interface to 5 specialized agents:
    - Strategy Agent
    - Weather Agent
    - Performance Agent
    - Race Control Agent
    - Race Position Agent
    """

    @staticmethod
    def create_layout(focused_driver: Optional[str] = None):
        """
        Create the AI Assistant dashboard layout.
        
        Args:
            focused_driver: Currently focused driver code
            
        Returns:
            Dash component tree
        """
        return dbc.Card([
            dbc.CardHeader([
                html.H4([
                    html.I(className="bi bi-robot me-2"),
                    "💬 AI Assistant"
                ], className="mb-0", style={"fontSize": "0.9rem"})
            ]),
            dbc.CardBody([
                # Welcome message - ultra-compact version
                dbc.Alert([
                    html.P([
                        html.Strong("F1 Strategist AI"),
                        html.Small(" - Ask about strategy, weather, performance, or positions", className="text-muted")
                    ], className="mb-0", style={'fontSize': '0.85rem'})
                ], color="info", className="mb-1", style={'padding': '0.35rem 0.75rem'}),
                
                # Context info
                dbc.Row([
                    dbc.Col([
                        dbc.Badge([
                            html.I(className="bi bi-calendar me-1"),
                            "Abu Dhabi GP 2025"
                        ], color="primary", className="me-2")
                    ], width="auto"),
                    dbc.Col([
                        dbc.Badge([
                            html.I(className="bi bi-flag me-1"),
                            "Race"
                        ], color="success", className="me-2")
                    ], width="auto"),
                    dbc.Col([
                        dbc.Badge([
                            html.I(className="bi bi-person me-1"),
                            f"Focus: {focused_driver or 'None'}"
                        ], color="warning" if focused_driver else "secondary")
                    ], width="auto")
                ], className="mb-2"),
                
                # Chat container
                html.Div([
                    html.Div(
                        id='chat-messages-container',
                        children=[],
                        style={
                            'height': '200px',
                            'overflow-y': 'auto',
                            'padding': '6px',
                            'background-color': '#1a1a1a',
                            'border-radius': '5px',
                            'margin-bottom': '8px'
                        }
                    ),
                    
                    # Input area
                    dbc.InputGroup([
                        dbc.Textarea(
                            id='chat-input',
                            placeholder="Ask a strategy question...",
                            style={'resize': 'none', 'fontSize': '0.85rem'},
                            rows=2
                        ),
                        dbc.Button(
                            [html.I(className="bi bi-send")],
                            id='chat-send-btn',
                            color="primary",
                            n_clicks=0,
                            style={'padding': '0.25rem 0.5rem'}
                        )
                    ], className="mb-1", size="sm"),
                    
                    # Quick action buttons
                    html.Div([
                        dbc.ButtonGroup([
                            dbc.Button(
                                "Pit",
                                id='quick-pit-btn',
                                size="sm",
                                outline=True,
                                color="secondary"
                            ),
                            dbc.Button(
                                "Weather",
                                id='quick-weather-btn',
                                size="sm",
                                outline=True,
                                color="secondary"
                            ),
                            dbc.Button(
                                "Gaps",
                                id='quick-gap-btn',
                                size="sm",
                                outline=True,
                                color="secondary"
                            ),
                            dbc.Button(
                                [html.I(className="bi bi-trash me-1"), "Clear"],
                                id='clear-chat-btn',
                                color="danger",
                                size="sm",
                                n_clicks=0
                            )
                        ], size="sm")
                    ], className="d-flex justify-content-between", style={'fontSize': '0.8rem'})
                ])
            ])
        ], className="mb-3")
    
    @staticmethod
    def create_user_message(content: str) -> html.Div:
        """
        Create a user message bubble.
        
        Args:
            content: Message content
            
        Returns:
            Message component
        """
        return html.Div([
            dbc.Row([
                dbc.Col(width=2),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.P(content, className="mb-1"),
                            html.Small(
                                datetime.now().strftime("%H:%M"),
                                className="text-muted"
                            )
                        ])
                    ], color="primary", inverse=True)
                ], width=10)
            ], className="mb-2")
        ])
    
    @staticmethod
    def create_assistant_message(
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> html.Div:
        """
        Create an assistant message bubble with metadata.
        
        Args:
            content: Message content
            metadata: Optional metadata (confidence, processing_time, agents_used)
            
        Returns:
            Message component
        """
        message_body = [
            html.P(content, className="mb-2"),
            html.Small(
                datetime.now().strftime("%H:%M"),
                className="text-muted"
            )
        ]
        
        # Add metadata if available
        if metadata:
            details = []
            if 'confidence' in metadata:
                details.append(
                    html.Span([
                        html.I(className="bi bi-graph-up me-1"),
                        f"{metadata['confidence']:.0%}"
                    ], className="me-3")
                )
            if 'processing_time' in metadata:
                details.append(
                    html.Span([
                        html.I(className="bi bi-clock me-1"),
                        f"{metadata['processing_time']:.2f}s"
                    ], className="me-3")
                )
            if 'agents_used' in metadata:
                details.append(
                    html.Span([
                        html.I(className="bi bi-people me-1"),
                        ", ".join(metadata['agents_used'])
                    ])
                )
            
            if details:
                message_body.append(html.Hr(className="my-2"))
                message_body.append(
                    html.Small(details, className="text-muted")
                )
        
        return html.Div([
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody(message_body)
                    ], color="secondary")
                ], width=10),
                dbc.Col(width=2)
            ], className="mb-2")
        ])
    
    @staticmethod
    def create_thinking_indicator() -> html.Div:
        """
        Create a thinking/loading indicator.
        
        Returns:
            Loading component
        """
        return html.Div([
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            dbc.Spinner(
                                size="sm",
                                color="primary",
                                spinner_style={"margin-right": "10px"}
                            ),
                            html.Span("AI is thinking...", className="text-muted")
                        ], className="d-flex align-items-center")
                    ], color="dark")
                ], width=10),
                dbc.Col(width=2)
            ], className="mb-2")
        ])
