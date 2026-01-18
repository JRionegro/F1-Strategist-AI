"""Tests for cache generation service covering creation, regeneration, and deletion."""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterator, List, cast

import pandas as pd
import pytest

from src.data.cache_config import CacheConfig
from src.data.cache_generation import CacheGenerationService
from src.data.fastf1_position_provider import FastF1PositionProvider
from src.data.openf1_data_provider import OpenF1DataProvider


class StubOpenF1Provider:
    """Minimal OpenF1 provider stub returning deterministic data sets."""

    def __init__(self) -> None:
        self._session_key = 2025001
        self._meeting_key = 42
        self._meeting_payload = {
            "meeting_key": self._meeting_key,
            "meeting_name": "Test Grand Prix",
            "date_start": "2025-05-10T14:00:00Z",
            "year": 2025,
            "location": "Test City",
            "country_name": "Testland",
        }

    # --- Core request helpers -------------------------------------------------
    def _request(self, endpoint: str, params: Dict) -> List[Dict]:  # noqa: D401
        """Return deterministic payloads for the sessions endpoint."""
        if endpoint != "sessions":
            return []
        return [
            {
                **self._meeting_payload,
                "session_key": self._session_key,
                "session_name": "Race",
                "date_start": "2025-05-11T15:00:00Z",
            },
            {
                **self._meeting_payload,
                "session_key": self._session_key + 1,
                "session_name": "Qualifying",
                "date_start": "2025-05-10T18:00:00Z",
            },
        ]

    def get_meetings(self, year: int):  # noqa: D401
        """Return a one-row DataFrame with meeting metadata."""
        if year != 2025:
            return pd.DataFrame()
        return pd.DataFrame([{
            "MeetingKey": self._meeting_key,
            "MeetingName": self._meeting_payload["meeting_name"],
            "StartDate": pd.to_datetime(self._meeting_payload["date_start"]),
            "Location": self._meeting_payload["location"],
            "Country": self._meeting_payload["country_name"],
            "Year": year,
        }])

    # --- Artifact methods -----------------------------------------------------
    def get_drivers(self, session_key: int):
        data = {
            "DriverNumber": [1, 11],
            "Abbreviation": ["AAA", "BBB"],
            "TeamName": ["Alpha", "Beta"],
        }
        return pd.DataFrame(data) if session_key else pd.DataFrame()

    def get_positions(self, session_key: int):
        data = {
            "DriverNumber": [1, 11],
            "Position": [1, 2],
            "Timestamp": pd.to_datetime([
                "2025-05-11T15:01:00Z",
                "2025-05-11T15:01:00Z",
            ]),
        }
        return pd.DataFrame(data) if session_key else pd.DataFrame()

    def get_intervals(self, session_key: int):
        data = {
            "DriverNumber": [1, 11],
            "GapToLeader": [0.0, 1.234],
            "Interval": [0.0, 1.234],
            "Timestamp": pd.to_datetime([
                "2025-05-11T15:01:00Z",
                "2025-05-11T15:01:00Z",
            ]),
        }
        return pd.DataFrame(data) if session_key else pd.DataFrame()

    def get_stints(self, session_key: int):
        data = {
            "DriverNumber": [1, 11],
            "StintStart": [1, 1],
            "StintEnd": [15, 12],
            "Compound": ["SOFT", "MEDIUM"],
        }
        return pd.DataFrame(data) if session_key else pd.DataFrame()

    def get_laps(self, session_key: int):
        data = {
            "DriverNumber": [1, 11],
            "LapNumber": [1, 1],
            "LapTime_seconds": [95.123, 95.455],
        }
        return pd.DataFrame(data) if session_key else pd.DataFrame()

    def get_pit_stops(self, session_key: int):
        data = {
            "DriverNumber": [11],
            "Lap": [12],
            "PitDuration": [25.5],
        }
        return pd.DataFrame(data) if session_key else pd.DataFrame()

    def get_weather(self, session_key: int):
        data = {
            "Time": pd.to_datetime(["2025-05-11T15:00:00Z"]),
            "AirTemp": [28.5],
            "TrackTemp": [42.2],
        }
        return pd.DataFrame(data) if session_key else pd.DataFrame()

    def get_race_control_messages(self, session_key: int):
        data = {
            "Time": pd.to_datetime(["2025-05-11T15:05:00Z"]),
            "Category": ["FLAG"],
            "Message": ["GREEN"],
        }
        return pd.DataFrame(data) if session_key else pd.DataFrame()

    def get_car_data(self, session_key: int):
        data = {
            "DriverNumber": [1, 1, 11, 11],
            "Timestamp": pd.to_datetime([
                "2025-05-11T15:00:01Z",
                "2025-05-11T15:00:02Z",
                "2025-05-11T15:00:01Z",
                "2025-05-11T15:00:02Z",
            ]),
            "Speed": [300, 305, 298, 301],
        }
        return pd.DataFrame(data) if session_key else pd.DataFrame()


class FakeFastF1Provider:
    """FastF1 stub that writes deterministic pickle payloads."""

    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def translate_openf1_session(self, session_payload: Dict[str, Any]):  # type: ignore[override]
        year = session_payload.get("year", 2025)
        country = session_payload.get("country_name") or session_payload.get("meeting_name")
        return {"year": year, "round": country, "identifier": "R"}

    def _get_positions_cache_path(self, year: int, country: str, session_type: str):
        safe_country = country.replace(" ", "_")
        path = self.cache_dir / str(year) / f"{safe_country}_{session_type}_positions.pkl"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def load_session(self, year: int, country: str, session_type: str) -> bool:
        path = self._get_positions_cache_path(year, country, session_type)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"stub")
        return True


@pytest.fixture()
def temp_cache_config() -> Iterator[CacheConfig]:
    base_dir = Path(tempfile.mkdtemp())
    config = CacheConfig(
        base_dir=base_dir / "data",
        cache_dir=base_dir / "cache",
        races_dir=base_dir / "data" / "races",
        telemetry_dir=base_dir / "data" / "telemetry",
        live_dir=base_dir / "data" / "live",
        processed_dir=base_dir / "data" / "processed",
    )
    yield config
    shutil.rmtree(base_dir, ignore_errors=True)


@pytest.fixture()
def cache_service(temp_cache_config: CacheConfig) -> CacheGenerationService:
    stub_openf1 = StubOpenF1Provider()
    fake_fastf1 = FakeFastF1Provider(temp_cache_config.cache_dir)
    service = CacheGenerationService(
        openf1_provider=cast(OpenF1DataProvider, stub_openf1),
        fastf1_provider=cast(FastF1PositionProvider, fake_fastf1),
        cache_config=temp_cache_config,
    )
    return service


def _status_paths(status: Dict[str, Any], key: str) -> Path:
    entry = next(item for item in status["entries"] if item["key"] == key)
    return Path(entry["path"])


def test_generate_session_caches_creates_files(cache_service: CacheGenerationService) -> None:
    keys = [
        "drivers",
        "positions",
        "intervals",
        "stints",
        "laps",
        "pit_stops",
        "weather",
        "race_control",
        "car_data",
        "track_map",
    ]
    cache_service.generate_caches(2025, meeting_key=42, session_code="R", selected_keys=keys)

    status = cache_service.describe_status(2025, meeting_key=42, session_code="R", selected_keys=keys)
    for key in keys:
        path = _status_paths(status, key)
        assert path.exists(), f"Cache {key} should exist"


def test_regeneration_updates_timestamps(cache_service: CacheGenerationService) -> None:
    keys = ["drivers", "positions"]
    cache_service.generate_caches(2025, meeting_key=42, session_code="R", selected_keys=keys)
    status = cache_service.describe_status(2025, meeting_key=42, session_code="R", selected_keys=keys)
    first_paths = {key: _status_paths(status, key) for key in keys}
    mtimes_before = {key: path.stat().st_mtime for key, path in first_paths.items()}

    cache_service.generate_caches(2025, meeting_key=42, session_code="R", selected_keys=keys)
    status_after = cache_service.describe_status(2025, meeting_key=42, session_code="R", selected_keys=keys)
    for key in keys:
        path = _status_paths(status_after, key)
        assert path.stat().st_mtime >= mtimes_before[key]


def test_skip_existing_caches_leaves_files_untouched(cache_service: CacheGenerationService) -> None:
    keys = ["drivers", "positions"]
    cache_service.generate_caches(2025, meeting_key=42, session_code="R", selected_keys=keys)
    status = cache_service.describe_status(2025, meeting_key=42, session_code="R", selected_keys=keys)
    first_paths = {key: _status_paths(status, key) for key in keys}
    mtimes_before = {key: path.stat().st_mtime for key, path in first_paths.items()}

    summary = cache_service.generate_caches(
        2025,
        meeting_key=42,
        session_code="R",
        selected_keys=keys,
        skip_existing=True,
    )

    status_after = cache_service.describe_status(2025, meeting_key=42, session_code="R", selected_keys=keys)
    for key in keys:
        path = _status_paths(status_after, key)
        assert path.stat().st_mtime == mtimes_before[key]

    assert summary["skipped"] == len(keys)
    assert summary["created"] == 0


def test_clear_caches_removes_files(cache_service: CacheGenerationService) -> None:
    keys = ["drivers", "positions", "track_map"]
    cache_service.generate_caches(2025, meeting_key=42, session_code="R", selected_keys=keys)
    status = cache_service.describe_status(2025, meeting_key=42, session_code="R", selected_keys=keys)
    paths = [
        _status_paths(status, "drivers"),
        _status_paths(status, "positions"),
        _status_paths(status, "track_map"),
    ]
    cache_service.clear_caches(2025, meeting_key=42, session_code="R", selected_keys=keys)
    for path in paths:
        assert not path.exists()
