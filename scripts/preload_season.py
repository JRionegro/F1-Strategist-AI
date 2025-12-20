"""
Script para precargar una temporada completa en caché.

Descarga datos históricos de todas las carreras de una temporada.
"""

import argparse
import logging
from typing import Optional

import pandas as pd

from src.data.f1_data_provider import UnifiedF1DataProvider
from src.data.cache_config import DataType

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def preload_season(
    year: int,
    data_types: Optional[list[str]] = None,
    skip_telemetry: bool = False
) -> None:
    """
    Precarga datos de una temporada completa.

    Args:
        year: Año de la temporada
        data_types: Tipos de datos a precargar (None para básicos)
        skip_telemetry: Si True, omite telemetría (muy pesada)
    """
    provider = UnifiedF1DataProvider(use_smart_cache=True)

    logger.info(f"Preloading season {year}")

    # Obtener calendario
    try:
        schedule = provider.get_season_schedule(year)
        logger.info(f"Found {len(schedule)} events in {year}")
    except Exception as e:
        logger.error(f"Error getting schedule: {e}")
        return

    # Tipos de datos a precargar
    if data_types is None:
        data_types = [
            "race_results",
            "qualifying",
            "weather",
            "pit_stops",
            "tire_strategy",
            "driver_info",
        ]

    total_races = len(schedule)

    for race_number, (_, event) in enumerate(schedule.iterrows(), start=1):
        race_name = event.get("EventName", f"Round {race_number}")

        logger.info(
            f"Processing {race_number}/{total_races}: {race_name}"
        )

        # Resultados de carrera
        if "race_results" in data_types:
            try:
                provider.get_race_results(year, race_number)
                logger.info(f"  ✓ Race results cached")
            except Exception as e:
                logger.warning(f"  ✗ Race results failed: {e}")

        # Clasificación
        if "qualifying" in data_types:
            try:
                provider.get_qualifying_results(year, race_number)
                logger.info(f"  ✓ Qualifying cached")
            except Exception as e:
                logger.warning(f"  ✗ Qualifying failed: {e}")

        # Clima
        if "weather" in data_types:
            try:
                provider.get_weather(year, race_number)
                logger.info(f"  ✓ Weather cached")
            except Exception as e:
                logger.warning(f"  ✗ Weather failed: {e}")

        # Pit stops
        if "pit_stops" in data_types:
            try:
                provider.get_pit_stops(year, race_number)
                logger.info(f"  ✓ Pit stops cached")
            except Exception as e:
                logger.warning(f"  ✗ Pit stops failed: {e}")

        # Estrategia de neumáticos
        if "tire_strategy" in data_types:
            try:
                provider.get_tire_strategy(year, race_number)
                logger.info(f"  ✓ Tire strategy cached")
            except Exception as e:
                logger.warning(f"  ✗ Tire strategy failed: {e}")

        # Información de pilotos
        if "driver_info" in data_types:
            try:
                provider.get_driver_info(year, race_number)
                logger.info(f"  ✓ Driver info cached")
            except Exception as e:
                logger.warning(f"  ✗ Driver info failed: {e}")

        # Tiempos por vuelta
        if "lap_times" in data_types:
            try:
                provider.get_lap_times(year, race_number)
                logger.info(f"  ✓ Lap times cached")
            except Exception as e:
                logger.warning(f"  ✗ Lap times failed: {e}")

    logger.info(f"Season {year} preload complete!")


def main() -> None:
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="Precarga temporada de F1 en caché"
    )
    parser.add_argument(
        "year",
        type=int,
        help="Año de la temporada a precargar",
    )
    parser.add_argument(
        "--types",
        nargs="+",
        default=None,
        help=(
            "Tipos de datos a precargar "
            "(race_results, qualifying, weather, etc)"
        ),
    )
    parser.add_argument(
        "--skip-telemetry",
        action="store_true",
        help="Omitir telemetría (muy pesada)",
    )

    args = parser.parse_args()

    preload_season(
        year=args.year,
        data_types=args.types,
        skip_telemetry=args.skip_telemetry,
    )


if __name__ == "__main__":
    main()
