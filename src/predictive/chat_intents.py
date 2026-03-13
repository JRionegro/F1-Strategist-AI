"""Chat-style helpers for pit-stop probability Q&A."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

import pandas as pd


@lru_cache(maxsize=4)
def _load_scored(scored_path: Path) -> pd.DataFrame:
    return pd.read_csv(scored_path)


def answer_pit_probability(
        scored_path: str | Path,
        driver_code: str,
        lap_number: int) -> str:
    """Return a simple chat-friendly answer for pit-stop probability.

    Args:
        scored_path: Path to a scored pit-window CSV containing pit_stop_proba.
        driver_code: Driver abbreviation (e.g., VER, HAM).
        lap_number: Lap number to query.
    """

    scored_path = Path(scored_path)
    if not scored_path.exists():
        return "No scored dataset available right now."

    df = _load_scored(scored_path)
    match = df[(df["driver_id"].str.upper() == driver_code.upper())
               & (df["lap_number"] == int(lap_number))]
    if match.empty:
        return "No probability found for that driver/lap."

    prob = float(match.iloc[0]["pit_stop_proba"])
    return f"Probabilidad de parada para {driver_code} en la vuelta {lap_number}: {
        prob:.2%}."


def lookup_pit_probability(
        scored_path: str | Path,
        driver_code: str,
        lap_number: int) -> Optional[float]:
    """Lightweight lookup for UI hooks (returns float or None)."""

    scored_path = Path(scored_path)
    if not scored_path.exists():
        return None

    df = _load_scored(scored_path)
    match = df[(df["driver_id"].str.upper() == driver_code.upper())
               & (df["lap_number"] == int(lap_number))]
    if match.empty:
        return None

    return float(match.iloc[0]["pit_stop_proba"])


__all__ = ["answer_pit_probability", "lookup_pit_probability"]
