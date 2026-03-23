"""Run real-race backtests from cached data and persist metrics/artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from src.data.cache_config import CacheConfig
from src.data.cache_manager import CacheManager
from src.predictive.artifacts import (
    ModelMetadata,
    PREDICTIVE_MODEL_VERSION,
    save_model_artifact,
    _nan_safe_default,
)
from src.predictive.backtesting import backtest_pit_baseline
from src.predictive.dataset_builder import build_pit_window_dataset_from_cache

METRICS_DIR = Path("data/processed/predictive/metrics")
ARTIFACTS_DIR = Path("data/processed/predictive/artifacts")


def _ensure_dirs() -> None:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


def backtest_race(
    *,
    year: int,
    race_name: str,
    cache_config: Optional[CacheConfig] = None,
    test_fraction: float = 0.3,
    max_iter: int = 200,
) -> Path:
    """Build dataset from cache, backtest baseline, persist metrics and model artifact.

    Args:
        year: Season year.
        race_name: Race identifier (matches cache naming used when saving).
        cache_config: Optional cache config override.
        test_fraction: Fraction for test split.
        max_iter: Max iterations for logistic regression.

    Returns:
        Path to metrics JSON report.
    """

    _ensure_dirs()

    cache_manager = CacheManager(config=cache_config or CacheConfig())

    # Build dataset from cached laps/pits
    dataset = build_pit_window_dataset_from_cache(
        cache_manager,
        year,
        race_name,
        window_half_width=0,
        horizon_laps=10,
        rolling_window=3,
        persist=False,
    )

    model, result = backtest_pit_baseline(
        dataset, test_fraction=test_fraction, max_iter=max_iter)

    report = {
        "race": race_name,
        "year": year,
        "version": PREDICTIVE_MODEL_VERSION,
        "metrics": result.as_dict(),
        "row_count": len(dataset),
    }

    metrics_path = METRICS_DIR / f"{year}_{race_name}_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=_nan_safe_default)

    # Persist artifact alongside metrics
    metadata = ModelMetadata.create(
        trained_on=f"{year}:{race_name}",
        n_train=result.n_train,
        n_test=result.n_test,
        auc=result.auc,
        brier=result.brier,
        positive_rate=result.positive_rate,
    )

    artifact_path = ARTIFACTS_DIR / f"{year}_{race_name}_pit_baseline.joblib"
    save_model_artifact(model, metadata, artifact_path)

    return metrics_path


__all__ = ["backtest_race", "METRICS_DIR", "ARTIFACTS_DIR"]
