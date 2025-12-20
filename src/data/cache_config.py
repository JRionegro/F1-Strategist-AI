"""
Configuración del sistema de caché para F1 Strategist AI.

Define políticas de almacenamiento, estructura de directorios y
límites de retención para datos históricos y en tiempo real.
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, Literal


class CacheMode(Enum):
    """Modos de operación del caché."""

    HISTORICAL = "historical"
    LIVE = "live"


class DataType(Enum):
    """Tipos de datos almacenados en caché."""

    RACE_RESULTS = "race_results"
    QUALIFYING_RESULTS = "qualifying_results"
    PRACTICE_RESULTS = "practice_results"
    SPRINT_RESULTS = "sprint_results"
    WEATHER = "weather"
    LAP_TIMES = "lap_times"
    TELEMETRY = "telemetry"
    PIT_STOPS = "pit_stops"
    TIRE_STRATEGY = "tire_strategy"
    DRIVER_INFO = "driver_info"
    TRACK_STATUS = "track_status"
    RACE_CONTROL = "race_control"


class RetentionPolicy(Enum):
    """Políticas de retención de datos."""

    PERMANENT = "permanent"
    DAYS_7 = "7_days"
    DAYS_30 = "30_days"
    DAYS_90 = "90_days"


@dataclass
class CacheConfig:
    """Configuración global del sistema de caché."""

    # Directorios base
    base_dir: Path = Path("./data")
    cache_dir: Path = Path("./cache")

    # Directorios de datos
    races_dir: Path = Path("./data/races")
    telemetry_dir: Path = Path("./data/telemetry")
    live_dir: Path = Path("./data/live")
    processed_dir: Path = Path("./data/processed")

    # Políticas de retención por tipo de dato
    retention_policies: Optional[Dict[DataType, RetentionPolicy]] = None

    # Límites de almacenamiento
    max_telemetry_size_gb: float = 10.0
    max_live_session_size_gb: float = 1.0

    # Configuración de formato
    use_parquet: bool = True
    compression: Literal[
        "snappy", "gzip", "brotli", "lz4", "zstd"
    ] = "snappy"

    # Configuración de live session
    live_update_interval_seconds: int = 5
    live_lap_buffer_size: int = 100

    def __post_init__(self):
        """Inicializa políticas de retención por defecto."""
        if self.retention_policies is None:
            self.retention_policies = {
                # Datos permanentes (resultados oficiales)
                DataType.RACE_RESULTS: RetentionPolicy.PERMANENT,
                DataType.QUALIFYING_RESULTS: RetentionPolicy.PERMANENT,
                DataType.PRACTICE_RESULTS: RetentionPolicy.DAYS_30,
                DataType.SPRINT_RESULTS: RetentionPolicy.PERMANENT,
                DataType.WEATHER: RetentionPolicy.PERMANENT,
                DataType.DRIVER_INFO: RetentionPolicy.PERMANENT,
                # Datos con retención temporal (pesados)
                DataType.LAP_TIMES: RetentionPolicy.DAYS_30,
                DataType.TELEMETRY: RetentionPolicy.DAYS_7,
                DataType.PIT_STOPS: RetentionPolicy.DAYS_90,
                DataType.TIRE_STRATEGY: RetentionPolicy.DAYS_90,
                # Eventos de carrera
                DataType.TRACK_STATUS: RetentionPolicy.DAYS_30,
                DataType.RACE_CONTROL: RetentionPolicy.DAYS_90,
            }

    def get_retention_days(self, data_type: DataType) -> int | None:
        """
        Obtiene el número de días de retención para un tipo de dato.

        Args:
            data_type: Tipo de dato

        Returns:
            Número de días o None si es permanente
        """
        if self.retention_policies is None:
            return 30

        policy = self.retention_policies.get(
            data_type,
            RetentionPolicy.DAYS_30
        )

        if policy == RetentionPolicy.PERMANENT:
            return None
        elif policy == RetentionPolicy.DAYS_7:
            return 7
        elif policy == RetentionPolicy.DAYS_30:
            return 30
        elif policy == RetentionPolicy.DAYS_90:
            return 90

        return 30

    def get_race_path(
        self,
        year: int,
        race_name: str
    ) -> Path:
        """
        Genera ruta para datos de carrera.

        Args:
            year: Año de la temporada
            race_name: Nombre de la carrera

        Returns:
            Path al directorio de la carrera
        """
        return (
            self.races_dir
            / str(year)
            / race_name.lower().replace(" ", "_")
        )

    def get_telemetry_path(
        self,
        year: int,
        race_name: str,
        driver: str
    ) -> Path:
        """
        Genera ruta para telemetría de piloto.

        Args:
            year: Año de la temporada
            race_name: Nombre de la carrera
            driver: Abreviatura del piloto (VER, HAM, etc)

        Returns:
            Path al directorio del piloto
        """
        return (
            self.telemetry_dir
            / str(year)
            / race_name.lower().replace(" ", "_")
            / driver.upper()
        )

    def get_live_session_path(self) -> Path:
        """
        Genera ruta para sesión en tiempo real.

        Returns:
            Path al directorio de sesión activa
        """
        return self.live_dir / "current_session"

    def get_live_driver_path(self, driver: str) -> Path:
        """
        Genera ruta para datos de piloto en sesión live.

        Args:
            driver: Abreviatura del piloto

        Returns:
            Path al directorio del piloto
        """
        return self.get_live_session_path() / "drivers" / driver.upper()

    def get_file_extension(self) -> str:
        """
        Obtiene extensión de archivo según configuración.

        Returns:
            Extensión (.parquet o .csv)
        """
        return ".parquet" if self.use_parquet else ".csv"


# Instancia global de configuración
DEFAULT_CACHE_CONFIG = CacheConfig()
