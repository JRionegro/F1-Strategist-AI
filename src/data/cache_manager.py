"""
Sistema de gestión de caché para F1 Strategist AI.

Proporciona almacenamiento y recuperación eficiente de datos históricos
y en tiempo real con soporte para múltiples formatos y políticas de
retención.
"""

import json
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import pandas as pd

from .cache_config import (
    CacheConfig,
    CacheMode,
    DataType,
    DEFAULT_CACHE_CONFIG,
)
from .models import (
    LapData,
    RaceEvent,
    RaceState,
    SessionMetadata,
    StintData,
)

logger = logging.getLogger(__name__)


class CacheManager:
    """Gestor de caché híbrido para datos históricos y en tiempo real."""

    def __init__(
        self,
        mode: CacheMode = CacheMode.HISTORICAL,
        config: Optional[CacheConfig] = None,
    ):
        """
        Inicializa el gestor de caché.

        Args:
            mode: Modo de operación (historical o live)
            config: Configuración personalizada (usa default si None)
        """
        self.mode = mode
        self.config = config or DEFAULT_CACHE_CONFIG
        self.logger = logging.getLogger(__name__)

        # Estado de sesión live
        self.live_session: Optional[SessionMetadata] = None
        self.live_stints: Dict[str, List[StintData]] = {}
        self.live_events: List[RaceEvent] = []
        self.race_state: Optional[RaceState] = None

        # Inicializar directorios
        self._init_directories()

    def _init_directories(self) -> None:
        """Crea estructura de directorios si no existe."""
        dirs = [
            self.config.base_dir,
            self.config.races_dir,
            self.config.telemetry_dir,
            self.config.processed_dir,
        ]

        if self.mode == CacheMode.LIVE:
            dirs.append(self.config.live_dir)

        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)

        self.logger.info(
            f"CacheManager initialized in {self.mode.value} mode"
        )

    # ==================== MODO HISTORICAL ====================

    def get_cached_race_data(
        self,
        year: int,
        race_name: str,
        data_type: DataType,
    ) -> Optional[pd.DataFrame]:
        """
        Recupera datos de carrera desde caché.

        Args:
            year: Año de la temporada
            race_name: Nombre de la carrera
            data_type: Tipo de datos a recuperar

        Returns:
            DataFrame con datos o None si no existe
        """
        file_path = self._get_cache_file_path(year, race_name, data_type)

        if not file_path.exists():
            self.logger.debug(f"Cache miss: {file_path}")
            return None

        try:
            if self.config.use_parquet:
                df = pd.read_parquet(file_path)
            else:
                df = pd.read_csv(file_path)

            self.logger.info(f"Cache hit: {file_path} ({len(df)} rows)")
            return df

        except Exception as e:
            self.logger.error(f"Error reading cache {file_path}: {e}")
            return None

    def save_race_data(
        self,
        year: int,
        race_name: str,
        data_type: DataType,
        data: pd.DataFrame,
    ) -> bool:
        """
        Guarda datos de carrera en caché.

        Args:
            year: Año de la temporada
            race_name: Nombre de la carrera
            data_type: Tipo de datos
            data: DataFrame con datos

        Returns:
            True si se guardó correctamente
        """
        file_path = self._get_cache_file_path(year, race_name, data_type)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            if self.config.use_parquet:
                data.to_parquet(
                    file_path,
                    compression=self.config.compression,
                    index=False,
                )
            else:
                data.to_csv(file_path, index=False)

            self.logger.info(
                f"Saved to cache: {file_path} ({len(data)} rows)"
            )
            return True

        except Exception as e:
            self.logger.error(f"Error saving cache {file_path}: {e}")
            return False

    def get_cached_telemetry(
        self,
        year: int,
        race_name: str,
        driver: str,
        lap_number: Optional[int] = None,
    ) -> Optional[pd.DataFrame]:
        """
        Recupera telemetría de piloto desde caché.

        Args:
            year: Año de la temporada
            race_name: Nombre de la carrera
            driver: Abreviatura del piloto
            lap_number: Vuelta específica (None para todas)

        Returns:
            DataFrame con telemetría o None
        """
        driver_path = self.config.get_telemetry_path(
            year, race_name, driver
        )

        if not driver_path.exists():
            return None

        try:
            if lap_number is not None:
                # Telemetría de vuelta específica
                file_path = (
                    driver_path
                    / f"lap_{lap_number}{self.config.get_file_extension()}"
                )
                if file_path.exists():
                    return (
                        pd.read_parquet(file_path)
                        if self.config.use_parquet
                        else pd.read_csv(file_path)
                    )
            else:
                # Todas las vueltas (consolidado)
                file_path = (
                    driver_path
                    / f"all_laps{self.config.get_file_extension()}"
                )
                if file_path.exists():
                    return (
                        pd.read_parquet(file_path)
                        if self.config.use_parquet
                        else pd.read_csv(file_path)
                    )

            return None

        except Exception as e:
            self.logger.error(f"Error reading telemetry: {e}")
            return None

    def save_telemetry(
        self,
        year: int,
        race_name: str,
        driver: str,
        lap_number: int,
        data: pd.DataFrame,
    ) -> bool:
        """
        Guarda telemetría de una vuelta específica.

        Args:
            year: Año de la temporada
            race_name: Nombre de la carrera
            driver: Abreviatura del piloto
            lap_number: Número de vuelta
            data: DataFrame con telemetría

        Returns:
            True si se guardó correctamente
        """
        driver_path = self.config.get_telemetry_path(
            year, race_name, driver
        )
        driver_path.mkdir(parents=True, exist_ok=True)

        file_path = (
            driver_path
            / f"lap_{lap_number}{self.config.get_file_extension()}"
        )

        try:
            if self.config.use_parquet:
                data.to_parquet(
                    file_path,
                    compression=self.config.compression,  # type: ignore
                    index=False,
                )
            else:
                data.to_csv(file_path, index=False)

            self.logger.debug(f"Saved telemetry: {file_path}")
            return True

        except Exception as e:
            self.logger.error(f"Error saving telemetry: {e}")
            return False

    # ==================== MODO LIVE ====================

    def start_live_session(self, session_info: SessionMetadata) -> bool:
        """
        Inicia una nueva sesión en tiempo real.

        Args:
            session_info: Metadatos de la sesión

        Returns:
            True si se inició correctamente
        """
        if self.mode != CacheMode.LIVE:
            self.logger.error("Cannot start live session in historical mode")
            return False

        # Limpiar sesión anterior si existe
        session_path = self.config.get_live_session_path()
        if session_path.exists():
            self.logger.warning("Removing previous live session")
            shutil.rmtree(session_path)

        # Crear estructura de directorios
        session_path.mkdir(parents=True, exist_ok=True)
        (session_path / "drivers").mkdir(exist_ok=True)
        (session_path / "events").mkdir(exist_ok=True)

        # Guardar metadatos
        session_info.is_live = True
        metadata_path = session_path / "session_metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(session_info.to_dict(), f, indent=2)

        # Inicializar estado
        self.live_session = session_info
        self.live_stints = {}
        self.live_events = []
        self.race_state = RaceState(
            current_lap=0, total_laps=session_info.year
        )

        self.logger.info(
            f"Live session started: {session_info.race_name} "
            f"{session_info.session_type.value}"
        )
        return True

    def update_driver_lap(
        self,
        driver: str,
        lap_data: LapData,
        telemetry: Optional[pd.DataFrame] = None,
    ) -> bool:
        """
        Actualiza datos de vuelta de un piloto en sesión live.

        Args:
            driver: Abreviatura del piloto
            lap_data: Datos de la vuelta
            telemetry: Telemetría opcional de la vuelta

        Returns:
            True si se actualizó correctamente
        """
        if self.mode != CacheMode.LIVE or not self.live_session:
            return False

        driver_path = self.config.get_live_driver_path(driver)
        driver_path.mkdir(parents=True, exist_ok=True)

        # Guardar datos de vuelta
        laps_file = driver_path / "lap_times.json"
        laps_data = []

        if laps_file.exists():
            with open(laps_file, "r", encoding="utf-8") as f:
                laps_data = json.load(f)

        laps_data.append(lap_data.to_dict())

        with open(laps_file, "w", encoding="utf-8") as f:
            json.dump(laps_data, f, indent=2)

        # Guardar telemetría si existe
        if telemetry is not None and not telemetry.empty:
            telemetry_file = (
                driver_path
                / f"lap_{lap_data.lap_number}"
                f"{self.config.get_file_extension()}"
            )
            if self.config.use_parquet:
                telemetry.to_parquet(telemetry_file, index=False)
            else:
                telemetry.to_csv(telemetry_file, index=False)

        # Actualizar stint actual
        self._update_current_stint(driver, lap_data)

        self.logger.debug(
            f"Updated lap {lap_data.lap_number} for {driver}"
        )
        return True

    def complete_stint(
        self,
        driver: str,
        stint_data: StintData,
    ) -> bool:
        """
        Marca un stint como completado.

        Args:
            driver: Abreviatura del piloto
            stint_data: Datos del stint completado

        Returns:
            True si se guardó correctamente
        """
        if self.mode != CacheMode.LIVE or not self.live_session:
            return False

        driver_path = self.config.get_live_driver_path(driver)
        driver_path.mkdir(parents=True, exist_ok=True)

        # Cargar stints completados
        completed_file = driver_path / "completed_stints.json"
        completed_stints = []

        if completed_file.exists():
            with open(completed_file, "r", encoding="utf-8") as f:
                completed_stints = json.load(f)

        completed_stints.append(stint_data.to_dict())

        with open(completed_file, "w", encoding="utf-8") as f:
            json.dump(completed_stints, f, indent=2)

        self.logger.info(
            f"Completed stint {stint_data.stint_number} for {driver}"
        )
        return True

    def get_current_stint(self, driver: str) -> Optional[StintData]:
        """
        Obtiene el stint actual de un piloto en sesión live.

        Args:
            driver: Abreviatura del piloto

        Returns:
            Stint actual o None
        """
        if self.mode != CacheMode.LIVE or not self.live_session:
            return None

        driver_path = self.config.get_live_driver_path(driver)
        current_file = driver_path / "current_stint.json"

        if not current_file.exists():
            return None

        try:
            with open(current_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return StintData.from_dict(data)
        except Exception as e:
            self.logger.error(f"Error reading current stint: {e}")
            return None

    def add_race_event(self, event: RaceEvent) -> bool:
        """
        Añade un evento a la sesión live.

        Args:
            event: Evento de carrera

        Returns:
            True si se guardó correctamente
        """
        if self.mode != CacheMode.LIVE or not self.live_session:
            return False

        session_path = self.config.get_live_session_path()
        events_file = session_path / "events" / "race_events.json"

        events_data = []
        if events_file.exists():
            with open(events_file, "r", encoding="utf-8") as f:
                events_data = json.load(f)

        events_data.append(event.to_dict())

        with open(events_file, "w", encoding="utf-8") as f:
            json.dump(events_data, f, indent=2)

        self.live_events.append(event)
        self.logger.debug(f"Added event: {event.event_type.value}")
        return True

    def update_race_state(self, race_state: RaceState) -> bool:
        """
        Actualiza el estado de la carrera.

        Args:
            race_state: Estado actual de la carrera

        Returns:
            True si se guardó correctamente
        """
        if self.mode != CacheMode.LIVE or not self.live_session:
            return False

        session_path = self.config.get_live_session_path()
        state_file = session_path / "race_state.json"

        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(race_state.to_dict(), f, indent=2)

        self.race_state = race_state
        return True

    def finalize_session(self) -> bool:
        """
        Finaliza sesión live y mueve datos a almacenamiento histórico.

        Returns:
            True si se finalizó correctamente
        """
        if self.mode != CacheMode.LIVE or not self.live_session:
            return False

        session_path = self.config.get_live_session_path()
        if not session_path.exists():
            return False

        try:
            # Actualizar metadatos
            self.live_session.end_time = datetime.now()
            self.live_session.is_live = False

            # Destino en histórico
            dest_path = self.config.get_race_path(
                self.live_session.year,
                self.live_session.race_name,
            )
            dest_path.mkdir(parents=True, exist_ok=True)

            # Mover datos
            shutil.copytree(
                session_path,
                dest_path / "live_data",
                dirs_exist_ok=True,
            )

            # Limpiar sesión live
            shutil.rmtree(session_path)

            self.logger.info(
                f"Finalized session: {self.live_session.race_name}"
            )
            self.live_session = None
            return True

        except Exception as e:
            self.logger.error(f"Error finalizing session: {e}")
            return False

    # ==================== UTILIDADES ====================

    def _get_cache_file_path(
        self,
        year: int,
        race_name: str,
        data_type: DataType,
    ) -> Path:
        """Genera ruta completa de archivo de caché."""
        race_path = self.config.get_race_path(year, race_name)
        filename = f"{data_type.value}{self.config.get_file_extension()}"
        return race_path / filename

    def _update_current_stint(
        self,
        driver: str,
        lap_data: LapData,
    ) -> None:
        """Actualiza el stint actual con datos de vuelta."""
        current_stint = self.get_current_stint(driver)

        if current_stint is None:
            # Crear nuevo stint
            current_stint = StintData(
                stint_number=1,
                driver=driver,
                start_lap=lap_data.lap_number,
                compound=lap_data.compound,
                tire_age_start=lap_data.tire_age or 0,
            )

        if lap_data.lap_time:
            current_stint.add_lap(
                lap_data.lap_number,
                lap_data.lap_time
            )

        # Guardar stint actualizado
        driver_path = self.config.get_live_driver_path(driver)
        current_file = driver_path / "current_stint.json"

        with open(current_file, "w", encoding="utf-8") as f:
            json.dump(current_stint.to_dict(), f, indent=2)

    def clean_old_data(self, data_type: DataType) -> int:
        """
        Limpia datos antiguos según política de retención.

        Args:
            data_type: Tipo de datos a limpiar

        Returns:
            Número de archivos eliminados
        """
        retention_days = self.config.get_retention_days(data_type)
        if retention_days is None:
            return 0

        cutoff_date = datetime.now() - timedelta(days=retention_days)
        deleted = 0

        # Buscar archivos antiguos
        search_dirs = [self.config.races_dir, self.config.telemetry_dir]

        for search_dir in search_dirs:
            if not search_dir.exists():
                continue

            for file_path in search_dir.rglob(
                f"*{data_type.value}*{self.config.get_file_extension()}"
            ):
                if file_path.stat().st_mtime < cutoff_date.timestamp():
                    try:
                        file_path.unlink()
                        deleted += 1
                        self.logger.debug(f"Deleted old file: {file_path}")
                    except Exception as e:
                        self.logger.error(
                            f"Error deleting {file_path}: {e}"
                        )

        self.logger.info(
            f"Cleaned {deleted} files of type {data_type.value}"
        )
        return deleted

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de uso de caché.

        Returns:
            Diccionario con estadísticas
        """
        stats = {
            "mode": self.mode.value,
            "total_size_mb": 0.0,
            "races_count": 0,
            "telemetry_drivers": 0,
            "live_session_active": self.live_session is not None,
        }

        # Calcular tamaño total
        for dir_path in [
            self.config.races_dir,
            self.config.telemetry_dir,
            self.config.live_dir,
        ]:
            if dir_path.exists():
                size = sum(
                    f.stat().st_size
                    for f in dir_path.rglob("*")
                    if f.is_file()
                )
                stats["total_size_mb"] += size / (1024 * 1024)

        # Contar carreras
        if self.config.races_dir.exists():
            stats["races_count"] = sum(
                1
                for _ in self.config.races_dir.rglob("*/")
                if _.is_dir()
            )

        return stats
