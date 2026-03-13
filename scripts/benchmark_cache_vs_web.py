"""Benchmark Qatar 2025 cache vs web load times.

This script compares the time spent loading key OpenF1 datasets directly from
the API versus reading the cached parquet files already generated in the
repository. The target session is the 2025 Qatar Grand Prix race.
"""

from __future__ import annotations
from src.data.openf1_data_provider import OpenF1DataProvider

import logging
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Callable, List, Sequence, Tuple

import pandas as pd

import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


TARGET_YEAR = 2025
TARGET_COUNTRY = "Qatar"
TARGET_SESSION_NAME = "Race"

OperationLoader = Callable[[OpenF1DataProvider, int], pd.DataFrame]


@dataclass
class OperationResult:
    """Store timing information for a single dataset load."""

    dataset: str
    mode: str
    duration: float
    rows: int


OPERATIONS: Sequence[Tuple[str, OperationLoader]] = (
    ("drivers", lambda provider, key: provider.get_drivers(key)),
    ("laps", lambda provider, key: provider.get_laps(key)),
    ("stints", lambda provider, key: provider.get_stints(key)),
    ("positions", lambda provider, key: provider.get_positions(key)),
    ("intervals", lambda provider, key: provider.get_intervals(key)),
    ("pit_stops", lambda provider, key: provider.get_pit_stops(key)),
    ("weather", lambda provider, key: provider.get_weather(key)),
    (
        "race_control",
        lambda provider, key: provider.get_race_control_messages(key),
    ),
)


def _infer_row_count(data: object) -> int:
    """Return the number of rows for pandas data frames or generic sequences."""

    if isinstance(data, pd.DataFrame):
        return int(data.shape[0])
    if hasattr(data, "__len__"):
        try:
            return int(len(data))  # type: ignore[arg-type]
        except TypeError:
            return 0
    return 0


def _resolve_session(provider: OpenF1DataProvider) -> Tuple[dict, int]:
    """Fetch session metadata for the Qatar 2025 race and return the key."""

    session_info = provider.get_session(
        year=TARGET_YEAR,
        session_name=TARGET_SESSION_NAME,
        country_name=TARGET_COUNTRY,
    )
    if not session_info:
        raise RuntimeError(
            "Could not locate session metadata; verify the Qatar 2025 race exists."
        )
    raw_key = session_info.get("session_key")
    if raw_key is None:
        raise RuntimeError("Session metadata missing 'session_key'.")
    try:
        session_key = int(raw_key)
    except (TypeError, ValueError) as exc:
        raise RuntimeError("Session key is not numeric.") from exc
    return session_info, session_key


def _benchmark_mode(
    mode_name: str,
    provider: OpenF1DataProvider,
    session_key: int,
    operations: Sequence[Tuple[str, OperationLoader]],
) -> List[OperationResult]:
    """Execute the loaders with a provider and capture timing statistics."""

    results: List[OperationResult] = []
    for dataset, loader in operations:
        start = perf_counter()
        data = loader(provider, session_key)
        duration = perf_counter() - start
        rows = _infer_row_count(data)
        results.append(
            OperationResult(
                dataset=dataset,
                mode=mode_name,
                duration=duration,
                rows=rows,
            )
        )
    return results


def _find_result(results: Sequence[OperationResult], dataset: str) -> OperationResult:
    """Locate the benchmarking outcome for a specific dataset."""

    for result in results:
        if result.dataset == dataset:
            return result
    raise KeyError(f"Dataset '{dataset}' not present in benchmark results.")


def _print_summary(
    session_key: int,
    datasets: Sequence[str],
    web_results: Sequence[OperationResult],
    cache_results: Sequence[OperationResult],
) -> None:
    """Pretty print a comparison table for web vs cache timings."""

    print(
        f"\nBenchmark target: Qatar {TARGET_YEAR} race (session_key={session_key})"
    )
    header = f"{'Dataset':<18}{'Web (s)':>12}{'Cache (s)':>12}{'Speedup':>10}{'Rows':>10}"
    print(header)
    print("-" * len(header))

    web_total = 0.0
    cache_total = 0.0
    for dataset in datasets:
        web_result = _find_result(web_results, dataset)
        cache_result = _find_result(cache_results, dataset)
        web_total += web_result.duration
        cache_total += cache_result.duration
        cache_duration = cache_result.duration if cache_result.duration > 0.0 else 1e-9
        speedup = web_result.duration / cache_duration
        rows = max(web_result.rows, cache_result.rows)
        print(
            f"{dataset:<18}{web_result.duration:>12.3f}{cache_result.duration:>12.3f}"
            f"{speedup:>10.2f}{rows:>10}"
        )

    total_speedup = web_total / cache_total if cache_total > 0.0 else float("inf")
    print("-" * len(header))
    print(
        f"{'TOTAL':<18}{web_total:>12.3f}{cache_total:>12.3f}{total_speedup:>10.2f}{'':>10}"
    )
    print("\nSpeedup > 1.0 indicates cached data is faster than fresh API calls.")


def main() -> None:
    """Run the Qatar 2025 benchmark for web vs cache performance."""

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    for logger_name in (
        "f1.data",
        "f1.startup",
        "f1.chat",
        "f1.race_overview",
        "f1.track_map",
    ):
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    metadata_provider = OpenF1DataProvider()
    session_info, session_key = _resolve_session(metadata_provider)

    web_provider = OpenF1DataProvider()
    web_results = _benchmark_mode(
        mode_name="web",
        provider=web_provider,
        session_key=session_key,
        operations=OPERATIONS,
    )

    cache_provider = OpenF1DataProvider()
    cache_provider.register_session_metadata(session_key, session_info)
    cache_dir = cache_provider._find_cached_race_directory(session_key, session_info)
    if cache_dir is None:
        raise RuntimeError(
            "Cached parquet files not found for Qatar 2025. Generate caches before benchmarking."
        )
    cache_results = _benchmark_mode(
        mode_name="cache",
        provider=cache_provider,
        session_key=session_key,
        operations=OPERATIONS,
    )

    dataset_order = [name for name, _ in OPERATIONS]
    _print_summary(session_key, dataset_order, web_results, cache_results)


if __name__ == "__main__":
    main()
