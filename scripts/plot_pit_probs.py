"""Plot pit-stop probabilities vs lap_number per driver from a scored CSV."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Optional

import matplotlib.pyplot as plt
import pandas as pd

DEFAULT_TOP_DRIVERS = 6


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_csv", type=Path, help="Scored pit-window CSV with pit_stop_proba column")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output image path (PNG). Defaults to <input>_pit_probs.png",
    )
    parser.add_argument(
        "--drivers",
        nargs="*",
        default=None,
        help="Optional list of driver_ids to plot. If omitted, plots top drivers by max probability",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=DEFAULT_TOP_DRIVERS,
        help="If --drivers not provided, number of top drivers by max probability",
    )
    return parser.parse_args()


def select_drivers(df: pd.DataFrame, drivers: Optional[List[str]], top: int) -> List[str]:
    if drivers:
        return drivers
    top_drivers = (
        df.groupby("driver_id")["pit_stop_proba"].max().sort_values(ascending=False).head(top).index.tolist()
    )
    return top_drivers


def plot_probs(df: pd.DataFrame, drivers: List[str], output_path: Path) -> Path:
    plt.figure(figsize=(10, 6))
    for drv in drivers:
        sub = df[df["driver_id"] == drv]
        if sub.empty:
            continue
        plt.plot(sub["lap_number"], sub["pit_stop_proba"], label=drv, linewidth=1.5)

    plt.xlabel("Lap")
    plt.ylabel("Pit stop probability")
    plt.title("Pit-stop probability vs lap")
    plt.legend()
    plt.grid(True, alpha=0.3)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    return output_path


def main() -> None:
    args = parse_args()
    input_csv: Path = args.input_csv
    output_path = args.output or input_csv.with_name(f"{input_csv.stem}_pit_probs.png")

    df = pd.read_csv(input_csv)
    if "pit_stop_proba" not in df.columns:
        raise ValueError("Input CSV must contain pit_stop_proba column")

    drivers = select_drivers(df, args.drivers, args.top)
    if not drivers:
        raise ValueError("No drivers to plot")

    result = plot_probs(df, drivers, Path(output_path))
    print(f"Wrote plot to {result}")


if __name__ == "__main__":
    main()
