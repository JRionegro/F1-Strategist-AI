"""List predictive metrics/artifacts for quick comparison."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Tuple


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--metrics-dir",
        type=Path,
        default=Path("data/processed/predictive/metrics"),
        help="Directory containing *_metrics.json files",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on number of rows to display (most recent first)",
    )
    return parser.parse_args()


def load_reports(metrics_dir: Path) -> List[Tuple[Path, dict]]:
    reports: List[Tuple[Path, dict]] = []
    for path in sorted(metrics_dir.glob("*_metrics.json")):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        reports.append((path, data))
    # Sort by path name descending to show latest first
    reports.sort(key=lambda x: x[0].name, reverse=True)
    return reports


def main() -> None:
    args = parse_args()
    reports = load_reports(args.metrics_dir)
    if args.limit:
        reports = reports[: args.limit]

    if not reports:
        print("No metrics found")
        return

    header = ["race", "year", "auc", "brier", "n_train", "n_test", "row_count", "file"]
    print("\t".join(header))
    for path, data in reports:
        metrics = data.get("metrics", {})
        row = [
            data.get("race", ""),
            str(data.get("year", "")),
            f"{metrics.get('auc', 0):.4f}" if metrics else "",
            f"{metrics.get('brier', 0):.4f}" if metrics else "",
            str(metrics.get("n_train", "")),
            str(metrics.get("n_test", "")),
            str(data.get("row_count", "")),
            path.name,
        ]
        print("\t".join(row))


if __name__ == "__main__":
    main()
