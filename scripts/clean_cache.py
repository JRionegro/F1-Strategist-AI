"""
Script de utilidad para limpiar caché antiguo.

Elimina datos según políticas de retención configuradas.
"""

import argparse
import logging
from pathlib import Path

from src.data.cache_manager import CacheManager
from src.data.cache_config import DataType, CacheMode

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def clean_cache(
    data_types: list[DataType] | None = None,
    dry_run: bool = False
) -> None:
    """
    Limpia datos de caché según políticas de retención.

    Args:
        data_types: Tipos de datos a limpiar (None para todos)
        dry_run: Si True, solo muestra lo que se eliminaría
    """
    cache_manager = CacheManager(mode=CacheMode.HISTORICAL)

    if data_types is None:
        data_types = [
            DataType.TELEMETRY,
            DataType.LAP_TIMES,
            DataType.PRACTICE_RESULTS,
            DataType.TRACK_STATUS,
        ]

    total_deleted = 0

    for data_type in data_types:
        retention_days = cache_manager.config.get_retention_days(data_type)

        if retention_days is None:
            logger.info(
                f"Skipping {data_type.value} (permanent retention)"
            )
            continue

        logger.info(
            f"Cleaning {data_type.value} "
            f"(retention: {retention_days} days)"
        )

        if not dry_run:
            deleted = cache_manager.clean_old_data(data_type)
            total_deleted += deleted
            logger.info(f"  Deleted {deleted} files")
        else:
            logger.info("  [DRY RUN] Would delete old files")

    logger.info(f"Total files cleaned: {total_deleted}")


def main() -> None:
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="Limpia caché de F1 Strategist AI"
    )
    parser.add_argument(
        "--types",
        nargs="+",
        choices=[dt.value for dt in DataType],
        help="Tipos de datos a limpiar",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Modo simulación (no elimina archivos)",
    )

    args = parser.parse_args()

    data_types = None
    if args.types:
        data_types = [DataType(t) for t in args.types]

    clean_cache(data_types=data_types, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
