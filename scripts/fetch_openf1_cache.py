"""CLI helper to fetch OpenF1 race data and persist CacheManager-friendly files."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from src.data.cache_config import CacheConfig
from src.data.openf1_cache_writer import fetch_and_cache_openf1_race


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, required=True, help="Season year")
    parser.add_argument(
        "--race-name",
        type=str,
        required=True,
        help="Race folder name, e.g., 2023-03-05_Bahrain_Grand_Prix",
    )
    parser.add_argument(
        "--session-key",
        type=int,
        default=None,
        help="Optional explicit OpenF1 session_key for the race session",
    )
    parser.add_argument(
        "--races-dir",
        type=Path,
        default=Path("./data/races"),
        help="Output cache directory (CacheConfig.races_dir)",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    args = parse_args()

    cache_config = CacheConfig(races_dir=args.races_dir)
    lap_path, pit_path = fetch_and_cache_openf1_race(
        year=args.year,
        race_name=args.race_name,
        cache_config=cache_config,
        session_key=args.session_key,
    )

    print(f"Saved lap_times to {lap_path}")
    print(f"Saved pit_stops to {pit_path}")


if __name__ == "__main__":
    main()
