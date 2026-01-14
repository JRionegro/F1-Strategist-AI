"""Schemas (contracts) for predictive AI datasets.

Option B target (MVP): Suggested pit window.

The goal of this module is to define stable dataset contracts so that:
- dataset building is reproducible
- training/inference use the same column set
- tests can enforce no-leakage and valid ranges
"""

from __future__ import annotations

from typing import Final, Optional

from pydantic import BaseModel, ConfigDict, Field


PIT_WINDOW_REQUIRED_COLUMNS: Final[tuple[str, ...]] = (
    "driver_id",
    "lap_number",
    "stint_lap",
    "compound",
    "last_lap_time_s",
    "rolling_lap_time_s",
    "gap_ahead_s",
    "gap_behind_s",
    "position",
    "pit_window_start_lap",
    "pit_window_end_lap",
    "pit_window_center_lap",
)


class PitWindowRow(BaseModel):
    """Single supervised row for pit window prediction.

    Notes:
        - Labels are optional because not every row has a future pit stop.
        - Labels, when present, must refer to a lap strictly in the future.
    """

    model_config = ConfigDict(extra="forbid")

    driver_id: str = Field(min_length=1)
    lap_number: int = Field(ge=1)

    compound: Optional[str] = None
    stint_lap: int = Field(ge=0)

    last_lap_time_s: Optional[float] = Field(default=None, gt=0)
    rolling_lap_time_s: Optional[float] = Field(default=None, gt=0)

    gap_ahead_s: Optional[float] = Field(default=None, ge=0)
    gap_behind_s: Optional[float] = Field(default=None, ge=0)

    position: Optional[int] = Field(default=None, ge=1)

    pit_window_start_lap: Optional[int] = Field(default=None, ge=1)
    pit_window_end_lap: Optional[int] = Field(default=None, ge=1)
    pit_window_center_lap: Optional[int] = Field(default=None, ge=1)

    def validate_label_ranges(self) -> None:
        """Validate label coherence.

        Raises:
            ValueError: if label fields are inconsistent.
        """
        if self.pit_window_center_lap is None:
            if any(
                value is not None
                for value in (
                    self.pit_window_start_lap,
                    self.pit_window_end_lap,
                )
            ):
                raise ValueError("If center label is None, start/end must also be None")
            return

        if self.pit_window_start_lap is None or self.pit_window_end_lap is None:
            raise ValueError("If center label is set, start and end must be set")

        if not (self.pit_window_start_lap <= self.pit_window_center_lap <= self.pit_window_end_lap):
            raise ValueError("pit window must include center lap")

        if self.pit_window_center_lap <= self.lap_number:
            raise ValueError("pit window center must be in the future")

        if self.pit_window_start_lap <= self.lap_number:
            raise ValueError("pit window start must be in the future")

        if self.pit_window_end_lap <= self.lap_number:
            raise ValueError("pit window end must be in the future")


class PitPolicyContext(BaseModel):
    """Cached pit-decision guidance loaded once per simulation from strategy.md."""

    model_config = ConfigDict(extra="forbid")

    pit_policy_notes: str = ""
    undercut_overcut_rules: str = ""
    tire_compound_rules: str = ""
    degradation_thresholds: str = ""
    safety_car_overrides: str = ""
    weather_overrides: str = ""
    fuel_energy_notes: str = ""
    source: Optional[str] = None  # relative path to strategy.md if present


class RaceStateRecord(BaseModel):
    """Minimal race state inputs allowed at inference time (simulation/live)."""

    model_config = ConfigDict(extra="forbid")

    driver_id: str = Field(min_length=1)
    lap_number: int = Field(ge=1)
    compound: Optional[str] = None
    stint_lap: int = Field(ge=0)
    gap_ahead_s: Optional[float] = Field(default=None, ge=0)
    gap_behind_s: Optional[float] = Field(default=None, ge=0)
    position: Optional[int] = Field(default=None, ge=1)
    safety_car_status: Optional[str] = Field(
        default=None,
        description="Track status flag (e.g., green, yellow, vsc, sc)",
    )
    weather_summary: Optional[str] = Field(
        default=None,
        description="Short text summary used for quick rule application",
    )
