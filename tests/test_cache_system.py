"""
Tests para el sistema de caché híbrido.

Valida funcionalidad de CacheManager en modos historical y live.
"""

import json
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from src.data.cache_manager import CacheManager
from src.data.cache_config import CacheConfig, CacheMode, DataType
from src.data.models import (
    EventType,
    LapData,
    RaceEvent,
    RaceState,
    SessionMetadata,
    SessionType,
    StintData,
    TireCompound,
)


@pytest.fixture
def temp_cache_dir():
    """Crea directorio temporal para tests."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def cache_config(temp_cache_dir):
    """Configuración de caché para tests."""
    config = CacheConfig(
        base_dir=temp_cache_dir / "data",
        cache_dir=temp_cache_dir / "cache",
        races_dir=temp_cache_dir / "data" / "races",
        telemetry_dir=temp_cache_dir / "data" / "telemetry",
        live_dir=temp_cache_dir / "data" / "live",
        processed_dir=temp_cache_dir / "data" / "processed",
    )
    return config


@pytest.fixture
def historical_cache(cache_config):
    """CacheManager en modo historical."""
    return CacheManager(mode=CacheMode.HISTORICAL, config=cache_config)


@pytest.fixture
def live_cache(cache_config):
    """CacheManager en modo live."""
    return CacheManager(mode=CacheMode.LIVE, config=cache_config)


@pytest.fixture
def sample_race_data():
    """Datos de ejemplo de carrera."""
    return pd.DataFrame({
        "Driver": ["VER", "HAM", "LEC"],
        "Position": [1, 2, 3],
        "Points": [25, 18, 15],
        "TeamName": ["Red Bull", "Mercedes", "Ferrari"],
    })


@pytest.fixture
def sample_telemetry():
    """Telemetría de ejemplo."""
    return pd.DataFrame({
        "Time": [0.0, 0.1, 0.2],
        "Speed": [320, 315, 310],
        "RPM": [12000, 11800, 11600],
        "Throttle": [100, 98, 95],
    })


# ==================== TESTS MODO HISTORICAL ====================


def test_cache_manager_initialization(historical_cache):
    """Test inicialización de CacheManager."""
    assert historical_cache.mode == CacheMode.HISTORICAL
    assert historical_cache.config.races_dir.exists()
    assert historical_cache.config.telemetry_dir.exists()


def test_save_and_get_race_data(historical_cache, sample_race_data):
    """Test guardar y recuperar datos de carrera."""
    year = 2024
    race_name = "bahrain"

    # Guardar
    success = historical_cache.save_race_data(
        year, race_name, DataType.RACE_RESULTS, sample_race_data
    )
    assert success

    # Recuperar
    cached = historical_cache.get_cached_race_data(
        year, race_name, DataType.RACE_RESULTS
    )
    assert cached is not None
    assert len(cached) == len(sample_race_data)
    assert list(cached.columns) == list(sample_race_data.columns)


def test_cache_miss(historical_cache):
    """Test cuando no existe dato en caché."""
    cached = historical_cache.get_cached_race_data(
        2099, "nonexistent", DataType.RACE_RESULTS
    )
    assert cached is None


def test_save_and_get_telemetry(
    historical_cache,
    sample_telemetry
):
    """Test guardar y recuperar telemetría."""
    year = 2024
    race_name = "bahrain"
    driver = "VER"
    lap_number = 15

    # Guardar
    success = historical_cache.save_telemetry(
        year, race_name, driver, lap_number, sample_telemetry
    )
    assert success

    # Recuperar
    cached = historical_cache.get_cached_telemetry(
        year, race_name, driver, lap_number
    )
    assert cached is not None
    assert len(cached) == len(sample_telemetry)


def test_cache_stats(historical_cache, sample_race_data):
    """Test estadísticas de caché."""
    # Guardar algunos datos
    historical_cache.save_race_data(
        2024, "bahrain", DataType.RACE_RESULTS, sample_race_data
    )

    stats = historical_cache.get_cache_stats()
    assert "mode" in stats
    assert stats["mode"] == "historical"
    assert "total_size_mb" in stats


# ==================== TESTS MODO LIVE ====================


def test_start_live_session(live_cache):
    """Test iniciar sesión live."""
    session_info = SessionMetadata(
        year=2024,
        race_name="Bahrain Grand Prix",
        session_type=SessionType.RACE,
        circuit_name="Bahrain International Circuit",
        country="Bahrain",
        start_time=datetime.now(),
    )

    success = live_cache.start_live_session(session_info)
    assert success
    assert live_cache.live_session is not None
    assert live_cache.live_session.race_name == "Bahrain Grand Prix"

    # Verificar estructura de directorios
    session_path = live_cache.config.get_live_session_path()
    assert session_path.exists()
    assert (session_path / "drivers").exists()
    assert (session_path / "events").exists()


def test_update_driver_lap(live_cache):
    """Test actualizar vuelta de piloto."""
    # Iniciar sesión
    session_info = SessionMetadata(
        year=2024,
        race_name="Bahrain",
        session_type=SessionType.RACE,
        circuit_name="Bahrain",
        country="Bahrain",
        start_time=datetime.now(),
    )
    live_cache.start_live_session(session_info)

    # Actualizar vuelta
    lap_data = LapData(
        lap_number=1,
        driver="VER",
        lap_time=92.456,
        compound=TireCompound.SOFT,
        tire_age=1,
        position=1,
    )

    success = live_cache.update_driver_lap("VER", lap_data)
    assert success

    # Verificar archivo
    driver_path = live_cache.config.get_live_driver_path("VER")
    laps_file = driver_path / "lap_times.json"
    assert laps_file.exists()


def test_complete_stint(live_cache):
    """Test completar stint."""
    # Iniciar sesión
    session_info = SessionMetadata(
        year=2024,
        race_name="Bahrain",
        session_type=SessionType.RACE,
        circuit_name="Bahrain",
        country="Bahrain",
        start_time=datetime.now(),
    )
    live_cache.start_live_session(session_info)

    # Crear y completar stint
    stint = StintData(
        stint_number=1,
        driver="VER",
        start_lap=1,
        compound=TireCompound.SOFT,
    )
    stint.add_lap(1, 92.5)
    stint.add_lap(2, 92.3)
    stint.complete_stint(end_lap=2, reason="pit_stop")

    success = live_cache.complete_stint("VER", stint)
    assert success

    # Verificar archivo
    driver_path = live_cache.config.get_live_driver_path("VER")
    completed_file = driver_path / "completed_stints.json"
    assert completed_file.exists()


def test_add_race_event(live_cache):
    """Test añadir evento de carrera."""
    # Iniciar sesión
    session_info = SessionMetadata(
        year=2024,
        race_name="Bahrain",
        session_type=SessionType.RACE,
        circuit_name="Bahrain",
        country="Bahrain",
        start_time=datetime.now(),
    )
    live_cache.start_live_session(session_info)

    # Añadir evento
    event = RaceEvent(
        event_type=EventType.PIT_ENTRY,
        timestamp=datetime.now(),
        driver="VER",
        lap_number=15,
        message="Pit stop",
    )

    success = live_cache.add_race_event(event)
    assert success

    # Verificar archivo
    session_path = live_cache.config.get_live_session_path()
    events_file = session_path / "events" / "race_events.json"
    assert events_file.exists()


def test_update_race_state(live_cache):
    """Test actualizar estado de carrera."""
    # Iniciar sesión
    session_info = SessionMetadata(
        year=2024,
        race_name="Bahrain",
        session_type=SessionType.RACE,
        circuit_name="Bahrain",
        country="Bahrain",
        start_time=datetime.now(),
    )
    live_cache.start_live_session(session_info)

    # Actualizar estado
    race_state = RaceState(current_lap=15, total_laps=57)
    race_state.update_positions({1: "VER", 2: "HAM", 3: "LEC"})

    success = live_cache.update_race_state(race_state)
    assert success

    # Verificar archivo
    session_path = live_cache.config.get_live_session_path()
    state_file = session_path / "race_state.json"
    assert state_file.exists()


def test_finalize_session(live_cache):
    """Test finalizar sesión y mover a histórico."""
    # Iniciar sesión
    session_info = SessionMetadata(
        year=2024,
        race_name="bahrain",
        session_type=SessionType.RACE,
        circuit_name="Bahrain",
        country="Bahrain",
        start_time=datetime.now(),
    )
    live_cache.start_live_session(session_info)

    # Añadir algunos datos
    lap_data = LapData(
        lap_number=1, driver="VER", lap_time=92.5
    )
    live_cache.update_driver_lap("VER", lap_data)

    # Finalizar
    success = live_cache.finalize_session()
    assert success

    # Verificar que se movió a histórico
    dest_path = live_cache.config.get_race_path(2024, "bahrain")
    assert (dest_path / "live_data").exists()

    # Verificar que se limpió live
    session_path = live_cache.config.get_live_session_path()
    assert not session_path.exists()


# ==================== TESTS MODELOS ====================


def test_stint_data_statistics():
    """Test cálculo de estadísticas de stint."""
    stint = StintData(
        stint_number=1,
        driver="VER",
        start_lap=1,
        compound=TireCompound.SOFT,
    )

    stint.add_lap(1, 92.5)
    stint.add_lap(2, 92.3)
    stint.add_lap(3, 92.8)

    assert stint.avg_lap_time is not None
    assert len(stint.lap_times) == 3
    assert len(stint.laps_completed) == 3


def test_stint_to_dict():
    """Test serialización de stint."""
    stint = StintData(
        stint_number=1,
        driver="VER",
        start_lap=1,
        compound=TireCompound.SOFT,
    )
    stint.add_lap(1, 92.5)

    data = stint.to_dict()
    assert "stint_number" in data
    assert "driver" in data
    assert "compound" in data

    # Verificar que se puede serializar a JSON
    json_str = json.dumps(data)
    assert json_str is not None


def test_race_state_update_positions():
    """Test actualización de posiciones."""
    state = RaceState(current_lap=10, total_laps=57)
    positions = {1: "VER", 2: "HAM", 3: "LEC"}

    state.update_positions(positions)

    assert state.leader == "VER"
    assert state.positions == positions
    assert state.last_update is not None
