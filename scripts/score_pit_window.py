"""CLI to score pit-window datasets with a saved pit baseline artifact."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from src.predictive.scoring import score_pit_window_csv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_csv", type=Path, help="Path to pit-window dataset CSV")
    parser.add_argument(
        "artifact_path",
        type=Path,
        help="Path to pit baseline artifact (.joblib) with accompanying metadata JSON",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output CSV path; defaults to <input>_scored.csv",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=5,
        help="Number of top rows (by probability) to display in summary",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    args = parse_args()

    result = score_pit_window_csv(
        input_path=args.input_csv,
        artifact_path=args.artifact_path,
        output_path=args.output,
        top_n=args.top_n,
        return_summary=True,
    )
    output_path, summary = result

    print(f"Wrote scored dataset to {output_path}")
    print(
        "Summary: count={count} mean={mean:.4f} min={min:.4f} max={max:.4f}".format(
            **summary
        )
    )
    print("Top rows (prob):")
    for row in summary["top"]:
        print(
            f"  driver={row['driver_id']} lap={row['lap_number']} prob={row['pit_stop_proba']:.4f}"
        )


if __name__ == "__main__":
    main()
