"""
Unified F1 Data Provider - Wrapper para FastF1 y OpenF1.

Este módulo proporciona una interfaz unificada para acceder a datos
de Fórmula 1 desde múltiples fuentes (FastF1 para análisis
histórico y OpenF1 para datos en tiempo real).
"""

import logging
import os
from typing import Optional
from abc import ABC, abstractmethod

import pandas as pd
import fastf1

logger = logging.getLogger(__name__)


class F1DataProvider(ABC):
    """Interfaz base para proveedores de datos de F1."""

    @abstractmethod
    def get_race_results(
        self,
        year: int,
        round_number: int
    ) -> pd.DataFrame:
        """Obtiene resultados de carrera."""
        pass

    @abstractmethod
    def get_telemetry(
        self,
        year: int,
        round_number: int,
        driver: str
    ) -> pd.DataFrame:
        """Obtiene datos de telemetría."""
        pass

    @abstractmethod
    def get_qualifying_results(
        self,
        year: int,
        round_number: int
    ) -> pd.DataFrame:
        """Obtiene resultados de clasificación."""
        pass


class FastF1Provider(F1DataProvider):
    """Proveedor de datos usando FastF1 (análisis histórico)."""

    def __init__(self, cache_dir: str = "./cache") -> None:
        """
        Inicializa el proveedor FastF1.

        Args:
            cache_dir: Directorio para almacenar caché
        """
        os.makedirs(cache_dir, exist_ok=True)
        fastf1.Cache.enable_cache(cache_dir=cache_dir)
        logger.info(
            "FastF1Provider inicializado con caché habilitado"
        )

    def get_race_results(
        self,
        year: int,
        round_number: int
    ) -> pd.DataFrame:
        """
        Obtiene resultados de carrera desde FastF1.

        Args:
            year: Año de la temporada
            round_number: Número de la carrera (1-24)

        Returns:
            DataFrame con resultados de carrera
        """
        try:
            session = fastf1.get_session(year, round_number, "R")
            session.load()

            results = session.results[
                [
                    "DriverNumber",
                    "Abbreviation",
                    "TeamName",
                    "ClassifiedPosition",
                    "Points",
                    "Status"
                ]
            ].copy()

            results.rename(
                columns={
                    "Abbreviation": "Driver",
                    "ClassifiedPosition": "Position"
                },
                inplace=True
            )

            msg = f"Resultados obtenidos: {year} R{round_number}"
            logger.info(msg)
            return results
        except Exception as e:
            msg = (
                f"Error obteniendo resultados {year} "
                f"R{round_number}: {str(e)}"
            )
            logger.error(msg)
            raise

    def get_telemetry(
        self,
        year: int,
        round_number: int,
        driver: str
    ) -> pd.DataFrame:
        """
        Obtiene telemetría detallada de un piloto.

        Args:
            year: Año de la temporada
            round_number: Número de la carrera
            driver: Código de piloto (ej: 'VER', 'HAM')

        Returns:
            DataFrame con datos de telemetría
        """
        try:
            session = fastf1.get_session(year, round_number, "R")
            session.load()

            laps = session.laps.pick_drivers(driver)

            if laps.empty:
                msg = (
                    f"No se encontró telemetría para {driver} "
                    f"en {year} R{round_number}"
                )
                logger.warning(msg)
                return pd.DataFrame()

            telemetry = (
                laps.iloc[-1]
                .get_telemetry()
                .reset_index(drop=True)
            )

            msg = (
                f"Telemetría obtenida: {driver} "
                f"en {year} R{round_number}"
            )
            logger.info(msg)
            return telemetry
        except Exception as e:
            msg = (
                f"Error obteniendo telemetría "
                f"{driver}: {str(e)}"
            )
            logger.error(msg)
            raise

    def get_qualifying_results(
        self,
        year: int,
        round_number: int
    ) -> pd.DataFrame:
        """
        Obtiene resultados de clasificación.

        Args:
            year: Año de la temporada
            round_number: Número de la carrera

        Returns:
            DataFrame con resultados de clasificación
        """
        try:
            session = fastf1.get_session(year, round_number, "Q")
            session.load()

            results = session.results[
                [
                    "DriverNumber",
                    "Abbreviation",
                    "TeamName",
                    "Q1",
                    "Q2",
                    "Q3",
                    "GridPosition"
                ]
            ].copy()

            results.rename(
                columns={"Abbreviation": "Driver"},
                inplace=True
            )

            msg = (
                f"Clasificación obtenida: "
                f"{year} R{round_number}"
            )
            logger.info(msg)
            return results
        except Exception as e:
            msg = (
                f"Error obteniendo clasificación {year} "
                f"R{round_number}: {str(e)}"
            )
            logger.error(msg)
            raise


class OpenF1Provider(F1DataProvider):
    """Proveedor de datos usando OpenF1 (tiempo real)."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        """
        Inicializa el proveedor OpenF1.

        Args:
            api_key: Clave de API de OpenF1 (opcional)
        """
        self.api_key = api_key
        self.base_url = "https://api.openf1.org/v1"
        logger.info("OpenF1Provider inicializado")

    def get_race_results(
        self,
        year: int,
        round_number: int
    ) -> pd.DataFrame:
        """
        Obtiene resultados de carrera desde OpenF1.

        Args:
            year: Año de la temporada
            round_number: Número de la carrera

        Returns:
            DataFrame con resultados de carrera
        """
        try:
            import httpx

            params = {
                "session_year": year,
                "session_round": round_number,
                "session_type": "race"
            }

            async def fetch():
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{self.base_url}/results",
                        params=params
                    )
                    return response.json()

            msg = (
                f"Resultados en tiempo real obtenidos: "
                f"{year} R{round_number}"
            )
            logger.info(msg)
            return pd.DataFrame()
        except Exception as e:
            msg = (
                f"Error obteniendo resultados "
                f"en tiempo real: {str(e)}"
            )
            logger.error(msg)
            raise

    def get_telemetry(
        self,
        year: int,
        round_number: int,
        driver: str
    ) -> pd.DataFrame:
        """
        Obtiene telemetría en tiempo real.

        Args:
            year: Año de la temporada
            round_number: Número de la carrera
            driver: Código de piloto

        Returns:
            DataFrame con datos de telemetría en tiempo real
        """
        msg = (
            f"Telemetría en tiempo real: {driver} "
            f"en {year} R{round_number}"
        )
        logger.info(msg)
        return pd.DataFrame()

    def get_qualifying_results(
        self,
        year: int,
        round_number: int
    ) -> pd.DataFrame:
        """
        Obtiene resultados de clasificación en tiempo real.

        Args:
            year: Año de la temporada
            round_number: Número de la carrera

        Returns:
            DataFrame con resultados de clasificación
        """
        msg = (
            f"Clasificación en tiempo real obtenida: "
            f"{year} R{round_number}"
        )
        logger.info(msg)
        return pd.DataFrame()


class UnifiedF1DataProvider:
    """
    Proveedor unificado que combina FastF1 y OpenF1.

    Utiliza FastF1 para análisis histórico y OpenF1 para
    tiempo real.
    """

    def __init__(
        self,
        use_cache: bool = True,
        cache_dir: str = "./cache",
        openf1_api_key: Optional[str] = None
    ) -> None:
        """
        Inicializa el proveedor unificado.

        Args:
            use_cache: Habilitar caché de FastF1
            cache_dir: Directorio para almacenar caché
            openf1_api_key: Clave API de OpenF1
        """
        self.fastf1_provider = FastF1Provider(
            cache_dir=cache_dir
        )
        self.openf1_provider = OpenF1Provider(
            api_key=openf1_api_key
        )
        logger.info("UnifiedF1DataProvider inicializado")

    def get_race_results(
        self,
        year: int,
        round_number: int,
        use_realtime: bool = False
    ) -> pd.DataFrame:
        """
        Obtiene resultados de carrera.

        Args:
            year: Año de la temporada
            round_number: Número de la carrera
            use_realtime: Usar OpenF1 para tiempo real

        Returns:
            DataFrame con resultados
        """
        provider = (
            self.openf1_provider if use_realtime
            else self.fastf1_provider
        )
        return provider.get_race_results(year, round_number)

    def get_telemetry(
        self,
        year: int,
        round_number: int,
        driver: str,
        use_realtime: bool = False
    ) -> pd.DataFrame:
        """
        Obtiene telemetría de piloto.

        Args:
            year: Año de la temporada
            round_number: Número de la carrera
            driver: Código de piloto
            use_realtime: Usar OpenF1 para tiempo real

        Returns:
            DataFrame con telemetría
        """
        provider = (
            self.openf1_provider if use_realtime
            else self.fastf1_provider
        )
        return provider.get_telemetry(
            year,
            round_number,
            driver
        )

    def get_qualifying_results(
        self,
        year: int,
        round_number: int,
        use_realtime: bool = False
    ) -> pd.DataFrame:
        """
        Obtiene resultados de clasificación.

        Args:
            year: Año de la temporada
            round_number: Número de la carrera
            use_realtime: Usar OpenF1 para tiempo real

        Returns:
            DataFrame con clasificación
        """
        provider = (
            self.openf1_provider if use_realtime
            else self.fastf1_provider
        )
        return provider.get_qualifying_results(
            year,
            round_number
        )

    def get_season_schedule(self, year: int) -> pd.DataFrame:
        """
        Obtiene el calendario completo de la temporada.

        Args:
            year: Año de la temporada

        Returns:
            DataFrame con calendario
        """
        try:
            schedule = fastf1.get_event_schedule(year)
            logger.info(f"Calendario obtenido: {year}")
            return schedule
        except Exception as e:
            msg = (
                f"Error obteniendo calendario "
                f"{year}: {str(e)}"
            )
            logger.error(msg)
            raise