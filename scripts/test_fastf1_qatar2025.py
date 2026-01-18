"""Quick helper to verify FastF1 telemetry availability for the 2025 Qatar GP."""
from __future__ import annotations

import argparse
import logging
from typing import List, Sequence

from src.data.fastf1_position_provider import FastF1PositionProvider

LOGGER = logging.getLogger("fastf1.sample")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def fetch_driver_numbers(provider: FastF1PositionProvider) -> List[int]:
    """Return the list of driver numbers contained in the current cache."""
    session_info = provider.get_session_info()
    if not session_info:
        return []
    drivers_value = session_info.get("drivers")
    if isinstance(drivers_value, Sequence):
        return [int(num) for num in drivers_value]
    if isinstance(drivers_value, int):
        return [drivers_value]
    return []


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", default="./cache", help="Path to the FastF1 cache directory")
    parser.add_argument("--lap", type=int, default=1, help="Lap number to sample")
    args = parser.parse_args()

    provider = FastF1PositionProvider(cache_dir=args.cache)
    if not provider.load_session(2025, "Qatar", "R"):
        LOGGER.error("Failed to load 2025 Qatar race from FastF1")
        return

    drivers = fetch_driver_numbers(provider)
    LOGGER.info("Loaded %d drivers", len(drivers))

    positions = provider.get_all_driver_positions(args.lap, drivers, elapsed_time=10.0)
    LOGGER.info("Retrieved %d driver positions at t=10s on lap %d", len(positions), args.lap)

    for driver_number, position in list(positions.items())[:3]:
        LOGGER.info(
            "Driver %s -> x=%.1f, y=%.1f, time=%.2f",
            driver_number,
            position["x"],
            position["y"],
            position["time"],
        )


if __name__ == "__main__":
    main()
