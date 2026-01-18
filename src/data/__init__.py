"""
Módulo de gestión de datos para F1 Strategist AI.

Incluye:
- F1DataProvider: Proveedores de datos (FastF1, OpenF1)
- CacheManager: Sistema de caché híbrido (historical + live)
- LiveSessionMonitor: Monitor de sesiones en tiempo real
- Models: Dataclasses para datos de F1
- CacheConfig: Configuración del sistema de caché
"""

from .cache_config import (
    CacheConfig,
    CacheMode,
    DataType,
    RetentionPolicy,
    DEFAULT_CACHE_CONFIG,
)
from .cache_manager import CacheManager
from .cache_generation import CacheGenerationService, CacheArtifact
from .openf1_data_provider import OpenF1DataProvider
from .live_session_monitor import (
    LiveSessionMonitor,
    OpenF1Client,
    monitor_live_session,
)
from .models import (
    EventType,
    LapData,
    RaceEvent,
    RaceState,
    SessionMetadata,
    SessionType,
    StintData,
    TireCompound,
)

__all__ = [
    # Config
    "CacheConfig",
    "CacheMode",
    "DataType",
    "RetentionPolicy",
    "DEFAULT_CACHE_CONFIG",
    # Cache Manager
    "CacheManager",
    "CacheGenerationService",
    "CacheArtifact",
    # Data Provider
    "OpenF1DataProvider",
    # Live Session
    "LiveSessionMonitor",
    "OpenF1Client",
    "monitor_live_session",
    # Models
    "EventType",
    "LapData",
    "RaceEvent",
    "RaceState",
    "SessionMetadata",
    "SessionType",
    "StintData",
    "TireCompound",
]
