"""Cache generation service for orchestrating OpenF1/FastF1 artifacts."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple, Union

import pandas as pd
import requests

from .cache_config import CacheConfig, DataType, DEFAULT_CACHE_CONFIG
from .cache_manager import CacheManager
from .fastf1_position_provider import FastF1PositionProvider
from .openf1_data_provider import OpenF1DataProvider

logger = logging.getLogger(__name__)


SessionCode = Optional[str]
ProgressCallback = Optional[Callable[[int, int, str], None]]
MeetingSelector = Union[int, str, None]


@dataclass(frozen=True)
class CacheArtifact:
    """Metadata describing a cacheable artifact."""

    key: str
    label: str
    level: str  # year | meeting | session | fastf1
    source: str  # openf1 | fastf1
    description: str
    data_type: Optional[DataType] = None
    method_name: Optional[str] = None
    requires_selection: bool = True


def _slugify(value: str) -> str:
    """Return filesystem-safe slug."""
    normalized = re.sub(r"[^a-z0-9]+", "_", value.lower())
    return normalized.strip("_") or "value"


class CacheGenerationService:
    """Build, regenerate, and inspect cache artifacts used by the dashboards."""

    SESSION_CODE_TO_NAME: Dict[str, str] = {
        "R": "Race",
        "RACE": "Race",
        "Q": "Qualifying",
        "QUALIFYING": "Qualifying",
        "S": "Sprint",
        "SPRINT": "Sprint",
        "SQ": "Sprint Qualifying",
        "SPRINT QUALIFYING": "Sprint Qualifying",
        "SS": "Sprint Shootout",
        "SPRINT SHOOTOUT": "Sprint Shootout",
        "P1": "Practice 1",
        "FP1": "Practice 1",
        "P2": "Practice 2",
        "FP2": "Practice 2",
        "P3": "Practice 3",
        "FP3": "Practice 3",
    }

    SESSION_CODE_TO_FASTF1: Dict[str, str] = {
        "R": "R",
        "RACE": "R",
        "Q": "Q",
        "QUALIFYING": "Q",
        "S": "S",
        "SPRINT": "S",
        "SQ": "SQ",
        "SPRINT QUALIFYING": "SQ",
        "SS": "SQ",
        "SPRINT SHOOTOUT": "SQ",
        "P1": "FP1",
        "FP1": "FP1",
        "P2": "FP2",
        "FP2": "FP2",
        "P3": "FP3",
        "FP3": "FP3",
    }

    _CANONICAL_CODES = {"R", "Q", "S", "SQ", "SS", "P1", "P2", "P3"}

    SESSION_ALIAS_TO_CODE: Dict[str, str] = {
        "RACE": "R",
        "GRAND PRIX": "R",
        "MAIN RACE": "R",
        "FEATURE": "R",
        "SPRINT": "S",
        "SPRINT RACE": "S",
        "S": "S",
        "SPRINT QUALIFYING": "SQ",
        "SQ": "SQ",
        "SPRINT SHOOTOUT": "SS",
        "SS": "SS",
        "QUALIFYING": "Q",
        "Q": "Q",
        "PRACTICE 1": "P1",
        "FP1": "P1",
        "P1": "P1",
        "DAY 1": "P1",
        "PRACTICE 2": "P2",
        "FP2": "P2",
        "P2": "P2",
        "DAY 2": "P2",
        "PRACTICE 3": "P3",
        "FP3": "P3",
        "P3": "P3",
        "DAY 3": "P3",
    }

    _CANONICAL_CODES = {"R", "Q", "S", "SQ", "SS", "P1", "P2", "P3"}

    SESSION_ALIAS_TO_CODE: Dict[str, str] = {
        "RACE": "R",
        "GRAND PRIX": "R",
        "MAIN RACE": "R",
        "FEATURE": "R",
        "SPRINT": "S",
        "SPRINT RACE": "S",
        "S": "S",
        "SPRINT QUALIFYING": "SQ",
        "SPRINT SHOOTOUT": "SS",
        "SQ": "SQ",
        "SS": "SS",
        "QUALIFYING": "Q",
        "Q": "Q",
        "PRACTICE 1": "P1",
        "FP1": "P1",
        "P1": "P1",
        "DAY 1": "P1",
        "PRACTICE 2": "P2",
        "FP2": "P2",
        "P2": "P2",
        "DAY 2": "P2",
        "PRACTICE 3": "P3",
        "FP3": "P3",
        "P3": "P3",
        "DAY 3": "P3",
    }

    ARTIFACTS: Sequence[CacheArtifact] = (
        CacheArtifact(
            key="calendar",
            label="Season calendar",
            level="year",
            source="openf1",
            description="Meeting list for the selected season",
            data_type=DataType.CALENDAR,
            method_name="get_meetings",
            requires_selection=False,
        ),
        CacheArtifact(
            key="session_list",
            label="Session catalog",
            level="meeting",
            source="openf1",
            description="OpenF1 sessions metadata for the selected meeting",
            data_type=DataType.SESSION_LIST,
            requires_selection=True,
        ),
        CacheArtifact(
            key="drivers",
            label="Drivers",
            level="session",
            source="openf1",
            description="Driver roster with team colors",
            data_type=DataType.DRIVER_INFO,
            method_name="get_drivers",
        ),
        CacheArtifact(
            key="positions",
            label="Positions",
            level="session",
            source="openf1",
            description="Leaderboard position stream",
            data_type=DataType.POSITIONS,
            method_name="get_positions",
        ),
        CacheArtifact(
            key="intervals",
            label="Intervals",
            level="session",
            source="openf1",
            description="Gap and interval data",
            data_type=DataType.INTERVALS,
            method_name="get_intervals",
        ),
        CacheArtifact(
            key="stints",
            label="Tire stints",
            level="session",
            source="openf1",
            description="Stint and compound allocation",
            data_type=DataType.TIRE_STRATEGY,
            method_name="get_stints",
        ),
        CacheArtifact(
            key="laps",
            label="Lap times",
            level="session",
            source="openf1",
            description="Lap timing dataset",
            data_type=DataType.LAP_TIMES,
            method_name="get_laps",
        ),
        CacheArtifact(
            key="pit_stops",
            label="Pit stops",
            level="session",
            source="openf1",
            description="Pit stop log",
            data_type=DataType.PIT_STOPS,
            method_name="get_pit_stops",
        ),
        CacheArtifact(
            key="weather",
            label="Weather",
            level="session",
            source="openf1",
            description="Weather telemetry",
            data_type=DataType.WEATHER,
            method_name="get_weather",
        ),
        CacheArtifact(
            key="race_control",
            label="Race control",
            level="session",
            source="openf1",
            description="Race control messages",
            data_type=DataType.RACE_CONTROL,
            method_name="get_race_control_messages",
        ),
        CacheArtifact(
            key="car_data",
            label="Car telemetry",
            level="session",
            source="openf1",
            description="Per-sample car telemetry (speed, throttle, DRS)",
            data_type=DataType.CAR_DATA,
            method_name="get_car_data",
        ),
        CacheArtifact(
            key="track_map",
            label="Track map positions",
            level="fastf1",
            source="fastf1",
            description="FastF1 preprocessed driver positions used by the track map",
            data_type=None,
            method_name=None,
        ),
    )

    def __init__(
        self,
        openf1_provider: Optional[OpenF1DataProvider] = None,
        fastf1_provider: Optional[FastF1PositionProvider] = None,
        cache_config: CacheConfig = DEFAULT_CACHE_CONFIG,
    ) -> None:
        self.openf1_provider = openf1_provider or OpenF1DataProvider()
        self.fastf1_provider = fastf1_provider or FastF1PositionProvider(
            cache_dir=str(cache_config.cache_dir)
        )
        self.cache_config = cache_config
        self.cache_manager = CacheManager(config=cache_config)
        self._season_meeting_cache: Dict[int, List[int]] = {}
        self._artifact_map: Dict[str, CacheArtifact] = {
            artifact.key: artifact for artifact in self.ARTIFACTS
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_artifacts(self) -> Sequence[CacheArtifact]:
        """Return available cache artifact definitions."""
        return self.ARTIFACTS

    def describe_status(
        self,
        year: int,
        meeting_key: MeetingSelector,
        session_code: SessionCode,
        selected_keys: Iterable[str],
    ) -> Dict[str, Any]:
        """Return status summary for requested cache artifacts."""
        artifacts = self._get_artifacts(selected_keys)
        meeting_keys = self._resolve_meeting_key_set(year, meeting_key, artifacts)
        if len(meeting_keys) > 1:
            return {
                "entries": [],
                "total_size_bytes": 0,
                "total_size_mb": 0.0,
                "requested": len(artifacts),
                "existing": 0,
                "missing": len(artifacts),
                "multi_meeting": True,
                "meeting_count": len(meeting_keys),
            }

        resolved_meeting = next(iter(meeting_keys)) if meeting_keys else None

        session_info = self._maybe_resolve_session(year, resolved_meeting, session_code, artifacts)
        meeting_reference = session_info or self._maybe_resolve_meeting(year, resolved_meeting, artifacts)

        entries: List[Dict[str, Any]] = []
        total_size = 0

        for artifact in artifacts:
            path = self._resolve_output_path(
                year,
                resolved_meeting,
                session_code,
                artifact,
                session_info=session_info,
                meeting_reference=meeting_reference,
            )
            exists = path is not None and path.exists()
            path_size = 0
            path_string: Optional[str] = None
            if exists and path is not None:
                try:
                    path_size = path.stat().st_size
                except OSError:
                    path_size = 0
                else:
                    total_size += path_size
                path_string = str(path)
            elif path is not None:
                path_string = str(path)
            entries.append({
                "key": artifact.key,
                "label": artifact.label,
                "exists": exists,
                "size_bytes": path_size,
                "size_mb": round(path_size / (1024 * 1024), 3) if path_size else 0.0,
                "path": path_string,
            })

        return {
            "entries": entries,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 3) if total_size else 0.0,
            "requested": len(entries),
            "existing": sum(1 for entry in entries if entry["exists"]),
            "missing": sum(1 for entry in entries if not entry["exists"]),
        }

    def clear_caches(
        self,
        year: int,
        meeting_key: MeetingSelector,
        session_code: SessionCode,
        selected_keys: Iterable[str],
    ) -> List[Path]:
        """Delete the selected caches without regenerating."""
        artifacts = self._get_artifacts(selected_keys)
        targets = list(
            self._iter_artifact_targets(year, meeting_key, session_code, artifacts)
        )
        deleted: List[Path] = []
        for artifact, resolved_meeting, session_info, meeting_reference in targets:
            target = self._resolve_output_path(
                year,
                resolved_meeting,
                session_code,
                artifact,
                session_info=session_info,
                meeting_reference=meeting_reference,
            )
            if target and target.exists():
                try:
                    target.unlink()
                except IsADirectoryError:
                    # Remove directories created for session grouping
                    for item in sorted(target.glob("**/*"), reverse=True):
                        if item.is_file():
                            item.unlink()
                        elif item.is_dir():
                            item.rmdir()
                    target.rmdir()
                deleted.append(target)
                logger.info("Deleted cache artifact %s", target)
        return deleted

    def generate_caches(
        self,
        year: int,
        meeting_key: MeetingSelector,
        session_code: SessionCode,
        selected_keys: Iterable[str],
        progress_callback: ProgressCallback = None,
        *,
        skip_existing: bool = False,
    ) -> Dict[str, Any]:
        """Create or regenerate the selected caches."""
        artifacts = self._get_artifacts(selected_keys)
        targets = list(
            self._iter_artifact_targets(year, meeting_key, session_code, artifacts)
        )
        total = len(targets)
        if total == 0:
            return {"results": [], "total": 0}

        results: List[Dict[str, Any]] = []
        created_count = 0
        skipped_count = 0
        for index, (artifact, resolved_meeting, session_info, meeting_reference) in enumerate(targets, start=1):
            label = artifact.label
            if isinstance(meeting_reference, dict):
                meeting_name = (
                    meeting_reference.get("meeting_name")
                    or meeting_reference.get("official_name")
                    or meeting_reference.get("location")
                    or meeting_reference.get("country_name")
                )
                if meeting_name:
                    label = f"{label} · {meeting_name}"  # noqa: PLC1901
            if progress_callback:
                progress_callback(index - 1, total, f"Preparing {label}")

            output_path = self._resolve_output_path(
                year,
                resolved_meeting,
                session_code,
                artifact,
                session_info=session_info,
                meeting_reference=meeting_reference,
            )
            if output_path is None:
                logger.warning(
                    "Skipping artifact %s (insufficient context)",
                    artifact.key,
                )
                continue

            if output_path.exists():
                if skip_existing:
                    if progress_callback:
                        progress_callback(index, total, f"Skipped {label} (already exists)")
                    results.append({
                        "artifact": artifact.key,
                        "status": "skipped",
                        "path": str(output_path),
                    })
                    skipped_count += 1
                    continue
                if output_path.is_file():
                    output_path.unlink()
                else:
                    for item in sorted(output_path.glob("**/*"), reverse=True):
                        if item.is_file():
                            item.unlink()
                        elif item.is_dir():
                            item.rmdir()
                    output_path.rmdir()

            if artifact.source == "openf1":
                generator_result = self._generate_openf1_artifact(
                    artifact,
                    year=year,
                    meeting_key=resolved_meeting,
                    session_code=session_code,
                    session_info=session_info,
                    meeting_reference=meeting_reference,
                    output_path=output_path,
                )
            else:
                generator_result = self._generate_fastf1_artifact(
                    artifact,
                    year=year,
                    session_code=session_code,
                    session_info=session_info,
                    output_path=output_path,
                )

            payload: Dict[str, Any]
            if isinstance(generator_result, dict):
                payload = dict(generator_result)
            else:
                payload = {"result": generator_result}
            payload.setdefault("artifact", artifact.key)
            payload.setdefault("path", str(output_path) if output_path else None)
            payload["status"] = payload.get("status", "created")
            results.append(payload)
            created_count += 1
            if progress_callback:
                progress_callback(index, total, f"Completed {label}")

        return {
            "results": results,
            "total": total,
            "created": created_count,
            "skipped": skipped_count,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_artifacts(self, selected_keys: Iterable[str]) -> List[CacheArtifact]:
        artifacts: List[CacheArtifact] = []
        for key in selected_keys:
            artifact = self._artifact_map.get(key)
            if artifact is not None:
                artifacts.append(artifact)
        return artifacts

    def _resolve_meeting_key_set(
        self,
        year: int,
        meeting_selector: MeetingSelector,
        artifacts: Sequence[CacheArtifact],
    ) -> Set[int]:
        meeting_keys: Set[int] = set()
        for artifact in artifacts:
            meeting_keys.update(
                self._resolve_meeting_keys_for_artifact(year, meeting_selector, artifact)
            )
        return meeting_keys

    def _resolve_meeting_keys_for_artifact(
        self,
        year: int,
        meeting_selector: MeetingSelector,
        artifact: CacheArtifact,
    ) -> List[int]:
        if artifact.level == "year":
            return []

        meeting_keys = self._select_meetings(year, meeting_selector)
        if artifact.level in {"meeting", "session", "fastf1"} and not meeting_keys:
            raise ValueError("No meetings found for requested season")
        return meeting_keys

    def _select_meetings(self, year: int, meeting_selector: MeetingSelector) -> List[int]:
        if meeting_selector is None:
            return self._list_meeting_keys(year)

        if isinstance(meeting_selector, str):
            selector_upper = meeting_selector.strip().upper()
            if selector_upper in {"ALL", "*", "YEAR"}:
                return self._list_meeting_keys(year)
            try:
                return [int(float(meeting_selector))]
            except (TypeError, ValueError):
                raise ValueError(f"Invalid meeting selector: {meeting_selector}") from None

        try:
            return [int(meeting_selector)] if meeting_selector is not None else self._list_meeting_keys(year)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid meeting selector: {meeting_selector}") from None

    def _list_meeting_keys(self, year: int) -> List[int]:
        if year in self._season_meeting_cache:
            return self._season_meeting_cache[year]

        keys: List[int] = []
        try:
            meetings_payload: Any = self.openf1_provider.get_meetings(year=year)
        except AttributeError:
            meetings_payload = None

        if isinstance(meetings_payload, pd.DataFrame):
            column_candidates = ["MeetingKey", "meeting_key"]
            for column in column_candidates:
                if column in meetings_payload.columns:
                    raw_values = meetings_payload[column].dropna().unique().tolist()
                    for value in raw_values:
                        try:
                            keys.append(int(value))
                        except (TypeError, ValueError):
                            continue
                    break
        elif isinstance(meetings_payload, (list, tuple)):
            for entry in meetings_payload:
                if isinstance(entry, dict):
                    value = entry.get("MeetingKey") or entry.get("meeting_key")
                    if value is None:
                        continue
                    try:
                        keys.append(int(value))
                    except (TypeError, ValueError):
                        continue

        keys = sorted(set(keys))
        self._season_meeting_cache[year] = keys
        if not keys:
            logger.warning("No meetings found for year %s when building cache plan", year)
        return keys

    def _iter_artifact_targets(
        self,
        year: int,
        meeting_selector: MeetingSelector,
        session_code: SessionCode,
        artifacts: Sequence[CacheArtifact],
    ) -> Iterable[Tuple[CacheArtifact, Optional[int], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]]:
        for artifact in artifacts:
            meeting_keys = self._resolve_meeting_keys_for_artifact(year, meeting_selector, artifact)
            if not meeting_keys:
                session_info = self._maybe_resolve_session(year, None, session_code, [artifact])
                meeting_reference = session_info or self._maybe_resolve_meeting(year, None, [artifact])
                if artifact.level in {"session", "fastf1"} and session_info is None:
                    logger.info(
                        "Skipping artifact %s for meeting selector %s (session %s unavailable)",
                        artifact.key,
                        meeting_selector,
                        session_code or "",
                    )
                    continue
                yield artifact, None, session_info, meeting_reference
                continue

            for resolved_meeting in meeting_keys:
                session_info = self._maybe_resolve_session(year, resolved_meeting, session_code, [artifact])
                meeting_reference = session_info or self._maybe_resolve_meeting(year, resolved_meeting, [artifact])
                if artifact.level in {"session", "fastf1"} and session_info is None:
                    logger.info(
                        "Skipping artifact %s for meeting %s (session %s unavailable)",
                        artifact.key,
                        resolved_meeting,
                        session_code or "",
                    )
                    continue
                yield artifact, resolved_meeting, session_info, meeting_reference

    def _maybe_resolve_meeting(
        self,
        year: int,
        meeting_key: Optional[int],
        artifacts: Sequence[CacheArtifact],
    ) -> Optional[Dict[str, Any]]:
        needs_meeting = any(
            artifact.level in {"meeting", "session", "fastf1"}
            for artifact in artifacts
        )
        if not needs_meeting or meeting_key is None:
            return None

        sessions = self._get_meeting_sessions(year, meeting_key)
        if not sessions:
            raise ValueError("No sessions found for requested meeting")
        sessions.sort(key=lambda payload: payload.get("date_start", ""))
        return sessions[0]

    def _maybe_resolve_session(
        self,
        year: int,
        meeting_key: Optional[int],
        session_code: SessionCode,
        artifacts: Sequence[CacheArtifact],
    ) -> Optional[Dict[str, Any]]:
        needs_session = any(
            artifact.level in {"session", "fastf1"}
            for artifact in artifacts
        )
        if not needs_session:
            return None
        if meeting_key is None:
            raise ValueError("Meeting selection required to build session caches")
        if not session_code:
            raise ValueError("Session selection required to build session caches")

        sessions = self._get_meeting_sessions(year, meeting_key)
        if not sessions:
            raise ValueError("No sessions found for requested meeting")

        target_code = self._canonical_session_code(session_code) or "R"

        def extract_codes(payload: Dict[str, Any]) -> List[str]:
            raw_values = [
                payload.get("session_type"),
                payload.get("session_code"),
                payload.get("session_name"),
            ]
            codes = [
                code
                for code in (
                    self._canonical_session_code(raw_value)
                    for raw_value in raw_values
                )
                if code is not None
            ]
            return codes

        sessions.sort(key=lambda payload: payload.get("date_start", ""))
        exact_matches: List[Dict[str, Any]] = []
        race_candidates: List[Dict[str, Any]] = []
        available_codes: Set[str] = set()

        for payload in sessions:
            codes = extract_codes(payload)
            if codes:
                available_codes.update(codes)
            if target_code in codes:
                exact_matches.append(payload)
            elif "R" in codes:
                race_candidates.append(payload)

        if exact_matches:
            return exact_matches[-1]

        if target_code == "R" and race_candidates:
            logger.debug(
                "Falling back to race candidate for meeting %s (target=%s)",
                meeting_key,
                target_code,
            )
            return race_candidates[-1]

        if target_code == "R" and "R" not in available_codes:
            logger.info(
                "Skipping meeting %s for session %s; available codes: %s",
                meeting_key,
                target_code,
                ", ".join(sorted(available_codes)) if available_codes else "none",
            )
            return None

        logger.warning(
            "Could not match session code '%s' for meeting %s; returning last session.",
            target_code,
            meeting_key,
        )
        return sessions[-1]

    def _get_meeting_sessions(
        self,
        year: int,
        meeting_key: int,
    ) -> List[Dict[str, Any]]:
        params = {"year": year, "meeting_key": meeting_key}
        sessions = self.openf1_provider._request("sessions", params)
        if not sessions:
            logger.warning("No OpenF1 sessions for meeting %s", meeting_key)
            return []
        return sessions

    def _resolve_output_path(
        self,
        year: int,
        meeting_key: Optional[int],
        session_code: SessionCode,
        artifact: CacheArtifact,
        *,
        session_info: Optional[Dict[str, Any]],
        meeting_reference: Optional[Dict[str, Any]],
    ) -> Optional[Path]:
        if artifact.level == "year":
            base_dir = self.cache_config.processed_dir / artifact.key
            base_dir.mkdir(parents=True, exist_ok=True)
            extension = self.cache_config.get_file_extension()
            if artifact.data_type is None:
                raise ValueError("Year-level artifact requires a data type")
            filename = f"{year}_{artifact.data_type.value}{extension}"
            return base_dir / filename

        if artifact.level == "meeting":
            if meeting_reference is None:
                return None
            slug = self._build_meeting_slug(meeting_reference)
            base_dir = self.cache_config.processed_dir / artifact.key / str(year)
            base_dir.mkdir(parents=True, exist_ok=True)
            extension = self.cache_config.get_file_extension()
            filename = f"{slug}{extension}"
            return base_dir / filename

        if artifact.source == "openf1":
            if session_info is None:
                return None
            race_name = self._build_race_cache_name(session_info, session_code)
            assert artifact.data_type is not None
            return self.cache_manager._get_cache_file_path(
                int(session_info.get("year", year)),
                race_name,
                artifact.data_type,
            )

        if artifact.source == "fastf1":
            if session_info is None:
                return None
            translation = self.fastf1_provider.translate_openf1_session(session_info)
            translated_year = int(translation.get("year") or year)
            country = str(
                translation.get("round")
                or session_info.get("country_name")
                or session_info.get("meeting_name")
                or session_info.get("location")
                or "Unknown"
            )
            identifier = self._map_to_fastf1_code(session_code)
            return self.fastf1_provider._get_positions_cache_path(
                translated_year,
                country,
                identifier,
            )

        return None

    # ------------------------------------------------------------------
    # Normalization helpers
    # ------------------------------------------------------------------

    @classmethod
    def _canonical_session_code(cls, raw_value: Any) -> Optional[str]:
        if raw_value is None:
            return None
        text = str(raw_value).strip().upper()
        if not text:
            return None
        if text in cls.SESSION_CODE_TO_NAME and text in cls._CANONICAL_CODES:
            return text
        alias = cls.SESSION_ALIAS_TO_CODE.get(text)
        if alias is not None:
            return alias
        if text in cls.SESSION_CODE_TO_NAME:
            mapped = cls.SESSION_ALIAS_TO_CODE.get(cls.SESSION_CODE_TO_NAME[text].upper())
            if mapped is not None:
                return mapped
            return text if text in cls._CANONICAL_CODES else None
        if "PRACTICE" in text:
            if "1" in text:
                return "P1"
            if "2" in text:
                return "P2"
            if "3" in text:
                return "P3"
            return "P1"
        if "QUALIFY" in text:
            if "SHOOTOUT" in text:
                return "SS"
            if "SPRINT" in text:
                return "SQ"
            return "Q"
        if "SPRINT" in text:
            return "S"
        if "RACE" in text:
            return "R"
        if "DAY 1" in text:
            return "P1"
        if "DAY 2" in text:
            return "P2"
        if "DAY 3" in text:
            return "P3"
        if text in cls._CANONICAL_CODES:
            return text
        return None

    def _build_race_cache_name(
        self,
        session_info: Dict[str, Any],
        session_code: SessionCode,
    ) -> str:
        slug = self._build_meeting_slug(session_info)
        segment = self._session_segment(session_code)
        return f"{slug}{segment}" if segment else slug

    def _build_meeting_slug(self, payload: Dict[str, Any]) -> str:
        date_raw = payload.get("date_start") or payload.get("meeting_start")
        try:
            parsed = pd.to_datetime(date_raw, format="mixed") if date_raw else None
        except Exception:  # noqa: BLE001
            parsed = None
        if parsed is not None:
            date_str = parsed.date().isoformat()
        else:
            year_val = int(payload.get("year") or 0)
            date_str = str(year_val) if year_val else "event"

        meeting_name = (
            payload.get("meeting_name")
            or payload.get("official_name")
            or payload.get("location")
            or payload.get("country_name")
            or "grand_prix"
        )
        return f"{date_str}_{_slugify(str(meeting_name))}"

    def _session_segment(self, session_code: SessionCode) -> str:
        if not session_code:
            return ""
        normalized = str(session_code).lower()
        if normalized in {"r", "race"}:
            return ""
        return normalized

    def _map_to_fastf1_code(self, session_code: SessionCode) -> str:
        if not session_code:
            return "R"
        return self.SESSION_CODE_TO_FASTF1.get(str(session_code).upper(), "R")

    def _generate_openf1_artifact(
        self,
        artifact: CacheArtifact,
        *,
        year: int,
        meeting_key: Optional[int],
        session_code: SessionCode,
        session_info: Optional[Dict[str, Any]],
        meeting_reference: Optional[Dict[str, Any]],
        output_path: Path,
    ) -> Dict[str, Any]:
        method_name = artifact.method_name
        if method_name is None:
            raise ValueError(f"Artifact {artifact.key} missing method binding")

        if artifact.level == "year":
            data = getattr(self.openf1_provider, method_name)(year=year)
            row_count = self._persist_dataframe(data, output_path)
            return {"key": artifact.key, "path": str(output_path), "rows": row_count}

        if artifact.level == "meeting":
            if meeting_key is None:
                raise ValueError("Meeting selection required for meeting-level cache")
            sessions = self._get_meeting_sessions(year, meeting_key)
            dataframe = pd.DataFrame(sessions)
            row_count = self._persist_dataframe(dataframe, output_path)
            return {"key": artifact.key, "path": str(output_path), "rows": row_count}

        if session_info is None:
            raise ValueError("Session info required for session-level cache")

        session_key = session_info.get("session_key")
        if session_key is None:
            raise ValueError("OpenF1 session key missing; cannot build cache")

        fetcher = getattr(self.openf1_provider, method_name)
        try:
            data_frame = fetcher(session_key=session_key)
        except requests.HTTPError as http_err:
            status_code = http_err.response.status_code if http_err.response is not None else None
            if status_code in {404, 422}:
                logger.warning(
                    "OpenF1 returned %s for %s (session_key=%s); proceeding with empty dataset.",
                    status_code,
                    method_name,
                    session_key,
                )
                data_frame = pd.DataFrame()
            else:
                raise
        except requests.RequestException as error:
            raise RuntimeError(f"Failed to fetch {method_name} for session {session_key}: {error}") from error

        row_count = self._persist_dataframe(data_frame, output_path)
        return {"key": artifact.key, "path": str(output_path), "rows": row_count}

    def _generate_fastf1_artifact(
        self,
        artifact: CacheArtifact,
        *,
        year: int,
        session_code: SessionCode,
        session_info: Optional[Dict[str, Any]],
        output_path: Path,
    ) -> Dict[str, Any]:
        if session_info is None:
            raise ValueError("FastF1 artifacts require session information")

        identifier = self._map_to_fastf1_code(session_code)
        translation = self.fastf1_provider.translate_openf1_session(session_info)
        translated_year = int(translation.get("year") or session_info.get("year") or year)
        country = str(
            translation.get("round")
            or session_info.get("country_name")
            or session_info.get("meeting_name")
            or session_info.get("location")
            or "Unknown"
        )

        success = self.fastf1_provider.load_session(
            translated_year,
            country,
            identifier,
        )
        if not success:
            raise RuntimeError(
                f"FastF1 session load failed for {translated_year} {country} {identifier}"
            )
        # The FastF1 provider saves the cache as a side effect; nothing else to write.
        file_size = output_path.stat().st_size if output_path.exists() else 0
        return {
            "key": artifact.key,
            "path": str(output_path),
            "rows": None,
            "size_bytes": file_size,
        }

    def _persist_dataframe(self, data: Any, path: Path) -> int:
        path.parent.mkdir(parents=True, exist_ok=True)
        if data is None:
            df = pd.DataFrame()
        elif isinstance(data, pd.DataFrame):
            df = data
        else:
            df = pd.DataFrame(data)

        if df.empty:
            # Persist empty frame for schema parity.
            if self.cache_config.use_parquet:
                df.to_parquet(path, index=False)
            else:
                df.to_csv(path, index=False)
            return 0

        if self.cache_config.use_parquet:
            df_to_write = df.copy()
            object_columns = [col for col in df_to_write.columns if df_to_write[col].dtype == object]
            for column in object_columns:
                df_to_write[column] = df_to_write[column].astype("string")

            df_to_write.to_parquet(
                path,
                index=False,
                compression=self.cache_config.compression,
            )
        else:
            df.to_csv(path, index=False)
        return int(df.shape[0])


__all__ = ["CacheGenerationService", "CacheArtifact"]
