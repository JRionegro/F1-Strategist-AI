"""Default tire compound thresholds with optional overrides."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Dict, Mapping, Optional

logger = logging.getLogger(__name__)


TireWindow = Dict[str, int]


DEFAULT_TIRE_WINDOWS: Dict[str, TireWindow] = {
    "SOFT": {"min": 8, "optimal": 12, "max": 18},
    "MEDIUM": {"min": 15, "optimal": 22, "max": 30},
    "HARD": {"min": 25, "optimal": 35, "max": 45},
    "INTERMEDIATE": {"min": 10, "optimal": 20, "max": 35},
    "WET": {"min": 15, "optimal": 30, "max": 50},
}


def resolve_tire_windows(
    overrides: Mapping[str, Mapping[str, int]] | None
) -> Dict[str, TireWindow]:
    """Merge optional overrides into default tire windows.

    Args:
        overrides: Mapping of compound -> window values. Missing keys
            fall back to defaults.

    Returns:
        Merged dictionary with normalized compound keys.
    """

    resolved: Dict[str, TireWindow] = {compound: window.copy(
    ) for compound, window in DEFAULT_TIRE_WINDOWS.items()}

    if not overrides:
        return resolved

    for compound, window in overrides.items():
        key = str(compound).upper()
        try:
            mn = int(window.get("min", 0))
            opt = int(window.get("optimal", 0))
            mx = int(window.get("max", 0))
        except (TypeError, ValueError):
            logger.warning(
                "Skipping non-numeric tire window override for %s", key
            )
            continue
        if not (5 <= mn < opt < mx <= 60):
            logger.warning(
                "Ignoring implausible tire window override for %s: "
                "min=%d optimal=%d max=%d (using defaults)",
                key, mn, opt, mx,
            )
            continue
        if key not in resolved:
            resolved[key] = {}
        resolved[key]["min"] = mn
        resolved[key]["optimal"] = opt
        resolved[key]["max"] = mx

    return resolved


def extract_tire_windows_from_text(text: str) -> Dict[str, TireWindow]:
    """Extract tire window overrides from free-form strategy text.

    This parser scans each line for compound names and uses the first three
    integers as min/optimal/max in that order.
    """

    overrides: Dict[str, TireWindow] = {}
    compounds = ["SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"]

    for line in text.splitlines():
        upper = line.upper()
        for compound in compounds:
            if compound not in upper:
                continue
            numbers = [int(x) for x in re.findall(r"\d+", line)]
            if len(numbers) < 3:
                continue
            overrides[compound] = {
                "min": numbers[0],
                "optimal": numbers[1],
                "max": numbers[2],
            }
    return overrides


def load_tire_window_overrides_from_path(
    path: str | Path,
) -> Optional[Dict[str, TireWindow]]:
    """Load tire window overrides from a strategy document path.

    Returns None if the file is missing or no overrides are detected.
    """

    path = Path(path)
    if not path.exists():
        return None

    content = path.read_text(encoding="utf-8", errors="ignore")
    overrides = extract_tire_windows_from_text(content)
    return overrides or None


def ai_extract_tire_windows(
    content: str,
    api_key: str,
    model: str,
) -> Optional[Dict[str, TireWindow]]:
    """Use Gemini to extract tire window overrides from strategy text.

    Sends the strategy document to Gemini and parses the JSON response.
    Returns None if the google-genai package is unavailable, the API call
    fails, or no valid windows can be extracted.

    Args:
        content: Full text of the strategy document.
        api_key: Google API key.
        model: Gemini model name (e.g. ``gemini-2.5-flash``).

    Returns:
        Dict mapping compound names to min/optimal/max dicts, or None.
    """
    try:
        from google import genai  # type: ignore  # optional dependency
        from google.genai import types  # type: ignore
    except ImportError:
        logger.debug("google-genai not available; skipping AI tire extraction")
        return None

    prompt = (
        "You are an F1 strategy analyst. "
        "Extract tire stint length constraints from the strategy document below. "
        "Return ONLY valid JSON with this exact structure "
        "(include only compounds present in the document):\n"
        '{"SOFT": {"min": 8, "optimal": 16, "max": 22}, '
        '"MEDIUM": {"min": 10, "optimal": 21, "max": 25}, '
        '"HARD": {"min": 18, "optimal": 30, "max": 40}}\n\n'
        "Rules:\n"
        "- min: earliest safe lap to pit (tire still has grip)\n"
        "- optimal: ideal lap range center for best performance\n"
        "- max: absolute maximum laps before severe degradation\n"
        "- If the document states 'max X laps on same wheels', "
        "use X as max for ALL compounds.\n"
        "- Values must satisfy: 1 <= min < optimal < max <= 60\n"
        "- Do NOT include any explanation, markdown, or code fences.\n\n"
        f"Strategy document:\n{content[:4000]}"
    )

    try:
        client = genai.Client(api_key=api_key)
        cfg = types.GenerateContentConfig(
            temperature=0.0,
            max_output_tokens=512,
        )
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=cfg,
            # Limit blocking time in the session-load callback to 10 s
            timeout=10.0,
        )
        text = (response.text or "").strip()
        # Strip markdown code fences if the model adds them
        text = re.sub(r"^```[a-z]*\n?", "", text).rstrip("`").strip()

        data = json.loads(text)
        result: Dict[str, TireWindow] = {}
        for compound, window in data.items():
            key = str(compound).upper()
            try:
                mn = int(window["min"])
                opt = int(window["optimal"])
                mx = int(window["max"])
            except (KeyError, TypeError, ValueError):
                continue
            # Physically: a tire cannot possibly be "due" in fewer than 5 laps
            if 5 <= mn < opt < mx <= 60:
                result[key] = {"min": mn, "optimal": opt, "max": mx}
            else:
                logger.warning(
                    "AI returned invalid window for %s: "
                    "min=%d optimal=%d max=%d — rejected",
                    key, mn, opt, mx,
                )

        if result:
            logger.info("AI extracted tire windows: %s", result)
            return result

        logger.warning(
            "AI response contained no valid tire windows; falling back"
        )
        return None

    except Exception as exc:
        logger.warning("AI tire window extraction failed: %s", exc)
        return None


__all__ = [
    "DEFAULT_TIRE_WINDOWS",
    "resolve_tire_windows",
    "extract_tire_windows_from_text",
    "load_tire_window_overrides_from_path",
    "ai_extract_tire_windows",
]
