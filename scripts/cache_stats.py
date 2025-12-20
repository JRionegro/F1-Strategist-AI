"""
Script de utilidad para ver estadísticas de caché.

Muestra uso de disco, cantidad de datos almacenados, etc.
"""

import logging
from pathlib import Path
from typing import Any

from src.data.cache_manager import CacheManager
from src.data.cache_config import CacheMode, DataType

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def format_size(size_bytes: float) -> str:
    """
    Formatea tamaño en bytes a formato legible.

    Args:
        size_bytes: Tamaño en bytes

    Returns:
        String formateado (KB, MB, GB)
    """
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def get_directory_stats(directory: Path) -> dict[str, Any]:
    """
    Obtiene estadísticas de un directorio.

    Args:
        directory: Ruta al directorio

    Returns:
        Diccionario con estadísticas
    """
    if not directory.exists():
        return {"exists": False}

    total_size = 0
    file_count = 0
    dir_count = 0

    for item in directory.rglob("*"):
        if item.is_file():
            total_size += item.stat().st_size
            file_count += 1
        elif item.is_dir():
            dir_count += 1

    return {
        "exists": True,
        "total_size_bytes": total_size,
        "total_size": format_size(total_size),
        "file_count": file_count,
        "dir_count": dir_count,
    }


def show_cache_stats() -> None:
    """Muestra estadísticas detalladas del caché."""
    cache_manager = CacheManager(mode=CacheMode.HISTORICAL)

    print("\n" + "=" * 60)
    print("F1 STRATEGIST AI - CACHE STATISTICS")
    print("=" * 60)

    # Estadísticas generales
    stats = cache_manager.get_cache_stats()
    print(f"\nMode: {stats['mode']}")
    print(f"Total Size: {stats['total_size_mb']:.2f} MB")
    print(f"Races Cached: {stats['races_count']}")
    print(
        f"Live Session Active: "
        f"{'Yes' if stats['live_session_active'] else 'No'}"
    )

    # Estadísticas por directorio
    print("\n" + "-" * 60)
    print("STORAGE BREAKDOWN")
    print("-" * 60)

    directories = {
        "Races": cache_manager.config.races_dir,
        "Telemetry": cache_manager.config.telemetry_dir,
        "Live": cache_manager.config.live_dir,
        "Processed": cache_manager.config.processed_dir,
    }

    for name, directory in directories.items():
        dir_stats = get_directory_stats(directory)

        if not dir_stats["exists"]:
            print(f"\n{name}: Not initialized")
            continue

        print(f"\n{name}:")
        print(f"  Location: {directory}")
        print(f"  Size: {dir_stats['total_size']}")
        print(f"  Files: {dir_stats['file_count']}")
        print(f"  Subdirectories: {dir_stats['dir_count']}")

    # Políticas de retención
    print("\n" + "-" * 60)
    print("RETENTION POLICIES")
    print("-" * 60)

    for data_type in DataType:
        retention = cache_manager.config.get_retention_days(data_type)
        policy = "Permanent" if retention is None else f"{retention} days"
        print(f"{data_type.value:25} {policy}")

    print("\n" + "=" * 60 + "\n")


def main() -> None:
    """Función principal."""
    try:
        show_cache_stats()
    except Exception as e:
        logger.error(f"Error showing cache stats: {e}")
        raise


if __name__ == "__main__":
    main()
