"""Utilities to score pit-window datasets with persisted artifacts."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from src.predictive.artifacts import PitPredictorService
from src.predictive.modeling import FEATURE_COLUMNS

logger = logging.getLogger(__name__)


REQUIRED_COLUMNS = set(FEATURE_COLUMNS) | {"lap_number", "pit_window_center_lap"}


def _summarize_scores(df: pd.DataFrame, top_n: int) -> dict[str, Any]:
    top = df.nlargest(top_n, "pit_stop_proba")[
        ["driver_id", "lap_number", "pit_stop_proba"]
    ].to_dict("records")
    return {
        "count": int(len(df)),
        "mean": float(df["pit_stop_proba"].mean()),
        "min": float(df["pit_stop_proba"].min()),
        "max": float(df["pit_stop_proba"].max()),
        "top": top,
    }


def score_pit_window_csv(
    *,
    input_path: str | Path,
    artifact_path: str | Path,
    output_path: Optional[str | Path] = None,
    top_n: int = 5,
    return_summary: bool = False,
) -> Path | tuple[Path, dict[str, Any]]:
    """Load pit-window rows from CSV, score with artifact, and persist probabilities.

    The input CSV must contain the feature columns defined in FEATURE_COLUMNS plus
    `lap_number` and `pit_window_center_lap` to satisfy the model's contract.

    Args:
        input_path: Path to pit-window dataset CSV.
        artifact_path: Persisted joblib artifact with metadata JSON.
        output_path: Optional output CSV path. Defaults to `<input>_scored.csv`.

    Returns:
        Path to the scored CSV containing a `pit_stop_proba` column. If
        `return_summary` is True, returns (Path, summary_dict).
    """

    input_path = Path(input_path)
    output_path = (
        Path(output_path)
        if output_path is not None
        else input_path.with_name(f"{input_path.stem}_scored{input_path.suffix}")
    )

    df = pd.read_csv(input_path)
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Input dataset missing required columns: {sorted(missing)}")

    service = PitPredictorService(artifact_path)
    service.load()

    proba = service.predict_proba(df)
    scored = df.copy()
    scored["pit_stop_proba"] = proba

    output_path.parent.mkdir(parents=True, exist_ok=True)
    scored.to_csv(output_path, index=False)

    summary = _summarize_scores(scored, top_n)
    logger.info(
        "Scored %d rows -> %s | mean=%.4f min=%.4f max=%.4f",
        len(scored),
        output_path,
        summary["mean"],
        summary["min"],
        summary["max"],
    )

    if return_summary:
        return output_path, summary

    return output_path


__all__ = ["score_pit_window_csv", "REQUIRED_COLUMNS"]
