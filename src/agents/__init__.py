"""
F1 Strategist AI - Agents Module

This module contains the multi-agent system for F1 race strategy analysis.

Agents:
- BaseAgent: Abstract base class for all agents
- StrategyAgent: Race and qualifying strategy optimization
- WeatherAgent: Weather impact and timing analysis
- PerformanceAgent: Lap time and telemetry analysis
- RaceControlAgent: Flags, penalties, and incidents
- RacePositionAgent: Position tracking and overtake analysis
- Orchestrator: Multi-agent coordination and query routing
"""

from src.agents.base_agent import BaseAgent

__all__ = ["BaseAgent"]
