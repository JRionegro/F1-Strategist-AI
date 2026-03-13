"""Tests para el proveedor unificado de datos F1."""

import pytest
from src.data.f1_data_provider import (
    UnifiedF1DataProvider,
    FastF1Provider,
    OpenF1Provider
)


@pytest.fixture
def unified_provider():
    """Fixture que proporciona el proveedor unificado."""
    return UnifiedF1DataProvider(use_cache=True)


@pytest.fixture
def fastf1_provider():
    """Fixture que proporciona el proveedor FastF1."""
    return FastF1Provider()


@pytest.fixture
def openf1_provider():
    """Fixture que proporciona el proveedor OpenF1."""
    return OpenF1Provider()


class TestFastF1Provider:
    """Tests para el proveedor FastF1."""

    def test_initialization(self, fastf1_provider):
        """Verifica la inicialización de FastF1Provider."""
        assert fastf1_provider is not None

    def test_get_season_schedule(self, unified_provider):
        """Verifica la obtención del calendario de temporada."""
        schedule = unified_provider.get_season_schedule(2024)
        assert schedule is not None
        assert not schedule.empty


class TestOpenF1Provider:
    """Tests para el proveedor OpenF1."""

    def test_initialization(self, openf1_provider):
        """Verifica la inicialización de OpenF1Provider."""
        assert openf1_provider is not None


class TestUnifiedProvider:
    """Tests para el proveedor unificado."""

    def test_initialization(self, unified_provider):
        """Verifica la inicialización del proveedor unificado."""
        assert unified_provider.fastf1_provider is not None
        assert unified_provider.openf1_provider is not None

    def test_get_race_results_historical(self, unified_provider):
        """Verifica obtención de resultados históricos."""
        results = unified_provider.get_race_results(
            year=2023,
            round_number=1,
            use_realtime=False
        )
        assert results is not None
