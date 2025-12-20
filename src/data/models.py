"""
Modelos de datos para el sistema de caché F1 Strategist AI.

Define dataclasses para representar sesiones, stints, vueltas y
eventos de carreras de Fórmula 1.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any


class SessionType(Enum):
    """Tipos de sesión de F1."""

    PRACTICE_1 = "FP1"
    PRACTICE_2 = "FP2"
    PRACTICE_3 = "FP3"
    QUALIFYING = "Q"
    SPRINT_QUALIFYING = "SQ"
    SPRINT = "S"
    RACE = "R"


class TireCompound(Enum):
    """Compuestos de neumáticos."""

    SOFT = "SOFT"
    MEDIUM = "MEDIUM"
    HARD = "HARD"
    INTERMEDIATE = "INTERMEDIATE"
    WET = "WET"
    UNKNOWN = "UNKNOWN"


class EventType(Enum):
    """Tipos de eventos durante una sesión."""

    PIT_ENTRY = "pit_entry"
    PIT_EXIT = "pit_exit"
    LAP_COMPLETED = "lap_completed"
    RACE_CONTROL = "race_control"
    FLAG_YELLOW = "flag_yellow"
    FLAG_RED = "flag_red"
    SAFETY_CAR = "safety_car"
    VSC = "virtual_safety_car"
    DRS_ENABLED = "drs_enabled"
    DRS_DISABLED = "drs_disabled"


@dataclass
class SessionMetadata:
    """Metadatos de una sesión de F1."""

    year: int
    race_name: str
    session_type: SessionType
    circuit_name: str
    country: str
    start_time: datetime
    end_time: Optional[datetime] = None
    is_live: bool = False
    weather_conditions: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para serialización JSON."""
        return {
            "year": self.year,
            "race_name": self.race_name,
            "session_type": self.session_type.value,
            "circuit_name": self.circuit_name,
            "country": self.country,
            "start_time": self.start_time.isoformat(),
            "end_time": (
                self.end_time.isoformat() if self.end_time else None
            ),
            "is_live": self.is_live,
            "weather_conditions": self.weather_conditions,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionMetadata":
        """Crea instancia desde diccionario."""
        return cls(
            year=data["year"],
            race_name=data["race_name"],
            session_type=SessionType(data["session_type"]),
            circuit_name=data["circuit_name"],
            country=data["country"],
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=(
                datetime.fromisoformat(data["end_time"])
                if data.get("end_time")
                else None
            ),
            is_live=data.get("is_live", False),
            weather_conditions=data.get("weather_conditions"),
        )


@dataclass
class LapData:
    """Datos de una vuelta individual."""

    lap_number: int
    driver: str
    lap_time: Optional[float] = None
    sector_1: Optional[float] = None
    sector_2: Optional[float] = None
    sector_3: Optional[float] = None
    compound: Optional[TireCompound] = None
    tire_age: Optional[int] = None
    is_personal_best: bool = False
    position: Optional[int] = None
    timestamp: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para serialización."""
        return {
            "lap_number": self.lap_number,
            "driver": self.driver,
            "lap_time": self.lap_time,
            "sector_1": self.sector_1,
            "sector_2": self.sector_2,
            "sector_3": self.sector_3,
            "compound": (
                self.compound.value if self.compound else None
            ),
            "tire_age": self.tire_age,
            "is_personal_best": self.is_personal_best,
            "position": self.position,
            "timestamp": (
                self.timestamp.isoformat() if self.timestamp else None
            ),
        }


@dataclass
class StintData:
    """Datos de un stint (periodo entre pit stops)."""

    stint_number: int
    driver: str
    start_lap: int
    end_lap: Optional[int] = None
    compound: Optional[TireCompound] = None
    tire_age_start: int = 0
    laps_completed: List[int] = field(default_factory=list)
    lap_times: List[float] = field(default_factory=list)
    avg_lap_time: Optional[float] = None
    degradation_rate: Optional[float] = None
    pit_loss_time: Optional[float] = None
    reason_ended: Optional[str] = None
    is_active: bool = True

    def add_lap(self, lap_number: int, lap_time: float) -> None:
        """
        Añade una vuelta al stint.

        Args:
            lap_number: Número de vuelta
            lap_time: Tiempo de vuelta en segundos
        """
        self.laps_completed.append(lap_number)
        self.lap_times.append(lap_time)
        self._update_statistics()

    def complete_stint(
        self,
        end_lap: int,
        reason: str = "pit_stop",
        pit_loss: Optional[float] = None
    ) -> None:
        """
        Marca el stint como completado.

        Args:
            end_lap: Vuelta final del stint
            reason: Razón de finalización
            pit_loss: Tiempo perdido en boxes (opcional)
        """
        self.end_lap = end_lap
        self.reason_ended = reason
        self.pit_loss_time = pit_loss
        self.is_active = False

    def _update_statistics(self) -> None:
        """Actualiza estadísticas del stint."""
        if len(self.lap_times) > 0:
            self.avg_lap_time = sum(self.lap_times) / len(self.lap_times)

            # Calcular degradación simple (pendiente de tiempos)
            if len(self.lap_times) >= 3:
                first_three = sum(self.lap_times[:3]) / 3
                last_three = sum(self.lap_times[-3:]) / 3
                self.degradation_rate = (
                    (last_three - first_three) / len(self.lap_times)
                )

    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para serialización."""
        return {
            "stint_number": self.stint_number,
            "driver": self.driver,
            "start_lap": self.start_lap,
            "end_lap": self.end_lap,
            "compound": (
                self.compound.value if self.compound else None
            ),
            "tire_age_start": self.tire_age_start,
            "laps_completed": self.laps_completed,
            "lap_times": self.lap_times,
            "avg_lap_time": self.avg_lap_time,
            "degradation_rate": self.degradation_rate,
            "pit_loss_time": self.pit_loss_time,
            "reason_ended": self.reason_ended,
            "is_active": self.is_active,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StintData":
        """Crea instancia desde diccionario."""
        return cls(
            stint_number=data["stint_number"],
            driver=data["driver"],
            start_lap=data["start_lap"],
            end_lap=data.get("end_lap"),
            compound=(
                TireCompound(data["compound"])
                if data.get("compound")
                else None
            ),
            tire_age_start=data.get("tire_age_start", 0),
            laps_completed=data.get("laps_completed", []),
            lap_times=data.get("lap_times", []),
            avg_lap_time=data.get("avg_lap_time"),
            degradation_rate=data.get("degradation_rate"),
            pit_loss_time=data.get("pit_loss_time"),
            reason_ended=data.get("reason_ended"),
            is_active=data.get("is_active", True),
        )


@dataclass
class RaceEvent:
    """Evento durante una sesión (pit stops, flags, etc)."""

    event_type: EventType
    timestamp: datetime
    driver: Optional[str] = None
    lap_number: Optional[int] = None
    message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para serialización."""
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "driver": self.driver,
            "lap_number": self.lap_number,
            "message": self.message,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RaceEvent":
        """Crea instancia desde diccionario."""
        return cls(
            event_type=EventType(data["event_type"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            driver=data.get("driver"),
            lap_number=data.get("lap_number"),
            message=data.get("message"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class RaceState:
    """Estado actual de una carrera en tiempo real."""

    current_lap: int
    total_laps: int
    leader: Optional[str] = None
    safety_car_active: bool = False
    vsc_active: bool = False
    red_flag: bool = False
    drs_enabled: bool = False
    positions: Dict[int, str] = field(default_factory=dict)
    last_update: Optional[datetime] = None

    def update_positions(self, positions: Dict[int, str]) -> None:
        """
        Actualiza posiciones actuales.

        Args:
            positions: Diccionario {posición: driver}
        """
        self.positions = positions
        if 1 in positions:
            self.leader = positions[1]
        self.last_update = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para serialización."""
        return {
            "current_lap": self.current_lap,
            "total_laps": self.total_laps,
            "leader": self.leader,
            "safety_car_active": self.safety_car_active,
            "vsc_active": self.vsc_active,
            "red_flag": self.red_flag,
            "drs_enabled": self.drs_enabled,
            "positions": self.positions,
            "last_update": (
                self.last_update.isoformat()
                if self.last_update
                else None
            ),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RaceState":
        """Crea instancia desde diccionario."""
        return cls(
            current_lap=data["current_lap"],
            total_laps=data["total_laps"],
            leader=data.get("leader"),
            safety_car_active=data.get("safety_car_active", False),
            vsc_active=data.get("vsc_active", False),
            red_flag=data.get("red_flag", False),
            drs_enabled=data.get("drs_enabled", False),
            positions=data.get("positions", {}),
            last_update=(
                datetime.fromisoformat(data["last_update"])
                if data.get("last_update")
                else None
            ),
        )
