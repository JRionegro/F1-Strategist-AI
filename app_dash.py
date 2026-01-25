"""
F1 Strategist AI - Main Dash Application.

Multi-dashboard F1 strategy platform with live and simulation modes.
Migrated from Streamlit to Dash for better layout control.
"""

import asyncio
import json
import logging
import os
import sys
import math
import threading
import importlib
import hashlib
from bisect import bisect_left
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, Tuple, Sequence, Set, Union, Mapping, cast
from numbers import Real
from uuid import uuid4

import dash
from dash import Dash, html, dcc, Input, Output, State, callback, ctx, Patch, ALL, no_update
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd

# OpenF1 data provider (replaces FastF1)
from src.data.openf1_adapter import get_session as get_openf1_session, SessionAdapter
from src.data.cache_generation import CacheGenerationService, MeetingSelector, SessionCode
from src.data.cache_config import DEFAULT_CACHE_CONFIG, DataType
from src.data.openf1_data_provider import OpenF1DataProvider
from src.data.last_race_finder import (
    get_last_completed_race,
    get_last_completed_meeting_key
)

# Core infrastructure (reused from Streamlit version)
from src.agents.orchestrator import AgentOrchestrator
from src.session.global_session import (
    GlobalSession,
    RaceContext,
    SessionMode,
    SessionType,
)
from src.session.simulation_controller import SimulationController
from src.session.live_detector import check_for_live_session
from src.session.event_detector import RaceEventDetector, RaceEvent
from src.session.tire_thresholds import load_tire_window_overrides_from_path

# FORCE RELOAD: Remove modules from cache BEFORE importing
modules_to_reload = [
    'src.dashboards_dash.weather_dashboard',
    'src.dashboards_dash.ai_assistant_dashboard', 
    'src.dashboards_dash.race_overview_dashboard'
]
for module_name in modules_to_reload:
    if module_name in sys.modules:
        del sys.modules[module_name]

# Clear Python's import cache
importlib.invalidate_caches()

# Remove compiled Python files
import os
import glob
project_root = os.path.dirname(os.path.abspath(__file__))
for pattern in ['**/*.pyc', '**/__pycache__']:
    for item in glob.glob(os.path.join(project_root, 'src', 'dashboards_dash', pattern), recursive=True):
        try:
            if os.path.isfile(item):
                os.remove(item)
            elif os.path.isdir(item):
                import shutil
                shutil.rmtree(item)
        except:
            pass

# NOW import dashboards (fresh, no cache)
from src.dashboards_dash.ai_assistant_dashboard import AIAssistantDashboard
from src.dashboards_dash.race_overview_dashboard import RaceOverviewDashboard
from src.dashboards_dash.race_control_dashboard import RaceControlDashboard
from src.dashboards_dash.telemetry_dashboard import TelemetryDashboard
from src.dashboards_dash.track_map_dashboard import get_track_map_dashboard, TrackMapDashboard
from src.dashboards_dash import weather_dashboard

# Predictive pit policy bootstrap
from src.predictive.bootstrap import bootstrap_pit_policy_context
from src.predictive.schemas import PitPolicyContext

# RAG Manager for document loading
from src.rag.rag_manager import get_rag_manager, reset_rag_manager
from src.rag.template_generator import get_template_generator
from src.rag.document_loader import DocumentLoader

# LLM providers for AI responses
from dotenv import load_dotenv
from src.llm.hybrid_router import HybridRouter
from src.llm.claude_provider import ClaudeProvider
from src.llm.gemini_provider import GeminiProvider
from src.llm.provider import LLMProvider
from src.llm.models import LLMConfig, LLMResponse
from src.llm.config import get_claude_config, get_gemini_config

# Centralized logging configuration
from src.utils.logging_config import (
    setup_logging,
    get_logger,
    LogCategory,
    enable_category,
    disable_category,
    apply_debug_profile,
    set_category_level,
)

# Load environment variables for API keys from centralized config/.env
load_dotenv(Path(__file__).parent / "config" / ".env", override=True)

# Initialize centralized logging system
# By default: only STARTUP and critical messages are shown
# To enable debugging, use: apply_debug_profile('telemetry') or enable_category(LogCategory.SIMULATION)
setup_logging(console_level=logging.INFO)

# Get loggers for different categories
logger = get_logger(LogCategory.STARTUP)  # Main app logger (startup messages)
sim_logger = get_logger(LogCategory.SIMULATION)  # Simulation timing
dash_logger = get_logger(LogCategory.DASHBOARD)  # Dashboard rendering
telem_logger = get_logger(LogCategory.TELEMETRY)  # Telemetry data
overview_logger = get_logger(LogCategory.RACE_OVERVIEW)  # Race overview
control_logger = get_logger(LogCategory.RACE_CONTROL)  # Race control
api_logger = get_logger(LogCategory.API)  # API calls
chat_logger = get_logger(LogCategory.CHAT)  # Chat/AI
proactive_logger = get_logger(LogCategory.PROACTIVE)  # Proactive AI alerts
track_map_logger = get_logger(LogCategory.TRACK_MAP)  # Track map diagnostics

# Log which LLM keys are visible after loading env
logger.info(
    "Env keys present -> Claude: %s, Gemini: %s",
    bool(os.getenv("ANTHROPIC_API_KEY")),
    bool(os.getenv("GOOGLE_API_KEY"))
)
enable_category(LogCategory.CHAT)
enable_category(LogCategory.TRACK_MAP)
data_log_level = os.getenv("LOG_LEVEL_F1_DATA")
if data_log_level:
    normalized_level = data_log_level.strip().upper()
    resolved_level = getattr(logging, normalized_level, None)
    if isinstance(resolved_level, int):
        set_category_level(LogCategory.DATA, resolved_level)
        logger.info(
            "Log level for %s set to %s via LOG_LEVEL_F1_DATA",
            LogCategory.DATA.value,
            normalized_level,
        )
    else:
        logger.warning(
            "Invalid LOG_LEVEL_F1_DATA value: %s (expected logging level name)",
            data_log_level,
        )
        enable_category(LogCategory.DATA)
else:
    enable_category(LogCategory.DATA)

# Uncomment to enable specific debugging:
# enable_category(LogCategory.SIMULATION)  # See simulation updates
# enable_category(LogCategory.TELEMETRY)   # See DRS/telemetry data
# apply_debug_profile('race')              # Enable race overview + control

# Initialize OpenF1 provider with SSL verification disabled for corporate proxies
openf1_provider = OpenF1DataProvider(verify_ssl=False)

# Initialize Race Overview Dashboard
race_overview_dashboard = RaceOverviewDashboard(openf1_provider)

# Initialize Race Control Dashboard
race_control_dashboard = RaceControlDashboard(openf1_provider)

# Initialize Telemetry Dashboard
telemetry_dashboard = TelemetryDashboard(openf1_provider)

# Initialize Race Event Detector for proactive AI alerts
event_detector = RaceEventDetector(openf1_provider)

# Cache generation service for manual cache orchestration
_cache_track_map_dashboard = get_track_map_dashboard()
cache_generation_service = CacheGenerationService(
    openf1_provider=openf1_provider,
    fastf1_provider=_cache_track_map_dashboard.provider,
    cache_config=DEFAULT_CACHE_CONFIG,
)
_CACHE_ARTIFACT_DEFS = cache_generation_service.list_artifacts()
CACHE_ARTIFACT_OPTIONS = [
    {"label": artifact.label, "value": artifact.key}
    for artifact in _CACHE_ARTIFACT_DEFS
]
CACHE_DEFAULT_SELECTION = [
    artifact.key
    for artifact in _CACHE_ARTIFACT_DEFS
    if artifact.level in {"session", "fastf1"}
]
CACHE_ARTIFACT_MAP = {artifact.key: artifact for artifact in _CACHE_ARTIFACT_DEFS}
CACHE_AVAILABLE_YEARS = list(range(datetime.now().year, 2017, -1))

_cache_job_lock = threading.Lock()
_cache_job_snapshot: Dict[str, Any] = {
    "job_id": None,
    "status": "idle",
    "completed": 0,
    "total": 0,
    "message": "",
    "error": None,
    "timestamp": None,
    "context": None,
}

CACHE_FILE_EXTENSION = DEFAULT_CACHE_CONFIG.get_file_extension()
PROCESSED_CACHE_DIR = DEFAULT_CACHE_CONFIG.processed_dir
RACES_CACHE_DIR = DEFAULT_CACHE_CONFIG.races_dir
_CALENDAR_CACHE: Dict[int, pd.DataFrame] = {}
_CALENDAR_METADATA: Dict[int, Dict[int, Dict[str, Any]]] = {}


def _set_cache_job_state(**updates: Any) -> None:
    with _cache_job_lock:
        _cache_job_snapshot.update(updates)


def _get_cache_job_state() -> Dict[str, Any]:
    with _cache_job_lock:
        return dict(_cache_job_snapshot)


def _cache_progress_payload() -> Dict[str, Any]:
    snapshot = _get_cache_job_state()
    return {
        key: snapshot.get(key)
        for key in [
            "status",
            "completed",
            "total",
            "message",
            "error",
            "timestamp",
            "context",
        ]
    }


def _read_cache_dataframe(path: Path) -> Optional[pd.DataFrame]:
    """Load a cached dataframe from disk if available."""
    if not path.exists():
        return None
    try:
        if path.suffix == ".parquet":
            return pd.read_parquet(path)
        if path.suffix == ".csv":
            return pd.read_csv(path)
        logger.warning("Unsupported cache format for %s", path)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to load cache %s: %s", path, exc)
    return None


def _normalize_record_keys(
    raw_records: Sequence[Mapping[Any, Any]]
) -> List[Dict[str, Any]]:
    """Return a copy of the records with string keys for type safety."""
    normalized: List[Dict[str, Any]] = []
    for raw in raw_records:
        normalized.append({str(key): value for key, value in raw.items()})
    return normalized


_SESSION_NAME_FIELDS: Sequence[str] = [
    "session_name",
    "SessionName",
    "name",
    "Session",
]
_SESSION_TYPE_FIELDS: Sequence[str] = ["session_type", "SessionType"]
_SESSION_CODE_FIELDS: Sequence[str] = ["session_code", "SessionCode"]
_SESSION_NAME_TO_CODE: Dict[str, str] = {
    "Practice 1": "P1",
    "Practice 2": "P2",
    "Practice 3": "P3",
    "Qualifying": "Q",
    "Sprint": "S",
    "Sprint Qualifying": "SQ",
    "Sprint Shootout": "SS",
    "Race": "R",
}
_SESSION_CODE_TO_LABEL: Dict[str, str] = {
    "P1": "Practice 1",
    "P2": "Practice 2",
    "P3": "Practice 3",
    "FP1": "Practice 1",
    "FP2": "Practice 2",
    "FP3": "Practice 3",
    "Q": "Qualifying",
    "QUALIFYING": "Qualifying",
    "SQ": "Sprint Qualifying",
    "SS": "Sprint Shootout",
    "S": "Sprint",
    "SPRINT": "Sprint",
    "R": "Race",
    "RACE": "Race",
}


def _load_cached_session_list(year: int, meeting_key: int) -> Optional[List[Dict[str, Any]]]:
    """Return cached session metadata for the meeting when available."""
    session_dir = PROCESSED_CACHE_DIR / "session_list" / str(year)
    if not session_dir.exists():
        return None

    candidate_paths: List[Path] = []
    meta = _CALENDAR_METADATA.get(year, {}).get(meeting_key)
    slug = meta.get("cache_slug") if meta else None
    if slug:
        candidate_paths.append(session_dir / f"{slug}{CACHE_FILE_EXTENSION}")
    if not candidate_paths:
        candidate_paths.extend(sorted(session_dir.glob(f"*{CACHE_FILE_EXTENSION}")))

    for path in candidate_paths:
        cached_df = _read_cache_dataframe(path)
        if cached_df is None or cached_df.empty:
            continue
        raw_records = cached_df.to_dict("records")
        if not raw_records:
            continue
        records = _normalize_record_keys(raw_records)
        sample = records[0]
        meeting_key_val = sample.get("meeting_key") or sample.get("MeetingKey")
        if meeting_key_val is None:
            continue
        try:
            meeting_key_int = int(meeting_key_val)
        except (TypeError, ValueError):
            continue
        if meeting_key_int == meeting_key:
            return records
    return None


def _extract_session_field(payload: Dict[str, Any], field_names: Sequence[str]) -> str:
    """Return the first non-empty string value for the given field names."""
    for field in field_names:
        value = payload.get(field)
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
        elif value not in (None, ""):
            return str(value)
    return ""


def _interpret_session_payload(payload: Dict[str, Any]) -> Tuple[str, str, str]:
    """Return normalized session code, label, and name for a payload."""
    session_name = _extract_session_field(payload, _SESSION_NAME_FIELDS)
    session_type_raw = _extract_session_field(payload, _SESSION_TYPE_FIELDS)
    session_code_raw = _extract_session_field(payload, _SESSION_CODE_FIELDS)

    # PRIORITY 1: Detect special sessions from session_name first
    normalized_code = None
    label = None
    if session_name:
        name_lower = session_name.lower()
        # Check Sprint Qualifying BEFORE generic qualifying/sprint
        if "sprint" in name_lower and "qualifying" in name_lower:
            normalized_code = "SQ"
            label = "Sprint Qualifying"
        elif "qualifying" in name_lower and "shootout" in name_lower:
            normalized_code = "SS"
            label = "Sprint Shootout"
        elif "shootout" in name_lower:
            normalized_code = "SS"
            label = "Sprint Shootout"
        elif "sprint" in name_lower:
            normalized_code = "S"
            label = "Sprint"

    # PRIORITY 2: Use session_code/session_type if not detected above
    if normalized_code is None:
        candidate_code = (
            (session_code_raw or session_type_raw).upper()
            if (session_code_raw or session_type_raw)
            else ""
        )
        if not candidate_code:
            fallback = _SESSION_NAME_TO_CODE.get(session_name)
            if fallback:
                candidate_code = fallback
            elif session_name:
                candidate_code = session_name.upper()
            else:
                candidate_code = "SESSION"

        normalized_code = candidate_code.upper()
        label = _SESSION_CODE_TO_LABEL.get(normalized_code)

    # PRIORITY 3: Fallback parsing if still not resolved
    if label is None:
        name_lower = session_name.lower()
        if "practice" in name_lower or name_lower.startswith("fp"):
            if "3" in name_lower:
                normalized_code = "P3"
                label = "Practice 3"
            elif "2" in name_lower:
                normalized_code = "P2"
                label = "Practice 2"
            else:
                normalized_code = "P1"
                label = "Practice 1"
        elif "sprint" in name_lower and "qualifying" in name_lower:
            normalized_code = "SQ"
            label = "Sprint Qualifying"
        elif "qualifying" in name_lower and "shootout" in name_lower:
            normalized_code = "SS"
            label = "Sprint Shootout"
        elif "qualifying" in name_lower:
            normalized_code = "Q"
            label = "Qualifying"
        elif "shootout" in name_lower:
            normalized_code = "SS"
            label = "Sprint Shootout"
        elif "sprint" in name_lower:
            normalized_code = "S"
            label = "Sprint"
        elif "race" in name_lower:
            normalized_code = "R"
            label = "Race"
        elif session_name:
            label = session_name
        else:
            label = normalized_code.title()

    return normalized_code.upper(), label, session_name


def _build_session_selector_options(sessions: Sequence[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Normalize raw session payloads into selector options."""
    normalized_sessions = _normalize_record_keys(sessions)
    options: List[Dict[str, str]] = []
    seen_values: Set[str] = set()

    logger.info(f"Building session options from {len(normalized_sessions)} sessions:")
    for payload in normalized_sessions:
        session_name = payload.get('session_name', 'Unknown')
        normalized_code, label, _session_name = _interpret_session_payload(payload)
        logger.info(f"  Session: '{session_name}' → code={normalized_code}, label={label}")
        
        if normalized_code in seen_values:
            logger.warning(f"  ⚠️ DUPLICATE CODE {normalized_code} - skipping '{session_name}'")
            continue
        
        seen_values.add(normalized_code)
        options.append({"label": label, "value": normalized_code})
        logger.info(f"  ✓ Added option: {label} ({normalized_code})")

    logger.info(f"Built {len(options)} unique session options")
    return options


def _find_session_payload(
    records: Sequence[Dict[str, Any]],
    target_code: str,
) -> Optional[Dict[str, Any]]:
    """Return session payload matching the target code if present."""
    if not records:
        return None

    normalized_target = target_code.upper()
    logger.info(f"Searching for session with target_code={normalized_target}")
    for payload in _normalize_record_keys(records):
        normalized_code, _label, session_name = _interpret_session_payload(payload)
        session_key = payload.get("session_key") or payload.get("SessionKey")
        logger.info(
            f"  Checking: {session_name} → normalized_code={normalized_code} "
            f"(session_key={session_key})"
        )
        if normalized_code == normalized_target:
            logger.info(f"  ✓ MATCH! Returning session_key={session_key}")
            return payload
    logger.warning(f"No session found matching target_code={normalized_target}")
    return None


def _get_session_key(payload: Dict[str, Any]) -> Optional[Union[int, str]]:
    return payload.get("session_key") or payload.get("SessionKey")


def _resolve_session_payload(
    year: int,
    meeting_key: int,
    session_code: str,
) -> Optional[Dict[str, Any]]:
    """Return canonical session payload for the requested session code."""
    normalized_code = session_code.upper()
    candidate: Optional[Dict[str, Any]] = None

    try:
        cached_records = _load_cached_session_list(int(year), int(meeting_key))
    except Exception as exc:  # noqa: BLE001
        logger.debug("Failed to load cached sessions for %s/%s: %s", year, meeting_key, exc)
        cached_records = None

    if cached_records:
        logger.info(
            "Session resolver cache hit (year=%s meeting_key=%s entries=%s)",
            year,
            meeting_key,
            len(cached_records),
        )
        candidate = _find_session_payload(cached_records, normalized_code)
        if candidate and _get_session_key(candidate):
            logger.info(
                "Session resolver returning cached payload (meeting_key=%s session_code=%s session_key=%s)",
                meeting_key,
                normalized_code,
                _get_session_key(candidate),
            )
            return candidate
    else:
        logger.info(
            "Session resolver cache miss (year=%s meeting_key=%s)",
            year,
            meeting_key,
        )

    def _request_sessions(params: Dict[str, Any]) -> List[Dict[str, Any]]:
        try:
            payloads = openf1_provider._request("sessions", params)
            if isinstance(payloads, list):
                return [
                    record if isinstance(record, dict) else {}
                    for record in payloads
                ]
        except Exception as exc:  # noqa: BLE001
            logger.warning("OpenF1 session request failed %s: %s", params, exc)
        return []

    api_records = _request_sessions({"year": year, "meeting_key": meeting_key})
    api_candidate = _find_session_payload(api_records, normalized_code)
    if api_candidate and _get_session_key(api_candidate):
        logger.info(
            "Session resolver using API payload from meeting/year request (meeting_key=%s session_code=%s session_key=%s)",
            meeting_key,
            normalized_code,
            _get_session_key(api_candidate),
        )
        return api_candidate

    if api_candidate is None and candidate and _get_session_key(candidate):
        logger.info(
            "Session resolver fallback to cached payload without initial API match (meeting_key=%s session_code=%s session_key=%s)",
            meeting_key,
            normalized_code,
            _get_session_key(candidate),
        )
        return candidate

    # Targeted requests using session_code and session_name fallbacks
    for query in (
        {"year": year, "meeting_key": meeting_key, "session_code": normalized_code},
        {
            "year": year,
            "meeting_key": meeting_key,
            "session_name": _SESSION_CODE_TO_LABEL.get(normalized_code, normalized_code),
        },
    ):
        targeted_records = _request_sessions(query)
        targeted_candidate = _find_session_payload(targeted_records, normalized_code)
        if targeted_candidate and _get_session_key(targeted_candidate):
            logger.info(
                "Session resolver using API payload from targeted query %s (session_key=%s)",
                {key: query[key] for key in sorted(query)},
                _get_session_key(targeted_candidate),
            )
            return targeted_candidate

    if api_candidate:
        logger.warning(
            "Session resolver returning API payload without session_key (meeting_key=%s session_code=%s)",
            meeting_key,
            normalized_code,
        )
        return api_candidate
    if candidate:
        logger.warning(
            "Session resolver returning cached payload without session_key (meeting_key=%s session_code=%s)",
            meeting_key,
            normalized_code,
        )
        return candidate
    logger.error(
        "Session resolver failed to locate payload (meeting_key=%s session_code=%s)",
        meeting_key,
        normalized_code,
    )
    return None


def _run_cache_job(
    job_id: str,
    action: str,
    year: int,
    meeting_key: MeetingSelector,
    session_code: SessionCode,
    selected_keys: List[str],
) -> None:
    try:
        if action == "delete":
            _set_cache_job_state(
                status="running",
                message="Deleting selected caches...",
                error=None,
                timestamp=datetime.now(timezone.utc).isoformat(),
                completed=0,
                total=len(selected_keys),
            )
            deleted_paths = cache_generation_service.clear_caches(
                year,
                meeting_key,
                session_code,
                selected_keys,
            )
            count = len(deleted_paths)
            _set_cache_job_state(
                status="completed",
                completed=count,
                total=max(count, 1),
                message=f"Deleted {count} cache files." if count else "No cache files deleted.",
                error=None,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            return

        skip_existing = action == "fill"

        def progress_callback(completed: int, total: int, message: str) -> None:
            with _cache_job_lock:
                if _cache_job_snapshot.get("job_id") != job_id:
                    return
                _cache_job_snapshot.update({
                    "status": "running",
                    "completed": completed,
                    "total": total,
                    "message": message,
                    "error": None,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

        summary = cache_generation_service.generate_caches(
            year,
            meeting_key,
            session_code,
            selected_keys,
            progress_callback=progress_callback,
            skip_existing=skip_existing,
        )
        total_requested = summary.get("total", len(selected_keys))
        created_count = summary.get("created", total_requested if not skip_existing else 0)
        skipped_count = summary.get("skipped", 0)
        if skip_existing:
            message = (
                f"Created {created_count} caches; {skipped_count} already up to date."
                if total_requested
                else "No missing caches detected."
            )
        else:
            message = "Cache generation finished successfully."
        _set_cache_job_state(
            status="completed",
            completed=total_requested,
            total=max(total_requested, 1),
            message=message,
            error=None,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Cache %s failed: %s", action, exc, exc_info=True)
        _set_cache_job_state(
            status="error",
            completed=0,
            total=max(len(selected_keys), 1),
            message="Cache deletion failed." if action == "delete" else "Cache generation failed.",
            error=str(exc),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    finally:
        with _cache_job_lock:
            _cache_job_snapshot["job_id"] = None

# Bootstrap Icons CDN for icon support
BOOTSTRAP_ICONS = "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css"

# Initialize Dash app with F1 theme
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG, BOOTSTRAP_ICONS],
    suppress_callback_exceptions=True,
    title="F1 Strategist AI",
    # Development settings to avoid asset loading issues
    compress=False,
    serve_locally=True
)

# Ensure all @callback decorators bind to this app (avoid dangling global callbacks)
callback = app.callback

server = app.server
server.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable Flask caching
server.config['TEMPLATES_AUTO_RELOAD'] = True

# Global session (singleton pattern maintained)
session = GlobalSession()

# Simulation controller (initialized with dummy times, will be updated)
simulation_controller: Optional[SimulationController] = None

# Current loaded session object (for circuit map and other dashboards)
current_session_obj = None

# Cached pit policy context (loaded once per simulation from RAG)
_pit_policy_context: Optional[PitPolicyContext] = None

# LLM provider singleton (lazy initialization)
_llm_provider: Optional[LLMProvider] = None
_llm_provider_type: Optional[str] = None  # 'hybrid', 'claude', 'gemini'

# Track map figure patching state
_track_map_trace_offset: Optional[int] = None
_track_map_driver_order: List[int] = []
_track_map_focus_driver: Optional[int] = None
_track_map_driver_laps: Dict[int, int] = {}
_track_map_retirements: Dict[int, Dict[str, Any]] = {}
_track_map_retirement_order: List[int] = []
TRACK_MAP_TRAJECTORY_CACHE_LIMIT = 4


def _extract_track_map_trace_offset(figure: Any) -> Optional[int]:
    """Return index of the first driver trace in a track map figure."""
    figure_dict = figure.to_dict() if hasattr(figure, "to_dict") else figure
    if not isinstance(figure_dict, dict):
        return None

    data_traces = figure_dict.get("data", [])
    if not isinstance(data_traces, list):
        return None

    for idx, raw_trace in enumerate(data_traces):
        trace_dict: Optional[Dict[str, Any]]
        if isinstance(raw_trace, dict):
            trace_dict = raw_trace
        elif hasattr(raw_trace, "to_plotly_json"):
            converted = raw_trace.to_plotly_json()
            trace_dict = converted if isinstance(converted, dict) else None
        else:
            trace_dict = None

        if trace_dict and trace_dict.get("mode") == "markers+text":
            return idx

    return None


def _parse_driver_selector_value(selector_value: Optional[str]) -> Tuple[Optional[str], Optional[int]]:
    """Return driver code and car number from the selector value."""
    if not selector_value or selector_value == 'none':
        return None, None
    parts = selector_value.split('_')
    if len(parts) < 3:
        return parts[0] if parts else None, None

    driver_code = parts[0]
    try:
        driver_number = int(parts[-1])
    except ValueError:
        return driver_code, None
    return driver_code, driver_number


def _update_track_map_lap_cache(positions: Dict[int, Any]) -> None:
    """Store the latest lap number per driver for tooltip fallbacks."""
    if not isinstance(positions, dict):
        return

    for driver_number, payload in positions.items():
        if not isinstance(driver_number, int):
            continue
        if not isinstance(payload, dict):
            continue

        lap_raw = payload.get("lap_number")
        if isinstance(lap_raw, Real):
            lap_value = float(lap_raw)
            if math.isfinite(lap_value) and lap_value >= 1.0:
                _track_map_driver_laps[driver_number] = int(lap_value)


def _interpolate_cached_track_positions(
    laps_section: Optional[Dict[str, Any]],
    current_lap: int,
    driver_order: Sequence[int],
    session_time: float,
) -> Dict[int, Dict[str, Any]]:
    """Convert cached lap trajectories into instantaneous marker positions."""
    if not isinstance(laps_section, dict) or not laps_section:
        return {}

    lap_payload_cache: Dict[int, Dict[str, Any]] = {}
    for lap_key, lap_payload in laps_section.items():
        if not isinstance(lap_payload, dict):
            continue
        try:
            lap_number = int(lap_key)
        except (TypeError, ValueError):
            continue
        lap_payload_cache[lap_number] = lap_payload

    if not lap_payload_cache:
        return {}

    candidate_laps = sorted(
        lap_payload_cache.keys(),
        key=lambda lap_num: (abs(lap_num - current_lap), lap_num),
    )

    interpolated: Dict[int, Dict[str, Any]] = {}
    for driver_number in driver_order:
        driver_key = str(driver_number)
        best_payload: Optional[Dict[str, Any]] = None
        best_lap_number: Optional[int] = None
        best_distance: float = float("inf")

        for lap_number in candidate_laps:
            lap_payload = lap_payload_cache.get(lap_number)
            if lap_payload is None:
                continue
            driver_payload = lap_payload.get(driver_key)
            if not isinstance(driver_payload, dict):
                continue

            time_values_raw = driver_payload.get("time")
            x_values_raw = driver_payload.get("x")
            y_values_raw = driver_payload.get("y")
            if (
                not isinstance(time_values_raw, list)
                or not isinstance(x_values_raw, list)
                or not isinstance(y_values_raw, list)
                or not time_values_raw
            ):
                continue

            try:
                time_values = [float(value) for value in time_values_raw]
                x_values = [float(value) for value in x_values_raw]
                y_values = [float(value) for value in y_values_raw]
            except (TypeError, ValueError):
                continue

            start_time = time_values[0]
            end_time = time_values[-1]

            if start_time <= session_time <= end_time:
                best_payload = {
                    "time": time_values,
                    "x": x_values,
                    "y": y_values,
                }
                best_lap_number = lap_number
                break

            if session_time < start_time:
                distance = start_time - session_time
            else:
                distance = session_time - end_time

            if distance < best_distance:
                best_distance = distance
                best_payload = {
                    "time": time_values,
                    "x": x_values,
                    "y": y_values,
                }
                best_lap_number = lap_number

        if best_payload is None or best_lap_number is None:
            continue

        time_values = best_payload["time"]
        x_values = best_payload["x"]
        y_values = best_payload["y"]

        start_time = time_values[0]
        end_time = time_values[-1]
        if start_time <= end_time:
            clamped_time = min(max(session_time, start_time), end_time)
        else:
            clamped_time = session_time

        insert_idx = bisect_left(time_values, clamped_time)
        prev_idx = max(insert_idx - 1, 0)
        next_idx = min(insert_idx, len(time_values) - 1)

        prev_time = time_values[prev_idx]
        next_time = time_values[next_idx]
        prev_x = x_values[prev_idx]
        prev_y = y_values[prev_idx]
        next_x = x_values[next_idx]
        next_y = y_values[next_idx]

        if next_time <= prev_time:
            ratio = 0.0
        else:
            ratio = (clamped_time - prev_time) / (next_time - prev_time)
            ratio = max(0.0, min(float(ratio), 1.0))

        interpolated_time = prev_time + (next_time - prev_time) * ratio
        interpolated_x = prev_x + (next_x - prev_x) * ratio
        interpolated_y = prev_y + (next_y - prev_y) * ratio

        previous_sample = {"time": prev_time, "x": prev_x, "y": prev_y}
        next_sample = {"time": next_time, "x": next_x, "y": next_y}

        interpolated[driver_number] = {
            "x": interpolated_x,
            "y": interpolated_y,
            "z": 0.0,
            "time": interpolated_time,
            "query_time": session_time,
            "previous_sample": previous_sample,
            "next_sample": next_sample,
            "lap_number": int(best_lap_number),
        }

    return interpolated


def _default_track_map_trajectory_store() -> Dict[str, Any]:
    """Return the baseline payload for the track map trajectory cache."""
    return {"time_offset": 0.0, "time_bounds": [0.0, 0.0], "laps": {}}


def _resolve_track_map_total_laps(session_payload: Optional[Dict[str, Any]]) -> Optional[int]:
    """Return the configured race distance if present in the session payload."""
    if not isinstance(session_payload, dict):
        return None

    raw_total = session_payload.get("total_laps")
    if isinstance(raw_total, (int, float)):
        return int(raw_total)

    session_section = session_payload.get("session")
    if isinstance(session_section, dict):
        section_total = session_section.get("total_laps")
        if isinstance(section_total, (int, float)):
            return int(section_total)

    circuit_meta = session_payload.get("circuit")
    if isinstance(circuit_meta, dict):
        circuit_name = circuit_meta.get("name") or circuit_meta.get("circuit_name")
        if isinstance(circuit_name, str):
            return _get_total_laps_for_circuit(circuit_name)

    circuit_name = session_payload.get("circuit_name")
    if isinstance(circuit_name, str):
        return _get_total_laps_for_circuit(circuit_name)

    return None


def _format_track_map_lap_label(
    current_lap: int,
    total_laps: Optional[int],
    formation_offset_seconds: float,
    elapsed_time_seconds: float,
) -> str:
    """Build the lap label shown below the track map."""
    if formation_offset_seconds > 0.0 and current_lap <= 1 and elapsed_time_seconds < 1.0:
        return "Formation Lap"

    lap_value = max(current_lap, 1)
    if total_laps and total_laps > 0:
        return f"Lap {lap_value} / {total_laps}"

    return f"Lap {lap_value}"


# Circuit total laps lookup table (works for both LIVE and historical)
# This is the authoritative source - matches official F1 race distances
CIRCUIT_TOTAL_LAPS = {
    "bahrain": 57,
    "sakhir": 57,
    "saudi": 50,
    "jeddah": 50,
    "australia": 58,
    "melbourne": 58,
    "japan": 53,
    "suzuka": 53,
    "china": 56,
    "shanghai": 56,
    "miami": 57,
    "monaco": 78,
    "monte carlo": 78,
    "spain": 66,
    "barcelona": 66,
    "canada": 70,
    "montreal": 70,
    "austria": 71,
    "spielberg": 71,
    "britain": 52,
    "silverstone": 52,
    "hungary": 70,
    "hungaroring": 70,
    "belgium": 44,
    "spa": 44,
    "netherlands": 72,
    "zandvoort": 72,
    "italy": 53,
    "monza": 53,
    "singapore": 62,
    "marina bay": 62,
    "qatar": 57,
    "lusail": 57,
    "usa": 56,
    "austin": 56,
    "cota": 56,
    "united states": 56,
    "las vegas": 50,
    "vegas": 50,
    "mexico": 71,
    "brazil": 71,
    "interlagos": 71,
    "sao paulo": 71,
    "abu dhabi": 58,
    "yas marina": 58,
    "azerbaijan": 51,
    "baku": 51,
    "imola": 63,
    "emilia": 63,
}


def _get_total_laps_for_circuit(circuit_name: str) -> int:
    """
    Get total racing laps for a circuit by name.
    
    Works for both LIVE and historical sessions by using
    the circuit name lookup table.
    
    Args:
        circuit_name: Circuit name (e.g., 'Las Vegas', 'Silverstone')
    
    Returns:
        Total racing laps for the circuit, or 57 as default
    """
    if not circuit_name:
        return 57
    
    circuit_lower = circuit_name.lower().strip()
    
    # Direct lookup
    if circuit_lower in CIRCUIT_TOTAL_LAPS:
        return CIRCUIT_TOTAL_LAPS[circuit_lower]
    
    # Partial match (e.g., "Las Vegas Street Circuit" -> "las vegas")
    for key, laps in CIRCUIT_TOTAL_LAPS.items():
        if key in circuit_lower or circuit_lower in key:
            return laps
    
    logger.warning(
        f"Unknown circuit '{circuit_name}', using default 57 laps"
    )
    return 57


def _calculate_total_laps(session_obj, circuit_name: Optional[str] = None) -> int:
    """
    Calculate total racing laps for a session.
    
    Strategy:
    1. If circuit_name provided, use lookup table (best for LIVE)
    2. Try to get from session lap data (for historical/completed races)
    3. Fall back to circuit lookup from session info
    4. Default to 57
    
    Args:
        session_obj: FastF1/OpenF1 session object
        circuit_name: Optional circuit name for direct lookup
    
    Returns:
        Total racing laps (int)
    """
    # Priority 1: Use circuit name if provided
    if circuit_name:
        laps = _get_total_laps_for_circuit(circuit_name)
        if laps != 57:  # Found a match
            return laps
    
    # Priority 2: Try to get circuit from session and use lookup
    try:
        if session_obj:
            # Try to get circuit name from session
            session_circuit = None
            if hasattr(session_obj, 'event') and session_obj.event is not None:
                if hasattr(session_obj.event, 'Location'):
                    session_circuit = session_obj.event.Location
                elif hasattr(session_obj.event, 'CircuitName'):
                    session_circuit = session_obj.event.CircuitName
            
            if session_circuit:
                laps = _get_total_laps_for_circuit(session_circuit)
                if laps != 57:
                    return laps
            
            # Priority 3: Calculate from actual lap data (historical only)
            if hasattr(session_obj, 'laps') and not session_obj.laps.empty:
                max_lap = session_obj.laps['LapNumber'].max()
                if pd.notna(max_lap) and max_lap > 0:
                    calculated = int(max_lap)
                    logger.info(
                        f"Calculated total_laps from data: {calculated}"
                    )
                    return calculated
    except Exception as e:
        logger.warning(f"Error calculating total_laps: {e}")
    
    return 57  # Default fallback


def _timedelta_to_seconds(value: Any) -> Optional[float]:
    """Convert timedelta-like values to floating seconds."""
    if value is None:
        return None

    if isinstance(value, float) and math.isnan(value):
        return None

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, timedelta):
        return value.total_seconds()

    if isinstance(value, pd.Timedelta):
        return float(value.total_seconds())

    try:
        converted = pd.to_timedelta(value, errors="coerce")
    except Exception:  # noqa: BLE001
        return None

    if pd.isna(converted):
        return None

    return float(converted.total_seconds())


def _extract_fastf1_lap1_seconds(
    dashboard: TrackMapDashboard,
    driver_number: int,
) -> Optional[float]:
    """Return lap-one duration from FastF1 telemetry in seconds."""
    provider = getattr(dashboard, "provider", None)
    session = getattr(provider, "session", None)
    if session is None or not hasattr(session, "laps"):
        return None

    laps_df = session.laps
    if laps_df is None or laps_df.empty:
        return None

    candidate = pd.DataFrame()
    if "DriverNumber" in laps_df.columns:
        driver_numbers = pd.to_numeric(laps_df["DriverNumber"], errors="coerce")
        candidate = laps_df.loc[driver_numbers == driver_number]

    if candidate.empty:
        provider_abbr = provider.get_driver_abbreviation(driver_number) if provider else None
        if provider_abbr:
            try:
                candidate = session.laps.pick_drivers(provider_abbr)
            except Exception:  # noqa: BLE001
                candidate = pd.DataFrame()

    if candidate.empty:
        candidate = laps_df

    lap_one = candidate.loc[candidate["LapNumber"] == 1]
    if lap_one.empty:
        return None

    first_row = lap_one.iloc[0]
    lap_time_seconds = _timedelta_to_seconds(first_row.get("LapTime"))
    if lap_time_seconds is not None and lap_time_seconds > 0:
        return lap_time_seconds

    start_seconds = _timedelta_to_seconds(first_row.get("LapStartTime"))
    end_seconds = _timedelta_to_seconds(first_row.get("LapEndTime"))
    if start_seconds is not None and end_seconds is not None and end_seconds > start_seconds:
        return end_seconds - start_seconds

    return None


def _normalize_lap_timing_data(
    lap_timing: pd.DataFrame,
    dashboard: TrackMapDashboard,
    driver_number: int,
) -> Tuple[pd.DataFrame, Optional[float], Optional[float]]:
    """Align OpenF1 lap timings with FastF1 estimated race start."""
    if lap_timing is None or lap_timing.empty:
        return lap_timing, None, None

    normalized = lap_timing.copy()

    if "LapNumber" in normalized.columns:
        normalized.loc[:, "LapNumber"] = pd.to_numeric(normalized["LapNumber"], errors="coerce")
    else:
        normalized.loc[:, "LapNumber"] = pd.Series(float("nan"), index=normalized.index)

    if "LapStartTime" in normalized.columns:
        normalized.loc[:, "LapStartTime"] = pd.to_timedelta(normalized["LapStartTime"], errors="coerce")
    else:
        normalized.loc[:, "LapStartTime"] = pd.NaT

    if "LapEndTime" in normalized.columns:
        normalized.loc[:, "LapEndTime"] = pd.to_timedelta(normalized["LapEndTime"], errors="coerce")
    else:
        normalized.loc[:, "LapEndTime"] = pd.NaT

    if "LapTime" in normalized.columns:
        normalized.loc[:, "LapTime"] = pd.to_timedelta(normalized["LapTime"], errors="coerce")

    lap_two = normalized.loc[normalized["LapNumber"] == 2].head(1)
    lap_two_start_seconds = _timedelta_to_seconds(lap_two.iloc[0]["LapStartTime"]) if not lap_two.empty else None

    fastf1_lap_one_seconds = _extract_fastf1_lap1_seconds(dashboard, driver_number)
    formation_offset_seconds = None

    if lap_two_start_seconds is not None and fastf1_lap_one_seconds is not None:
        gap_seconds = lap_two_start_seconds - fastf1_lap_one_seconds
        if gap_seconds > 1.0:
            formation_offset_seconds = gap_seconds

    if formation_offset_seconds is not None:
        offset_td = pd.to_timedelta(formation_offset_seconds, unit="s")
        start_valid_mask = normalized["LapStartTime"].notna()
        end_valid_mask = normalized["LapEndTime"].notna()

        normalized.loc[start_valid_mask, "LapStartTime"] = (
            normalized.loc[start_valid_mask, "LapStartTime"] - offset_td
        )
        normalized.loc[end_valid_mask, "LapEndTime"] = (
            normalized.loc[end_valid_mask, "LapEndTime"] - offset_td
        )

        zero_td = pd.to_timedelta(0, unit="s")
        start_series = normalized.loc[start_valid_mask, "LapStartTime"]
        normalized.loc[start_valid_mask, "LapStartTime"] = start_series.where(start_series >= zero_td, zero_td)

        end_series = normalized.loc[end_valid_mask, "LapEndTime"]
        normalized.loc[end_valid_mask, "LapEndTime"] = end_series.where(end_series >= zero_td, zero_td)

        if "LapTime" in normalized.columns:
            recompute_mask = normalized["LapEndTime"].isna() & normalized["LapTime"].notna()
            if recompute_mask.any():
                normalized.loc[recompute_mask, "LapEndTime"] = (
                    normalized.loc[recompute_mask, "LapStartTime"]
                    + normalized.loc[recompute_mask, "LapTime"]
                )

    lap_one_mask = normalized["LapNumber"] == 1
    normalized.loc[lap_one_mask, "LapStartTime"] = normalized.loc[lap_one_mask, "LapStartTime"].fillna(pd.Timedelta(seconds=0))
    if "LapTime" in normalized.columns:
        normalized.loc[lap_one_mask, "LapEndTime"] = (
            normalized.loc[lap_one_mask, "LapStartTime"] + normalized.loc[lap_one_mask, "LapTime"]
        )

    normalized.loc[:, "LapStartTime_seconds"] = normalized["LapStartTime"].apply(_timedelta_to_seconds)
    normalized.loc[:, "LapEndTime_seconds"] = normalized["LapEndTime"].apply(_timedelta_to_seconds)

    return normalized, formation_offset_seconds, fastf1_lap_one_seconds


def _is_retirement_status(status: str) -> bool:
    """Return True when a FastF1 status indicates retirement or DNF."""
    if not status:
        return False

    normalized = str(status).strip().lower()
    if not normalized:
        return False

    if normalized in {"finished", "classified"}:
        return False

    if normalized.startswith("+"):
        # +1 Lap, +2 Laps -> still classified
        return False

    if normalized.startswith("disqualified"):
        return True

    retirement_keywords = (
        "ret",  # retired
        "dnf",
        "accident",
        "collision",
        "engine",
        "gearbox",
        "hydraul",
        "suspension",
        "electrical",
        "oil",
        "damage",
        "brake",
        "fuel",
        "not classified",
        "did not finish",
        "stopped",
        "tyre",
        "power unit",
        "water",
    )
    return any(keyword in normalized for keyword in retirement_keywords)


def _refresh_track_map_retirements(track_dashboard: TrackMapDashboard) -> Dict[int, Dict[str, Any]]:
    """Compute retirement metadata using FastF1 session results."""
    global _track_map_retirements, _track_map_retirement_order

    provider = getattr(track_dashboard, "provider", None)
    session = getattr(provider, "session", None)
    if session is None or not hasattr(session, "results"):
        _track_map_retirements = {}
        _track_map_retirement_order = []
        return _track_map_retirements

    results_df = getattr(session, "results", None)
    if not isinstance(results_df, pd.DataFrame) or results_df.empty:
        _track_map_retirements = {}
        _track_map_retirement_order = []
        return _track_map_retirements

    laps_df = getattr(session, "laps", None)

    session_start_dt: Optional[datetime] = None
    if simulation_controller is not None:
        start_candidate = getattr(simulation_controller, "start_time", None)
        session_start_dt = start_candidate if isinstance(start_candidate, datetime) else None

    def _extract_seconds(raw_value: Any) -> Optional[float]:
        if raw_value is None:
            return None

        if isinstance(raw_value, pd.Timedelta):
            if pd.isna(raw_value):
                return None
            return float(raw_value.total_seconds())

        if isinstance(raw_value, Real):
            numeric_value = float(raw_value)
            return numeric_value if math.isfinite(numeric_value) else None

        if isinstance(raw_value, pd.Timestamp):
            if pd.isna(raw_value):
                return None
            if session_start_dt is None:
                return None
            timestamp_dt = raw_value.to_pydatetime()
        elif isinstance(raw_value, datetime):
            timestamp_dt = raw_value
        else:
            return None

        if session_start_dt is None:
            return None
        return max((timestamp_dt - session_start_dt).total_seconds(), 0.0)

    retirements: Dict[int, Dict[str, Any]] = {}
    positions_df = getattr(provider, "positions_df", None)
    time_offset_value = getattr(provider, "_session_time_offset", 0.0)
    try:
        time_offset = float(time_offset_value)
    except (TypeError, ValueError):
        time_offset = 0.0

    for _, row in results_df.iterrows():
        driver_number_raw = row.get("DriverNumber")
        status_raw = row.get("Status")
        if driver_number_raw is None:
            continue
        try:
            driver_number = int(cast(float | int | str, driver_number_raw))
        except (TypeError, ValueError):
            continue

        status_text = str(status_raw or "").strip()
        if not _is_retirement_status(status_text):
            continue

        retired_lap: Optional[int] = None
        retire_time: Optional[float] = None
        if isinstance(laps_df, pd.DataFrame) and not laps_df.empty and "DriverNumber" in laps_df.columns:
            numeric_driver_numbers = pd.to_numeric(laps_df["DriverNumber"], errors="coerce")
            driver_laps = laps_df.loc[numeric_driver_numbers == driver_number]
            if not driver_laps.empty and "LapNumber" in driver_laps.columns:
                lap_values = pd.to_numeric(driver_laps["LapNumber"], errors="coerce").dropna()
                if not lap_values.empty:
                    retired_lap = int(lap_values.max())
            if not driver_laps.empty:
                driver_laps_sorted = driver_laps.sort_values("LapNumber")
                final_lap_row = driver_laps_sorted.iloc[-1]
                for key in ("LapEndTime", "LapStartTime", "Time"):
                    timestamp_candidate = final_lap_row.get(key)
                    retire_time = _extract_seconds(timestamp_candidate)
                    if retire_time is not None:
                        break

        if retired_lap is None:
            cached_lap = _track_map_driver_laps.get(driver_number)
            if isinstance(cached_lap, int) and cached_lap >= 1:
                retired_lap = cached_lap

        if retire_time is None and isinstance(positions_df, pd.DataFrame) and not positions_df.empty:
            try:
                driver_slice = positions_df[positions_df["driver_number"] == str(driver_number)]
            except Exception:  # noqa: BLE001
                driver_slice = pd.DataFrame()
            if not driver_slice.empty and "time" in driver_slice.columns:
                time_series = pd.to_numeric(driver_slice["time"], errors="coerce").dropna()
                if not time_series.empty:
                    retire_time = float(time_series.max())

        if isinstance(retire_time, (int, float)):
            retire_time = max(0.0, float(retire_time) - time_offset)

        retirements[driver_number] = {
            "status": status_text or "Retired",
            "lap": retired_lap,
            "time": retire_time,
        }

    ordered = sorted(
        retirements.items(),
        key=lambda item: (
            item[1]["lap"] if item[1]["lap"] is not None else float("inf"),
            item[0],
        ),
    )
    _track_map_retirement_order = [driver for driver, _ in ordered]
    for idx, driver in enumerate(_track_map_retirement_order):
        retirements[driver]["order"] = idx

    _track_map_retirements = retirements
    return _track_map_retirements


def _build_track_map_driver_data(
    focused_driver_value: Optional[str] = None,
    current_lap: Optional[int] = None,
    retirements: Optional[Dict[int, Dict[str, Any]]] = None,
    elapsed_time_seconds: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Collect driver metadata for the track map dashboard."""
    if current_session_obj is None:
        return []

    driver_entries: List[Dict[str, Any]] = []
    _, focus_driver_number = _parse_driver_selector_value(focused_driver_value)
    retirement_lookup = retirements or _track_map_retirements

    try:
        results = getattr(current_session_obj, "results", None)
        if isinstance(results, pd.DataFrame) and not results.empty:
            seen_numbers: set[int] = set()
            for _, row in results.iterrows():
                raw_driver_number = row.get("DriverNumber")
                if raw_driver_number is None:
                    continue
                if isinstance(raw_driver_number, float) and math.isnan(raw_driver_number):
                    continue

                try:
                    driver_number = int(raw_driver_number)
                except (TypeError, ValueError):
                    continue

                if driver_number in seen_numbers:
                    continue

                driver_name = (
                    row.get("BroadcastName")
                    or row.get("FullName")
                    or row.get("Driver")
                    or row.get("Name")
                    or f"Driver {driver_number}"
                )
                team_name = (
                    row.get("TeamName")
                    or row.get("Team")
                    or row.get("ConstructorName")
                    or row.get("ConstructorTeamName")
                    or "Unknown"
                )

                lap_hint = _track_map_driver_laps.get(driver_number)
                if not isinstance(lap_hint, int) or lap_hint < 1:
                    lap_hint = None

                driver_entries.append({
                    "driver_number": driver_number,
                    "driver_name": str(driver_name),
                    "team_name": str(team_name),
                    "is_focus_driver": driver_number == focus_driver_number,
                    "lap_fallback": lap_hint,
                    "retired": False,
                    "retired_lap": None,
                    "retired_status": None,
                    "retired_order": None,
                })
                seen_numbers.add(driver_number)

    except Exception as exc:  # noqa: BLE001
        dash_logger.warning("Unable to build track map driver list: %s", exc)

    driver_entries.sort(key=lambda item: item["driver_number"])

    if retirement_lookup:
        for entry in driver_entries:
            driver_number = entry["driver_number"]
            retirement_info = retirement_lookup.get(driver_number)
            if retirement_info is None:
                continue

            retired_lap = retirement_info.get("lap")
            retired_status = retirement_info.get("status") or "Retired"
            retired_order = retirement_info.get("order")
            retired_time = retirement_info.get("time")

            should_flag = False
            if isinstance(retired_time, Real) and math.isfinite(retired_time) and elapsed_time_seconds is not None:
                should_flag = elapsed_time_seconds >= float(retired_time)
            elif retired_lap is None:
                should_flag = True
            elif isinstance(retired_lap, int):
                if current_lap is not None:
                    should_flag = current_lap >= max(retired_lap, 1)
                else:
                    cached_lap = _track_map_driver_laps.get(driver_number)
                    if isinstance(cached_lap, int):
                        should_flag = cached_lap >= max(retired_lap, 1)

            if should_flag:
                entry["retired"] = True
                entry["retired_lap"] = int(retired_lap) if isinstance(retired_lap, int) else None
                entry["retired_status"] = retired_status
                entry["retired_order"] = int(retired_order) if isinstance(retired_order, int) else 0
                if entry["lap_fallback"] is None and isinstance(retired_lap, int):
                    entry["lap_fallback"] = retired_lap

    return driver_entries


def get_llm_provider() -> Optional[LLMProvider]:
    """
    Get or initialize the LLM provider (singleton).
    
    Logic:
    - If both keys configured: Use HybridRouter (balances by complexity)
    - If only Claude key: Use ClaudeProvider only
    - If only Gemini key: Use GeminiProvider only
    - If no keys: Return None (will show error in chatbot)
    """
    global _llm_provider, _llm_provider_type
    
    if _llm_provider is not None:
        return _llm_provider
    
    # Get API keys from environment
    claude_api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    gemini_api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    
    # No keys configured
    if not claude_api_key and not gemini_api_key:
        logger.warning(
            "No LLM API keys configured. "
            "Set ANTHROPIC_API_KEY or GOOGLE_API_KEY in Configuration."
        )
        return None
    
    try:
        # Case 1: Both keys - use HybridRouter for smart routing
        if claude_api_key and gemini_api_key:
            claude_config = get_claude_config()
            claude_config.max_tokens = 2048
            claude_config.temperature = 0.7

            gemini_config = get_gemini_config()
            gemini_config.max_tokens = 2048
            gemini_config.temperature = 0.7
            gemini_config.extra_params["enable_thinking"] = False
            _llm_provider = HybridRouter(
                claude_config=claude_config,
                gemini_config=gemini_config
            )
            _llm_provider_type = 'hybrid'
            logger.info(
                "LLM initialized: HybridRouter (Claude + Gemini, "
                "routes by complexity)"
            )
        
        # Case 2: Only Claude key
        elif claude_api_key:
            claude_config = get_claude_config()
            claude_config.max_tokens = 2048
            claude_config.temperature = 0.7
            _llm_provider = ClaudeProvider(claude_config)
            _llm_provider_type = 'claude'
            logger.info("LLM initialized: Claude only")
        
        # Case 3: Only Gemini key
        elif gemini_api_key:
            gemini_config = get_gemini_config()
            gemini_config.max_tokens = 2048
            gemini_config.temperature = 0.7
            gemini_config.extra_params["enable_thinking"] = False
            _llm_provider = GeminiProvider(gemini_config)
            _llm_provider_type = 'gemini'
            logger.info("LLM initialized: Gemini only")
        
        return _llm_provider
        
    except Exception as e:
        logger.error(f"Failed to initialize LLM provider: {e}")
        return None


def get_llm_provider_type() -> Optional[str]:
    """Get the type of LLM provider currently in use."""
    return _llm_provider_type


def get_last_completed_race_context() -> RaceContext:
    """
    Get the most recent completed race from OpenF1.

    Falls back to a default if OpenF1 is unavailable.

    Returns:
        RaceContext with the last completed race information.
    """
    # Try to get from OpenF1
    race_context = get_last_completed_race(openf1_provider)

    if race_context:
        logger.info(
            f"Found last completed race: {race_context.country} GP "
            f"(Round {race_context.round_number}, {race_context.year})"
        )
        return race_context

    # Fallback: return a sensible default (last known race)
    logger.warning(
        "Could not find last race from OpenF1, using fallback"
    )
    return RaceContext(
        year=datetime.now().year,
        round_number=1,
        circuit_name="Unknown Circuit",
        circuit_key="unknown",
        country="Unknown",
        session_type=SessionType.RACE,
        session_date=datetime.now(),
        total_laps=57,
        current_lap=1
    )


def load_f1_calendar(year: int) -> pd.DataFrame:
    """Return season schedule tagged with race or testing metadata."""
    if year in _CALENDAR_CACHE:
        return _CALENDAR_CACHE[year]

    if year < 2023:
        logger.warning(f"OpenF1 data not available for year {year}. Use 2023-2025.")
        return pd.DataFrame()

    calendar_cache_path = PROCESSED_CACHE_DIR / "calendar" / f"{year}_calendar{CACHE_FILE_EXTENSION}"
    meetings_df = _read_cache_dataframe(calendar_cache_path)
    if meetings_df is not None and not meetings_df.empty:
        logger.info(
            "Loaded %s meetings for %s from cache (%s)",
            len(meetings_df),
            year,
            calendar_cache_path,
        )
    else:
        meetings_df = openf1_provider.get_meetings(year=year)
        if meetings_df is None or meetings_df.empty:
            logger.warning(f"No meeting data available for year {year}")
            return pd.DataFrame()

    meetings_df = meetings_df.copy()
    rename_map = {
        "meeting_key": "MeetingKey",
        "MeetingKey": "MeetingKey",
        "meeting_name": "MeetingName",
        "MeetingName": "MeetingName",
        "meeting_official_name": "OfficialName",
        "official_name": "OfficialName",
        "MeetingOfficialName": "OfficialName",
        "location": "Location",
        "Location": "Location",
        "country_name": "Country",
        "Country": "Country",
        "circuit_short_name": "CircuitShortName",
        "Circuit": "CircuitShortName",
        "year": "Year",
        "StartDate": "EventDate",
        "date_start": "EventDate",
        "meeting_start": "EventDate",
    }
    meetings_df = meetings_df.rename(columns=rename_map)

    if "EventDate" in meetings_df.columns:
        meetings_df["EventDate"] = pd.to_datetime(meetings_df["EventDate"], errors="coerce")
    else:
        meetings_df["EventDate"] = pd.NaT

    if "EventName" not in meetings_df.columns:
        if "MeetingName" in meetings_df.columns and meetings_df["MeetingName"].notna().any():
            meetings_df["EventName"] = meetings_df["MeetingName"].fillna("")
        else:
            country_series = meetings_df.get("Country")
            if isinstance(country_series, pd.Series):
                meetings_df["EventName"] = country_series.fillna("").astype(str) + " Grand Prix"
            else:
                meetings_df["EventName"] = "Grand Prix"

    meetings_records = _normalize_record_keys(meetings_df.to_dict("records"))

    session_cache_dir = PROCESSED_CACHE_DIR / "session_list" / str(year)
    cached_session_keys: Set[int] = set()
    sessions_by_meeting: Dict[int, List[Dict[str, Any]]] = {}
    if session_cache_dir.exists():
        for cache_file in session_cache_dir.glob(f"*{CACHE_FILE_EXTENSION}"):
            cached_df = _read_cache_dataframe(cache_file)
            if cached_df is None or cached_df.empty:
                continue
            cached_records_raw = cached_df.to_dict("records")
            if not cached_records_raw:
                continue
            cached_records = _normalize_record_keys(cached_records_raw)
            sample = cached_records[0]
            meeting_key_val = sample.get("meeting_key") or sample.get("MeetingKey")
            if meeting_key_val is None:
                continue
            try:
                meeting_key_int = int(meeting_key_val)
            except (TypeError, ValueError):
                continue
            sessions_by_meeting[meeting_key_int] = cached_records
            cached_session_keys.add(meeting_key_int)

    meeting_keys: List[int] = []
    for record in meetings_records:
        meeting_key_val = record.get("MeetingKey")
        if meeting_key_val is None:
            continue
        try:
            meeting_key_int = int(meeting_key_val)
        except (TypeError, ValueError):
            continue
        meeting_keys.append(meeting_key_int)

    missing_session_keys = [key for key in meeting_keys if key not in sessions_by_meeting]

    session_payloads_by_meeting: Dict[int, List[Dict[str, Any]]] = {
        key: value for key, value in sessions_by_meeting.items()
    }

    if missing_session_keys:
        try:
            session_payloads = openf1_provider._request("sessions", {"year": year})
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to load sessions for %s: %s", year, exc)
            session_payloads = []

        grouped_sessions: Dict[int, List[Dict[str, Any]]] = {}
        for payload in session_payloads:
            normalized_payload = {str(key): value for key, value in payload.items()}
            key_val = normalized_payload.get("meeting_key") or normalized_payload.get("MeetingKey")
            if key_val is None:
                continue
            try:
                key_int = int(key_val)
            except (TypeError, ValueError):
                continue
            grouped_sessions.setdefault(key_int, []).append(normalized_payload)

        for key in missing_session_keys:
            if key in grouped_sessions:
                session_payloads_by_meeting[key] = grouped_sessions[key]

    race_counter = 1
    test_counter = 1
    records: List[Dict[str, Any]] = []
    calendar_metadata: Dict[int, Dict[str, Any]] = {}

    def _build_slug_from_record(record: Dict[str, Any]) -> str:
        payload = {
            "date_start": record.get("EventDate"),
            "meeting_start": record.get("EventDate"),
            "meeting_name": record.get("MeetingName") or record.get("EventName"),
            "official_name": record.get("OfficialName"),
            "location": record.get("Location"),
            "country_name": record.get("Country"),
            "year": record.get("Year") or year,
        }
        return cache_generation_service._build_meeting_slug(payload)

    for record in meetings_records:
        meeting_key_val = record.get("MeetingKey")
        if meeting_key_val is None:
            logger.warning("Skipping meeting with missing key value")
            continue
        try:
            meeting_key = int(meeting_key_val)
        except (TypeError, ValueError):
            logger.warning("Skipping meeting with invalid key: %s", meeting_key_val)
            continue

        session_payloads = session_payloads_by_meeting.get(meeting_key, [])
        codes_seen: Set[str] = set()
        raw_texts: Set[str] = set()
        for payload in session_payloads:
            for key in ("session_type", "session_code", "session_name"):
                raw_value = payload.get(key)
                if raw_value is None:
                    continue
                text_value = str(raw_value).strip()
                if text_value:
                    raw_texts.add(text_value.lower())
                code = CacheGenerationService._canonical_session_code(raw_value)
                if code:
                    codes_seen.add(code)

        practice_codes: Set[str] = {"P1", "P2", "P3"}
        has_canonical_race = "R" in codes_seen
        has_competition_hint = bool(codes_seen - practice_codes) or any(
            "race" in text or "grand prix" in text for text in raw_texts
        )
        has_day_hint = any("day" in text for text in raw_texts)

        is_race_weekend = has_canonical_race or has_competition_hint
        if not is_race_weekend and has_day_hint:
            is_race_weekend = False
        if not session_payloads and isinstance(record.get("EventName"), str):
            if "testing" in record["EventName"].lower():
                is_race_weekend = False

        country = str(record.get("Country") or "")
        location = str(record.get("Location") or "")
        event_year = record.get("Year") or year
        circuit_short_name = record.get("CircuitShortName")
        event_date_val = record.get("EventDate")
        event_name = record.get("EventName") or (f"{country} Grand Prix" if country else "Grand Prix")

        if is_race_weekend:
            round_number: Optional[int] = race_counter
            test_number: Optional[int] = None
            race_counter += 1
        else:
            round_number = None
            test_number = test_counter
            test_counter += 1

        cache_slug = _build_slug_from_record(record)
        records.append({
            "MeetingKey": meeting_key,
            "Country": country,
            "Location": location,
            "EventDate": event_date_val,
            "Year": event_year,
            "CircuitShortName": circuit_short_name,
            "RoundNumber": round_number,
            "TestNumber": test_number,
            "IsRaceWeekend": is_race_weekend,
            "SessionCodes": sorted(codes_seen),
            "EventName": event_name,
            "CacheSlug": cache_slug,
            "SessionSource": "cache" if meeting_key in cached_session_keys else "api",
        })

        calendar_metadata[meeting_key] = {
            "cache_slug": cache_slug,
            "is_race_weekend": is_race_weekend,
            "session_codes": sorted(codes_seen),
            "session_source": "cache" if meeting_key in cached_session_keys else "api",
        }

    calendar = pd.DataFrame(records)
    if calendar.empty:
        logger.warning(f"No meetings constructed for year {year}")
        return calendar

    calendar = calendar.sort_values("EventDate")

    logger.info(
        "Loaded %s meetings for %s (races=%s, tests=%s)",
        len(calendar),
        year,
        calendar["IsRaceWeekend"].sum(),
        (~calendar["IsRaceWeekend"]).sum(),
    )

    _CALENDAR_CACHE[year] = calendar
    _CALENDAR_METADATA[year] = calendar_metadata
    return calendar


def get_available_sessions(
    schedule: pd.DataFrame,
    round_number: int
) -> list[tuple[str, SessionType]]:
    """Get available sessions for a specific race."""
    event = schedule[schedule['RoundNumber'] == round_number].iloc[0]
    
    sessions = []
    
    # Check each session column in the event
    for i in range(1, 6):
        col = f'Session{i}'
        session_value = event.get(col)
        
        if pd.notna(session_value):
            session_str = str(session_value)
            
            # Determine session name and type based on content
            if 'Practice 1' in session_str or session_str == 'Practice 1':
                sessions.append(('FP1', SessionType.FP1))
            elif 'Practice 2' in session_str or session_str == 'Practice 2':
                sessions.append(('FP2', SessionType.FP2))
            elif 'Practice 3' in session_str or session_str == 'Practice 3':
                sessions.append(('FP3', SessionType.FP3))
            elif 'Sprint Shootout' in session_str or 'Sprint Qualifying' in session_str:
                sessions.append(('Sprint Qualifying', SessionType.SPRINT_QUALIFYING))
            elif 'Sprint' in session_str and 'Qualifying' not in session_str and 'Shootout' not in session_str:
                sessions.append(('Sprint', SessionType.SPRINT))
            elif 'Qualifying' in session_str:
                sessions.append(('Qualifying', SessionType.QUALIFYING))
            elif 'Race' in session_str:
                sessions.append(('Race', SessionType.RACE))
    
    return sessions


# ============================================================================
# SIDEBAR COMPONENT
# ============================================================================

def create_sidebar():
    """Create sidebar with all controls."""
    return dbc.Col([
        html.Div([
            html.H4([
                html.Span("🏎️", style={'fontSize': '3rem'}),
                " F1 Strategist"
            ], className="text-center mb-1"),
            
            html.Hr(),
            
            # Mode selector (collapsed)
            dbc.Accordion([
                dbc.AccordionItem([
                    dbc.RadioItems(
                        id="mode-selector",
                        options=[
                            {"label": " 🏁 Live", "value": "live"},
                            {"label": " ⏯️ Simulation", "value": "sim"}
                        ],
                        value="sim",
                        className="mb-1"
                    ),
                    dbc.Button(
                        "Manage caches",
                        id='cache-manager-open',
                        color='secondary',
                        size='sm',
                        className='w-100 mt-2',
                        outline=True,
                    ),
                ], title="🎮 Mode", className="mb-1")
            ], start_collapsed=True),
            
            html.Hr(),
            
            # Context selector (expanded by default)
            dbc.Accordion([
                dbc.AccordionItem([
                    dbc.Label("Year", className="fw-bold"),
                    dcc.Dropdown(
                        id='year-selector',
                        options=[
                            {'label': str(y), 'value': y} 
                            for y in range(2025, 2017, -1)
                        ],
                        value=2025,
                        className="mb-1",
                        clearable=False
                    ),
                    
                    dbc.Label("Circuit", className="fw-bold"),
                    dcc.Dropdown(
                        id='circuit-selector',
                        options=[],  # Will be populated by callback
                        value=None,
                        className="mb-1",
                        clearable=False
                    ),
                    
                    dbc.Label("Session", className="fw-bold"),
                    dcc.Dropdown(
                        id='session-selector',
                        options=[],  # Will be populated by callback
                        value=None,
                        className="mb-1",
                        clearable=False
                    ),
                    
                    dbc.Label("Driver", className="fw-bold"),
                    html.Div(id='driver-dropdown-container', children=[
                        dcc.Loading(
                            dcc.Dropdown(
                                id='driver-selector',
                                options=[],
                                value=None,
                                placeholder="Loading drivers...",
                                className="mb-1",
                                clearable=True
                            ),
                            type="circle",
                            color="#e10600"
                        )
                    ])
                ], title="🗺️ Context", className="mb-1")
            ], start_collapsed=False),
            
            html.Hr(),
            
            # Dashboard selector (collapsed)
            dbc.Accordion([
                dbc.AccordionItem([
                    dbc.Checklist(
                        id="dashboard-selector",
                        options=[
                            {"label": " AI Assistant", "value": "ai"},
                            {
                                "label": " Race Overview",
                                "value": "race_overview",
                                "disabled": True  # Must stay visible in sim/live
                            },
                            {"label": " Race Control", "value": "race_control"},
                            {
                                "label": " Track Map",
                                "value": "track_map",
                                "disabled": True
                            },
                            {"label": " Weather", "value": "weather"},
                            {"label": " Telemetry", "value": "telemetry"},
                            # Phase 2 Dashboards (Coming Soon)
                            # {"label": " Tire Strategy", "value": "tires"},
                            # {"label": " Lap Analysis", "value": "laps"},
                            # {"label": " Qualifying", "value": "qualifying"},
                        ],
                        value=["ai", "race_overview", "track_map", "race_control", "weather", "telemetry"],
                        className="mb-1"
                    )
                ], title="📊 Dashboards", className="mb-1")
            ], start_collapsed=True),
            
            html.Hr(),
            
            # Simulation controls (collapsed)
            dbc.Accordion([
                dbc.AccordionItem([
                    dbc.Row([
                        dbc.Col([
                            dbc.Button(
                                "▶️",
                                id="play-btn",
                                color="success",
                                className="w-100 mb-1"
                            ),
                            dbc.Tooltip(
                                "Play simulation",
                                target="play-btn",
                                placement="top",
                                id="play-btn-tooltip"
                            )
                        ], width=6),
                        dbc.Col([
                            dbc.Button(
                                "⏮️",
                                id="restart-btn",
                                color="secondary",
                                className="w-100 mb-1"
                            ),
                            dbc.Tooltip("Restart simulation", target="restart-btn", placement="top")
                        ], width=6)
                    ]),
                    
                    dbc.Label("Speed", className="mt-1"),
                    dcc.Slider(
                        id='speed-slider',
                        min=1.0,
                        max=10.0,
                        step=0.5,
                        value=1.0,
                        marks={
                            1.0: '1x',
                            2.0: '2x',
                            4.0: '4x',
                            6.0: '6x',
                            8.0: '8x',
                            10.0: '10x'
                        },
                        className="mb-1"
                    ),
                    
                    dbc.Row([
                        dbc.Col([
                            dbc.Button(
                                "⏪",
                                id="back-btn",
                                color="secondary",
                                className="w-100"
                            ),
                            dbc.Tooltip("Previous lap", target="back-btn", placement="bottom")
                        ], width=6),
                        dbc.Col([
                            dbc.Button(
                                "⏩",
                                id="forward-btn",
                                color="secondary",
                                className="w-100"
                            ),
                            dbc.Tooltip("Next lap", target="forward-btn", placement="bottom")
                        ], width=6)
                    ]),
                    
                    html.Div(
                        id="simulation-progress",
                        children="⏱️ Not started",
                        className="text-center mt-1 small text-muted"
                    ),
                    
                    # Interval for updating simulation progress
                    # Base interval is 1.5 seconds, adjusted dynamically by speed
                    dcc.Interval(
                        id='simulation-interval',
                        interval=1500,  # milliseconds (1.5 seconds base)
                        n_intervals=0,
                        disabled=True  # Start disabled, enable when playing
                    )
                ], title="⏯️ Playback", className="mb-1", id="playback-accordion-item")
            ], start_collapsed=True, id="playback-accordion"),
            
            html.Hr(),
            
            # Hidden dummy components for removed FIA Manager (to keep callbacks working)
            html.Div([
                dcc.Dropdown(id='fia-year-selector', style={'display': 'none'}),
                html.Div(id='fia-reg-status', style={'display': 'none'}),
                html.Div(id='fia-existing-regs', style={'display': 'none'}),
                dcc.Upload(id='fia-reg-upload', style={'display': 'none'}),
                html.Div(id='fia-upload-preview', style={'display': 'none'}),
            ], style={'display': 'none'}),
            
            # RAG Documents Section
            dbc.Accordion([
                dbc.AccordionItem([
                    # RAG Status indicator
                    html.Div([
                        html.Span(id="rag-status", children="⚪ Not loaded"),
                        html.Small(
                            id="rag-doc-count",
                            className="text-muted ms-2"
                        )
                    ], className="mb-1"),
                    
                    # Document list by category
                    html.Div([
                        # Global Documents
                        html.Div([
                            html.Div([
                                html.H6(
                                    "🌐 Global",
                                    className="text-info mb-1 d-inline-block",
                                    style={'fontSize': '0.85rem'}
                                ),
                                html.Button(
                                    "+",
                                    id={'type': 'rag-upload-btn', 'category': 'global'},
                                    n_clicks=0,
                                    className="btn btn-sm btn-outline-info ms-2",
                                    style={'fontSize': '0.7rem', 'padding': '0px 6px', 'lineHeight': '1.2'}
                                )
                            ], className="d-flex align-items-center"),
                            html.Div(
                                id="rag-global-docs",
                                className="ps-2 small text-muted"
                            )
                        ], className="mb-1"),
                        
                        # Strategy Documents
                        html.Div([
                            html.Div([
                                html.H6(
                                    "📋 Strategy",
                                    className="text-info mb-1 d-inline-block",
                                    style={'fontSize': '0.85rem'}
                                ),
                                html.Button(
                                    "+",
                                    id={'type': 'rag-upload-btn', 'category': 'strategy'},
                                    n_clicks=0,
                                    className="btn btn-sm btn-outline-info ms-2",
                                    style={'fontSize': '0.7rem', 'padding': '0px 6px', 'lineHeight': '1.2'}
                                )
                            ], className="d-flex align-items-center"),
                            html.Div(
                                id="rag-strategy-docs",
                                className="ps-2 small text-muted"
                            )
                        ], className="mb-1"),
                        
                        # Weather Documents
                        html.Div([
                            html.Div([
                                html.H6(
                                    "🌦️ Weather",
                                    className="text-info mb-1 d-inline-block",
                                    style={'fontSize': '0.85rem'}
                                ),
                                html.Button(
                                    "+",
                                    id={'type': 'rag-upload-btn', 'category': 'weather'},
                                    n_clicks=0,
                                    className="btn btn-sm btn-outline-info ms-2",
                                    style={'fontSize': '0.7rem', 'padding': '0px 6px', 'lineHeight': '1.2'}
                                )
                            ], className="d-flex align-items-center"),
                            html.Div(
                                id="rag-weather-docs",
                                className="ps-2 small text-muted"
                            )
                        ], className="mb-1"),
                        
                        # Performance Documents
                        html.Div([
                            html.Div([
                                html.H6(
                                    "📊 Performance",
                                    className="text-info mb-1 d-inline-block",
                                    style={'fontSize': '0.85rem'}
                                ),
                                html.Button(
                                    "+",
                                    id={'type': 'rag-upload-btn', 'category': 'performance'},
                                    n_clicks=0,
                                    className="btn btn-sm btn-outline-info ms-2",
                                    style={'fontSize': '0.7rem', 'padding': '0px 6px', 'lineHeight': '1.2'}
                                )
                            ], className="d-flex align-items-center"),
                            html.Div(
                                id="rag-performance-docs",
                                className="ps-2 small text-muted"
                            )
                        ], className="mb-1"),
                        
                        # Race Control Documents
                        html.Div([
                            html.Div([
                                html.H6(
                                    "🚦 Race Control",
                                    className="text-info mb-1 d-inline-block",
                                    style={'fontSize': '0.85rem'}
                                ),
                                html.Button(
                                    "+",
                                    id={'type': 'rag-upload-btn', 'category': 'race_control'},
                                    n_clicks=0,
                                    className="btn btn-sm btn-outline-info ms-2",
                                    style={'fontSize': '0.7rem', 'padding': '0px 6px', 'lineHeight': '1.2'}
                                )
                            ], className="d-flex align-items-center"),
                            html.Div(
                                id="rag-race-control-docs",
                                className="ps-2 small text-muted"
                            )
                        ], className="mb-1"),
                        
                        # Race Position Documents
                        html.Div([
                            html.Div([
                                html.H6(
                                    "🏁 Positions",
                                    className="text-info mb-1 d-inline-block",
                                    style={'fontSize': '0.85rem'}
                                ),
                                html.Button(
                                    "+",
                                    id={'type': 'rag-upload-btn', 'category': 'race_position'},
                                    n_clicks=0,
                                    className="btn btn-sm btn-outline-info ms-2",
                                    style={'fontSize': '0.7rem', 'padding': '0px 6px', 'lineHeight': '1.2'}
                                )
                            ], className="d-flex align-items-center"),
                            html.Div(
                                id="rag-race-position-docs",
                                className="ps-2 small text-muted"
                            )
                        ], className="mb-1"),
                        
                        # FIA Regulations Documents
                        html.Div([
                            html.Div([
                                html.H6(
                                    "📖 FIA Regulations",
                                    className="text-info mb-1 d-inline-block",
                                    style={'fontSize': '0.85rem'}
                                ),
                                html.Button(
                                    "+",
                                    id={'type': 'rag-upload-btn', 'category': 'fia'},
                                    n_clicks=0,
                                    className="btn btn-sm btn-outline-info ms-2",
                                    style={'fontSize': '0.7rem', 'padding': '0px 6px', 'lineHeight': '1.2'}
                                )
                            ], className="d-flex align-items-center"),
                            html.Div(
                                id="rag-fia-docs",
                                className="ps-2 small text-muted"
                            )
                        ], className="mb-1"),
                    ]),
                    
                    # Hidden Upload Components (one per category)
                    html.Div([
                        dcc.Upload(
                            id={'type': 'rag-upload-input', 'category': cat},
                            accept='.pdf,.docx,.md',
                            max_size=10*1024*1024,  # 10MB
                            style={'display': 'none'}
                        ) for cat in ['global', 'strategy', 'weather', 'performance', 'race_control', 'race_position', 'fia']
                    ]),
                    
                    # Action buttons
                    html.Div([
                        dbc.Button(
                            "🔄 Reload",
                            id="rag-reload-btn",
                            size="sm",
                            color="secondary",
                            outline=True,
                            className="me-2"
                        ),
                        dbc.Button(
                            "📝 Generate",
                            id="rag-generate-btn",
                            size="sm",
                            color="info",
                            outline=True,
                            title="Generate circuit templates from historical data"
                        ),
                    ], className="mt-1 d-flex"),
                    
                    # RAG reload status message
                    html.Div(
                        id="rag-reload-status",
                        className="small text-muted mt-1"
                    )
                ], title="📚 RAG Documents", className="mb-1")
            ], start_collapsed=True, id="rag-accordion"),
            
            html.Hr(),
            
            # Menu (collapsed)
            dbc.Accordion([
                dbc.AccordionItem([
                    # Config option
                    html.Div([
                        # API Keys
                        html.Div([
                            html.P("🔑 API Keys", className="fw-bold mb-1"),
                            dbc.Label("Claude API Key", className="small"),
                            dbc.Input(
                                id='claude-api-key-input',
                                type="password",
                                placeholder="Enter Anthropic Claude API Key",
                                value=os.getenv("ANTHROPIC_API_KEY", ""),
                                className="mb-1",
                                style={'fontSize': '0.85rem'}
                            ),
                            dbc.Label("Gemini API Key", className="small"),
                            dbc.Input(
                                id='gemini-api-key-input',
                                type="password",
                                placeholder="Enter Google Gemini API Key",
                                value=os.getenv("GOOGLE_API_KEY", ""),
                                className="mb-1",
                                style={'fontSize': '0.85rem'}
                            ),
                            dbc.Label("OpenF1 API Key", className="small"),
                            dbc.Input(
                                id='openf1-api-key-input',
                                type="password",
                                placeholder="Enter OpenF1 API Key",
                                value=os.getenv("OPENF1_API_KEY", ""),
                                className="mb-1",
                                style={'fontSize': '0.85rem'}
                            ),
                            dbc.Button(
                                "💾 Save Keys",
                                id="save-api-keys-btn",
                                color="primary",
                                size="sm",
                                className="w-100 mb-1"
                            ),
                            html.Div(id="api-keys-save-status", className="small text-muted")
                        ], className="mb-1"),
                        
                        # LLM Settings
                        html.Div([
                            html.P("🤖 LLM Settings", className="fw-bold mb-1"),
                            dbc.Label("Provider", className="small"),
                            dcc.Dropdown(
                                id='llm-provider-selector',
                                options=[
                                    {'label': 'Hybrid (Auto)', 'value': 'hybrid'},
                                    {'label': 'Claude Only', 'value': 'claude'},
                                    {'label': 'Gemini Only', 'value': 'gemini'}
                                ],
                                value='hybrid',
                                className="mb-1",
                                clearable=False,
                                style={'fontSize': '0.85rem'}
                            )
                        ], className="mb-1"),
                        
                        # Data Sources
                        html.Div([
                            html.P("📂 Data Sources", className="fw-bold mb-1"),
                            html.Small(f"Cache: ./cache", className="text-muted d-block"),
                            html.Small(f"Vector Store: ChromaDB", className="text-muted d-block")
                        ])
                    ])
                ], title="⚙️ Configuration", className="mb-1")
            ], start_collapsed=True),
            
            # Help button
            dbc.Button(
                [html.I(className="bi bi-question-circle me-1"), "Help"],
                id="help-btn",
                color="info",
                outline=True,
                size="sm",
                className="w-100"
            )
            
        ], className="p-3", style={
            'height': '100vh',
            'overflow-y': 'auto',
            'background-color': '#1a1a1a'
        })
    ], width=2, id='sidebar-column', className="border-end border-secondary")


# ============================================================================
# MAIN CONTENT AREA
# ============================================================================

def create_main_content():
    """Create main content area with dashboard placeholders."""
    return dbc.Col([
        # Toggle sidebar button
        html.Div([
            dbc.Button(
                "<<",
                id='sidebar-toggle-btn',
                color="dark",
                size="sm",
                className="mb-2",
                style={'position': 'fixed', 'top': '10px', 'left': '10px', 'zIndex': '1000', 'fontSize': '0.7rem', 'fontWeight': 'bold', 'padding': '2px 6px'}
            ),
            dbc.Tooltip(
                "Hide sidebar",
                target="sidebar-toggle-btn",
                placement="right"
            )
        ]),
        html.Div([
            # Dashboard container - will be populated dynamically
            html.Div(id='dashboard-container', children=[
                html.Div([
                    html.H3(
                        "🏎️ F1 Strategist AI",
                        className="text-center mt-5"
                    ),
                    html.P(
                        "Select dashboards from the sidebar to begin",
                        className="text-center text-muted"
                    )
                ], className="text-center")
            ])
        ], className="p-3")
    ], width=10, id='main-content-column')


# ============================================================================
# APP LAYOUT
# ============================================================================

# Responsive CSS is loaded from assets/responsive_grid.css automatically by Dash

app.layout = dbc.Container([
    # Store components for state management
    dcc.Store(id='session-store', data={}),
    dcc.Store(id='session-bootstrap-store', data={}),
    dcc.Store(id='user-prefs-store', data={
        'focused_driver': 'VER',
        'visible_dashboards': ['circuit', 'ai']
    }),
    dcc.Store(id='cache-buster-store', data={'timestamp': 0}),
    dcc.Store(id='sidebar-visible-store', data=True),
    dcc.Store(id='simulation-time-store', data={'time': 0.0, 'timestamp': 0}),
    dcc.Store(id='current-lap-store', data={'lap': 1, 'total': 57}),  # For fast lap updates
    dcc.Store(
        id='track-map-trajectory-store',
        data={'time_offset': 0.0, 'time_bounds': [0.0, 0.0], 'laps': {}},
    ),
    dcc.Store(id='weather-last-update-store', data={'timestamp': 0, 'state': None}),
    
    # Telemetry comparison driver store
    dcc.Store(id='telemetry-comparison-store', data={'driver': None}),
    
    # AI Chat stores
    dcc.Store(id='chat-messages-store', storage_type='memory', data=[]),
    dcc.Store(id='chat-pending-query-store', data={'query': None, 'quick': None}),
    dcc.Store(id='proactive-last-check-store', data={'last_lap': 0}),
    dcc.Store(id='cache-progress-store', data={
        'status': 'idle',
        'completed': 0,
        'total': 0,
        'message': '',
        'error': None,
        'timestamp': None,
    }),
    dcc.Interval(
        id='cache-progress-poll',
        interval=1000,
        n_intervals=0,
        disabled=True,
    ),
    
    # Interval for proactive AI alerts (every 15 seconds when simulation running)
    dcc.Interval(
        id='proactive-check-interval',
        interval=15000,  # 15 seconds
        n_intervals=0,
        disabled=True  # Enable when simulation is playing
    ),
    
    # Cache Manager Modal
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("🗂️ Cache Management")),
        dbc.ModalBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Year", className="fw-bold"),
                    dcc.Dropdown(
                        id='cache-year-selector',
                        options=[{"label": str(year), "value": year} for year in CACHE_AVAILABLE_YEARS],
                        value=CACHE_AVAILABLE_YEARS[0] if CACHE_AVAILABLE_YEARS else None,
                        clearable=False,
                        className="mb-2",
                    ),
                    dbc.Label("Circuit", className="fw-bold"),
                    dcc.Dropdown(
                        id='cache-meeting-selector',
                        options=[],
                        value=None,
                        placeholder="Select meeting",
                        className="mb-2",
                    ),
                    dbc.Label("Session", className="fw-bold"),
                    dcc.Dropdown(
                        id='cache-session-selector',
                        options=[],
                        value=None,
                        placeholder="Select session",
                        className="mb-2",
                    ),
                    dbc.Label("Cache types", className="fw-bold"),
                    dbc.Checklist(
                        id='cache-type-checklist',
                        options=cast(Sequence[Any], CACHE_ARTIFACT_OPTIONS),
                        value=CACHE_DEFAULT_SELECTION,
                        className="border rounded p-2",
                    ),
                ], md=5),
                dbc.Col([
                    dbc.Alert(
                        id='cache-error-alert',
                        color='danger',
                        is_open=False,
                        className="py-2 mb-2"
                    ),
                    html.Div(id='cache-status-summary', className='mb-2'),
                    dcc.Loading(
                        dbc.Table(
                            id='cache-status-table',
                            bordered=True,
                            striped=True,
                            hover=True,
                            size='sm',
                            className='mb-2'
                        ),
                        type="circle",
                        color="#e10600",
                    ),
                    dbc.Progress(
                        id='cache-progress-bar',
                        value=0,
                        max=1,
                        label='',
                        striped=True,
                        animated=True,
                        className='mb-1'
                    ),
                    html.Small(
                        id='cache-progress-message',
                        className='text-muted'
                    ),
                ], md=7),
            ])
        ]),
        dbc.ModalFooter([
            dbc.Button(
                "Regenerate caches",
                id='cache-regenerate-button',
                color='danger',
                className='me-2'
            ),
            dbc.Button(
                "Generate missing caches",
                id='cache-fill-button',
                color='primary',
                outline=True,
                className='me-2'
            ),
            dbc.Button(
                "Delete caches",
                id='cache-delete-button',
                color='warning',
                outline=True,
                className='me-2'
            ),
            dbc.Button(
                "Close",
                id='cache-modal-close',
                color='secondary'
            )
        ]),
    ], id='cache-manager-modal', size='xl', is_open=False),

    # Help Modal
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("❓ Help & Documentation")),
        dbc.ModalBody([
            html.H5("🚀 Quick Start", className="mb-2"),
            html.Ul([
                html.Li("Load a race via the year / event selectors and let the FastF1 cache warm up."),
                html.Li("Choose Simulation mode to unlock the playback controls and track map dashboards."),
                html.Li("Pick the dashboards you need from the sidebar; the layout updates immediately."),
                html.Li("Press Play to drive the synchronized dashboards; use lap jump buttons for quick rewinds."),
            ], className="mb-3"),

            html.H5("📊 Core Dashboards", className="mb-2"),
            html.Ul([
                html.Li("Track Map: FastF1 telemetry with cached interpolation for smooth XY animation."),
                html.Li("Race Overview: Leaderboard, stints, and driver focus with cached OpenF1 data."),
                html.Li("Weather & Race Control: Real-time flags, incidents, and weather trends."),
                html.Li("Telemetry Comparison: Overlay lap telemetry once drivers are selected."),
            ], className="mb-3"),

            html.H5("🤖 AI Toolkit", className="mb-2"),
            html.Ul([
                html.Li("Hybrid router automatically chooses Claude or Gemini based on availability."),
                html.Li("Strategy prompts read the same simulation state used by dashboards."),
                html.Li("RAG answers come from indexed PDFs and session reports stored in ChromaDB."),
            ], className="mb-3"),

            html.H5("🧰 Troubleshooting", className="mb-2"),
            html.Ul([
                html.Li("Use Cache Manager to regenerate FastF1 or OpenF1 artifacts before race weekends."),
                html.Li("If telemetry freezes, restart playback and check the track map cache status badge."),
                html.Li("Verify API keys under Configuration when AI responses fail."),
            ], className="mb-0"),
        ]),
        dbc.ModalFooter(
            dbc.Button("Close", id="close-help-modal", className="ms-auto", n_clicks=0)
        )
    ], id="help-modal", is_open=False, size="lg"),
    
    # Document Editor Modal (for RAG documents)
    dbc.Modal([
        dbc.ModalHeader([
            dbc.ModalTitle(id="doc-editor-title", children="📝 Edit Document"),
        ]),
        dbc.ModalBody([
            # Document path info
            html.Div([
                html.Small(id="doc-editor-path", className="text-muted")
            ], className="mb-2"),
            # Textarea for editing
            dcc.Textarea(
                id="doc-editor-textarea",
                style={
                    "width": "100%",
                    "height": "450px",
                    "fontFamily": "'Consolas', 'Monaco', monospace",
                    "fontSize": "13px",
                    "lineHeight": "1.5",
                    "padding": "10px",
                    "border": "1px solid #444",
                    "borderRadius": "4px",
                    "backgroundColor": "#1e1e1e",
                    "color": "#d4d4d4"
                },
                placeholder="Document content will appear here..."
            ),
            # Status message
            html.Div(id="doc-editor-status", className="mt-2 small")
        ]),
        dbc.ModalFooter([
            html.Div([
                dbc.Button(
                    "💾 Save",
                    id="doc-editor-save-btn",
                    color="primary",
                    className="me-2"
                ),
                dbc.Button(
                    "Cancel",
                    id="doc-editor-cancel-btn",
                    color="secondary",
                    outline=True
                )
            ])
        ])
    ], id="doc-editor-modal", is_open=False, size="xl", centered=True),
    
    # Hidden store for current document being edited
    dcc.Store(id="doc-editor-store", data={"filepath": None, "category": None}),
    
    # Document Upload Confirmation Modal
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("📤 Confirm Document Upload")),
        dbc.ModalBody([
            # File info section
            html.Div([
                html.H6("📄 File Information", className="text-info mb-2"),
                html.Div(id="upload-file-info", className="mb-3")
            ]),
            
            # Category selection
            html.Div([
                html.H6("📂 Category", className="text-info mb-2"),
                dcc.Dropdown(
                    id='upload-category-override',
                    options=[
                        {'label': '🌐 Global', 'value': 'global'},
                        {'label': '📋 Strategy', 'value': 'strategy'},
                        {'label': '🌦️ Weather', 'value': 'weather'},
                        {'label': '📊 Performance', 'value': 'performance'},
                        {'label': '🚦 Race Control', 'value': 'race_control'},
                        {'label': '🏁 Positions', 'value': 'race_position'},
                        {'label': '📖 FIA Regulations', 'value': 'fia'},
                    ],
                    placeholder="Select document category...",
                    className="mb-3"
                ),
            ]),
            
            # Conversion preview (collapsible)
            html.Div([
                dbc.Button(
                    "👁️ Preview Converted Content",
                    id="upload-preview-toggle",
                    color="info",
                    size="sm",
                    className="mb-2"
                ),
                dbc.Collapse([
                    html.Pre(
                        id="upload-preview-content",
                        className="bg-dark text-light p-2",
                        style={"maxHeight": "200px", "overflow": "auto", "fontSize": "0.75rem"}
                    )
                ], id="upload-preview-collapse", is_open=False)
            ], className="mb-3"),
            
            # Target path
            html.Div([
                html.H6("📍 Target Path", className="text-info mb-2"),
                html.Code(id="upload-target-path", className="d-block p-2 bg-dark text-light")
            ], className="mb-3"),
            
            # Filename editor
            html.Div([
                html.H6("✏️ Filename", className="text-info mb-2"),
                dbc.Input(
                    id="upload-filename-edit",
                    type="text",
                    placeholder="Enter filename (without extension)...",
                    className="mb-2"
                ),
                html.Small("Extension .md will be added automatically", className="text-muted")
            ], className="mb-3"),
            
            # Duplicate warning
            html.Div(id="upload-duplicate-warning", className="mb-2"),
            
            # Processing status/spinner - This will show the loading overlay
            html.Div(id="upload-processing-status", className="text-center"),
            
            # Loading overlay (hidden by default, shown during processing)
            html.Div(
                id="upload-loading-overlay",
                children=[
                    html.Div([
                        dbc.Spinner(color="primary", size="lg"),
                        html.H5("🔄 Processing...", className="mt-3 text-primary"),
                        html.P("Converting PDF to markdown and indexing...", className="text-muted"),
                        html.P("This may take 10-30 seconds for large PDFs", className="text-muted small"),
                    ], className="text-center")
                ],
                style={
                    "display": "none",  # Hidden by default
                    "position": "absolute",
                    "top": 0,
                    "left": 0,
                    "right": 0,
                    "bottom": 0,
                    "backgroundColor": "rgba(0, 0, 0, 0.8)",
                    "zIndex": 1000,
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "center",
                    "borderRadius": "0.3rem"
                }
            )
        ], style={"position": "relative"}),  # Make ModalBody relative for overlay positioning
        dbc.ModalFooter([
            dbc.Button(
                "✅ Upload & Index",
                id="upload-confirm-btn",
                color="primary",
                className="me-2"
            ),
            dbc.Button(
                "❌ Cancel",
                id="upload-cancel-btn",
                color="secondary",
                outline=True
            )
        ])
    ], id="upload-modal", is_open=False, size="lg", centered=True, backdrop="static"),
    
    # Hidden stores for upload state
    dcc.Store(id="upload-file-store", data=None),
    dcc.Store(id="upload-metadata-store", data=None),
    
    # Template Generation Confirmation Modal
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("⚠️ Confirm Template Generation")),
        dbc.ModalBody([
            html.P(id="rag-generate-confirm-message"),
            html.Div(id="rag-generate-existing-files", className="small text-warning")
        ]),
        dbc.ModalFooter([
            dbc.Button(
                "Cancel",
                id="rag-generate-cancel-btn",
                color="secondary",
                className="me-2"
            ),
            dbc.Button(
                "Generate & Overwrite",
                id="rag-generate-confirm-btn",
                color="danger"
            ),
        ])
    ], id="rag-generate-confirm-modal", is_open=False, centered=True),
    
    # Store for tracking template generation state
    dcc.Store(id="rag-generate-store", data={"year": None, "circuit": None}),
    
    # Main layout
    dbc.Row([
        create_sidebar(),
        create_main_content()
    ], className="g-0", style={'height': '100vh'})
], fluid=True, className="vh-100 p-0")


# ============================================================================
# CLIENTSIDE CALLBACKS
# ============================================================================

# (Auto-scroll removed - user prefers seeing newest messages at top)


# ============================================================================
# CALLBACKS
# ============================================================================

# Callback to enable/disable Live mode based on live session availability
@callback(
    Output('mode-selector', 'options'),
    Input('mode-selector', 'value'),  # Dummy input to trigger on load
    prevent_initial_call=False
)
def update_live_mode_availability(_):
    """Check if live session is available and enable/disable Live mode."""
    live_session = check_for_live_session()
    
    if live_session:
        # Live session available - enable both modes
        return [
            {"label": " 🏁 Live", "value": "live", "disabled": False},
            {"label": " ⏯️ Simulation", "value": "sim", "disabled": False}
        ]
    else:
        # No live session - disable Live mode
        return [
            {"label": " 🏁 Live (No race now)", "value": "live", "disabled": True},
            {"label": " ⏯️ Simulation", "value": "sim", "disabled": False}
        ]


# Callback to lock/unlock Context controls based on mode
@callback(
    Output('year-selector', 'disabled'),
    Output('circuit-selector', 'disabled'),
    Output('session-selector', 'disabled'),
    Output('year-selector', 'value', allow_duplicate=True),
    Output('circuit-selector', 'value', allow_duplicate=True),
    Output('session-selector', 'value', allow_duplicate=True),
    Input('mode-selector', 'value'),
    prevent_initial_call=True
)
def handle_mode_change(mode):
    """Lock Context controls in Live mode and auto-load live session data."""
    if mode == "live":
        # Get live session information
        live_session = check_for_live_session()
        
        if live_session:
            # Lock controls and set values from live session
            year = live_session.year
            circuit_key = live_session.circuit_key
            
            # Map SessionType enum to dropdown value
            session_type_map = {
                'Practice 1': 'P1',
                'Practice 2': 'P2',
                'Practice 3': 'P3',
                'Qualifying': 'Q',
                'Sprint': 'S',
                'Sprint Qualifying': 'SQ',
                'Race': 'R'
            }
            session_value = session_type_map.get(live_session.session_type.value, 'R')
            
            logger.info(f"Live mode activated: year={year}, circuit={circuit_key}, session={session_value}")
            
            return True, True, True, year, circuit_key, session_value
        else:
            # No live session, keep simulation mode
            logger.warning("Live mode selected but no live session available")
            return False, False, False, 2025, None, None
    else:
        # Simulation mode - unlock controls
        return False, False, False, 2025, None, None


@callback(
    Output('dashboard-selector', 'value'),
    Input('dashboard-selector', 'value'),
    State('mode-selector', 'value'),
    prevent_initial_call=True
)
def enforce_race_overview(selected_dashboards, mode):
    """Ensure Race Overview stays selected in simulation/live modes."""
    required = {'race_overview'}
    selected_set = set(selected_dashboards or [])

    # If the required dashboard is missing, add it back preserving order
    if mode in ('sim', 'live') and not required.issubset(selected_set):
        base_order = ["ai", "race_overview", "race_control", "track_map", "weather", "telemetry"]
        selected_set.update(required)
        fixed = [item for item in base_order if item in selected_set]
        return fixed

    raise PreventUpdate


@callback(
    Output('dashboard-selector', 'options'),
    Input('mode-selector', 'value'),
    Input('session-store', 'data'),
    State('dashboard-selector', 'options'),
    prevent_initial_call=False
)
def sync_dashboard_options(mode, session_data, current_options):
    """Enable Track Map only when simulation mode has FastF1 cache ready."""
    if not current_options:
        raise PreventUpdate

    track_map_ready = bool(session_data and session_data.get('track_map', {}).get('ready'))
    enable_track_map = mode == 'sim' and track_map_ready

    updated_options: List[Dict[str, Any]] = []
    changed = False

    for option in current_options:
        option_copy = option.copy()
        if option_copy.get('value') == 'track_map':
            disabled_target = not enable_track_map
            if option_copy.get('disabled') != disabled_target:
                option_copy['disabled'] = disabled_target
                changed = True
            # Ensure label remains informative without toggling unnecessarily
            base_label = " Track Map"
            if enable_track_map:
                if option_copy.get('label') != base_label:
                    option_copy['label'] = base_label
                    changed = True
            else:
                locked_label = " Track Map (simulation cache required)"
                if option_copy.get('label') != locked_label:
                    option_copy['label'] = locked_label
                    changed = True
        updated_options.append(option_copy)

    if not changed:
        raise PreventUpdate

    return updated_options


@callback(
    Output('circuit-selector', 'options'),
    Output('circuit-selector', 'value'),
    Output('session-selector', 'options', allow_duplicate=True),
    Output('session-selector', 'value', allow_duplicate=True),
    Input('year-selector', 'value'),
    State('circuit-selector', 'value'),
    prevent_initial_call='initial_duplicate'
)
def update_circuits(year, current_circuit):
    """Update circuit dropdown based on selected year. Clears session when year changes."""
    if year is None:
        return [], None, [], None
    
    schedule = load_f1_calendar(year)
    if schedule.empty:
        return [], None
    
    circuit_options = []
    circuit_keys = []
    circuit_short_names = {
        'United Arab Emirates': 'Abu Dhabi',
        'United States': 'USA',
        'United Kingdom': 'Britain',
        'Saudi Arabia': 'Saudi',
    }
    
    for _, event in schedule.iterrows():
        country = str(event.get('Country') or '')
        location = str(event.get('Location') or '')
        meeting_key = event['MeetingKey']
        is_race_weekend = bool(event.get('IsRaceWeekend', True))
        round_num = event.get('RoundNumber')
        test_num = event.get('TestNumber')

        if country == 'United States':
            if 'Miami' in location:
                display_base = "Miami"
            elif 'Austin' in location:
                display_base = "USA (Austin)"
            elif 'Las Vegas' in location:
                display_base = "Las Vegas"
            else:
                display_base = circuit_short_names.get(country, country)
        else:
            display_base = circuit_short_names.get(country, country)

        if not display_base:
            display_base = location or country or "Event"

        if not is_race_weekend:
            display_base = str(event.get('EventName') or display_base)

        if is_race_weekend and pd.notna(round_num):
            prefix = f"R{int(round_num)}"
        elif not is_race_weekend and pd.notna(test_num):
            prefix = f"Test {int(test_num)}"
        else:
            prefix = "Event"

        circuit_keys.append(meeting_key)
        circuit_options.append({
            'label': f"{prefix} - {display_base}",
            'value': meeting_key
        })
    
    # When year changes, always clear circuit selection to force user to choose
    # This also triggers session dropdown to clear
    from dash import ctx
    triggered_id = ctx.triggered_id if ctx.triggered else None
    
    if triggered_id == 'year-selector':
        # Year changed - clear circuit and session, let user select
        logger.info(f"Year changed to {year}, clearing circuit and session selections")
        return circuit_options, None, [], None
    
    # Keep current selection if it exists in new options
    if current_circuit and current_circuit in circuit_keys:
        default_value = current_circuit
    else:
        # Try to get last completed race from OpenF1
        last_meeting_key = get_last_completed_meeting_key(openf1_provider)

        if last_meeting_key and last_meeting_key in circuit_keys:
            default_value = last_meeting_key
            logger.info(
                f"Auto-selected last completed race: meeting_key={last_meeting_key}"
            )
        elif circuit_options:
            # Fallback: select last race in list for current year, first otherwise
            default_value = circuit_options[-1]['value']
            logger.info("Using last circuit in calendar as default")
        else:
            default_value = None

    # Return empty session options - will be populated by update_sessions callback
    return circuit_options, default_value, [], None


@callback(
    Output('session-selector', 'options', allow_duplicate=True),
    Output('session-selector', 'value', allow_duplicate=True),
    Input('circuit-selector', 'value'),
    Input('year-selector', 'value'),
    State('session-selector', 'value'),
    prevent_initial_call=True
)
def update_sessions(circuit_key, year, current_session):
    """Update session dropdown based on selected circuit (meeting_key from OpenF1)."""
    from dash import ctx
    
    if not circuit_key or not year:
        return [], None
    
    # When circuit changes, always clear session selection
    triggered_id = ctx.triggered_id if ctx.triggered else None
    force_clear = triggered_id == 'circuit-selector'
    
    try:
        meeting_key = circuit_key

        cached_sessions: Optional[List[Dict[str, Any]]] = None
        try:
            cached_sessions = _load_cached_session_list(int(year), int(meeting_key))
        except (TypeError, ValueError):
            cached_sessions = None

        if cached_sessions is not None:
            sessions = cached_sessions
            logger.info(
                "Loaded %s sessions for meeting_key=%s from cache",
                len(sessions),
                meeting_key,
            )
        else:
            sessions_params = {"year": year, "meeting_key": meeting_key}
            sessions = openf1_provider._request("sessions", sessions_params)
            if not sessions:
                logger.warning(
                    "No sessions found for meeting_key=%s year=%s",
                    meeting_key,
                    year,
                )
                return [], None
            
            # DEBUG: Log raw sessions from API
            logger.info(
                "Received %s sessions from OpenF1 API for meeting_key=%s:",
                len(sessions),
                meeting_key,
            )
            for session in sessions:
                logger.info(
                    "  Session: %s (key=%s)",
                    session.get('session_name', 'Unknown'),
                    session.get('session_key', 'N/A'),
                )

        session_options = _build_session_selector_options(sessions)
        session_values = [opt['value'] for opt in session_options]

        if force_clear:
            logger.info(
                "Circuit changed, clearing session selection. Found %s sessions for meeting_key=%s",
                len(session_options),
                meeting_key,
            )
            default_value = None
        elif current_session and current_session in session_values:
            default_value = current_session
        else:
            default_value = None

        logger.info(
            "Session selector populated with %s options for meeting_key=%s",
            len(session_options),
            meeting_key,
        )
        return session_options, default_value

    except Exception as e:
        logger.error(f"Error updating sessions: {e}")
        return [], None


import time


def _format_size(size_bytes: int) -> str:
    """Return human readable size string."""
    if size_bytes <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size_bytes)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{value:.2f} TB"


def _describe_cache_job_context(context: Optional[Dict[str, Any]]) -> str:
    """Return compact description for the active cache job context."""
    if not context:
        return ""

    parts: List[str] = []
    year = context.get("year")
    meeting = context.get("meeting")
    session = context.get("session")
    action = context.get("action")
    artifacts = context.get("artifacts") or []

    if action:
        parts.append(str(action).capitalize())
    if year is not None:
        parts.append(f"Year: {year}")
    if meeting not in {None, ""}:
        parts.append(f"Meeting: {meeting}")
    if session not in {None, ""}:
        parts.append(f"Session: {session}")
    if artifacts:
        parts.append(f"Artifacts: {len(artifacts)} selected")

    return " · ".join(parts)


@callback(
    Output('cache-manager-modal', 'is_open'),
    Input('cache-manager-open', 'n_clicks'),
    Input('cache-modal-close', 'n_clicks'),
    State('cache-manager-modal', 'is_open'),
    prevent_initial_call=True,
)
def toggle_cache_manager_modal(open_clicks, close_clicks, is_open):
    """Toggle cache manager modal visibility."""
    triggered = ctx.triggered_id if ctx.triggered else None
    if triggered == 'cache-manager-open':
        return True
    if triggered == 'cache-modal-close':
        return False
    return is_open


@callback(
    Output('cache-meeting-selector', 'options'),
    Output('cache-meeting-selector', 'value'),
    Input('cache-year-selector', 'value'),
)
def update_cache_meetings(year):
    """Populate meeting selector inside cache modal."""
    if year is None:
        return [], None

    schedule = load_f1_calendar(year)
    if schedule.empty:
        return [], None

    circuit_short_names = {
        'United Arab Emirates': 'Abu Dhabi',
        'United States': 'USA',
        'United Kingdom': 'Britain',
        'Saudi Arabia': 'Saudi',
    }

    options = []
    for _, event in schedule.iterrows():
        country = str(event.get('Country') or '')
        location = str(event.get('Location') or '')
        meeting_key = event['MeetingKey']
        is_race_weekend = bool(event.get('IsRaceWeekend', True))
        round_num = event.get('RoundNumber')
        test_num = event.get('TestNumber')

        if country == 'United States':
            if 'Miami' in location:
                display_name = 'Miami'
            elif 'Austin' in location:
                display_name = 'USA (Austin)'
            elif 'Las Vegas' in location:
                display_name = 'Las Vegas'
            else:
                display_name = circuit_short_names.get(country, country)
        else:
            display_name = circuit_short_names.get(country, country)

        if not display_name:
            display_name = location or country or 'Event'

        if not is_race_weekend:
            display_name = str(event.get('EventName') or display_name)

        if is_race_weekend and pd.notna(round_num):
            prefix = f"R{int(round_num)}"
        elif not is_race_weekend and pd.notna(test_num):
            prefix = f"Test {int(test_num)}"
        else:
            prefix = 'Event'

        options.append({
            'label': f"{prefix} - {display_name}",
            'value': meeting_key,
        })
    if options:
        options.insert(0, {'label': 'All meetings', 'value': 'ALL'})

    return options, (options[0]['value'] if options else None)


@callback(
    Output('cache-session-selector', 'options'),
    Output('cache-session-selector', 'value'),
    Input('cache-meeting-selector', 'value'),
    State('cache-year-selector', 'value'),
)
def update_cache_sessions(meeting_key, year):
    """Populate session selector inside cache modal."""
    if meeting_key is None or year is None:
        return [], None

    if isinstance(meeting_key, str) and meeting_key.strip().upper() in {'ALL', '*', 'YEAR'}:
        options = [
            {'label': 'Race', 'value': 'R'},
            {'label': 'Qualifying', 'value': 'Q'},
            {'label': 'Sprint', 'value': 'S'},
            {'label': 'Sprint Qualifying', 'value': 'SQ'},
            {'label': 'Sprint Shootout', 'value': 'SS'},
            {'label': 'Practice 1', 'value': 'P1'},
            {'label': 'Practice 2', 'value': 'P2'},
            {'label': 'Practice 3', 'value': 'P3'},
        ]
        return options, 'R'

    cached_sessions: Optional[List[Dict[str, Any]]] = None
    try:
        cached_sessions = _load_cached_session_list(int(year), int(meeting_key))
    except (TypeError, ValueError):
        cached_sessions = None

    if cached_sessions is not None:
        sessions = cached_sessions
        logger.info(
            "Loaded %s sessions for meeting_key=%s from cache",
            len(sessions),
            meeting_key,
        )
    else:
        sessions_params = {"year": year, "meeting_key": meeting_key}
        sessions = openf1_provider._request("sessions", sessions_params)
        if not sessions:
            logger.warning(
                "No sessions found for meeting_key=%s year=%s",
                meeting_key,
                year,
            )
            return [], None

    options = _build_session_selector_options(sessions)
    default_value = None
    if options:
        race_option = next(
            (opt['value'] for opt in options if opt['value'] in {'R', 'RACE'}),
            None,
        )
        default_value = race_option or options[0]['value']

    return options, default_value


@callback(
    Output('cache-status-summary', 'children'),
    Output('cache-status-table', 'children'),
    Output('cache-regenerate-button', 'disabled'),
    Output('cache-fill-button', 'disabled'),
    Output('cache-error-alert', 'is_open'),
    Output('cache-error-alert', 'children'),
    Output('cache-progress-bar', 'value'),
    Output('cache-progress-bar', 'label'),
    Output('cache-progress-bar', 'max'),
    Output('cache-progress-message', 'children'),
    Output('cache-year-selector', 'disabled'),
    Output('cache-meeting-selector', 'disabled'),
    Output('cache-session-selector', 'disabled'),
    Output('cache-type-checklist', 'disabled'),
    Input('cache-year-selector', 'value'),
    Input('cache-meeting-selector', 'value'),
    Input('cache-session-selector', 'value'),
    Input('cache-type-checklist', 'value'),
    Input('cache-progress-store', 'data'),
)
def refresh_cache_status(year, meeting_key, session_code, selected_keys, progress_data):
    """Refresh cache status summary and table based on selection."""
    logger.debug(
        "Cache modal refresh -> year=%s meeting=%s session=%s selected=%s",
        year,
        meeting_key,
        session_code,
        selected_keys,
    )

    progress_data = progress_data or {}
    progress_status = progress_data.get('status', 'idle')
    progress_context = progress_data.get('context') or {}
    progress_completed = int(progress_data.get('completed', 0))
    progress_total = int(progress_data.get('total', 0))
    progress_max = max(progress_total, 1)
    is_running = progress_status == 'running'
    disable_inputs = is_running

    display_year = year
    display_meeting = meeting_key
    display_session = session_code
    selected_keys_list = list(selected_keys or [])

    if is_running:
        display_year = progress_context.get('year', year)
        display_meeting = progress_context.get('meeting', meeting_key)
        display_session = progress_context.get('session', session_code)
        selected_keys_list = list(progress_context.get('artifacts') or selected_keys_list)

    context_description = _describe_cache_job_context(progress_context)

    if is_running:
        if progress_total:
            progress_label = f"Working... ({progress_completed}/{progress_total})"
        else:
            progress_label = "Working..."
    else:
        progress_label = f"{progress_completed}/{progress_total}" if progress_total else ''

    progress_value = progress_completed
    if is_running and progress_completed == 0 and progress_total:
        progress_value = 0.01

    progress_message = progress_data.get('message') or ''
    if is_running:
        base_message = progress_message or 'Working on cache job...'
        progress_message = f"{base_message} ({context_description})" if context_description else base_message
    elif progress_message and context_description:
        progress_message = f"{progress_message} ({context_description})"

    alert_open = False
    alert_message = ''

    summary_parts: List[Any] = []

    if is_running:
        summary_parts.append(
            dbc.Alert(
                [
                    dbc.Spinner(size='sm', color='warning', spinner_class_name='me-2'),
                    html.Span('Cache job in progress'),
                    html.Br(),
                    html.Small(context_description or 'Tracking active cache request'),
                ],
                color='warning',
                className='mb-2 py-2'
            )
        )

    if not selected_keys_list:
        summary_parts.append(
            dbc.Alert(
                "Select at least one cache type to inspect status.",
                color='info',
                className='mb-2 py-2'
            )
        )
        return (
            summary_parts,
            [],
            True,
            True,
            alert_open,
            alert_message,
            progress_value,
            progress_label,
            progress_max,
            progress_message,
            disable_inputs,
            disable_inputs,
            disable_inputs,
            disable_inputs,
        )

    artifacts = [CACHE_ARTIFACT_MAP[key] for key in selected_keys_list if key in CACHE_ARTIFACT_MAP]
    requires_meeting = any(artifact.level in {'meeting', 'session', 'fastf1'} for artifact in artifacts)
    requires_session = any(artifact.level in {'session', 'fastf1'} for artifact in artifacts)

    disable_button = False
    disable_fill = False
    is_all_meetings = isinstance(display_meeting, str) and display_meeting.strip().upper() in {'ALL', '*', 'YEAR'}
    missing_messages: List[str] = []
    if requires_meeting and not is_all_meetings and display_meeting in (None, ''):
        disable_button = True
        disable_fill = True
        alert_open = True
        missing_messages.append("Select a circuit to manage meeting or session caches.")

    if requires_session and not display_session:
        disable_button = True
        disable_fill = True
        alert_open = True
        missing_messages.append("Select a session to generate session-level caches.")

    if missing_messages:
        alert_message = " ".join(missing_messages)

    if missing_messages:
        summary_parts.append(
            dbc.Alert(
                alert_message or "Select the required filters to inspect caches.",
                color='info',
                className='mb-2 py-2'
            )
        )
        return (
            summary_parts,
            [],
            True,
            True,
            alert_open,
            alert_message,
            progress_value,
            progress_label,
            progress_max,
            progress_message,
            disable_inputs,
            disable_inputs,
            disable_inputs,
            disable_inputs,
        )

    meeting_value: Optional[int] = None
    if display_meeting not in (None, '') and not is_all_meetings:
        try:
            meeting_value = int(display_meeting)
        except (TypeError, ValueError):
            meeting_value = None

    session_value = display_session

    table_children: List[Any] = []
    summary_children: Optional[Any] = None

    try:
        status = cache_generation_service.describe_status(
            int(display_year) if display_year is not None else datetime.now().year,
            display_meeting if is_all_meetings else meeting_value,
            session_value,
            selected_keys_list,
        )

        if status.get('multi_meeting'):
            summary_children = dbc.Alert(
                f"Inspecting {status.get('meeting_count', 0)} meetings. Cache status preview is unavailable for season-wide selection.",
                color='info',
                className='mb-2 py-2'
            )
            table_children = []
            disable_button = False
        else:
            summary_children = html.Div([
                html.H6("Cache summary", className='mb-1'),
                html.Div(
                    f"{status['existing']} of {status['requested']} caches ready"
                    f" · {status['total_size_mb']:.3f} MB",
                    className='small text-muted'
                ),
            ])

            header = html.Thead(html.Tr([
                html.Th("Cache"),
                html.Th("Exists", className='text-center'),
                html.Th("Size"),
                html.Th("Path"),
            ]))

            rows = []
            for entry in status['entries']:
                exists_badge = dbc.Badge(
                    "Yes" if entry['exists'] else "No",
                    color='success' if entry['exists'] else 'secondary',
                    pill=True,
                    className='px-2'
                )
                size_label = _format_size(int(entry['size_bytes']))
                rows.append(html.Tr([
                    html.Td(entry['label']),
                    html.Td(exists_badge, className='text-center'),
                    html.Td(size_label),
                    html.Td(entry['path'] or "—", className='text-break small'),
                ]))

            table_children = [header, html.Tbody(rows)]

    except Exception as exc:  # noqa: BLE001
        logger.error("Cache status refresh failed: %s", exc)
        summary_children = dbc.Alert(
            f"Error inspecting cache status: {exc}",
            color='danger',
            className='mb-2 py-2'
        )
        table_children = []
        disable_button = True
        disable_fill = True
        disable_inputs = is_running

    if progress_status == 'running':
        disable_button = True
        disable_fill = True

    if progress_status == 'error':
        alert_open = True
        base_error = progress_data.get('error') or 'Cache generation failed.'
        alert_message = f"{base_error} ({context_description})" if context_description else base_error

    if summary_children:
        summary_parts.append(summary_children)

    return (
        summary_parts,
        table_children,
        disable_button,
        disable_fill,
        alert_open,
        alert_message,
        progress_value,
        progress_label,
        progress_max,
        progress_message,
        disable_inputs,
        disable_inputs,
        disable_inputs,
        disable_inputs,
    )


@callback(
    Output('cache-delete-button', 'disabled'),
    Input('cache-year-selector', 'value'),
    Input('cache-meeting-selector', 'value'),
    Input('cache-session-selector', 'value'),
    Input('cache-type-checklist', 'value'),
    Input('cache-progress-store', 'data'),
)
def update_cache_delete_button(year, meeting_key, session_code, selected_keys, progress_data):
    """Enable delete button only when context is valid."""
    if (progress_data or {}).get('status') == 'running':
        return True

    selected_keys = selected_keys or []
    if not selected_keys:
        return True

    artifacts = [CACHE_ARTIFACT_MAP[key] for key in selected_keys if key in CACHE_ARTIFACT_MAP]
    if not artifacts:
        return True

    requires_meeting = any(artifact.level in {'meeting', 'session', 'fastf1'} for artifact in artifacts)
    requires_session = any(artifact.level in {'session', 'fastf1'} for artifact in artifacts)
    is_all_meetings = isinstance(meeting_key, str) and meeting_key.strip().upper() in {'ALL', '*', 'YEAR'}

    if requires_meeting and not is_all_meetings and meeting_key in (None, ''):
        return True
    if requires_session and not session_code:
        return True

    return False


@callback(
    Output('cache-progress-store', 'data', allow_duplicate=True),
    Input('cache-regenerate-button', 'n_clicks'),
    Input('cache-fill-button', 'n_clicks'),
    Input('cache-delete-button', 'n_clicks'),
    State('cache-year-selector', 'value'),
    State('cache-meeting-selector', 'value'),
    State('cache-session-selector', 'value'),
    State('cache-type-checklist', 'value'),
    prevent_initial_call=True,
)
def handle_cache_actions(regen_clicks, fill_clicks, delete_clicks, year, meeting_key, session_code, selected_keys):
    """Process cache regeneration or deletion requests from the modal."""
    triggered = ctx.triggered_id
    if triggered not in {'cache-regenerate-button', 'cache-delete-button', 'cache-fill-button'}:
        raise PreventUpdate

    selected_keys = list(selected_keys or [])
    if not selected_keys:
        raise PreventUpdate

    current_state = _get_cache_job_state()
    if current_state.get('status') == 'running':
        return _cache_progress_payload()

    if triggered == 'cache-delete-button':
        action = 'delete'
    elif triggered == 'cache-fill-button':
        action = 'fill'
    else:
        action = 'regenerate'
    year_value = int(year) if year is not None else datetime.now().year

    logger.info(
        "Manual cache %s requested -> year=%s meeting=%s session=%s keys=%s",
        action,
        year,
        meeting_key,
        session_code,
        selected_keys,
    )

    job_id = str(uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    if action == 'delete':
        initial_message = 'Deleting selected caches...'
    elif action == 'fill':
        initial_message = 'Generating missing caches...'
    else:
        initial_message = 'Starting cache generation...'
    job_context = {
        'job_id': job_id,
        'action': action,
        'year': year_value,
        'meeting': meeting_key,
        'session': session_code,
        'artifacts': list(selected_keys),
    }

    with _cache_job_lock:
        _cache_job_snapshot.update({
            'job_id': job_id,
            'status': 'running',
            'completed': 0,
            'total': len(selected_keys) or 1,
            'message': initial_message,
            'error': None,
            'timestamp': timestamp,
            'context': job_context,
        })

    worker = threading.Thread(
        target=_run_cache_job,
        args=(job_id, action, year_value, meeting_key, session_code, selected_keys),
        daemon=True,
    )
    worker.start()

    return _cache_progress_payload()


@callback(
    Output('cache-progress-poll', 'disabled'),
    Input('cache-progress-store', 'data'),
)
def toggle_cache_progress_poll(progress_data):
    status = (progress_data or {}).get('status')
    return status != 'running'


@callback(
    Output('cache-progress-store', 'data', allow_duplicate=True),
    Input('cache-progress-poll', 'n_intervals'),
    prevent_initial_call=True,
)
def poll_cache_progress(_interval):
    state = _cache_progress_payload()
    if state.get('status') in {None, 'idle'}:
        raise PreventUpdate
    return state


@callback(
    Output('driver-dropdown-container', 'children'),
    Output('session-store', 'data', allow_duplicate=True),
    Output('session-bootstrap-store', 'data', allow_duplicate=True),
    Input('year-selector', 'value'),
    Input('circuit-selector', 'value'),
    Input('session-selector', 'value'),
    prevent_initial_call=True
)
def clear_driver_dropdown_immediately(year, circuit, session):
    """Reset driver selector and mark session context as loading."""
    placeholder = dcc.Loading(
        dcc.Dropdown(
            id='driver-selector',
            options=[],
            value=None,
            placeholder="Loading drivers...",
            className="mb-2",
            clearable=True
        ),
        type="circle",
        color="#e10600"
    )
    loading_session = {
        'loaded': False,
        'error': None,
        'drivers': {},
        'track_map': {
            'ready': False,
            'error': None,
            'params': None,
            'formation_offset_seconds': 0.0,
            'fastf1_lap_one_seconds': None,
        },
    }
    bootstrap_reset = {
        'ready': False,
        'driver_options': [],
        'drivers': {},
    }
    return placeholder, loading_session, bootstrap_reset

@callback(
    Output('driver-dropdown-container', 'children', allow_duplicate=True),
    Output('session-bootstrap-store', 'data', allow_duplicate=True),
    Input('session-selector', 'value'),
    Input('circuit-selector', 'value'),
    Input('year-selector', 'value'),
    prevent_initial_call=True
)
def update_drivers(session, circuit_key, year):
    """Load driver dropdown and stage session metadata before dashboard bootstrap."""
    placeholder_dropdown = dcc.Loading(
        dcc.Dropdown(
            id='driver-selector',
            options=[],
            value=None,
            placeholder="Session not available",
            className="mb-2",
            clearable=True
        ),
        type="circle",
        color="#e10600"
    )

    def _bootstrap_failure(error_message: Optional[str]) -> Dict[str, Any]:
        return {
            'ready': False,
            'error': error_message,
            'driver_options': [],
            'drivers': {},
        }

    if not session or not circuit_key or not year:
        logger.warning(
            "Missing parameters: session=%s, circuit_key=%s, year=%s",
            session,
            circuit_key,
            year,
        )
        bootstrap_reset = _bootstrap_failure("Incomplete context selection")
        return placeholder_dropdown, bootstrap_reset

    meeting_key = circuit_key
    try:
        meeting_key_int = int(meeting_key)
    except (TypeError, ValueError):
        logger.error("Invalid meeting_key received for driver update: %s", meeting_key)
        bootstrap_reset = _bootstrap_failure("Invalid meeting key")
        return placeholder_dropdown, bootstrap_reset

    try:
        year_int = int(year)
    except (TypeError, ValueError):
        logger.error("Invalid year received for driver update: %s", year)
        bootstrap_reset = _bootstrap_failure("Invalid year")
        return placeholder_dropdown, bootstrap_reset

    try:
        logger.info(
            "Loading drivers for year=%s, meeting_key=%s, session=%s",
            year_int,
            meeting_key_int,
            session,
        )

        session_info = _resolve_session_payload(year_int, meeting_key_int, session)
        if not session_info:
            logger.error(
                "No session payload found for meeting_key=%s, session_code=%s",
                meeting_key_int,
                session,
            )
            bootstrap_reset = _bootstrap_failure("Session metadata unavailable")
            return placeholder_dropdown, bootstrap_reset

        raw_session_key = _get_session_key(session_info)
        try:
            session_key_int = int(raw_session_key) if raw_session_key is not None else None
        except (TypeError, ValueError):
            session_key_int = None

        if isinstance(session_info, dict):
            calendar_meta = _CALENDAR_METADATA.get(year_int, {}).get(meeting_key_int)
            cache_slug = (calendar_meta or {}).get("cache_slug")
            if cache_slug and not session_info.get("cache_slug"):
                session_info["cache_slug"] = cache_slug

        if session_key_int is None:
            logger.error(
                "Resolved session lacks session_key for meeting_key=%s, session_code=%s",
                meeting_key_int,
                session,
            )
            bootstrap_reset = _bootstrap_failure("Session key missing")
            return placeholder_dropdown, bootstrap_reset

        logger.info("Loading session with session_key=%s", session_key_int)
        session_obj = SessionAdapter(
            provider=openf1_provider,
            session_info=session_info,
            session_key=session_key_int,
        )

        try:
            session_obj.load()
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to load session data: %s", exc)
            bootstrap_reset = _bootstrap_failure("Session load failed")
            return placeholder_dropdown, bootstrap_reset

        # Store session object for downstream bootstrap callbacks
        global current_session_obj
        global _track_map_trace_offset, _track_map_driver_order
        current_session_obj = session_obj
        _track_map_trace_offset = None
        _track_map_driver_order = []

        drivers = session_obj.drivers
        results = session_obj.results
        logger.info("Loaded %s drivers from session", len(drivers))

        driver_options: List[Dict[str, str]] = []
        for _, driver_data in results.iterrows():
            try:
                driver_num = driver_data['DriverNumber']
                abbr = driver_data['Abbreviation']
                full_name = driver_data['FullName']
                label = f"#{str(driver_num).rjust(2)} {abbr.ljust(3)} - {full_name}"
                driver_options.append({
                    'label': label,
                    'value': f"{abbr}_{year}_{driver_num}",
                })
            except Exception as exc:  # noqa: BLE001
                logger.error("Error loading driver row: %s", exc)
                continue

        logger.info("Created %s driver options", len(driver_options))
        sample_labels = [opt['label'] for opt in driver_options[:5]]
        if sample_labels:
            logger.info("Sample drivers: %s", ', '.join(sample_labels))

        dropdown_component = dcc.Loading(
            dcc.Dropdown(
                id='driver-selector',
                options=driver_options,  # type: ignore[arg-type]
                value=None,
                placeholder="Select a driver...",
                className="mb-2",
                clearable=True,
                style={
                    'fontSize': '12px',
                    'fontFamily': 'monospace',
                    'lineHeight': '1.2',
                },
            ),
            type="circle",
            color="#e10600",
        )

        session_info_serializable = json.loads(json.dumps(session_info, default=str))
        bootstrap_payload = {
            'ready': True,
            'year': year_int,
            'meeting_key': meeting_key_int,
            'session': session,
            'session_key': session_key_int,
            'session_info': session_info_serializable,
            'driver_options': driver_options,
            'drivers': {opt['value']: opt['label'] for opt in driver_options},
        }

        return dropdown_component, bootstrap_payload

    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Unexpected error while preparing drivers for %s/%s/%s: %s",
            year,
            circuit_key,
            session,
            exc,
        )
        bootstrap_reset = _bootstrap_failure(str(exc))
        return placeholder_dropdown, bootstrap_reset


# ============================================================================
# RAG DOCUMENT CALLBACKS
# ============================================================================

def _build_session_store_payload(
    session_obj: SessionAdapter,
    session_info: Dict[str, Any],
    year: int,
    meeting_key: int,
    session_code: str,
    driver_options: Sequence[Dict[str, str]],
) -> Dict[str, Any]:
    """Return session-store payload after preparing dashboards."""
    track_map_status: Dict[str, Any] = {
        'ready': False,
        'error': None,
        'params': None,
        'formation_offset_seconds': 0.0,
        'fastf1_lap_one_seconds': None,
    }

    track_map_dashboard: Optional[TrackMapDashboard] = None
    try:
        track_map_dashboard = get_track_map_dashboard()
        translation = track_map_dashboard.provider.translate_openf1_session(session_info)

        raw_year = translation.get('year', year)
        try:
            translation_year = int(raw_year) if raw_year is not None else year
        except (TypeError, ValueError):  # pragma: no cover - defensive
            translation_year = year

        translation_country = str(
            translation.get('round')
            or session_info.get('country_name')
            or session_info.get('meeting_name', '')
        ).strip()
        translation_identifier = str(
            translation.get('identifier')
            or session_code
        )

        if translation_country:
            cache_loaded = track_map_dashboard.load_session(
                translation_year,
                translation_country,
                translation_identifier,
            )
            if cache_loaded:
                track_map_status.update({
                    'ready': True,
                    'error': None,
                    'params': {
                        'year': translation_year,
                        'country': translation_country,
                        'session_type': translation_identifier,
                    },
                })
            else:
                track_map_status['error'] = (
                    "FastF1 telemetry cache unavailable for this session."
                )
        else:
            track_map_status['error'] = (
                "Could not determine host country for FastF1 session preload."
            )
    except Exception as exc:  # noqa: BLE001
        track_map_status['error'] = str(exc)
        logger.warning("Track map preload failed: %s", exc)

    # Bootstrap pit policy context once per simulation
    global _pit_policy_context
    try:
        rag_manager = get_rag_manager()
        _pit_policy_context = bootstrap_pit_policy_context(rag_manager)
        logger.info("Pit policy context loaded from RAG (strategy.md)")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to bootstrap pit policy context: %s", exc)
        _pit_policy_context = PitPolicyContext()

    # Initialize proactive event detector with RAG tire window overrides
    global event_detector
    tire_window_overrides = _load_tire_window_overrides(
        session_info=session_info,
        session_obj=session_obj,
    )
    event_detector = RaceEventDetector(
        openf1_provider,
        tire_windows=tire_window_overrides,
    )

    # Initialize simulation controller with session times
    global simulation_controller
    try:
        session_date = session_obj.date
        laps = session_obj.laps

        if laps.empty or 'LapEndTime_seconds' not in laps.columns:
            logger.warning("No lap data available for simulation controller")
            simulation_controller = None
        else:
            first_lap_end = laps['LapEndTime_seconds'].min()
            last_lap_end = laps['LapEndTime_seconds'].max()

            if pd.isna(last_lap_end):
                logger.warning("Could not extract lap times for simulation")
                simulation_controller = None
            else:
                lap_timing_data: Optional[pd.DataFrame] = None
                formation_offset_seconds: float = 0.0
                fastf1_lap_one_seconds: Optional[float] = None

                if {'LapStartTime', 'LapNumber', 'DriverNumber'}.issubset(laps.columns):
                    driver_numbers = pd.to_numeric(laps['DriverNumber'], errors='coerce')
                    target_driver_number = 1
                    leader_mask = driver_numbers == target_driver_number

                    if not leader_mask.any():
                        fallback_number: Optional[int] = None
                        results_frame = getattr(session_obj, 'results', None)
                        if isinstance(results_frame, pd.DataFrame) and not results_frame.empty:
                            driver_numbers_series = results_frame.get('DriverNumber')
                            if driver_numbers_series is not None:
                                fallback_candidates = pd.to_numeric(
                                    driver_numbers_series,
                                    errors='coerce',
                                ).dropna()
                                if not fallback_candidates.empty:
                                    fallback_number = int(fallback_candidates.iloc[0])

                        if fallback_number is None:
                            valid_numbers = driver_numbers.dropna().astype(int)
                            if not valid_numbers.empty:
                                fallback_number = int(valid_numbers.iloc[0])

                        if fallback_number is not None:
                            target_driver_number = fallback_number
                            leader_mask = driver_numbers == target_driver_number
                            logger.warning(
                                "Driver #1 lap data missing; using driver #%s for lap tracking",
                                target_driver_number,
                            )
                        else:
                            logger.warning("No valid lap data available for lap tracking")

                    leader_laps = laps.loc[leader_mask].copy()
                    if not leader_laps.empty:
                        leader_laps.loc[:, 'DriverNumber'] = int(target_driver_number)

                        select_columns = ['LapNumber', 'LapStartTime', 'LapEndTime', 'DriverNumber']
                        if 'LapTime' in leader_laps.columns:
                            select_columns.append('LapTime')

                        lap_timing_candidate = leader_laps[select_columns].copy()
                        if track_map_dashboard is not None:
                            normalized_laps, offset_seconds, lap_one_seconds = _normalize_lap_timing_data(
                                lap_timing_candidate,
                                track_map_dashboard,
                                int(target_driver_number),
                            )
                        else:
                            normalized_laps = lap_timing_candidate
                            offset_seconds = None
                            lap_one_seconds = None
                            logger.warning(
                                "Track map dashboard unavailable; skipping lap timing normalization",
                            )

                        if offset_seconds is not None:
                            formation_offset_seconds = offset_seconds
                            logger.info(
                                "Applied formation offset %.1fs using FastF1 lap-one %.1fs",
                                formation_offset_seconds,
                                lap_one_seconds if lap_one_seconds is not None else float('nan'),
                            )

                        if lap_one_seconds is not None:
                            fastf1_lap_one_seconds = lap_one_seconds

                        lap_timing_data = normalized_laps
                        logger.info(
                            "Prepared lap timing data from driver #%s: %d laps",
                            target_driver_number,
                            len(lap_timing_data) if lap_timing_data is not None else 0,
                        )
                    else:
                        logger.warning("Unable to build lap timing data; no laps matched target driver")

                def _derive_boundary_seconds() -> Tuple[float, float, float]:
                    start_seconds = 0.0
                    lap_one_end_seconds = float(first_lap_end) if pd.notna(first_lap_end) else 0.0
                    session_end_seconds = float(last_lap_end)

                    if lap_timing_data is not None and not lap_timing_data.empty:
                        lap_one_mask = pd.Series(False, index=lap_timing_data.index)
                        if 'LapNumber' in lap_timing_data.columns:
                            lap_numbers = pd.to_numeric(lap_timing_data['LapNumber'], errors='coerce')
                            lap_numbers_clean = lap_numbers.dropna()
                            if not lap_numbers_clean.empty:
                                first_lap_number = lap_numbers_clean.min()
                                lap_one_mask = lap_numbers == first_lap_number

                        if 'LapStartTime_seconds' in lap_timing_data.columns:
                            start_series = lap_timing_data.loc[lap_one_mask, 'LapStartTime_seconds'].dropna()
                            if not start_series.empty:
                                start_seconds = float(start_series.iloc[0])
                        elif 'LapStartTime' in lap_timing_data.columns:
                            raw_start_series = lap_timing_data.loc[lap_one_mask, 'LapStartTime'].dropna()
                            if not raw_start_series.empty:
                                derived_series = raw_start_series.apply(_timedelta_to_seconds).dropna()
                                if not derived_series.empty:
                                    start_seconds = float(derived_series.iloc[0])

                        if 'LapEndTime_seconds' in lap_timing_data.columns:
                            end_series = lap_timing_data.loc[lap_one_mask, 'LapEndTime_seconds'].dropna()
                            if not end_series.empty:
                                lap_one_end_seconds = float(end_series.iloc[0])
                            session_end_candidates = lap_timing_data['LapEndTime_seconds'].dropna()
                            if not session_end_candidates.empty:
                                session_end_seconds = float(session_end_candidates.max())
                        elif 'LapEndTime' in lap_timing_data.columns:
                            raw_end_series = lap_timing_data.loc[lap_one_mask, 'LapEndTime'].dropna()
                            if not raw_end_series.empty:
                                derived_end_series = raw_end_series.apply(_timedelta_to_seconds).dropna()
                                if not derived_end_series.empty:
                                    lap_one_end_seconds = float(derived_end_series.iloc[0])
                            session_end_series = lap_timing_data['LapEndTime'].dropna()
                            session_value_series = session_end_series.apply(_timedelta_to_seconds).dropna()
                            if not session_value_series.empty:
                                session_end_seconds = float(session_value_series.max())

                    return start_seconds, lap_one_end_seconds, session_end_seconds

                start_seconds, first_lap_end_seconds, session_end_seconds = _derive_boundary_seconds()

                offset_seconds = 0.0
                if formation_offset_seconds is not None:
                    try:
                        offset_seconds = float(formation_offset_seconds)
                    except (TypeError, ValueError):
                        offset_seconds = 0.0

                offset_td = timedelta(seconds=offset_seconds)

                start_time = session_date + timedelta(seconds=start_seconds) + offset_td
                end_time = session_date + timedelta(seconds=session_end_seconds) + offset_td

                track_map_status['formation_offset_seconds'] = offset_seconds
                track_map_status['fastf1_lap_one_seconds'] = fastf1_lap_one_seconds

                simulation_controller = SimulationController(
                    start_time,
                    end_time,
                    lap_data=lap_timing_data,
                )
                simulation_controller.pause()

                logger.info(
                    "SimulationController initialized: %s -> %s (lap1 end %.1fs, final lap %.1fs)",
                    start_time,
                    end_time,
                    first_lap_end_seconds,
                    session_end_seconds,
                )
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to initialize SimulationController: %s", exc)
        simulation_controller = None

    resolved_session_name = (
        session_info.get('session_name')
        or session_info.get('SessionName')
        or _SESSION_CODE_TO_LABEL.get(str(session_code).upper(), session_code)
    )
    race_name = session_info.get('meeting_name', 'Race')

    total_laps = _calculate_total_laps(
        session_obj,
        str(
            session_info.get('circuit_short_name')
            or session_info.get('location')
            or '',
        ),
    )

    return {
        'loaded': True,
        'year': year,
        'meeting_key': meeting_key,
        'session': session_code,
        'session_key': session_obj.session_key,
        'race_name': race_name,
        'session_type': resolved_session_name,
        'drivers': {opt['value']: opt['label'] for opt in driver_options},
        'total_laps': total_laps,
        'track_map': track_map_status,
    }


@callback(
    Output('session-store', 'data', allow_duplicate=True),
    Input('session-bootstrap-store', 'data'),
    prevent_initial_call=True
)
def finalize_session_store(bootstrap_data):
    """Complete session bootstrap before dashboards render."""
    if not bootstrap_data:
        raise PreventUpdate

    drivers_map = bootstrap_data.get('drivers', {}) if isinstance(bootstrap_data, dict) else {}

    def _empty_track_map() -> Dict[str, Any]:
        return {
            'ready': False,
            'error': None,
            'params': None,
            'formation_offset_seconds': 0.0,
            'fastf1_lap_one_seconds': None,
        }

    if not bootstrap_data.get('ready'):
        error_message = bootstrap_data.get('error')
        if error_message:
            logger.warning("Session bootstrap aborted: %s", error_message)
        return {
            'loaded': False,
            'error': error_message,
            'drivers': drivers_map,
            'track_map': _empty_track_map(),
        }

    session_key = bootstrap_data.get('session_key')
    year_value = bootstrap_data.get('year')
    meeting_value = bootstrap_data.get('meeting_key')
    session_code_raw = bootstrap_data.get('session')
    session_info = bootstrap_data.get('session_info') or {}
    driver_options = bootstrap_data.get('driver_options') or []

    global current_session_obj
    if current_session_obj is None or getattr(current_session_obj, 'session_key', None) != session_key:
        logger.warning(
            "Session object missing or mismatched (expected %s)",
            session_key,
        )
        return {
            'loaded': False,
            'error': "Session object unavailable",
            'drivers': drivers_map,
            'track_map': _empty_track_map(),
        }

    if year_value is None:
        logger.error("Missing year in bootstrap payload")
        return {
            'loaded': False,
            'error': "Invalid year",
            'drivers': drivers_map,
            'track_map': _empty_track_map(),
        }

    if isinstance(year_value, int):
        year_int = year_value
    else:
        try:
            year_int = int(year_value)
        except (TypeError, ValueError):  # pragma: no cover - validation guard
            logger.error("Invalid year in bootstrap payload: %s", year_value)
            return {
                'loaded': False,
                'error': "Invalid year",
                'drivers': drivers_map,
                'track_map': _empty_track_map(),
            }

    if meeting_value is None:
        logger.error("Missing meeting key in bootstrap payload")
        return {
            'loaded': False,
            'error': "Invalid meeting key",
            'drivers': drivers_map,
            'track_map': _empty_track_map(),
        }

    if isinstance(meeting_value, int):
        meeting_key_int = meeting_value
    else:
        try:
            meeting_key_int = int(meeting_value)
        except (TypeError, ValueError):  # pragma: no cover - validation guard
            logger.error("Invalid meeting key in bootstrap payload: %s", meeting_value)
            return {
                'loaded': False,
                'error': "Invalid meeting key",
                'drivers': drivers_map,
                'track_map': _empty_track_map(),
            }

    if session_code_raw is None:
        logger.error("Missing session code in bootstrap payload")
        return {
            'loaded': False,
            'error': "Invalid session code",
            'drivers': drivers_map,
            'track_map': _empty_track_map(),
        }

    session_code = (
        session_code_raw
        if isinstance(session_code_raw, str)
        else str(session_code_raw)
    )

    try:
        payload = _build_session_store_payload(
            session_obj=current_session_obj,
            session_info=session_info,
            year=year_int,
            meeting_key=meeting_key_int,
            session_code=session_code,
            driver_options=driver_options,
        )
        logger.info(
            "Session bootstrap completed for session_key=%s",
            session_key,
        )
        return payload
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to finalize session bootstrap: %s", exc)
        return {
            'loaded': False,
            'error': str(exc),
            'drivers': drivers_map,
            'track_map': _empty_track_map(),
        }


def _format_doc_list(docs: list, category: str = "unknown") -> list:
    """
    Format document list for display in sidebar with edit and delete buttons.
    
    Args:
        docs: List of document dicts or strings
        category: Document category (global, strategy, weather, tire, fia)
    
    Returns:
        List of html components with clickable document names
    """
    if not docs:
        return [html.Small("No documents", className="text-muted fst-italic")]
    
    items = []
    for idx, doc in enumerate(docs):
        if isinstance(doc, dict):
            filename = doc.get('filename', 'Unknown')
            filepath = doc.get('filepath', '')
        else:
            filename = str(doc)
            filepath = ""
        
        # Use Button with filepath encoded in the index
        # Format: category|idx|filepath (base64 encoded to avoid special chars)
        import base64
        encoded_path = base64.b64encode(filepath.encode()).decode() if filepath else ""
        btn_index = f"{category}|{idx}|{encoded_path}"
        
        items.append(
            html.Div(
                [
                    html.I(className="bi bi-file-earmark-text me-1"),
                    dbc.Button(
                        filename,
                        id={"type": "doc-edit-btn", "index": btn_index},
                        color="link",
                        size="sm",
                        className="p-0 text-start flex-grow-1",
                        style={
                            "textDecoration": "underline dotted",
                            "color": "#6ea8fe",
                            "fontSize": "inherit",
                        },
                    ),
                    dbc.Button(
                        "✖",
                        id={"type": "doc-delete-btn", "index": btn_index},
                        color="danger",
                        outline=True,
                        size="sm",
                        className="ms-2",
                        title="Delete document",
                        style={
                            "padding": "0px 4px",
                            "lineHeight": "1.15",
                            "fontSize": "0.5rem",
                        },
                    ),
                ],
                className="small d-flex align-items-center mb-1",
            )
        )
    return items


@callback(
    Output('rag-reload-status', 'children', allow_duplicate=True),
    Output('rag-status', 'children', allow_duplicate=True),
    Output('rag-doc-count', 'children', allow_duplicate=True),
    Output('rag-global-docs', 'children', allow_duplicate=True),
    Output('rag-strategy-docs', 'children', allow_duplicate=True),
    Output('rag-weather-docs', 'children', allow_duplicate=True),
    Output('rag-performance-docs', 'children', allow_duplicate=True),
    Output('rag-race-control-docs', 'children', allow_duplicate=True),
    Output('rag-race-position-docs', 'children', allow_duplicate=True),
    Output('rag-fia-docs', 'children', allow_duplicate=True),
    Input({'type': 'doc-delete-btn', 'index': ALL}, 'n_clicks'),
    prevent_initial_call=True
)
def delete_rag_document(_delete_clicks):
    """Delete a RAG document from disk and remove its chunks from ChromaDB."""
    import base64
    from pathlib import Path

    triggered = ctx.triggered_id
    if not triggered or not isinstance(triggered, dict):
        raise PreventUpdate

    # Guard: ignore initial render when no delete button was actually clicked
    if not ctx.triggered or ctx.triggered[0].get('value') in (None, 0):
        raise PreventUpdate

    btn_index = triggered.get('index', '')
    try:
        _category, _idx, encoded_path = btn_index.split('|', 2)
    except ValueError:
        logger.warning("Invalid delete button index: %s", btn_index)
        raise PreventUpdate

    try:
        decoded_path = base64.b64decode(encoded_path.encode()).decode() if encoded_path else ""
        if not decoded_path:
            raise ValueError("Missing document path")

        rag_manager = get_rag_manager()
        base_path = Path(rag_manager.document_loader.base_path).resolve()
        file_path = Path(decoded_path).resolve()

        if not file_path.exists():
            status_msg = "⚠️ Document not found on disk"
        else:
            try:
                relative_source = file_path.relative_to(base_path)
            except ValueError:
                logger.warning("Refusing to delete path outside base_path: %s", file_path)
                return (
                    "❌ Refused: invalid path",
                    dash.no_update,
                    dash.no_update,
                    dash.no_update,
                    dash.no_update,
                    dash.no_update,
                    dash.no_update,
                    dash.no_update,
                    dash.no_update,
                    dash.no_update,
                )

            # Remove from vector store (delete all chunks for this source)
            source = str(relative_source)
            all_docs = rag_manager.vector_store.get_all_documents()
            ids_to_delete = [
                doc["id"]
                for doc in all_docs
                if doc.get("metadata", {}).get("source") == source
            ]
            rag_manager.vector_store.delete(ids_to_delete)

            # Remove file from disk
            file_path.unlink(missing_ok=True)

            status_msg = f"✅ Deleted: {file_path.name} ({len(ids_to_delete)} chunks)"

        # Refresh sidebar lists from current vector store state
        stats = rag_manager.vector_store.get_collection_stats()
        chunk_count = int(stats.get("document_count", 0))
        current_context = rag_manager.current_context
        docs = rag_manager.list_documents(
            year=current_context.year if current_context else None,
            circuit=current_context.circuit if current_context else None,
        )

        # Update cached context counts if context exists
        if rag_manager.current_context is not None:
            rag_manager.current_context.chunk_count = chunk_count
            rag_manager.current_context.document_count = sum(
                len(v) for v in docs.values() if isinstance(v, list)
            )
            rag_manager.current_context.categories = {
                k: len(v) for k, v in docs.items() if isinstance(v, list)
            }

        status = "🟢 Loaded" if chunk_count > 0 else "🟡 No docs"
        doc_count_text = f"({chunk_count} chunks)" if chunk_count > 0 else ""

        return (
            status_msg,
            status,
            doc_count_text,
            _format_doc_list(docs.get("global", []), "global"),
            _format_doc_list(docs.get("strategy", []), "strategy"),
            _format_doc_list(docs.get("weather", []), "weather"),
            _format_doc_list(docs.get("performance", []), "performance"),
            _format_doc_list(docs.get("race_control", []), "race_control"),
            _format_doc_list(docs.get("race_position", []), "race_position"),
            _format_doc_list(docs.get("fia", []), "fia"),
        )

    except Exception as exc:  # noqa: BLE001
        logger.error("Error deleting RAG document: %s", exc, exc_info=True)
        return (
            "❌ Error deleting document",
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
        )


def _get_circuit_name_for_rag(meeting_key: int, year: int) -> str:
    """
    Convert meeting_key to circuit name for RAG folder lookup.
    
    Args:
        meeting_key: OpenF1 meeting key
        year: Season year
        
    Returns:
        Circuit name in snake_case (e.g., 'abu_dhabi')
    """
    try:
        # Get meeting info from OpenF1
        meetings = openf1_provider._request(
            "meetings",
            {"year": year, "meeting_key": meeting_key}
        )
        if meetings:
            # Extract circuit name and convert to folder format
            meeting_name = meetings[0].get('meeting_name', '')
            # Remove "Grand Prix" and convert to snake_case
            circuit = meeting_name.lower()
            circuit = circuit.replace(' grand prix', '')
            circuit = circuit.replace(' ', '_')
            circuit = circuit.replace('-', '_')
            return circuit
    except Exception as e:
        logger.warning(f"Could not get circuit name for meeting_key={meeting_key}: {e}")
    return ""


def _load_tire_window_overrides(
    session_info: dict,
    session_obj: Optional[SessionAdapter],
) -> Optional[Dict[str, Dict[str, int]]]:
    if session_obj is None:
        return None

    year = session_info.get("year") or session_obj.date.year
    meeting_key = session_info.get("meeting_key")
    if not year or not meeting_key:
        return None

    circuit_name = _get_circuit_name_for_rag(int(meeting_key), int(year))
    if not circuit_name:
        return None

    strategy_path = (
        Path("data/rag")
        / str(year)
        / "circuits"
        / circuit_name
        / "strategy.md"
    )

    overrides = load_tire_window_overrides_from_path(strategy_path)
    if overrides:
        logger.info("Loaded tire window overrides from %s", strategy_path)
    else:
        logger.info("No tire window overrides found; using defaults")
    return overrides


@callback(
    Output('rag-status', 'children'),
    Output('rag-doc-count', 'children'),
    Output('rag-global-docs', 'children'),
    Output('rag-strategy-docs', 'children'),
    Output('rag-weather-docs', 'children'),
    Output('rag-performance-docs', 'children'),
    Output('rag-race-control-docs', 'children'),
    Output('rag-race-position-docs', 'children'),
    Output('rag-fia-docs', 'children'),
    Input('year-selector', 'value'),
    Input('circuit-selector', 'value'),
    prevent_initial_call=False
)
def update_rag_on_context_change(year, meeting_key):
    """
    Load RAG documents when year/circuit context changes.
    
    This callback:
    1. Loads global documents (always)
    2. Loads year-level documents
    3. Loads circuit-specific documents if available
    4. Updates the sidebar display with document lists
    """
    if not year:
        return (
            "⚪ Not loaded",
            "",
            [html.Small("Select year first", className="text-muted fst-italic")],
            [], [], [], [], [], []
        )
    
    try:
        rag_manager = get_rag_manager()
        
        # Convert meeting_key to circuit name
        circuit = None
        if meeting_key:
            circuit = _get_circuit_name_for_rag(meeting_key, year)
        
        # Load context into ChromaDB
        chunk_count = rag_manager.load_context(year=year, circuit=circuit)
        
        # Get document lists by category
        docs = rag_manager.list_documents(year=year, circuit=circuit)
        
        # Debug: Log what documents are found per category
        logger.info(f"RAG docs by category: {[(k, len(v)) for k, v in docs.items()]}")
        
        # Determine status icon
        if chunk_count > 0:
            status = "🟢 Loaded"
        else:
            status = "🟡 No docs"
        
        doc_count_text = f"({chunk_count} chunks)"
        
        # Format lists for display (with category for clickable editing)
        global_list = _format_doc_list(docs.get("global", []), "global")
        strategy_list = _format_doc_list(docs.get("strategy", []), "strategy")
        weather_list = _format_doc_list(docs.get("weather", []), "weather")
        performance_list = _format_doc_list(
            docs.get("performance", []), "performance"
        )
        race_control_list = _format_doc_list(
            docs.get("race_control", []), "race_control"
        )
        race_position_list = _format_doc_list(
            docs.get("race_position", []), "race_position"
        )
        fia_list = _format_doc_list(docs.get("fia", []), "fia")
        
        return (
            status,
            doc_count_text,
            global_list,
            strategy_list,
            weather_list,
            performance_list,
            race_control_list,
            race_position_list,
            fia_list
        )
        
    except Exception as e:
        logger.error(f"Error loading RAG context: {e}")
        return (
            "🔴 Error",
            "",
            [html.Small(f"Error: {str(e)[:50]}", className="text-danger")],
            [], [], [], [], [], []
        )


@callback(
    Output('rag-reload-status', 'children'),
    Output('rag-status', 'children', allow_duplicate=True),
    Output('rag-doc-count', 'children', allow_duplicate=True),
    Input('rag-reload-btn', 'n_clicks'),
    State('year-selector', 'value'),
    State('circuit-selector', 'value'),
    prevent_initial_call=True
)
def reload_rag_documents(n_clicks, year, meeting_key):
    """Manually reload RAG documents."""
    if not n_clicks:
        raise PreventUpdate
    
    try:
        rag_manager = get_rag_manager()
        
        # Convert meeting_key to circuit name
        circuit = None
        if meeting_key and year:
            circuit = _get_circuit_name_for_rag(meeting_key, year)
        
        # Force reload
        chunk_count = rag_manager.reload()
        
        status_msg = f"✅ Reloaded {chunk_count} chunks"
        return (
            status_msg,
            "🟢 Loaded" if chunk_count > 0 else "🟡 No docs",
            f"({chunk_count} chunks)"
        )
        
    except Exception as e:
        logger.error(f"Error reloading RAG: {e}")
        return f"❌ Error: {str(e)[:50]}", "🔴 Error", ""


@callback(
    Output('fia-reg-status', 'children'),
    Output('fia-existing-regs', 'children'),
    Input('fia-year-selector', 'value'),
    prevent_initial_call=False
)
def update_fia_regulations_status(selected_year):
    """Update FIA regulations status and list existing regulations."""
    from pathlib import Path
    
    if not selected_year:
        return "⚠️ No year selected", ""
    
    try:
        # Check for existing regulation file
        fia_dir = Path('data/rag') / str(selected_year)
        reg_file = fia_dir / f"fia_regulations_{selected_year}.md"
        
        if reg_file.exists():
            status = html.Span([
                html.I(className="fas fa-check-circle text-success me-1"),
                f"✅ {selected_year} regulations loaded"
            ], className="small text-success")
            
            # Show file with edit button
            existing_list = html.Div([
                html.Button(
                    [html.I(className="fas fa-file-alt me-1"), f"fia_regulations_{selected_year}.md"],
                    id={'type': 'doc-edit-btn', 'index': str(reg_file)},
                    n_clicks=0,
                    className="btn btn-sm btn-link text-start p-0 text-info"
                ),
                html.Small(f" • {reg_file.stat().st_size / 1024:.1f} KB", className="text-muted ms-2")
            ])
        else:
            status = html.Span([
                html.I(className="fas fa-exclamation-circle text-warning me-1"),
                f"⚠️ No regulations for {selected_year}"
            ], className="small text-warning")
            existing_list = html.Small("No regulation file found. Upload one above.", className="text-muted")
        
        return status, existing_list
        
    except Exception as e:
        logger.error(f"Error checking FIA regulations: {e}")
        return html.Span(f"❌ Error: {str(e)[:30]}", className="small text-danger"), ""


@callback(
    Output('fia-upload-preview', 'children'),
    Input('fia-reg-upload', 'contents'),
    State('fia-reg-upload', 'filename'),
    prevent_initial_call=True
)
def preview_fia_upload(contents, filename):
    """Show preview of uploaded FIA regulation file."""
    if not contents or not filename:
        return ""
    
    try:
        file_size = len(contents) * 3 / 4  # Approximate decoded size
        return html.Div([
            html.Small([
                html.I(className="fas fa-file-pdf text-danger me-1"),
                html.Strong(filename),
                f" ({file_size / 1024:.1f} KB)"
            ], className="text-muted"),
            html.Br(),
            html.Small("Click to open upload modal and confirm", className="text-info")
        ], className="p-2 bg-dark rounded")
        
    except Exception:
        return ""


# ============================================================================
# DOCUMENT UPLOAD CALLBACKS

# Hidden style for overlay (used to hide it)
OVERLAY_HIDDEN = {"display": "none"}
OVERLAY_VISIBLE = {
    "display": "flex",
    "position": "absolute",
    "top": 0,
    "left": 0,
    "right": 0,
    "bottom": 0,
    "backgroundColor": "rgba(0, 0, 0, 0.85)",
    "zIndex": 1000,
    "alignItems": "center",
    "justifyContent": "center",
    "borderRadius": "0.3rem"
}

@callback(
    Output('upload-modal', 'is_open'),
    Output('upload-file-info', 'children'),
    Output('upload-category-override', 'value'),
    Output('upload-preview-content', 'children'),
    Output('upload-target-path', 'children'),
    Output('upload-filename-edit', 'value'),
    Output('upload-duplicate-warning', 'children'),
    Output('upload-file-store', 'data'),
    Output('upload-processing-status', 'children'),
    Output('upload-loading-overlay', 'style', allow_duplicate=True),
    Output('upload-confirm-btn', 'disabled'),
    Output('upload-confirm-btn', 'children'),
    # Add RAG status outputs to update sidebar after upload
    Output('rag-status', 'children', allow_duplicate=True),
    Output('rag-doc-count', 'children', allow_duplicate=True),
    Output('rag-global-docs', 'children', allow_duplicate=True),
    Output('rag-strategy-docs', 'children', allow_duplicate=True),
    Output('rag-weather-docs', 'children', allow_duplicate=True),
    Output('rag-performance-docs', 'children', allow_duplicate=True),
    Output('rag-race-control-docs', 'children', allow_duplicate=True),
    Output('rag-race-position-docs', 'children', allow_duplicate=True),
    Output('rag-fia-docs', 'children', allow_duplicate=True),
    Input({'type': 'rag-upload-input', 'category': ALL}, 'contents'),
    Input('fia-reg-upload', 'contents'),
    Input('upload-confirm-btn', 'n_clicks'),
    Input('upload-cancel-btn', 'n_clicks'),
    State({'type': 'rag-upload-input', 'category': ALL}, 'filename'),
    State('fia-reg-upload', 'filename'),
    State('fia-year-selector', 'value'),
    State('year-selector', 'value'),
    State('circuit-selector', 'value'),
    State('upload-category-override', 'value'),
    State('upload-filename-edit', 'value'),
    State('upload-file-store', 'data'),
    prevent_initial_call=True
)
def handle_document_upload(
    category_upload_contents_list, fia_contents, confirm_clicks, cancel_clicks,
    category_upload_filenames_list, fia_filename, fia_year, context_year, context_circuit,
    category_override, edited_filename, stored_file_data
):
    """Handle document upload flow: file selection → preview/LLM → confirmation → save."""
    import base64
    import io
    from pathlib import Path
    
    triggered_id = ctx.triggered_id
    
    # Helper for RAG no_update tuple (9 values for RAG outputs)
    rag_no_updates = (
        dash.no_update, dash.no_update,  # status, doc_count
        dash.no_update, dash.no_update, dash.no_update,  # global, strategy, weather
        dash.no_update, dash.no_update, dash.no_update, dash.no_update  # perf, rc, pos, fia
    )
    
    # UI reset values (overlay hidden, button enabled, button text)
    ui_reset = (OVERLAY_HIDDEN, False, "✅ Upload & Index")
    
    # Cancel button - close modal (9 original + 3 UI + 9 RAG = 21 outputs)
    if triggered_id == 'upload-cancel-btn':
        return (False, "", "", None, "", "", "", None, "") + ui_reset + rag_no_updates
    
    # Confirm button - process and save document
    if triggered_id == 'upload-confirm-btn' and stored_file_data:
        try:
            # Decode file
            content_type, content_string = stored_file_data['content'].split(',')
            decoded = base64.b64decode(content_string)
            filename = stored_file_data['filename']
            category = category_override if category_override else stored_file_data.get('default_category', 'global')
            
            # Check if user selected FIA category OR if uploaded via FIA button
            is_fia_category = (category == 'fia') or stored_file_data.get('is_fia')
            
            # Determine target directory
            if is_fia_category:
                # FIA documents go to year level: data/rag/2025/fia_regulations.md
                year = fia_year if fia_year else context_year
                target_dir = Path('data/rag') / str(year)
                if edited_filename:
                    final_filename = edited_filename if edited_filename.endswith('.md') else f"{edited_filename}.md"
                else:
                    final_filename = f"fia_regulations_{year}.md"
            elif category == 'global':
                # Global category goes to data/rag/global/
                target_dir = Path('data/rag') / 'global'
                if edited_filename:
                    final_filename = edited_filename if edited_filename.endswith('.md') else f"{edited_filename}.md"
                else:
                    final_filename = filename.replace('.pdf', '.md').replace('.docx', '.md').replace('.doc', '.md')
                    final_filename = final_filename.lower().replace(' ', '_')
            else:
                # Circuit-specific categories: strategy, weather, performance, race_control, race_position
                if context_circuit and context_year:
                    circuit_name = _get_circuit_name_for_rag(context_circuit, context_year)
                    target_dir = Path('data/rag') / str(context_year) / 'circuits' / circuit_name
                    # Use category as filename: strategy.md, weather.md, etc.
                    if category in ['strategy', 'weather', 'performance', 'race_control', 'race_position']:
                        final_filename = f"{category}.md"
                    else:
                        # Other category - use original filename
                        if edited_filename:
                            final_filename = edited_filename if edited_filename.endswith('.md') else f"{edited_filename}.md"
                        else:
                            final_filename = filename.replace('.pdf', '.md').replace('.docx', '.md').replace('.doc', '.md')
                            final_filename = final_filename.lower().replace(' ', '_')
                elif context_year:
                    # Year level but no circuit - save to year folder
                    target_dir = Path('data/rag') / str(context_year)
                    if edited_filename:
                        final_filename = edited_filename if edited_filename.endswith('.md') else f"{edited_filename}.md"
                    else:
                        final_filename = filename.replace('.pdf', '.md').replace('.docx', '.md').replace('.doc', '.md')
                        final_filename = final_filename.lower().replace(' ', '_')
                else:
                    # No context - save to global
                    target_dir = Path('data/rag') / 'global'
                    if edited_filename:
                        final_filename = edited_filename if edited_filename.endswith('.md') else f"{edited_filename}.md"
                    else:
                        final_filename = filename.replace('.pdf', '.md').replace('.docx', '.md').replace('.doc', '.md')
                        final_filename = final_filename.lower().replace(' ', '_')
            
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path = target_dir / final_filename
            
            # No backup - just overwrite existing file if it exists
            
            # Convert to markdown
            file_ext = Path(filename).suffix.lower()
            
            if file_ext == '.pdf':
                # Convert PDF
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                    tmp.write(decoded)
                    tmp_path = tmp.name
                
                try:
                    document_loader = DocumentLoader()
                    markdown_content = document_loader.convert_pdf_to_markdown(tmp_path, str(target_path))
                    
                except Exception as conv_error:
                    # Conversion failed - reject upload
                    error_msg = html.Div([
                        html.I(className="fas fa-exclamation-triangle text-danger me-2"),
                        html.Span(f"PDF conversion failed: {str(conv_error)[:100]}", className="text-danger"),
                        html.Br(),
                        html.Small("File may be corrupted, password-protected, or have unsupported formatting.", className="text-muted")
                    ], className="alert alert-danger")
                    
                    return False, "", "", None, "", "", "", None, error_msg
                finally:
                    Path(tmp_path).unlink(missing_ok=True)
                    
            elif file_ext in ['.docx', '.doc']:
                # Convert DOCX
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
                    tmp.write(decoded)
                    tmp_path = tmp.name
                
                try:
                    document_loader = DocumentLoader()
                    markdown_content = document_loader.convert_docx_to_markdown(tmp_path, str(target_path))
                except Exception as conv_error:
                    error_msg = html.Div([
                        html.I(className="fas fa-exclamation-triangle text-danger me-2"),
                        html.Span(f"DOCX conversion failed: {str(conv_error)[:100]}", className="text-danger")
                    ], className="alert alert-danger")
                    return False, "", "", None, "", "", "", None, error_msg
                finally:
                    Path(tmp_path).unlink(missing_ok=True)
                    
            elif file_ext == '.md':
                # Already markdown - just save
                markdown_content = decoded.decode('utf-8')
                with open(target_path, 'w', encoding='utf-8') as f:
                    # Add metadata header if not present
                    if not markdown_content.strip().startswith('---'):
                        from datetime import datetime
                        metadata = f"""---
category: {category}
year: {context_year or fia_year}
uploaded_at: {datetime.now().isoformat()}
---

"""
                        f.write(metadata + markdown_content)
                    else:
                        f.write(markdown_content)
            
            # Reload RAG with correct year from UI state (not cached context)
            rag_manager = get_rag_manager()
            # Use context_year from UI, or fia_year for FIA docs
            reload_year = context_year or fia_year
            # Convert circuit selector value to circuit name
            reload_circuit = None
            if context_circuit:
                reload_circuit = _get_circuit_name_for_rag(context_circuit, reload_year)
            chunk_count = rag_manager.load_context(
                year=reload_year,
                circuit=reload_circuit,
                clear_existing=True
            )
            
            # Get updated document lists for sidebar
            docs = rag_manager.list_documents(
                year=reload_year,
                circuit=reload_circuit,
            )
            
            # Format lists for display
            global_list = _format_doc_list(docs.get("global", []), "global")
            strategy_list = _format_doc_list(docs.get("strategy", []), "strategy")
            weather_list = _format_doc_list(docs.get("weather", []), "weather")
            performance_list = _format_doc_list(
                docs.get("performance", []), "performance"
            )
            race_control_list = _format_doc_list(
                docs.get("race_control", []), "race_control"
            )
            race_position_list = _format_doc_list(
                docs.get("race_position", []), "race_position"
            )
            fia_list = _format_doc_list(docs.get("fia", []), "fia")
            
            # Success - show toast and close modal
            success_msg = html.Div([
                html.I(className="fas fa-check-circle text-success me-2"),
                html.Span(f"✅ {final_filename} uploaded successfully ({chunk_count} chunks indexed)", className="text-success")
            ], className="alert alert-success")
            
            # Close modal and show success (9 original + 3 UI + 9 RAG = 21 outputs)
            return (
                False, "", "", None, "", "", "", None, success_msg,
                # UI reset (hide overlay, enable button, reset text)
                OVERLAY_HIDDEN, False, "✅ Upload & Index",
                # RAG status updates
                "🟢 Loaded",
                f"({chunk_count} chunks)",
                global_list, strategy_list, weather_list,
                performance_list, race_control_list, race_position_list, fia_list
            )
            
        except Exception as e:
            logger.error(f"Upload processing error: {e}", exc_info=True)
            error_msg = html.Div([
                html.I(className="fas fa-times-circle text-danger me-2"),
                html.Span(f"Upload failed: {str(e)[:100]}", className="text-danger")
            ], className="alert alert-danger")
            return (False, "", "", None, "", "", "", None, error_msg) + ui_reset + rag_no_updates
    
    # File upload - open modal with preview and LLM suggestion
    file_contents = None
    filename = None
    is_fia = False
    category_hint = None
    
    # Check which upload triggered
    if triggered_id and isinstance(triggered_id, dict) and triggered_id.get('type') == 'rag-upload-input':
        # Category upload from hidden dcc.Upload
        category_hint = triggered_id.get('category')
        
        # Find which upload has content
        for i, contents in enumerate(category_upload_contents_list):
            if contents:
                file_contents = contents
                filename = category_upload_filenames_list[i]
                break
        
    elif triggered_id == 'fia-reg-upload' and fia_contents:
        file_contents = fia_contents
        filename = fia_filename
        is_fia = True
        category_hint = 'fia'
    
    if not file_contents or not filename:
        raise PreventUpdate
    
    try:
        # Parse file
        content_type, content_string = file_contents.split(',')
        decoded = base64.b64decode(content_string)
        file_size = len(decoded)
        file_ext = Path(filename).suffix.lower()
        
        # Validate file
        if file_size > 10 * 1024 * 1024:  # 10MB limit
            error_msg = html.Div([
                html.I(className="fas fa-exclamation-triangle text-warning me-2"),
                html.Span(f"File too large: {file_size / 1024 / 1024:.1f}MB (max 10MB)", className="text-warning")
            ], className="alert alert-warning")
            return (False, error_msg, "", None, "", "", "", None, "") + ui_reset + rag_no_updates
        
        if file_ext not in ['.pdf', '.docx', '.doc', '.md']:
            error_msg = html.Div([
                html.I(className="fas fa-exclamation-triangle text-warning me-2"),
                html.Span(f"Unsupported file type: {file_ext}", className="text-warning")
            ], className="alert alert-warning")
            return (False, error_msg, "", None, "", "", "", None, "") + ui_reset + rag_no_updates
        
        # File info display
        file_info = html.Div([
            html.P([html.Strong("Name: "), filename]),
            html.P([html.Strong("Size: "), f"{file_size / 1024:.1f} KB"]),
            html.P([html.Strong("Type: "), file_ext.upper()])
        ])
        
        # Quick preview (detailed extraction happens at save time)
        preview_text = ""
        if file_ext == '.md':
            preview_text = decoded.decode('utf-8', errors='ignore')[:500]
        elif file_ext == '.pdf':
            preview_text = f"📄 PDF file ready to upload. Content will be extracted during save."
        elif file_ext in ['.docx', '.doc']:
            preview_text = f"📝 Word document ready to upload. Content will be extracted during save."
        
        # Determine default category based on button source
        if is_fia:
            default_category = 'fia'
        else:
            # Try to infer from filename
            fname_lower = filename.lower()
            if 'fia' in fname_lower or 'regulation' in fname_lower or 'sporting' in fname_lower:
                default_category = 'fia'
            elif 'strategy' in fname_lower or 'tyre' in fname_lower or 'pit' in fname_lower:
                default_category = 'strategy'
            elif 'weather' in fname_lower or 'rain' in fname_lower or 'temperature' in fname_lower:
                default_category = 'weather'
            elif 'telemetry' in fname_lower or 'performance' in fname_lower or 'lap' in fname_lower:
                default_category = 'performance'
            elif 'flag' in fname_lower or 'incident' in fname_lower or 'safety' in fname_lower:
                default_category = 'race_control'
            elif 'position' in fname_lower or 'gap' in fname_lower or 'overtake' in fname_lower:
                default_category = 'race_position'
            else:
                default_category = None  # User must select
        
        # Determine initial target path based on default category
        is_fia_category = (default_category == 'fia')
        
        if default_category:
            if is_fia_category:
                # FIA documents go to year level
                year = fia_year if fia_year else context_year
                target_path_str = f"data/rag/{year}/fia_regulations_{year}.md"
                suggested_filename = f"fia_regulations_{year}"
            elif default_category == 'global':
                # Global category
                target_path_str = f"data/rag/global/{filename.replace(file_ext, '.md')}"
                suggested_filename = filename.replace(file_ext, '')
            elif default_category in ['strategy', 'weather', 'performance', 'race_control', 'race_position']:
                # Circuit-specific categories
                if context_circuit and context_year:
                    circuit = _get_circuit_name_for_rag(context_circuit, context_year)
                    target_path_str = f"data/rag/{context_year}/circuits/{circuit}/{default_category}.md"
                    suggested_filename = default_category
                elif context_year:
                    target_path_str = f"data/rag/{context_year}/{default_category}.md"
                    suggested_filename = default_category
                else:
                    target_path_str = f"data/rag/global/{filename.replace(file_ext, '.md')}"
                    suggested_filename = filename.replace(file_ext, '')
            else:
                # Fallback
                target_path_str = f"data/rag/global/{filename.replace(file_ext, '.md')}"
                suggested_filename = filename.replace(file_ext, '')
        else:
            # No default - show placeholder until user selects
            target_path_str = "⚠️ Select a category first"
            suggested_filename = filename.replace(file_ext, '')
        
        # Check for duplicates
        target_path_obj = Path(target_path_str)
        if target_path_obj.exists():
            duplicate_warning = html.Div([
                html.I(className="fas fa-exclamation-triangle text-warning me-2"),
                html.Span("⚠️ File exists! Uploading will create a backup of the old version.", className="text-warning fw-bold")
            ], className="alert alert-warning")
        else:
            duplicate_warning = ""
        
        # Store file data for confirmation
        stored_data = {
            'content': file_contents,
            'filename': filename,
            'default_category': default_category,
            'is_fia': is_fia
        }
        
        # Return modal opened with all info (9 original + 3 UI + 9 RAG no_update)
        return (
            True,  # is_open
            file_info,
            default_category,  # Pre-select default category (if any)
            preview_text[:500],  # Preview first 500 chars
            target_path_str,
            suggested_filename,
            duplicate_warning,
            stored_data,
            ""  # No processing status yet
        ) + ui_reset + rag_no_updates
        
    except Exception as e:
        logger.error(f"Error preparing upload: {e}", exc_info=True)
        error_msg = html.Div([
            html.I(className="fas fa-times-circle text-danger me-2"),
            html.Span(f"Error: {str(e)[:100]}", className="text-danger")
        ], className="alert alert-danger")
        return (False, error_msg, "", None, "", "", "", None, "") + ui_reset + rag_no_updates


@callback(
    Output('upload-target-path', 'children', allow_duplicate=True),
    Output('upload-filename-edit', 'value', allow_duplicate=True),
    Input('upload-category-override', 'value'),
    State('upload-file-store', 'data'),
    State('year-selector', 'value'),
    State('circuit-selector', 'value'),
    State('fia-year-selector', 'value'),
    prevent_initial_call=True
)
def update_target_path_on_category_change(
    selected_category, stored_file_data, context_year, context_circuit, fia_year
):
    """Update target path display when user changes category in dropdown."""
    if not stored_file_data or not selected_category:
        raise PreventUpdate
    
    try:
        from pathlib import Path
        
        filename = stored_file_data['filename']
        file_ext = Path(filename).suffix.lower()
        is_fia_from_button = stored_file_data.get('is_fia', False)
        
        # User selected category takes priority
        is_fia_category = (selected_category == 'fia') or is_fia_from_button
        
        # Calculate new target path based on selected category
        if is_fia_category:
            year = fia_year if fia_year else context_year
            target_path_str = f"data/rag/{year}/fia_regulations_{year}.md"
            suggested_filename = f"fia_regulations_{year}"
        elif selected_category == 'global':
            target_path_str = f"data/rag/global/{filename.replace(file_ext, '.md')}"
            suggested_filename = filename.replace(file_ext, '')
        elif selected_category in ['strategy', 'weather', 'performance', 'race_control', 'race_position']:
            if context_circuit and context_year:
                circuit = _get_circuit_name_for_rag(context_circuit, context_year)
                target_path_str = f"data/rag/{context_year}/circuits/{circuit}/{selected_category}.md"
                suggested_filename = selected_category
            elif context_year:
                target_path_str = f"data/rag/{context_year}/{selected_category}.md"
                suggested_filename = selected_category
            else:
                target_path_str = f"data/rag/global/{filename.replace(file_ext, '.md')}"
                suggested_filename = filename.replace(file_ext, '')
        else:
            # Other/unknown category
            if context_circuit and context_year:
                circuit = _get_circuit_name_for_rag(context_circuit, context_year)
                target_path_str = f"data/rag/{context_year}/circuits/{circuit}/{filename.replace(file_ext, '.md')}"
            elif context_year:
                target_path_str = f"data/rag/{context_year}/{filename.replace(file_ext, '.md')}"
            else:
                target_path_str = f"data/rag/global/{filename.replace(file_ext, '.md')}"
            
            suggested_filename = filename.replace(file_ext, '')
        
        return target_path_str, suggested_filename
        
    except Exception as e:
        logger.error(f"Error updating target path: {e}", exc_info=True)
        raise PreventUpdate


@callback(
    Output('upload-preview-collapse', 'is_open'),
    Input('upload-preview-toggle', 'n_clicks'),
    State('upload-preview-collapse', 'is_open'),
    prevent_initial_call=True
)
def toggle_upload_preview(n_clicks, is_open):
    """Toggle preview content visibility."""
    return not is_open if n_clicks else is_open


# ============================================================================
# TEMPLATE GENERATION CALLBACKS
# ============================================================================

@callback(
    Output('rag-generate-confirm-modal', 'is_open'),
    Output('rag-generate-confirm-message', 'children'),
    Output('rag-generate-existing-files', 'children'),
    Output('rag-generate-store', 'data'),
    Output('rag-reload-status', 'children', allow_duplicate=True),
    Output('rag-status', 'children', allow_duplicate=True),
    Output('rag-doc-count', 'children', allow_duplicate=True),
    Output('rag-global-docs', 'children', allow_duplicate=True),
    Output('rag-strategy-docs', 'children', allow_duplicate=True),
    Output('rag-weather-docs', 'children', allow_duplicate=True),
    Output('rag-performance-docs', 'children', allow_duplicate=True),
    Output('rag-race-control-docs', 'children', allow_duplicate=True),
    Output('rag-race-position-docs', 'children', allow_duplicate=True),
    Output('rag-fia-docs', 'children', allow_duplicate=True),
    Input('rag-generate-btn', 'n_clicks'),
    Input('rag-generate-cancel-btn', 'n_clicks'),
    Input('rag-generate-confirm-btn', 'n_clicks'),
    State('year-selector', 'value'),
    State('circuit-selector', 'value'),
    State('rag-generate-store', 'data'),
    prevent_initial_call=True
)
def handle_template_generation(
    gen_clicks, cancel_clicks, confirm_clicks,
    year, meeting_key, store_data
):
    """Handle template generation with confirmation for overwrites."""
    from pathlib import Path
    from dash.exceptions import PreventUpdate
    
    triggered_id = ctx.triggered_id
    
    # Default empty doc lists for early returns (7 categories)
    no_update_lists = (
        dash.no_update, dash.no_update, dash.no_update, dash.no_update,
        dash.no_update, dash.no_update, dash.no_update
    )
    
    # Cancel button - close modal
    if triggered_id == 'rag-generate-cancel-btn':
        return (
            False, "", "", {"year": None, "circuit": None}, "",
            dash.no_update, dash.no_update,
            *no_update_lists
        )
    
    # Generate button clicked - check for existing files
    if triggered_id == 'rag-generate-btn':
        if not year or not meeting_key:
            return (
                False, "", "", store_data, "⚠️ Select year and circuit first",
                dash.no_update, dash.no_update,
                *no_update_lists
            )
        
        # Get circuit name
        circuit = _get_circuit_name_for_rag(meeting_key, year)
        if not circuit:
            return (
                False, "", "", store_data, "⚠️ Could not determine circuit",
                dash.no_update, dash.no_update,
                *no_update_lists
            )
        
        # Check for existing files
        rag_path = Path("data/rag") / str(year) / "circuits" / circuit
        existing_files = []
        if rag_path.exists():
            existing_files = [f.name for f in rag_path.glob("*.md")]
        
        circuit_display = circuit.replace('_', ' ').title()
        
        if existing_files:
            # Show confirmation modal
            message = f"Generate templates for {circuit_display} ({year})?"
            files_msg = f"⚠️ Will overwrite: {', '.join(existing_files)}"
            return (
                True,
                message,
                files_msg,
                {"year": year, "circuit": circuit},
                "",
                dash.no_update, dash.no_update,
                *no_update_lists
            )
        else:
            # No existing files - generate directly
            return _do_generate_templates(year, circuit, circuit_display)
    
    # Confirm button - actually generate
    if triggered_id == 'rag-generate-confirm-btn':
        if store_data and store_data.get('year') and store_data.get('circuit'):
            circuit_display = store_data['circuit'].replace('_', ' ').title()
            return _do_generate_templates(
                store_data['year'],
                store_data['circuit'],
                circuit_display
            )
    
    raise PreventUpdate


def _do_generate_templates(year: int, circuit: str, circuit_display: str):
    """
    Execute template generation and return callback outputs.
    
    Args:
        year: Target year
        circuit: Circuit name in snake_case
        circuit_display: Circuit name for display
    
    Returns:
        Tuple of callback outputs (15 values for new category structure)
    """
    try:
        generator = get_template_generator()
        
        # Generate with save_to_disk=True
        logger.info(f"Generating templates for {circuit} ({year})...")
        docs = generator.generate_for_circuit(
            year=year,
            circuit=circuit,
            use_historical=True,
            save_to_disk=True
        )
        
        # Reload RAG context with correct year/circuit (not cached context)
        rag_manager = get_rag_manager()
        chunk_count = rag_manager.load_context(
            year=year,
            circuit=circuit,
            clear_existing=True
        )
        
        # Get updated document lists
        all_docs = rag_manager.list_documents(year=year, circuit=circuit)
        
        # Format lists for display
        global_list = _format_doc_list(all_docs.get("global", []), "global")
        strategy_list = _format_doc_list(
            all_docs.get("strategy", []), "strategy"
        )
        weather_list = _format_doc_list(all_docs.get("weather", []), "weather")
        performance_list = _format_doc_list(
            all_docs.get("performance", []), "performance"
        )
        race_control_list = _format_doc_list(
            all_docs.get("race_control", []), "race_control"
        )
        race_position_list = _format_doc_list(
            all_docs.get("race_position", []), "race_position"
        )
        fia_list = _format_doc_list(all_docs.get("fia", []), "fia")
        
        files_generated = list(docs.keys())
        status_msg = (
            f"✅ Generated {len(files_generated)} templates for "
            f"{circuit_display}: {', '.join(files_generated)}"
        )
        logger.info(status_msg)
        
        return (
            False,  # Close modal
            "",
            "",
            {"year": None, "circuit": None},
            status_msg,
            "🟢 Loaded",
            f"({chunk_count} chunks)",
            global_list,
            strategy_list,
            weather_list,
            performance_list,
            race_control_list,
            race_position_list,
            fia_list
        )
        
    except Exception as e:
        logger.error(f"Error generating templates: {e}")
        return (
            False,
            "",
            "",
            {"year": None, "circuit": None},
            f"❌ Error: {str(e)[:80]}",
            dash.no_update, dash.no_update,
            dash.no_update, dash.no_update, dash.no_update,
            dash.no_update, dash.no_update, dash.no_update,
            dash.no_update, dash.no_update
        )


# ============================================================================
# UPLOAD BUTTON TRIGGER (Clientside to activate file picker)
# ============================================================================

app.clientside_callback(
    """
    function(n_clicks_list) {
        // Find which button was clicked
        const triggered = dash_clientside.callback_context.triggered;
        if (!triggered || triggered.length === 0) {
            return window.dash_clientside.no_update;
        }
        
        const triggeredId = triggered[0].prop_id;
        
        // Extract category from the triggered button
        const match = triggeredId.match(/"category":"([^"]+)"/);
        if (match && match[1]) {
            const category = match[1];
            
            // Find and click the corresponding hidden upload input
            const uploadInputs = document.querySelectorAll('[id*="rag-upload-input"]');
            for (let input of uploadInputs) {
                const inputId = input.id;
                if (inputId.includes(category)) {
                    // Trigger click on the hidden dcc.Upload's file input
                    const fileInput = input.querySelector('input[type="file"]');
                    if (fileInput) {
                        fileInput.click();
                        return window.dash_clientside.no_update;
                    }
                }
            }
        }
        
        return window.dash_clientside.no_update;
    }
    """,
    Output({'type': 'rag-upload-btn', 'category': ALL}, 'n_clicks', allow_duplicate=True),
    Input({'type': 'rag-upload-btn', 'category': ALL}, 'n_clicks'),
    prevent_initial_call=True
)


# Clientside callback to show loading overlay immediately on upload confirm
app.clientside_callback(
    """
    function(n_clicks) {
        if (n_clicks) {
            // Show the loading overlay immediately
            const overlay = document.getElementById('upload-loading-overlay');
            if (overlay) {
                overlay.style.display = 'flex';
            }
            // Disable the buttons to prevent double-click
            const confirmBtn = document.getElementById('upload-confirm-btn');
            const cancelBtn = document.getElementById('upload-cancel-btn');
            if (confirmBtn) {
                confirmBtn.disabled = true;
                confirmBtn.innerHTML = '⏳ Processing...';
            }
            if (cancelBtn) {
                cancelBtn.disabled = true;
            }
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output('upload-loading-overlay', 'style'),
    Input('upload-confirm-btn', 'n_clicks'),
    prevent_initial_call=True
)


# ============================================================================
# DOCUMENT EDITOR MODAL CALLBACKS
# ============================================================================

@callback(
    Output('doc-editor-modal', 'is_open'),
    Output('doc-editor-title', 'children'),
    Output('doc-editor-path', 'children'),
    Output('doc-editor-textarea', 'value'),
    Output('doc-editor-store', 'data'),
    Output('doc-editor-status', 'children'),
    Input({'type': 'doc-edit-btn', 'index': ALL}, 'n_clicks'),
    Input('doc-editor-cancel-btn', 'n_clicks'),
    Input('doc-editor-save-btn', 'n_clicks'),
    State('doc-editor-textarea', 'value'),
    State('doc-editor-store', 'data'),
    prevent_initial_call=True
)
def handle_document_editor(
    btn_clicks, cancel_clicks, save_clicks,
    textarea_content, store_data
):
    """
    Handle document editor modal: open, save, cancel.
    
    This callback manages:
    - Opening modal when a document is clicked
    - Loading document content into textarea
    - Saving edited content back to file
    - Closing modal on cancel or after save
    """
    import base64
    import json
    from pathlib import Path
    
    # Debug: log what triggered the callback
    triggered = ctx.triggered
    triggered_id = ctx.triggered_id
    logger.debug(f"DOC EDITOR - triggered: {triggered}")
    logger.debug(f"DOC EDITOR - triggered_id: {triggered_id}")
    logger.debug(f"DOC EDITOR - btn_clicks: {btn_clicks}")
    
    # If no trigger info, prevent update
    if not triggered or triggered[0]['value'] is None:
        raise PreventUpdate
    
    # Cancel button - close modal
    if triggered_id == 'doc-editor-cancel-btn':
        return False, "", "", "", {"filepath": None}, ""
    
    # Save button - save content and close
    if triggered_id == 'doc-editor-save-btn':
        if store_data and store_data.get('filepath'):
            try:
                filepath = Path(store_data['filepath'])
                if filepath.exists() and filepath.suffix == '.md':
                    filepath.write_text(textarea_content, encoding='utf-8')
                    logger.info(f"Document saved: {filepath}")
                    return (
                        False, "", "", "",
                        {"filepath": None},
                        ""
                    )
                else:
                    return (
                        True,
                        f"📝 {store_data.get('filename', 'Document')}",
                        f"📁 {store_data.get('filepath', '')}",
                        textarea_content,
                        store_data,
                        "❌ Cannot save: invalid file path or not .md file"
                    )
            except Exception as e:
                logger.error(f"Error saving document: {e}")
                return (
                    True,
                    f"📝 {store_data.get('filename', 'Document')}",
                    f"📁 {store_data.get('filepath', '')}",
                    textarea_content,
                    store_data,
                    f"❌ Error saving: {str(e)[:50]}"
                )
        raise PreventUpdate
    
    # Document button click - check if any button was actually clicked
    # With ALL pattern, btn_clicks is a list, check if any is not None
    if btn_clicks and any(c is not None for c in btn_clicks):
        # Find which button was clicked from ctx.triggered
        triggered_prop = triggered[0].get('prop_id', '')
        logger.debug(f"DOC EDITOR - prop_id: {triggered_prop}")
        
        # prop_id format: {"type":"doc-edit-btn","index":"cat|idx|b64"}.n_clicks
        if 'doc-edit-btn' in triggered_prop:
            try:
                # Extract the JSON part before .n_clicks
                json_part = triggered_prop.rsplit('.', 1)[0]
                btn_info = json.loads(json_part)
                click_index = btn_info.get('index', '')
                
                logger.debug(f"DOC EDITOR - click_index: {click_index}")
                
                parts = click_index.split('|')
                if len(parts) >= 3:
                    encoded_path = parts[2]
                    
                    if encoded_path:
                        filepath = base64.b64decode(encoded_path.encode()).decode()
                        filename = Path(filepath).name if filepath else "Document"
                        
                        file_path = Path(filepath)
                        if file_path.exists():
                            content = file_path.read_text(encoding='utf-8')
                            logger.info(f"Opening document for edit: {filepath}")
                            return (
                                True,
                                f"📝 {filename}",
                                f"📁 {filepath}",
                                content,
                                {"filepath": filepath, "filename": filename},
                                ""
                            )
                        else:
                            return (
                                True,
                                f"📝 {filename}",
                                f"📁 {filepath}",
                                f"# File not found\n\nPath: {filepath}",
                                {"filepath": filepath, "filename": filename},
                                "⚠️ File does not exist"
                            )
                    else:
                        logger.warning(
                            f"No filepath in button index: {click_index}"
                        )
            except Exception as e:
                logger.error(f"Error parsing document button click: {e}")
                return (
                    True,
                    "📝 Error",
                    "",
                    f"# Error loading document\n\n{str(e)}",
                    {"filepath": None},
                    f"❌ Error: {str(e)[:50]}"
                )
    
    raise PreventUpdate


@callback(
    Output('dashboard-container', 'children'),
    Input('dashboard-selector', 'value'),
    Input('session-store', 'data'),
    Input('mode-selector', 'value'),
    Input('driver-selector', 'value'),
    Input('circuit-selector', 'value'),
    Input('session-selector', 'value'),
    State('telemetry-comparison-store', 'data'),  # Telemetry comparison driver
    State('circuit-selector', 'options'),
    prevent_initial_call=False
)
def update_dashboards(
    selected_dashboards,
    session_data,
    mode_value,
    focused_driver,
    selected_circuit,
    selected_session,
    telemetry_comparison_data,
    circuit_options,
):
    """Update visible dashboards based on selection."""
    global current_session_obj
    global _cached_weather_component, _cached_weather_lap, _cached_weather_session_key
    global _cached_telemetry_component, _cached_telemetry_key
    global _cached_race_control_component, _cached_race_control_sig
    global _track_map_trace_offset, _track_map_driver_order

    driver_code = None
    if focused_driver and focused_driver != 'none':
        parts = focused_driver.split('_')
        driver_code = parts[0] if parts else focused_driver
    
    if not selected_dashboards:
        return html.Div([
            html.H4("No dashboards selected", className="text-center mt-5"),
            html.P(
                "Select one or more dashboards from the sidebar",
                className="text-center text-muted"
            )
        ])
    
    # Check if session is loaded (for dashboards that require it)
    session_loaded = session_data and session_data.get('loaded', False)
    mode_is_simulation = mode_value == 'sim'
    track_map_status: Dict[str, Any] = {
        'ready': False,
        'error': None,
        'params': None,
    }
    if session_data and isinstance(session_data, dict):
        maybe_track_map = session_data.get('track_map')
        if isinstance(maybe_track_map, dict):
            track_map_status = maybe_track_map

    track_map_ready = bool(track_map_status.get('ready'))
    
    # Create dashboards based on selection
    dashboards = []
    
    for dashboard_id in selected_dashboards:
        if dashboard_id == "ai":
            # Placeholder; real rendering happens in dedicated callback to avoid re-mounts
            dashboards.append(html.Div(id='ai-dashboard-slot'))
        elif dashboard_id == "race_overview":
            # Race Overview Dashboard (Leaderboard + Circuit Map)
            if not session_loaded:
                dash_logger.debug("Race overview: session not yet loaded")
                dashboards.append(
                    dbc.Card(
                        [
                            dbc.CardHeader(
                                html.H5("🏁 Race Overview", className="mb-0", style={"fontSize": "1.2rem"}),
                                className="py-1",
                                style={"backgroundColor": "#1e1e1e"}
                            ),
                            dbc.CardBody(
                                [
                                    dcc.Loading(
                                        html.Div([
                                            html.P("Loading session data...", className="text-center p-5 text-muted"),
                                            html.P("Please wait while we load the race information.", 
                                                   className="text-center text-muted small")
                                        ]),
                                        type="circle",
                                        color="#e10600"
                                    )
                                ],
                                className="p-2",
                                style={
                                    "backgroundColor": "#121212",
                                    "display": "flex",
                                    "flexDirection": "column",
                                    "flex": "1 1 auto",
                                    "minHeight": "0"
                                }
                            )
                        ],
                        className="border border-secondary mb-3 h-100",
                        style={
                            "backgroundColor": "#121212",
                            "display": "flex",
                            "flexDirection": "column",
                            "height": "100%",
                            "minHeight": "0"
                        }
                    )
                )
                continue
                
            try:
                if current_session_obj is None:
                    logger.warning("Race overview requested but no session loaded")
                    dashboards.append(
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    html.H5("🏁 Race Overview", className="mb-0", style={"fontSize": "1.2rem"}),
                                    className="py-1",
                                    style={"backgroundColor": "#1e1e1e"}
                                ),
                                dbc.CardBody(
                                    [
                                        html.P(
                                            "No session loaded. Please select a race session from the sidebar.", 
                                            className="text-muted text-center p-5")
                                    ],
                                    className="p-2",
                                    style={
                                        "backgroundColor": "#121212",
                                        "display": "flex",
                                        "flexDirection": "column",
                                        "flex": "1 1 auto",
                                        "minHeight": "0"
                                    }
                                )
                            ],
                            className="border border-secondary mb-3 h-100",
                            style={
                                "backgroundColor": "#121212",
                                "display": "flex",
                                "flexDirection": "column",
                                "height": "100%",
                                "minHeight": "0"
                            }
                        )
                    )
                else:
                    overview_logger.info("Rendering race overview dashboard...")
                    openf1_provider.reset_api_call_counts()
                    overview_logger.debug("Race overview API counters reset")
                    # Get session_key from loaded session
                    session_key = None
                    simulation_time = None
                    
                    if current_session_obj and hasattr(current_session_obj, 'session_key'):
                        session_key = current_session_obj.session_key

                    if simulation_controller is not None:
                        try:
                            simulation_time = simulation_controller.get_elapsed_seconds()
                            sim_logger.debug(
                                "Race overview using controller time: %.1fs",
                                simulation_time
                            )
                        except Exception as exc:
                            logger.warning("Could not get simulation time: %s", exc)
                            simulation_time = 0.0
                    else:
                        simulation_time = 0.0
                    
                    # Get session start time from controller
                    session_start_time = None
                    if simulation_controller is not None:
                        session_start_time = pd.Timestamp(simulation_controller.start_time)
                    
                    # Get current lap from simulation controller
                    # This is the GLOBAL lap (OpenF1 format) from the leader
                    overview_current_lap = None
                    if simulation_controller is not None:
                        try:
                            overview_current_lap = simulation_controller.get_current_lap()
                            sim_logger.debug(
                                f"Passing current_lap to overview: {overview_current_lap}"
                            )
                        except Exception as e:
                            logger.warning(f"Could not get lap for overview: {e}")
                    
                    formation_offset_seconds = None
                    if isinstance(track_map_status, dict):
                        formation_offset_value = track_map_status.get('formation_offset_seconds')
                        if isinstance(formation_offset_value, (int, float)):
                            formation_offset_seconds = float(formation_offset_value)
                    overview_logger.debug(
                        "Race overview (initial) formation offset: %s",
                        formation_offset_seconds,
                    )

                    overview_content = race_overview_dashboard.render(
                        session_key=session_key,
                        simulation_time=simulation_time,
                        session_start_time=session_start_time,
                        formation_offset_seconds=formation_offset_seconds,
                        current_lap=overview_current_lap,
                        focused_driver_code=driver_code
                    )
                    context_label = f"Race overview render (session {session_key})"
                    openf1_provider.log_api_call_summary(
                        context_label,
                        reset=True,
                        level=logging.INFO,
                    )
                    
                    # Build lap info for header
                    total_laps = session_data.get('total_laps', 57) if session_data else 57
                    display_lap = overview_current_lap if overview_current_lap and overview_current_lap > 0 else 1
                    lap_info_text = (
                        f"Lap 1 (untimed)/{total_laps}" if display_lap == 1
                        else f"Lap {display_lap}/{total_laps}"
                    )
                    
                    dashboards.append(
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    dbc.Row([
                                        dbc.Col(
                                            html.H5("🏁 Race Overview", className="mb-0", style={"fontSize": "1.2rem"}),
                                            width="auto"
                                        ),
                                        dbc.Col(
                                            html.Span(
                                                lap_info_text,
                                                id="race-overview-lap-badge",
                                                className="badge bg-danger ms-2",
                                                style={"fontSize": "0.85rem", "fontWeight": "normal"}
                                            ),
                                            width="auto",
                                            className="ms-auto"
                                        ),
                                    ], className="align-items-center g-0"),
                                    className="py-1",
                                    style={"backgroundColor": "#1e1e1e"}
                                ),
                                dbc.CardBody(
                                    [overview_content],
                                    className="p-2",
                                    id="race-overview-body",
                                    style={
                                        "backgroundColor": "#121212",
                                        "display": "flex",
                                        "flexDirection": "column",
                                        "flex": "1 1 auto",
                                        "minHeight": "0",
                                        "overflow": "hidden"
                                    }
                                )
                            ],
                            className="border border-secondary mb-3 h-100",
                            style={
                                "backgroundColor": "#121212",
                                "display": "flex",
                                "flexDirection": "column",
                                "height": "100%",
                                "minHeight": "0"
                            }
                        )
                    )
                    overview_logger.info("Race overview dashboard rendered successfully")
                    
            except Exception as e:
                logger.error(f"Error creating race overview dashboard: {e}", exc_info=True)
                dashboards.append(
                    dbc.Card(
                        [
                            dbc.CardHeader(
                                html.H5("🏁 Race Overview", className="mb-0", style={"fontSize": "1.2rem"}),
                                className="py-1",
                                style={"backgroundColor": "#1e1e1e"}
                            ),
                            dbc.CardBody(
                                [html.P(f"Error loading race overview: {str(e)}", className="text-danger")],
                                className="p-2",
                                style={
                                    "backgroundColor": "#121212",
                                    "display": "flex",
                                    "flexDirection": "column",
                                    "flex": "1 1 auto",
                                    "minHeight": "0"
                                }
                            )
                        ],
                        className="border border-secondary mb-3 h-100",
                        style={
                            "backgroundColor": "#121212",
                            "display": "flex",
                            "flexDirection": "column",
                            "height": "100%",
                            "minHeight": "0"
                        }
                    )
                )
        
        elif dashboard_id == "race_control":
            # Race Control Dashboard (Flags, SC/VSC, Penalties)
            if not session_loaded:
                dash_logger.debug("Race control: session not yet loaded")
                dashboards.append(
                    html.Div(
                        dbc.Card([
                            dbc.CardHeader(html.H5(" Race Control", className="mb-0", style={"fontSize": "1.2rem"}), className="py-1"),
                            dbc.CardBody([
                                dcc.Loading(
                                    html.Div([
                                        html.P("Loading session data...", className="text-center p-5 text-muted"),
                                        html.P("Please wait while we load the race control information.",
                                               className="text-center text-muted small")
                                    ]),
                                    type="circle",
                                    color="#e10600"
                                )
                            ], className="p-2", style={
                                "backgroundColor": "#121212",
                                "display": "flex",
                                "flexDirection": "column",
                                "flex": "1 1 auto",
                                "minHeight": "0"
                            })
                        ], className="border border-secondary mb-3 h-100", style={
                            "backgroundColor": "#121212",
                            "display": "flex",
                            "flexDirection": "column",
                            "height": "100%",
                            "minHeight": "0"
                        }),
                        id="race-control-wrapper",
                        style={"height": "100%"}
                    )
                )
                continue

            try:
                if current_session_obj is None:
                    logger.warning("Race control requested but no session loaded")
                    dashboards.append(
                        html.Div(
                            dbc.Card([
                                dbc.CardHeader(html.H5(" Race Control", className="mb-0", style={"fontSize": "1.2rem"}), className="py-1"),
                                dbc.CardBody([
                                    html.P("No session loaded. Please select a race session from the sidebar.",
                                           className="text-muted text-center p-5")
                                ], className="p-2", style={
                                    "backgroundColor": "#121212",
                                    "display": "flex",
                                    "flexDirection": "column",
                                    "flex": "1 1 auto",
                                    "minHeight": "0"
                                })
                            ], className="border border-secondary mb-3 h-100", style={
                                "backgroundColor": "#121212",
                                "display": "flex",
                                "flexDirection": "column",
                                "height": "100%",
                                "minHeight": "0"
                            }),
                            id="race-control-wrapper",
                            style={"height": "100%"}
                        )
                    )
                else:
                    control_logger.info("Rendering race control dashboard (static mount)...")
                    race_control_component = _render_race_control(
                        focused_driver=focused_driver,
                        use_store_time=False,
                    )
                    dashboards.append(html.Div(
                        race_control_component,
                        id="race-control-wrapper",
                        style={"height": "100%"}
                    ))
                    control_logger.info("Race control dashboard mounted")

            except Exception as e:
                logger.error(f"Error creating race control dashboard: {e}", exc_info=True)
                dashboards.append(
                    html.Div(
                        dbc.Card([
                            dbc.CardHeader(html.H5(" Race Control", className="mb-0", style={"fontSize": "1.2rem"}), className="py-1"),
                            dbc.CardBody([
                                html.P(f"Error loading race control: {str(e)}", className="text-danger")
                            ], className="p-2", style={
                                "backgroundColor": "#121212",
                                "display": "flex",
                                "flexDirection": "column",
                                "flex": "1 1 auto",
                                "minHeight": "0"
                            })
                        ], className="border border-secondary mb-3 h-100", style={
                            "backgroundColor": "#121212",
                            "display": "flex",
                            "flexDirection": "column",
                            "height": "100%",
                            "minHeight": "0"
                        }),
                        id="race-control-wrapper",
                        style={"height": "100%"}
                    )
                )

        elif dashboard_id == "weather":
            # Weather Dashboard (Phase 1 MVP) - Compact 33% width
            if not session_loaded:
                dash_logger.info("Weather dashboard requested but session not yet loaded")
                dashboards.append(
                    html.Div(
                        dbc.Card([
                            dbc.CardHeader(html.H5("🌤️ Weather", className="mb-0"), className="py-1"),
                            dbc.CardBody([
                                dcc.Loading(
                                    html.Div([
                                        html.P("Loading...", className="text-center p-3 text-muted", style={"fontSize": "0.8rem"}),
                                    ]),
                                    type="circle",
                                    color="#e10600"
                                )
                            ], className="p-2")
                        ], className="mb-3 h-100"),
                        id="weather-wrapper"
                    )
                )
            else:
                dash_logger.info("Rendering weather dashboard (static mount)...")
                try:
                    weather_component = _render_weather()
                    dashboards.append(html.Div(weather_component, id="weather-wrapper"))
                except Exception as e:
                    logger.error(f"Error rendering weather dashboard: {e}", exc_info=True)
                    dashboards.append(
                        html.Div(
                            dbc.Card([
                                dbc.CardHeader(html.H5("🌤️ Weather", className="mb-0")),
                                dbc.CardBody([
                                    html.P(f"Error: {str(e)}", className="text-danger text-center")
                                ])
                            ], className="mb-3 h-100"),
                            id="weather-wrapper"
                        )
                    )

        elif dashboard_id == "track_map":
            card_id = "track-map-wrapper"
            base_style = {"minHeight": "480px", "height": "100%", "overflow": "hidden"}

            if not mode_is_simulation:
                dashboards.append(
                    html.Div(
                        dbc.Card([
                            dbc.CardHeader(
                                html.H5("🗺️ Track Map", className="mb-0", style={"fontSize": "1.2rem"}),
                                className="py-1"
                            ),
                            dbc.CardBody([
                                html.P(
                                    "Track Map is available in simulation mode only.",
                                    className="text-center text-muted mt-5"
                                )
                            ], className="p-2")
                        ], className="mb-3", style=base_style),
                        id=card_id
                    )
                )
                continue

            if not session_loaded:
                dashboards.append(
                    html.Div(
                        dbc.Card([
                            dbc.CardHeader(
                                html.H5("🗺️ Track Map", className="mb-0", style={"fontSize": "1.2rem"}),
                                className="py-1"
                            ),
                            dbc.CardBody([
                                dcc.Loading(
                                    html.Div([
                                        html.P("Preparing simulation session...", className="text-center text-muted mt-4"),
                                    ]),
                                    type="circle",
                                    color="#e10600"
                                )
                            ], className="p-2")
                        ], className="mb-3", style=base_style),
                        id=card_id
                    )
                )
                continue

            if not track_map_ready:
                error_message = track_map_status.get('error')
                message_class = "text-warning" if error_message is None else "text-danger"
                display_text = (
                    error_message
                    if error_message
                    else "Preloading FastF1 telemetry cache... this can take a minute on first load."
                )
                dashboards.append(
                    html.Div(
                        dbc.Card([
                            dbc.CardHeader(
                                html.H5("🗺️ Track Map", className="mb-0", style={"fontSize": "1.2rem"}),
                                className="py-1"
                            ),
                            dbc.CardBody([
                                html.P(display_text, className=f"text-center mt-4 {message_class}"),
                            ], className="p-2")
                        ], className="mb-3", style=base_style),
                        id=card_id
                    )
                )
                continue

            formation_offset_value = track_map_status.get('formation_offset_seconds')
            formation_offset_seconds = (
                float(formation_offset_value)
                if isinstance(formation_offset_value, (int, float))
                else 0.0
            )
            total_laps = _resolve_track_map_total_laps(session_data)
            _, focus_driver_number = _parse_driver_selector_value(focused_driver)
            global _track_map_focus_driver
            _track_map_focus_driver = focus_driver_number

            initial_elapsed = 0.0
            initial_lap = 1
            if simulation_controller is not None:
                try:
                    initial_elapsed = simulation_controller.get_elapsed_seconds()
                except Exception as exc:  # noqa: BLE001
                    dash_logger.debug("Unable to read simulation time for initial track map: %s", exc)
                    initial_elapsed = 0.0
                try:
                    initial_lap = simulation_controller.get_current_lap() or 1
                except Exception as exc:  # noqa: BLE001
                    dash_logger.debug("Unable to read lap for initial track map: %s", exc)
                    initial_lap = 1

            track_map_dashboard = get_track_map_dashboard()
            retirements = _refresh_track_map_retirements(track_map_dashboard)
            driver_entries = _build_track_map_driver_data(
                focused_driver,
                current_lap=max(initial_lap, 1),
                retirements=retirements,
                elapsed_time_seconds=initial_elapsed,
            )

            effective_initial_elapsed = initial_elapsed
            if simulation_controller is not None:
                try:
                    effective_initial_elapsed = simulation_controller.clamp_elapsed_to_lap(
                        initial_elapsed,
                        max(initial_lap, 1),
                    )
                except Exception as exc:  # noqa: BLE001
                    dash_logger.debug("Unable to clamp elapsed time for track map: %s", exc)
                    effective_initial_elapsed = initial_elapsed

            if driver_entries:
                try:
                    driver_entries = _build_track_map_driver_data(
                        focused_driver,
                        current_lap=max(initial_lap, 1),
                        retirements=retirements,
                        elapsed_time_seconds=effective_initial_elapsed,
                    )
                    base_figure = track_map_dashboard.create_figure(
                        current_lap=max(initial_lap, 1),
                        driver_data=driver_entries,
                        elapsed_time=effective_initial_elapsed,
                    )
                    offset = _extract_track_map_trace_offset(base_figure)
                    if offset is not None:
                        _track_map_trace_offset = offset
                        _track_map_driver_order = sorted(entry["driver_number"] for entry in driver_entries)
                    else:
                        _track_map_trace_offset = None
                        _track_map_driver_order = []
                except Exception as exc:  # noqa: BLE001
                    dash_logger.error("Failed to build initial track map figure: %s", exc, exc_info=True)
                    base_figure = track_map_dashboard.get_circuit_figure()
                    _track_map_trace_offset = None
                    _track_map_driver_order = []
                else:
                    if track_map_logger.isEnabledFor(logging.DEBUG):
                        track_map_logger.debug(
                            (
                                "[TrackMapInitial] drivers=%d sim_elapsed_store=%.3f sim_elapsed_ctrl=%.3f "
                                "sim_elapsed_clamped=%.3f sim_lap=%s"
                            ),
                            len(_track_map_driver_order),
                            initial_elapsed,
                            initial_elapsed,
                            effective_initial_elapsed,
                            max(initial_lap, 1),
                        )
            else:
                base_figure = track_map_dashboard.get_circuit_figure()
                _track_map_trace_offset = None
                _track_map_driver_order = []
            base_figure.update_layout(title=dict(text=""), autosize=True)
            initial_lap_label = _format_track_map_lap_label(
                current_lap=max(initial_lap, 1),
                total_laps=total_laps,
                formation_offset_seconds=formation_offset_seconds,
                elapsed_time_seconds=max(initial_elapsed, 0.0),
            )
            status_badge = dbc.Badge(
                "FastF1 cache ready",
                color="success",
                className="ms-2",
            )
            lap_badge = dbc.Badge(
                initial_lap_label,
                id="track-map-lap-label",
                color="light",
                className="ms-3 text-dark border border-secondary",
                style={"fontSize": "0.85rem"},
            )
            dashboards.append(
                html.Div(
                    dbc.Card([
                        dbc.CardHeader(
                            dbc.Row([
                                dbc.Col(
                                    html.H5(
                                        "🗺️ Track Map",
                                        className="mb-0",
                                        style={"fontSize": "1.2rem"}
                                    ),
                                    width="auto"
                                ),
                                dbc.Col(lap_badge, width="auto"),
                                dbc.Col(status_badge, width="auto", className="ms-auto")
                            ], className="align-items-center g-0"),
                            className="py-1"
                        ),
                        dbc.CardBody(
                            [
                                html.Div(
                                    [
                                        html.Button(
                                            "↺",
                                            id='track-map-reset-view-btn',
                                            className='btn btn-sm btn-dark text-white',
                                            title='Reset view',
                                            style={
                                                'position': 'absolute',
                                                'top': '8px',
                                                'left': '8px',
                                                'zIndex': 20,
                                                'padding': '2px 8px',
                                                'transform': 'scale(0.4)',
                                                'transformOrigin': 'top left',
                                            },
                                        ),
                                        dcc.Loading(
                                            dcc.Graph(
                                                id='track-map-graph',
                                                figure=base_figure,
                                                config={'displayModeBar': False, 'responsive': True},
                                                responsive=True,
                                                style={'height': '100%', 'width': '100%'}
                                            ),
                                            type="circle",
                                            color="#e10600",
                                            style={'flex': '1 1 auto'},
                                            delay_show=750,
                                            show_initially=False
                                        ),
                                    ],
                                    style={'flex': '1 1 auto', 'minHeight': '360px', 'position': 'relative'}
                                ),
                            ],
                            style={
                                'height': '100%',
                                'padding': '6px',
                                'display': 'flex',
                                'flexDirection': 'column',
                            }
                        )
                    ], className="mb-3 h-100", style=base_style),
                    id=card_id
                )
            )
        elif dashboard_id == "telemetry":
            # Telemetry Dashboard - Speed, Throttle, Brake, Gear for focus driver
            try:
                telem_logger.info("Rendering telemetry dashboard (static mount)...")

                telemetry_component = _render_telemetry(
                    focused_driver=focused_driver,
                    telemetry_comparison_data=telemetry_comparison_data,
                    session_data=session_data,
                    use_store_time=False,
                )
                dashboards.append(html.Div(telemetry_component, id="telemetry-wrapper"))
                telem_logger.info("Telemetry dashboard mounted")

            except Exception as e:
                logger.error(f"Error creating telemetry dashboard: {e}", exc_info=True)
                dashboards.append(
                    html.Div(
                        dbc.Card([
                            dbc.CardHeader(
                                html.H5(
                                    "📊 Telemetry",
                                    className="mb-0",
                                    style={"fontSize": "1.2rem"}
                                ),
                                className="py-1"
                            ),
                            dbc.CardBody([
                                html.P(
                                    f"Error loading telemetry: {str(e)}",
                                    className="text-danger"
                                )
                            ], className="p-2")
                        ], className="mb-3", style={"height": "620px"}),
                        id="telemetry-wrapper"
                    )
                )
        
        else:
            # Generic placeholder for other dashboards
            dashboards.append(
                dbc.Card([
                    dbc.CardHeader(html.H5(f"📊 {dashboard_id.title()}")),
                    dbc.CardBody([
                        html.P(f"Dashboard: {dashboard_id}", className="text-muted"),
                        html.Div(
                            f"{dashboard_id.title()} dashboard content coming soon",
                            className="text-center p-5 bg-dark rounded"
                        )
                    ])
                ], className="mb-3")
            )
    
    # Layout dashboards:
    # Grid layout: 2 rows x 3 columns (33% width each, 50vh height each row)
    # No vertical scroll - all dashboards fit in viewport
    if len(dashboards) == 0:
        return html.Div("No dashboards selected", className="text-center text-muted p-5")
    
    # Wrap all dashboards in responsive columns
    # CSS handles the layout switching between landscape (3 cols) and portrait (2 cols)
    wrapped_dashboards = []
    for idx, dash in enumerate(dashboards):
        # Border style for visual separation
        border_style = {"borderRight": "1px solid #333"}
        
        if isinstance(dash, dbc.Col):
            # Already wrapped (e.g., weather) - recreate with responsive class
            wrapped_dashboards.append(
                html.Div(
                    dash.children,
                    className="dashboard-grid-col",
                    style={**border_style}
                )
            )
        else:
            # Wrap with responsive class
            wrapped_dashboards.append(
                html.Div(
                    dash,
                    className="dashboard-grid-col",
                    style={**border_style}
                )
            )
    
    # Return flex container - CSS handles responsive layout
    # Landscape: wraps at 3 items per row (33% each)
    # Portrait: wraps at 2 items per row (50% each)
    return html.Div(
        wrapped_dashboards,
        className="dashboard-grid-container"
    )


# Callback: Render AI dashboard independently to avoid refresh flicker
@callback(
    Output('ai-dashboard-slot', 'children'),
    Input('chat-messages-store', 'data'),
    Input('driver-selector', 'value'),
    Input('circuit-selector', 'value'),
    Input('session-selector', 'value'),
    State('session-store', 'data'),
    State('circuit-selector', 'options'),
    prevent_initial_call=False
)
def render_ai_dashboard(
    chat_messages: list[dict[str, Any]] | dict[str, Any] | None,
    focused_driver: str | None,
    selected_circuit: str | None,
    selected_session: str | None,
    session_data: dict[str, Any] | None,
    circuit_options: list[dict[str, Any]] | None,
):
    """Render AI assistant without being driven by simulation ticks."""
    global _cached_ai_component, _cached_ai_sig
    # Circuit name from options label
    circuit_name = 'Unknown Circuit'
    if selected_circuit and circuit_options:
        for opt in circuit_options:
            if opt.get('value') == selected_circuit:
                label = opt.get('label', '')
                circuit_name = label.split(' - ', 1)[1] if ' - ' in label else label
                break

    session_type = selected_session if selected_session else 'Race'

    driver_code = None
    if focused_driver and focused_driver != 'none':
        parts = focused_driver.split('_')
        driver_code = parts[0] if parts else focused_driver

    # Prefer sanitized incoming store; fall back to last known messages to avoid empties
    effective_chat = _ensure_json_safe_messages(chat_messages)
    if not effective_chat and _last_chat_messages:
        try:
            effective_chat = json.loads(json.dumps(_last_chat_messages))
        except Exception:
            effective_chat = _ensure_json_safe_messages(_last_chat_messages)

    session_loaded = bool(session_data and session_data.get('loaded'))
    ai_signature_payload = {
        "messages": effective_chat,
        "driver_code": driver_code,
        "circuit_name": circuit_name,
        "session_type": session_type,
        "session_loaded": session_loaded,
    }
    ai_signature = json.dumps(ai_signature_payload, sort_keys=True, default=str)

    # If layout was remounted (e.g., other dashboards refresh) re-serve cached AI
    if _cached_ai_component is not None and _cached_ai_sig == ai_signature:
        return _cached_ai_component

    # Only allow proactive AI if session is loaded; otherwise show placeholder
    if not session_loaded:
        component = AIAssistantDashboard.create_layout(
            focused_driver=driver_code,
            race_name=circuit_name,
            session_type=session_type,
            messages=[]
        )
        _cached_ai_component = component
        _cached_ai_sig = ai_signature
        return component

    component = AIAssistantDashboard.create_layout(
        focused_driver=driver_code,
        race_name=circuit_name,
        session_type=session_type,
        messages=effective_chat
    )
    _cached_ai_component = component
    _cached_ai_sig = ai_signature
    return component


# Callback: Refresh race overview body using simulation time without re-rendering other dashboards
@callback(
    Output('race-overview-body', 'children'),
    Input('simulation-time-store', 'data'),
    Input('driver-selector', 'value'),
    State('dashboard-selector', 'value'),
    State('session-store', 'data'),
    prevent_initial_call=True
)
def refresh_race_overview_body(
    simulation_time_data: dict[str, Any] | None,
    focused_driver: str | None,
    selected_dashboards: list[str] | None,
    session_data: dict[str, Any] | None,
):
    """Refresh the race overview content frequently without rebuilding all dashboards."""
    global current_session_obj, simulation_controller

    if not selected_dashboards or 'race_overview' not in selected_dashboards:
        raise PreventUpdate
    if not session_data or not session_data.get('loaded'):
        raise PreventUpdate
    if current_session_obj is None:
        raise PreventUpdate

    try:
        session_key = getattr(current_session_obj, 'session_key', None)

        driver_code = None
        if focused_driver and focused_driver != 'none':
            parts = focused_driver.split('_')
            driver_code = parts[0] if parts else focused_driver

        simulation_time = 0.0
        if simulation_time_data and 'time' in simulation_time_data:
            simulation_time = simulation_time_data.get('time', 0.0)
        elif simulation_controller is not None:
            simulation_time = simulation_controller.get_elapsed_seconds()

        session_start_time = None
        if simulation_controller is not None:
            session_start_time = pd.Timestamp(simulation_controller.start_time)

        overview_current_lap = None
        if simulation_controller is not None:
            try:
                overview_current_lap = simulation_controller.get_current_lap()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not read lap for overview refresh: %s", exc)

        formation_offset_seconds = None
        if isinstance(session_data, dict):
            track_map_status = session_data.get('track_map', {})
            if isinstance(track_map_status, dict):
                formation_offset_value = track_map_status.get('formation_offset_seconds')
                if isinstance(formation_offset_value, (int, float)):
                    formation_offset_seconds = float(formation_offset_value)
        overview_logger.debug(
            "Race overview formation offset: %s", formation_offset_seconds
        )

        overview_content = race_overview_dashboard.render(
            session_key=session_key,
            simulation_time=simulation_time,
            session_start_time=session_start_time,
            formation_offset_seconds=formation_offset_seconds,
            current_lap=overview_current_lap,
            focused_driver_code=driver_code,
            retirements=_track_map_retirements,
        )
        return overview_content
    except Exception as exc:  # noqa: BLE001
        logger.error("Error refreshing race overview body: %s", exc, exc_info=True)
        raise PreventUpdate


@callback(
    Output('track-map-trajectory-store', 'data'),
    Input('simulation-time-store', 'data'),
    Input('session-store', 'data'),
    Input('driver-selector', 'value'),
    State('dashboard-selector', 'value'),
    State('track-map-trajectory-store', 'data'),
    prevent_initial_call=True
)
def cache_track_map_trajectories(
    simulation_time_data: Optional[Dict[str, Any]],
    session_data: Optional[Dict[str, Any]],
    focused_driver_value: Optional[str],
    selected_dashboards: Optional[List[str]],
    existing_store: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Populate the track map trajectory store with per-lap XY telemetry."""
    default_store = _default_track_map_trajectory_store()

    if not session_data or not session_data.get('loaded'):
        if isinstance(existing_store, dict) and existing_store == default_store:
            raise PreventUpdate
        return default_store

    track_map_status = session_data.get('track_map', {}) if isinstance(session_data, dict) else {}
    if not track_map_status.get('ready'):
        if isinstance(existing_store, dict) and existing_store == default_store:
            raise PreventUpdate
        return default_store

    if not selected_dashboards or 'track_map' not in selected_dashboards:
        raise PreventUpdate

    elapsed_time = 0.0
    if isinstance(simulation_time_data, dict):
        try:
            elapsed_time = float(simulation_time_data.get('time', 0.0))
        except (TypeError, ValueError):
            elapsed_time = 0.0

    if simulation_controller is not None:
        try:
            elapsed_time = simulation_controller.get_elapsed_seconds()
        except Exception as exc:  # noqa: BLE001
            dash_logger.debug("Unable to read simulation time for trajectory cache: %s", exc)

    current_lap = 1
    if simulation_controller is not None:
        try:
            current_lap = simulation_controller.get_current_lap() or 1
        except Exception as exc:  # noqa: BLE001
            dash_logger.debug("Unable to read lap for trajectory cache: %s", exc)

    if current_lap < 1 and isinstance(existing_store, dict):
        laps_section = existing_store.get('laps')
        if isinstance(laps_section, dict) and laps_section:
            try:
                current_lap = max(int(key) for key in laps_section.keys())
            except ValueError:
                current_lap = 1

    current_lap = max(current_lap, 1)
    lap_key = str(current_lap)

    track_dashboard = get_track_map_dashboard()
    retirements = _refresh_track_map_retirements(track_dashboard)
    driver_entries = _build_track_map_driver_data(
        focused_driver_value,
        current_lap=current_lap,
        retirements=retirements,
        elapsed_time_seconds=elapsed_time,
    )
    if not driver_entries:
        raise PreventUpdate

    driver_numbers = sorted(entry['driver_number'] for entry in driver_entries)
    provider = track_dashboard.provider
    if provider is None:
        raise PreventUpdate

    store_payload: Dict[str, Any] = {
        'time_offset': provider.get_session_time_offset(),
        'time_bounds': [float(bound) for bound in provider.get_time_bounds()],
        'laps': {},
    }

    if isinstance(existing_store, dict):
        existing_laps = existing_store.get('laps')
        if isinstance(existing_laps, dict):
            store_payload['laps'] = dict(existing_laps)

    if lap_key in store_payload['laps']:
        previous_offset = 0.0
        previous_bounds = [0.0, 0.0]
        if isinstance(existing_store, dict):
            previous_offset = float(existing_store.get('time_offset', 0.0))
            maybe_bounds = existing_store.get('time_bounds')
            if isinstance(maybe_bounds, list) and len(maybe_bounds) == 2:
                previous_bounds = [float(maybe_bounds[0]), float(maybe_bounds[1])]

        if (
            math.isclose(store_payload['time_offset'], previous_offset, rel_tol=1e-6, abs_tol=1e-6)
            and store_payload['time_bounds'] == previous_bounds
        ):
            raise PreventUpdate

    trajectories = provider.get_lap_trajectories(current_lap, driver_numbers=driver_numbers)
    if not trajectories:
        track_map_logger.debug("No lap trajectories available for lap %s", lap_key)
        raise PreventUpdate

    store_payload['laps'][lap_key] = trajectories

    try:
        lap_keys_sorted = sorted(store_payload['laps'].keys(), key=lambda key: int(key))
    except ValueError:
        lap_keys_sorted = list(store_payload['laps'].keys())

    while len(lap_keys_sorted) > TRACK_MAP_TRAJECTORY_CACHE_LIMIT:
        oldest_key = lap_keys_sorted.pop(0)
        store_payload['laps'].pop(oldest_key, None)

    if isinstance(existing_store, dict) and store_payload == existing_store:
        raise PreventUpdate

    track_map_logger.debug(
        "[TrajectoryCache] Stored lap %s with %d drivers",
        lap_key,
        len(trajectories),
    )
    return store_payload


@callback(
    Output('track-map-graph', 'figure'),
    Output('track-map-lap-label', 'children'),
    Input('simulation-time-store', 'data'),
    Input('session-store', 'data'),
    Input('driver-selector', 'value'),
    Input('track-map-trajectory-store', 'data'),
    State('dashboard-selector', 'value'),
    State('mode-selector', 'value'),
    State('track-map-graph', 'figure'),
    prevent_initial_call=True
)
def refresh_track_map_figure(
    simulation_time_data: Optional[Dict[str, Any]],
    session_data: Optional[Dict[str, Any]],
    focused_driver_value: Optional[str],
    trajectory_store: Optional[Dict[str, Any]],
    selected_dashboards: Optional[List[str]],
    mode_value: Optional[str],
    _existing_figure: Optional[Dict[str, Any]],
):
    """Refresh Track Map markers using cached FastF1 positions and simulation time."""
    if not selected_dashboards or 'track_map' not in selected_dashboards:
        raise PreventUpdate
    if mode_value != 'sim':
        raise PreventUpdate
    if not session_data or not session_data.get('loaded'):
        raise PreventUpdate

    track_map_status = session_data.get('track_map', {})
    if not track_map_status.get('ready'):
        raise PreventUpdate

    formation_offset_value = track_map_status.get('formation_offset_seconds')
    formation_offset_seconds = (
        float(formation_offset_value)
        if isinstance(formation_offset_value, (int, float))
        else 0.0
    )
    total_laps = _resolve_track_map_total_laps(session_data)
    _, focus_driver_number = _parse_driver_selector_value(focused_driver_value)

    track_dashboard = get_track_map_dashboard()

    elapsed_time = 0.0
    store_elapsed_time = 0.0
    if simulation_time_data and isinstance(simulation_time_data, dict):
        try:
            elapsed_time = float(simulation_time_data.get('time', 0.0))
            store_elapsed_time = elapsed_time
        except (TypeError, ValueError):
            elapsed_time = 0.0
            store_elapsed_time = 0.0

    current_lap = 1
    if simulation_controller is not None:
        try:
            elapsed_time = simulation_controller.get_elapsed_seconds()
        except Exception as exc:  # noqa: BLE001
            dash_logger.debug("Falling back to store time for track map: %s", exc)
        try:
            current_lap = simulation_controller.get_current_lap() or 1
        except Exception as exc:  # noqa: BLE001
            dash_logger.debug("Unable to determine current lap for track map: %s", exc)

    current_lap = max(current_lap, 1)
    effective_elapsed_time = max(elapsed_time, 0.0)
    retirements = _refresh_track_map_retirements(track_dashboard)
    driver_data = _build_track_map_driver_data(
        focused_driver_value,
        current_lap=current_lap,
        retirements=retirements,
        elapsed_time_seconds=effective_elapsed_time,
    )
    driver_style_lookup = {
        entry["driver_number"]: track_dashboard.resolve_marker_style(entry)
        for entry in driver_data
    }
    driver_metadata_lookup = {
        entry["driver_number"]: entry for entry in driver_data
    }
    lap_label_text = _format_track_map_lap_label(
        current_lap=current_lap,
        total_laps=total_laps,
        formation_offset_seconds=formation_offset_seconds,
        elapsed_time_seconds=store_elapsed_time,
    )

    if not driver_data:
        dash_logger.debug("Track map driver data unavailable; returning base circuit figure")
        empty_figure = track_dashboard.get_circuit_figure()
        empty_figure.update_layout(title=dict(text=""))
        return empty_figure, lap_label_text

    driver_numbers = sorted(entry["driver_number"] for entry in driver_data)

    global _track_map_trace_offset, _track_map_driver_order, _track_map_focus_driver

    try:
        requires_new_base = False
        if not _track_map_driver_order:
            requires_new_base = True
        elif _track_map_driver_order != driver_numbers:
            requires_new_base = True

        focus_changed = _track_map_focus_driver != focus_driver_number
        if focus_changed:
            requires_new_base = True
        _track_map_focus_driver = focus_driver_number

        if requires_new_base or _track_map_trace_offset is None:
            dash_logger.debug(
                "Track map full refresh: offset=%s order_changed=%s drivers=%d",  # noqa: G004
                _track_map_trace_offset,
                _track_map_driver_order != driver_numbers,
                len(driver_numbers),
            )
            full_figure = track_dashboard.create_figure(
                current_lap=current_lap,
                driver_data=driver_data,
                elapsed_time=effective_elapsed_time,
            )
            offset = _extract_track_map_trace_offset(full_figure)
            if offset is None:
                dash_logger.warning("Track map figure missing driver traces; returning full figure")
                _track_map_trace_offset = None
                _track_map_driver_order = []
                full_figure.update_layout(title=dict(text=""))
                return full_figure, lap_label_text

            _track_map_trace_offset = offset
            _track_map_driver_order = list(driver_numbers)
            full_figure.update_layout(title=dict(text=""))
            return full_figure, lap_label_text

        provider = track_dashboard.provider
        session_time = effective_elapsed_time
        if provider is not None:
            session_time = provider.clamp_session_time(effective_elapsed_time)

        cache_driver_order = _track_map_driver_order or driver_numbers
        laps_section: Optional[Dict[str, Any]] = None
        laps_available = False
        if isinstance(trajectory_store, dict):
            candidate_section = trajectory_store.get('laps')
            if isinstance(candidate_section, dict) and candidate_section:
                laps_section = candidate_section
                laps_available = True

        positions = _interpolate_cached_track_positions(
            laps_section,
            current_lap,
            cache_driver_order,
            session_time,
        )

        used_cache = bool(positions)

        if not positions and provider is not None:
            positions = provider.get_all_driver_positions(
                lap_number=None,
                driver_numbers=cache_driver_order,
                elapsed_time=effective_elapsed_time,
            )

        if positions and not used_cache and provider is not None and not laps_available:
            session_time = provider.clamp_session_time(effective_elapsed_time)

        _update_track_map_lap_cache(positions)

        if track_map_logger.isEnabledFor(logging.DEBUG):
            debug_driver: Optional[int] = None
            if _track_map_driver_order:
                debug_driver = _track_map_driver_order[0]
            elif driver_numbers:
                debug_driver = driver_numbers[0]

            if debug_driver is not None:
                cache_entry = positions.get(debug_driver)
                lap_value: str | int = 'n/a'
                prev_time_value = float('nan')
                next_time_value = float('nan')
                query_time_value = float('nan')
                sample_time_value = float('nan')
                source_text = 'cache' if used_cache else 'provider'

                if isinstance(cache_entry, dict):
                    cache_lap_raw = cache_entry.get('lap_number')
                    if isinstance(cache_lap_raw, (int, float)):
                        lap_value = int(cache_lap_raw)

                    previous_sample = cache_entry.get('previous_sample')
                    if isinstance(previous_sample, dict):
                        prev_time_raw = previous_sample.get('time')
                        if isinstance(prev_time_raw, (int, float)):
                            prev_time_value = float(prev_time_raw)

                    next_sample = cache_entry.get('next_sample')
                    if isinstance(next_sample, dict):
                        next_time_raw = next_sample.get('time')
                        if isinstance(next_time_raw, (int, float)):
                            next_time_value = float(next_time_raw)

                    query_time_raw = cache_entry.get('query_time')
                    if isinstance(query_time_raw, (int, float)):
                        query_time_value = float(query_time_raw)

                    sample_time_raw = cache_entry.get('time')
                    if isinstance(sample_time_raw, (int, float)):
                        sample_time_value = float(sample_time_raw)

                track_map_logger.debug(
                    (
                        "[TrackMap] driver=%s source=%s sim_elapsed_store=%.3f sim_elapsed_ctrl=%.3f "
                        "sim_elapsed_clamped=%.3f sim_lap=%s cache_lap=%s prev_time=%.3f next_time=%.3f "
                        "query_time=%.3f sample_time=%.3f"
                    ),
                    debug_driver,
                    source_text,
                    store_elapsed_time,
                    elapsed_time,
                    effective_elapsed_time,
                    current_lap,
                    lap_value,
                    prev_time_value,
                    next_time_value,
                    query_time_value,
                    sample_time_value,
                )
    except Exception as exc:  # noqa: BLE001
        dash_logger.error("Error updating track map positions: %s", exc, exc_info=True)
        fallback_figure = track_dashboard.get_circuit_figure()
        fallback_figure.update_layout(title=dict(text=""))
        return fallback_figure, lap_label_text

    patch = Patch()

    has_retired_drivers = any(entry.get('retired') for entry in driver_metadata_lookup.values())
    if not positions and not has_retired_drivers:
        patch['layout']['annotations'] = [{
            'text': "No position data available",
            'xref': 'paper',
            'yref': 'paper',
            'x': 0.5,
            'y': 0.5,
            'showarrow': False,
            'font': {'size': 16, 'color': 'orange'},
        }]
    else:
        patch['layout']['annotations'] = []

    trace_offset = _track_map_trace_offset or 0
    for idx, driver_number in enumerate(_track_map_driver_order):
        entry = driver_metadata_lookup.get(driver_number, {})
        position = positions.get(driver_number)
        trace_idx = trace_offset + idx
        is_retired = bool(entry.get('retired'))
        if position is None and not is_retired:
            continue

        position_payload = position.copy() if isinstance(position, dict) else {}
        team_name = entry.get('team_name', 'Unknown')

        lap_hint = entry.get('lap_fallback') if isinstance(entry.get('lap_fallback'), int) else None
        if not isinstance(lap_hint, int) or lap_hint < 1:
            lap_hint = _track_map_driver_laps.get(driver_number)
        if not isinstance(lap_hint, int) or lap_hint < 1:
            lap_hint = current_lap

        if is_retired:
            order_index = int(entry.get('retired_order') or 0)
            anchor_x, anchor_y = track_dashboard.get_retirement_marker_position(order_index)
            retired_lap = entry.get('retired_lap')
            if isinstance(retired_lap, int) and retired_lap >= 1:
                lap_hint = retired_lap
            position_payload.update({
                'x': anchor_x,
                'y': anchor_y,
                'time': position_payload.get('time', effective_elapsed_time),
                'query_time': position_payload.get('query_time', effective_elapsed_time),
                'previous_sample': position_payload.get('previous_sample') or {},
                'next_sample': position_payload.get('next_sample') or {},
                'lap_number': lap_hint,
            })
            x_value = float(anchor_x)
            y_value = float(anchor_y)
        else:
            pos_x = position_payload.get('x')
            pos_y = position_payload.get('y')
            x_value = float(pos_x) if isinstance(pos_x, (int, float)) else 0.0
            y_value = float(pos_y) if isinstance(pos_y, (int, float)) else 0.0
            position_payload.setdefault('lap_number', lap_hint)

        patch['data'][trace_idx]['x'] = [x_value]
        patch['data'][trace_idx]['y'] = [y_value]
        patch['data'][trace_idx]['text'] = [str(driver_number)]
        customdata = track_dashboard._build_customdata(
            driver_number,
            position_payload,
            fallback_lap=lap_hint,
        )
        patch['data'][trace_idx]['customdata'] = customdata
        patch['data'][trace_idx]['hovertemplate'] = track_dashboard.build_hovertemplate(entry, team_name)

        styles = driver_style_lookup.get(driver_number)
        if styles:
            patch['data'][trace_idx]['marker'] = {
                'size': 20,
                'color': styles['fill_color'],
                'line': {
                    'color': styles['outline_color'],
                    'width': styles['outline_width'],
                },
            }
            patch['data'][trace_idx]['textfont'] = {
                'color': styles['text_color'],
                'size': 10,
                'family': 'Arial Black',
            }

    patch['layout']['title'] = {'text': ''}
    return patch, lap_label_text


@callback(
    Output('track-map-graph', 'figure', allow_duplicate=True),
    Input('track-map-reset-view-btn', 'n_clicks'),
    prevent_initial_call=True
)
def reset_track_map_zoom(n_clicks: Optional[int]):
    """Restore default track map zoom extents when the reset button is pressed."""
    if not n_clicks:
        raise PreventUpdate

    dashboard = get_track_map_dashboard()
    axis_ranges = dashboard.get_axis_ranges()
    if not axis_ranges:
        raise PreventUpdate

    x_range, y_range = axis_ranges
    patch = Patch()
    patch['layout']['xaxis']['range'] = list(x_range)
    patch['layout']['yaxis']['range'] = list(y_range)
    return patch


# NOTE: Render callback REMOVED - chat callback writes directly to container
# This avoids Dash callback conflicts with allow_duplicate=True


# Callback: Hide/Show Playback based on Mode
@callback(
    Output('playback-accordion', 'style'),
    Input('mode-selector', 'value'),
    prevent_initial_call=False
)
def toggle_playback_visibility(mode):
    """Hide playback controls when in Live mode."""
    if mode == 'live':
        return {'display': 'none'}
    return {'display': 'block'}


@callback(
    Output('telemetry-graph', 'figure', allow_duplicate=True),
    Input('telemetry-reset-view-btn', 'n_clicks'),
    prevent_initial_call=True
)
def reset_telemetry_zoom(n_clicks: Optional[int]):
    """Reset telemetry charts to their default zoom ranges."""
    if not n_clicks:
        raise PreventUpdate

    patch = Patch()
    for axis_key in ('xaxis', 'xaxis2', 'xaxis3', 'xaxis4'):
        patch['layout'][axis_key]['autorange'] = True
        patch['layout'][axis_key]['range'] = None
    patch['layout']['uirevision'] = f"telemetry-reset-{n_clicks}"
    return patch


# Callback: Save API Keys to .env file
@callback(
    Output('api-keys-save-status', 'children'),
    Input('save-api-keys-btn', 'n_clicks'),
    State('claude-api-key-input', 'value'),
    State('gemini-api-key-input', 'value'),
    State('openf1-api-key-input', 'value'),
    prevent_initial_call=True
)
def save_api_keys(n_clicks, claude_key, gemini_key, openf1_key):
    """Save API keys to .env file."""
    if not n_clicks:
        raise PreventUpdate
    
    try:
        env_path = Path(__file__).parent / 'config' / '.env'
        lines = []
        
        # Read existing .env file if it exists
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                lines = f.readlines()
        
        # Update or add keys
        claude_found = False
        gemini_found = False
        openf1_found = False
        
        for i, line in enumerate(lines):
            if line.startswith('ANTHROPIC_API_KEY='):
                lines[i] = f'ANTHROPIC_API_KEY={claude_key}\n'
                claude_found = True
            elif line.startswith('GOOGLE_API_KEY='):
                lines[i] = f'GOOGLE_API_KEY={gemini_key}\n'
                gemini_found = True
            elif line.startswith('OPENF1_API_KEY='):
                lines[i] = f'OPENF1_API_KEY={openf1_key}\n'
                openf1_found = True
        
        # Add keys if not found
        if not claude_found:
            lines.append(f'ANTHROPIC_API_KEY={claude_key}\n')
        if not gemini_found:
            lines.append(f'GOOGLE_API_KEY={gemini_key}\n')
        if not openf1_found:
            lines.append(f'OPENF1_API_KEY={openf1_key}\n')
        
        # Write back to .env
        with open(env_path, 'w') as f:
            f.writelines(lines)
        
        # Update environment variables in current session
        os.environ['ANTHROPIC_API_KEY'] = claude_key or ''
        os.environ['GOOGLE_API_KEY'] = gemini_key or ''
        os.environ['OPENF1_API_KEY'] = openf1_key or ''
        
        # Reset LLM provider to use new keys
        global _llm_provider, _llm_provider_type
        _llm_provider = None
        _llm_provider_type = None
        
        # Determine which provider will be used
        has_claude = bool(claude_key and claude_key.strip())
        has_gemini = bool(gemini_key and gemini_key.strip())
        
        if has_claude and has_gemini:
            provider_msg = "HybridRouter (Claude + Gemini)"
        elif has_claude:
            provider_msg = "Claude only"
        elif has_gemini:
            provider_msg = "Gemini only"
        else:
            return dbc.Alert(
                "⚠️ No API keys provided. At least one is required.",
                color="warning", dismissable=True, duration=5000,
                className="small py-1 mb-0 mt-2"
            )
        
        return dbc.Alert(
            f"✅ Keys saved! Using: {provider_msg}",
            color="success", dismissable=True, duration=5000,
            className="small py-1 mb-0 mt-2"
        )
    
    except Exception as e:
        logger.error(f"Error saving API keys: {e}")
        return dbc.Alert(f"❌ Error: {str(e)}", color="danger", dismissable=True, duration=3000, className="small py-1 mb-0 mt-2")


# Callback: Play/Pause simulation
@callback(
    Output('play-btn', 'children'),
    Output('play-btn', 'color'),
    Output('simulation-interval', 'disabled'),
    Output('play-btn-tooltip', 'children'),
    Input('play-btn', 'n_clicks'),
    prevent_initial_call=True
)
def toggle_play_pause(n_clicks):
    """Toggle play/pause for simulation."""
    global simulation_controller, current_session_obj, _pit_policy_context, event_detector
    
    if simulation_controller is None:
        return "▶️", "success", True, "Play simulation"

    if _pit_policy_context is None:
        try:
            rag_manager = get_rag_manager()
            _pit_policy_context = bootstrap_pit_policy_context(rag_manager)
            logger.info("Pit policy context initialized on play")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Pit policy bootstrap failed on play: %s", exc)
            _pit_policy_context = PitPolicyContext()

        session_info = {}
        if current_session_obj is not None:
            session_info = current_session_obj.session_info or {}

        tire_window_overrides = _load_tire_window_overrides(
            session_info=session_info,
            session_obj=current_session_obj,
        )
        event_detector = RaceEventDetector(
            openf1_provider,
            tire_windows=tire_window_overrides,
        )
    
    # If simulation ended, restart from the beginning before playing
    if simulation_controller.is_at_end():
        simulation_controller.restart()
    
    # Toggle play/pause state (simulation always starts from 0)
    is_playing = simulation_controller.toggle_play_pause()
    sim_logger.info(f"Play/Pause toggled: is_playing={is_playing}")
    
    if is_playing:
        return "⏸️", "warning", False, "Pause simulation"
    else:
        return "▶️", "success", True, "Play simulation"


# Callback: Restart simulation
@callback(
    Output('restart-btn', 'n_clicks'),
    Input('restart-btn', 'n_clicks'),
    prevent_initial_call=True
)
def restart_simulation(n_clicks):
    """Restart simulation from beginning."""
    global simulation_controller
    
    if simulation_controller:
        simulation_controller.restart()
    
    raise PreventUpdate  # Don't update anything, just execute the action


# Callback: Change simulation speed
@callback(
    Output('speed-slider', 'value'),
    Output('simulation-interval', 'interval'),
    Input('speed-slider', 'value'),
    prevent_initial_call=True
)
def change_speed(speed):
    """Change simulation playback speed and adjust update interval."""
    global simulation_controller
    
    # Calculate optimal interval based on speed
    # At high speeds, we need faster updates to keep UI in sync
    # Base interval: 1500ms at 1x, decreasing at higher speeds
    # Formula: interval = 1500 / sqrt(speed) to balance responsiveness and load
    import math
    base_interval = 1500
    # Minimum 500ms to avoid overwhelming the browser
    optimal_interval = max(500, int(base_interval / math.sqrt(float(speed))))
    
    if simulation_controller:
        try:
            simulation_controller.set_speed(float(speed))
            sim_logger.debug(
                f"Speed changed to {speed}x, interval={optimal_interval}ms"
            )
            return speed, optimal_interval
        except ValueError as e:
            logger.error(f"Invalid speed value: {e}")
            return 1.0, base_interval
    
    return speed, optimal_interval


# Callback: Handle lap jump buttons (forward/backward)
# These MUST update simulation-time-store to trigger dashboard refresh
@callback(
    Output('simulation-time-store', 'data', allow_duplicate=True),
    Input('back-btn', 'n_clicks'),
    Input('forward-btn', 'n_clicks'),
    State('simulation-time-store', 'data'),
    prevent_initial_call=True
)
def handle_lap_jumps(back_clicks, forward_clicks, current_time_data):
    """Handle lap jump buttons and update simulation time store."""
    global simulation_controller
    
    if simulation_controller is None:
        raise PreventUpdate
    
    triggered = ctx.triggered_id
    old_lap = simulation_controller.get_current_lap()
    
    if triggered == 'back-btn':
        simulation_controller.jump_backward(90)  # ~90 seconds per lap
        sim_logger.debug("Jumped to previous lap")
    elif triggered == 'forward-btn':
        simulation_controller.jump_forward(90)  # ~90 seconds per lap
        sim_logger.debug("Jumped to next lap")
    else:
        raise PreventUpdate
    
    # Return updated time to trigger dashboard refresh
    new_time = simulation_controller.get_elapsed_seconds()
    new_lap = simulation_controller.get_current_lap()
    
    sim_logger.debug(f"Lap jump: {old_lap} -> {new_lap} (time={new_time:.1f}s)")
    
    return {
        'time': new_time,
        'timestamp': datetime.now().timestamp()
    }


# Callback: Update simulation progress display every second
@callback(
    Output('simulation-progress', 'children'),
    Input('simulation-interval', 'n_intervals'),
    State('session-store', 'data'),
    prevent_initial_call=False
)
def update_simulation_progress(n_intervals, session_data):
    """Update the simulation progress display in real-time."""
    global simulation_controller
    
    sim_logger.debug(f"update_simulation_progress: n_intervals={n_intervals}")
    
    if simulation_controller is None:
        return "⏱️ Not started"
    
    try:
        # Update simulation time
        simulation_controller.update()
        
        # Get progress information
        remaining = simulation_controller.get_remaining_time()
        
        # Get EXACT current lap from simulation controller (no estimation)
        current_lap = simulation_controller.get_current_lap()

        # Keep raw lap count; if first lap has no timing (NaT), display as untimed
        display_lap = current_lap if current_lap and current_lap > 0 else 1
        is_untimed_lap = display_lap == 1

        # Get total_laps from session_data (calculated from actual race data)
        total_laps = session_data.get('total_laps', 57) if session_data else 57

        sim_logger.debug(f"Lap {display_lap}/{total_laps}, remaining: {remaining}")
        
        # Format remaining time
        remaining_minutes = int(remaining.total_seconds() // 60)
        remaining_seconds = int(remaining.total_seconds() % 60)
        
        # Get current speed multiplier
        speed = simulation_controller.speed_multiplier
        
        lap_label = f"Lap {int(display_lap)}" if not is_untimed_lap else "Lap 1 (untimed)"
        progress_text = (
            f"⏱️ {lap_label}/{int(total_laps)} | "
            f"⏳ {remaining_minutes}m {remaining_seconds}s left | 🚀 {speed}x"
        )
        
        return progress_text
    except Exception as e:
        logger.error(f"Error in update_simulation_progress: {e}", exc_info=True)
        return f"⏱️ Error: {str(e)}"


# Sync play button when simulation reaches the end so it shows Play
@callback(
    Output('play-btn', 'children', allow_duplicate=True),
    Output('play-btn', 'color', allow_duplicate=True),
    Output('simulation-interval', 'disabled', allow_duplicate=True),
    Output('play-btn-tooltip', 'children', allow_duplicate=True),
    Input('simulation-interval', 'n_intervals'),
    prevent_initial_call=True
)
def sync_play_button_on_finish(n_intervals):
    """Show Play when the run finishes without clearing lap/time data."""
    global simulation_controller

    if simulation_controller is None:
        raise PreventUpdate

    if not simulation_controller.is_at_end():
        raise PreventUpdate

    # Simulation already paused in controller.update(); just reflect UI state
    return "▶️", "success", True, "Play simulation"


# NOTE: Circuit map real-time updates disabled
# The circuit map shows static driver positions at race start
# Real-time position tracking proved too computationally expensive for smooth UI
# Future optimization: Consider WebGL-based rendering or server-side position streaming
#
# Previous attempts:
# 1. Full figure regeneration every second -> UI blocking
# 2. Patch() with 3-second updates -> Still causes blocking
# 
# The static display is functional and doesn't interfere with simulation playback


# Track last dashboard update time (real-world time) to throttle updates
_last_dashboard_update_time = 0.0
_DASHBOARD_UPDATE_INTERVAL = 2.0  # Update dashboard every 2 real seconds

# Lightweight dashboard cache to avoid unnecessary re-renders
_cached_weather_component = None
_cached_weather_lap = None
_cached_weather_session_key = None

_cached_telemetry_component = None
_cached_telemetry_key = None  # (session_key, focused_driver, comparison_driver, lap)

_cached_ai_component = None
_cached_ai_sig = None  # hash over messages + context

_cached_race_control_component = None
_cached_race_control_sig = None  # (session_key, message_count, latest_time, focused_driver, lap)


def _render_race_control(
    focused_driver: str | None,
    use_store_time: bool,
    simulation_time_data: dict | None = None,
):
    """Build Race Control dashboard content with optional store-based time."""
    global current_session_obj, simulation_controller
    global _cached_race_control_component, _cached_race_control_sig

    if current_session_obj is None:
        raise PreventUpdate

    session_key = None
    simulation_time = None

    if current_session_obj and hasattr(current_session_obj, 'session_key'):
        session_key = current_session_obj.session_key

    if use_store_time and simulation_time_data and 'time' in simulation_time_data:
        simulation_time = simulation_time_data.get('time', 0.0)
        sim_logger.debug("Race control using simulation time from store: %.1fs", simulation_time)
    elif simulation_controller is not None:
        try:
            simulation_time = simulation_controller.get_elapsed_seconds()
            sim_logger.debug("Race control using controller time: %.1fs", simulation_time)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not get simulation time: %s", exc)
            simulation_time = 0.0

    session_start_time = None
    if simulation_controller is not None:
        session_start_time = pd.Timestamp(simulation_controller.start_time)

    current_lap = None
    if simulation_controller is not None:
        try:
            openf1_lap = simulation_controller.get_current_lap()
            current_lap = openf1_lap if openf1_lap and openf1_lap > 0 else 1
            sim_logger.debug("Current lap from controller: OpenF1 %s", openf1_lap)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not get lap from controller: %s", exc)
            current_lap = None

    rc_signature = race_control_dashboard.get_signature(
        session_key=session_key,
        simulation_time=simulation_time,
        session_start_time=session_start_time,
        focused_driver=focused_driver if focused_driver != 'none' else None,
        current_lap=current_lap,
    )

    if (
        _cached_race_control_component is not None
        and rc_signature is not None
        and rc_signature == _cached_race_control_sig
    ):
        control_logger.info("Race control unchanged; reusing cached component")
        return _cached_race_control_component

    control_content = race_control_dashboard.render(
        session_key=session_key,
        simulation_time=simulation_time,
        session_start_time=session_start_time,
        focused_driver=focused_driver if focused_driver != 'none' else None,
        current_lap=current_lap
    )
    _cached_race_control_component = control_content
    _cached_race_control_sig = rc_signature
    return control_content


def _render_weather(simulation_time_data: dict | None = None):
    """Build Weather dashboard content with lap-aware caching."""
    global current_session_obj, simulation_controller
    global _cached_weather_component, _cached_weather_lap, _cached_weather_session_key

    weather_session_key = current_session_obj.session_key if current_session_obj else None

    if weather_session_key is None:
        raise PreventUpdate

    simulation_time = None
    if simulation_time_data and 'time' in simulation_time_data:
        simulation_time = simulation_time_data.get('time', 0.0)
    elif simulation_controller is not None:
        try:
            simulation_time = simulation_controller.get_elapsed_seconds()
        except Exception:  # noqa: BLE001
            simulation_time = 0.0

    weather_lap = None
    if simulation_controller is not None:
        try:
            openf1_lap = simulation_controller.get_current_lap()
            weather_lap = openf1_lap if openf1_lap and openf1_lap > 0 else 1
        except Exception as exc:  # noqa: BLE001
            logger.debug("Weather lap read failed: %s", exc)
            weather_lap = None

    if (
        _cached_weather_component is not None
        and weather_lap is not None
        and _cached_weather_lap == weather_lap
        and _cached_weather_session_key == weather_session_key
    ):
        return _cached_weather_component

    session_start_time = None
    if simulation_controller is not None:
        try:
            session_start_time = pd.Timestamp(simulation_controller.start_time)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Weather start_time unavailable: %s", exc)

    weather_content = weather_dashboard.render_weather_content(
        session_key=weather_session_key,
        simulation_time=simulation_time,
        session_start_time=session_start_time
    )

    _cached_weather_component = weather_content
    _cached_weather_lap = weather_lap
    _cached_weather_session_key = weather_session_key
    return weather_content


def _render_telemetry(
    focused_driver: str | None,
    telemetry_comparison_data: dict | None,
    session_data: dict | None,
    use_store_time: bool,
    simulation_time_data: dict | None = None,
):
    """Build Telemetry dashboard content with caching."""
    global current_session_obj, simulation_controller
    global _cached_telemetry_component, _cached_telemetry_key

    session_key = None
    simulation_time = None

    if current_session_obj and hasattr(current_session_obj, 'session_key'):
        session_key = current_session_obj.session_key

    if use_store_time and simulation_time_data and 'time' in simulation_time_data:
        simulation_time = simulation_time_data.get('time', 0.0)
        sim_logger.debug("Telemetry using simulation time from store: %.1fs", simulation_time)
    elif simulation_controller is not None:
        try:
            simulation_time = simulation_controller.get_elapsed_seconds()
            sim_logger.debug("Telemetry using controller time: %.1fs", simulation_time)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not get simulation time: %s", exc)
            simulation_time = 0.0

    session_start_time = None
    if simulation_controller is not None:
        session_start_time = pd.Timestamp(simulation_controller.start_time)

    current_lap = None
    if simulation_controller is not None:
        try:
            openf1_lap = simulation_controller.get_current_lap()
            current_lap = openf1_lap if openf1_lap and openf1_lap > 0 else 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not get lap: %s", exc)
            current_lap = None

    comparison_driver = None
    if telemetry_comparison_data:
        comparison_driver = telemetry_comparison_data.get('driver')

    driver_options = []
    if session_data and session_data.get('drivers'):
        drivers_dict = session_data.get('drivers', {})
        driver_options = [
            {'label': label, 'value': value}
            for value, label in drivers_dict.items()
        ]

    cache_key = (
        session_key,
        focused_driver if focused_driver != 'none' else None,
        comparison_driver,
        current_lap
    )

    if _cached_telemetry_component is not None and cache_key == _cached_telemetry_key:
        return _cached_telemetry_component

    telemetry_content = telemetry_dashboard.render(
        session_key=session_key,
        simulation_time=simulation_time,
        session_start_time=session_start_time,
        focused_driver=focused_driver if focused_driver != 'none' else None,
        comparison_driver=comparison_driver,
        current_lap=current_lap,
        driver_options=driver_options
    )
    _cached_telemetry_component = telemetry_content
    _cached_telemetry_key = cache_key
    return telemetry_content


@callback(
    Output('race-control-status-card', 'children', allow_duplicate=True),
    Output('race-control-messages-view', 'children', allow_duplicate=True),
    Output('race-control-penalties-view', 'children', allow_duplicate=True),
    Input('simulation-time-store', 'data'),
    State('dashboard-selector', 'value'),
    State('driver-selector', 'value'),
    State('session-store', 'data'),
    prevent_initial_call=True
)
def refresh_race_control_content(
    simulation_time_data: dict[str, Any] | None,
    selected_dashboards: list[str] | None,
    focused_driver: str | None,
    session_data: dict[str, Any] | None,
):
    """Refresh Race Control content (messages and penalties) without destroying the Store or Card structure.
    
    This updates only the scrollable content divs, preserving:
    - dcc.Store (toggle state)
    - Card structure
    - CardHeader with toggle buttons
    - View containers
    """
    if not selected_dashboards or 'race_control' not in selected_dashboards:
        raise PreventUpdate
    if not session_data or not session_data.get('loaded'):
        raise PreventUpdate

    global current_session_obj, simulation_controller, race_control_dashboard

    if current_session_obj is None:
        raise PreventUpdate

    session_key = getattr(current_session_obj, 'session_key', None)
    
    # Get simulation time
    simulation_time = 0.0
    if simulation_time_data and 'time' in simulation_time_data:
        simulation_time = simulation_time_data.get('time', 0.0)
    elif simulation_controller is not None:
        simulation_time = simulation_controller.get_elapsed_seconds()

    session_start_time = None
    if simulation_controller is not None:
        session_start_time = pd.Timestamp(simulation_controller.start_time)

    current_lap = None
    if simulation_controller is not None:
        try:
            openf1_lap = simulation_controller.get_current_lap()
            current_lap = openf1_lap if openf1_lap and openf1_lap > 0 else 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not get lap from controller: %s", exc)

    # Re-render the Cards and extract their content divs
    try:
        if session_key is None:
            raise PreventUpdate
            
        # Get fresh messages DataFrame  
        messages_df, drivers_df = race_control_dashboard._get_messages_and_drivers(session_key)
        
        if messages_df is None or messages_df.empty:
            raise PreventUpdate
        
        # Filter messages by simulation time
        filtered_messages = race_control_dashboard._filter_messages_by_time(
            messages_df,
            simulation_time,
            session_start_time
        )
        
        if filtered_messages.empty:
            filtered_messages = messages_df.tail(50)
        
        # Build complete Cards with proper flex styling
        timeline_card = race_control_dashboard._create_messages_timeline(
            messages=filtered_messages,
            focused_driver=focused_driver if focused_driver != 'none' else None,
            drivers=drivers_df
        )
        
        # Get penalties summary and status
        if session_key is not None and simulation_time is not None and session_start_time is not None:
            # Calculate display lap
            display_lap = current_lap if current_lap and current_lap > 0 else 1
            
            summary_data = race_control_dashboard.get_status_summary(
                session_key=session_key,
                simulation_time=simulation_time,
                session_start_time=session_start_time,
                current_lap=display_lap
            )
            summary_card = race_control_dashboard._create_summary_panel(summary_data)
            
            # Build status card
            flag_state, sc_detail = race_control_dashboard._extract_current_status(
                filtered_messages,
                current_lap=display_lap
            )
            
            flag_color = {
                "GREEN": "success",
                "YELLOW": "warning",
                "RED": "danger",
                "SC": "warning",
                "VSC": "warning",
                "CHEQUERED": "secondary",
            }.get(flag_state, "secondary")

            flag_icon = {
                "GREEN": "🟢",
                "YELLOW": "🟡",
                "RED": "🔴",
                "SC": "🚗",
                "VSC": "🟡",
                "CHEQUERED": "🏁",
            }.get(flag_state, "🏁")

            flag_text = {
                "SC": "SAFETY CAR",
                "VSC": "VIRTUAL SC",
                "CHEQUERED": "SESSION ENDED",
            }.get(flag_state, flag_state)
            
            status_content = dbc.CardBody([
                html.Div([
                    dbc.Badge(
                        [flag_icon, f" {flag_text}"],
                        color=flag_color,
                        className="me-2",
                        style={"fontSize": "0.9rem"}
                    ),
                    html.Span(
                        f"Lap {display_lap}",
                        className="text-white",
                        style={"fontSize": "0.85rem"}
                    ),
                    html.Span(
                        f" | {sc_detail}" if sc_detail else "",
                        className="text-warning ms-2",
                        style={"fontSize": "0.75rem"}
                    )
                ], style={"display": "flex", "alignItems": "center"})
            ], className="p-2")
        else:
            summary_card = dbc.Card([
                dbc.CardHeader("⚖️ Investigations & Penalties", className="text-white py-1"),
                dbc.CardBody(html.Div("Waiting for timing data...", className="text-muted text-center p-3"))
            ])
            status_content = dbc.CardBody([
                html.Div("Waiting for data...", className="text-muted", style={"fontSize": "0.85rem"})
            ], className="p-2")
        
        return status_content, timeline_card, summary_card
        
    except Exception as exc:  # noqa: BLE001
        logger.error("Error refreshing race control content: %s", exc, exc_info=True)
        raise PreventUpdate


# Use clientside callback for instant toggle without server round-trip
app.clientside_callback(
    """
    function(n_clicks_list, current_state) {
        // Get which button was clicked
        const triggered = dash_clientside.callback_context.triggered;
        if (!triggered || triggered.length === 0) {
            // On initial load, restore state from store
            if (current_state === 'penalties') {
                return [
                    {'display': 'none'},
                    {'display': 'flex', 'flex': '1 1 auto', 'minHeight': '0', 'flexDirection': 'column', 'overflow': 'hidden'},
                    'secondary',
                    'primary',
                    'penalties'
                ];
            }
            return [window.dash_clientside.no_update, window.dash_clientside.no_update, window.dash_clientside.no_update, window.dash_clientside.no_update, window.dash_clientside.no_update];
        }
        
        const triggeredId = triggered[0].prop_id.split('.')[0];
        let view = current_state || 'messages';  // default
        
        try {
            const idObj = JSON.parse(triggeredId);
            view = idObj.view;
        } catch (e) {
            return [window.dash_clientside.no_update, window.dash_clientside.no_update, window.dash_clientside.no_update, window.dash_clientside.no_update, window.dash_clientside.no_update];
        }
        
        if (view === 'messages') {
            // Show messages, hide penalties
            return [
                {'display': 'flex', 'flex': '1 1 auto', 'minHeight': '0', 'flexDirection': 'column', 'overflow': 'hidden'},
                {'display': 'none'},
                'primary',
                'secondary',
                'messages'
            ];
        } else {
            // Show penalties, hide messages
            return [
                {'display': 'none'},
                {'display': 'flex', 'flex': '1 1 auto', 'minHeight': '0', 'flexDirection': 'column', 'overflow': 'hidden'},
                'secondary',
                'primary',
                'penalties'
            ];
        }
    }
    """,
    Output('race-control-messages-view', 'style'),
    Output('race-control-penalties-view', 'style'),
    Output({'type': 'race-control-toggle', 'view': 'messages'}, 'color'),
    Output({'type': 'race-control-toggle', 'view': 'penalties'}, 'color'),
    Output('race-control-view-state', 'data'),
    Input({'type': 'race-control-toggle', 'view': ALL}, 'n_clicks'),
    State('race-control-view-state', 'data'),
    prevent_initial_call=False
)


@callback(
    Output('weather-wrapper', 'children', allow_duplicate=True),
    Input('simulation-time-store', 'data'),
    State('dashboard-selector', 'value'),
    State('session-store', 'data'),
    prevent_initial_call=True
)
def refresh_weather_wrapper(
    simulation_time_data: dict[str, Any] | None,
    selected_dashboards: list[str] | None,
    session_data: dict[str, Any] | None,
):
    """Refresh Weather dashboard independently to avoid AI flicker."""
    if not selected_dashboards or 'weather' not in selected_dashboards:
        raise PreventUpdate
    if not session_data or not session_data.get('loaded'):
        raise PreventUpdate
    if current_session_obj is None:
        raise PreventUpdate

    return _render_weather(simulation_time_data=simulation_time_data)


@callback(
    Output('telemetry-wrapper', 'children', allow_duplicate=True),
    Input('simulation-time-store', 'data'),
    State('dashboard-selector', 'value'),
    State('driver-selector', 'value'),
    State('session-store', 'data'),
    State('telemetry-comparison-store', 'data'),
    prevent_initial_call=True
)
def refresh_telemetry_wrapper(
    simulation_time_data: dict[str, Any] | None,
    selected_dashboards: list[str] | None,
    focused_driver: str | None,
    session_data: dict[str, Any] | None,
    telemetry_comparison_data: dict[str, Any] | None,
):
    """Refresh Telemetry dashboard without remounting other panels."""
    if not selected_dashboards or 'telemetry' not in selected_dashboards:
        raise PreventUpdate
    if not session_data or not session_data.get('loaded'):
        raise PreventUpdate

    return _render_telemetry(
        focused_driver=focused_driver,
        telemetry_comparison_data=telemetry_comparison_data,
        session_data=session_data,
        use_store_time=True,
        simulation_time_data=simulation_time_data,
    )


@callback(
    Output('simulation-time-store', 'data'),
    Input('simulation-interval', 'n_intervals'),
    State('dashboard-selector', 'value'),
    State('simulation-time-store', 'data'),
    prevent_initial_call=True
)
def update_simulation_time_store(n_intervals, selected_dashboards, current_store):
    """Update simulation time store for dashboard updates.
    
    This triggers the full dashboard refresh including gaps/intervals.
    Throttled to update every 2 real seconds to prevent UI freezing.
    """
    global simulation_controller, _last_dashboard_update_time
    
    # Only update if race_overview dashboard is selected
    if not selected_dashboards or 'race_overview' not in selected_dashboards:
        raise PreventUpdate
    
    # Check if simulation is running
    if simulation_controller is None:
        raise PreventUpdate
    
    # NOTE: Removed is_playing check here.
    # The interval is disabled when paused (via toggle_play_pause),
    # so this callback won't run anyway when paused.
    # The previous is_playing check was causing race conditions.
    
    try:
        # Throttle: only update dashboard every N real seconds
        current_real_time = time.time()
        time_since_last_update = current_real_time - _last_dashboard_update_time
        
        if time_since_last_update < _DASHBOARD_UPDATE_INTERVAL:
            # Not enough real time has passed, skip this update
            raise PreventUpdate
        
        # Update timestamp for throttling
        _last_dashboard_update_time = current_real_time
        
        # Get current simulation time
        simulation_time = simulation_controller.get_elapsed_seconds()
        
        logger.debug(
            f"Dashboard update triggered: sim_time={simulation_time:.1f}s, "
            f"real_interval={time_since_last_update:.1f}s"
        )
        
        return {
            'time': simulation_time,
            'timestamp': n_intervals  # Force update even if time is same
        }
        
    except PreventUpdate:
        raise
    except Exception as e:
        logger.error(
            f"Error updating simulation time store: {e}",
            exc_info=True
        )
        raise PreventUpdate


# Callback: Fast update for lap badge only (lightweight, runs on every interval)
# This updates the lap counter immediately without regenerating the dashboard
@callback(
    Output('current-lap-store', 'data'),
    Input('simulation-interval', 'n_intervals'),
    State('session-store', 'data'),
    prevent_initial_call=True
)
def update_current_lap_store(n_intervals, session_data):
    """Update current lap store for fast badge updates."""
    global simulation_controller
    
    if simulation_controller is None or not simulation_controller.is_playing:
        raise PreventUpdate
    
    try:
        # Get current lap from controller (raw count)
        current_lap = simulation_controller.get_current_lap()
        total_laps = session_data.get('total_laps', 57) if session_data else 57

        display_lap = current_lap if current_lap and current_lap > 0 else 1
        is_untimed_lap = display_lap == 1

        return {
            'lap': display_lap,
            'total': total_laps,
            'untimed': is_untimed_lap,
            'timestamp': n_intervals
        }
    except Exception as e:
        logger.error(f"Error updating lap store: {e}")
        raise PreventUpdate


# Callback: Update race overview lap badge independently (fast path)
@callback(
    Output('race-overview-lap-badge', 'children'),
    Input('current-lap-store', 'data'),
    prevent_initial_call=True
)
def update_lap_badge(lap_data):
    """Update lap badge text quickly without regenerating dashboard."""
    if not lap_data:
        raise PreventUpdate
    
    lap = lap_data.get('lap', 1)
    total = lap_data.get('total', 57)
    untimed = lap_data.get('untimed', False)

    if untimed:
        return f"Lap 1 (untimed)/{total}"
    return f"Lap {lap}/{total}"


# Callback: Update circuit map driver positions in real-time
@callback(
    Output('circuit-map-graph', 'figure'),
    Input('simulation-interval', 'n_intervals'),
    State('dashboard-selector', 'value'),
    State('circuit-map-graph', 'figure'),
    prevent_initial_call=True
)
def update_circuit_map_realtime(n_intervals, selected_dashboards, current_figure):
    """Update driver positions on circuit map using Patch for efficiency."""
    global simulation_controller, current_session_obj
    
    # Only update if race_overview dashboard is selected
    if not selected_dashboards or 'race_overview' not in selected_dashboards:
        raise PreventUpdate
    
    # Check if simulation is running and session loaded
    if simulation_controller is None or current_session_obj is None:
        raise PreventUpdate
    
    try:
        # Get current simulation time
        current_time = simulation_controller.current_time
        
        # Get session data
        laps = current_session_obj.laps
        results = current_session_obj.results
        drivers = current_session_obj.drivers
        
        # Use Patch to update only driver positions (Traces 2+)
        patched_figure = Patch()
        
        driver_idx = 0
        for driver_num in drivers:
            try:
                driver_info = results[results['DriverNumber'] == str(driver_num)].iloc[0]
                
                # Get driver's laps
                driver_laps = laps[laps['DriverNumber'] == driver_num]
                if driver_laps.empty:
                    continue
                
                # Find appropriate lap based on current_time
                if 'Time' in driver_laps.columns:
                    valid_laps = driver_laps[
                        pd.notna(driver_laps['Time']) &  # type: ignore
                        (driver_laps['Time'] <= current_time)
                    ]
                    if not valid_laps.empty:
                        current_lap = valid_laps.iloc[-1]
                    else:
                        current_lap = driver_laps.iloc[0]
                else:
                    current_lap = driver_laps.iloc[0]
                
                telemetry = current_lap.get_telemetry()
                
                if not telemetry.empty and 'X' in telemetry.columns and 'Y' in telemetry.columns:
                    if 'Time' in telemetry.columns:
                        valid_telem = telemetry[pd.notna(telemetry['Time'])]
                        if not valid_telem.empty:
                            # Find closest telemetry point by time
                            time_diffs = (valid_telem['Time'] - current_time).abs()
                            closest_idx = time_diffs.idxmin()
                            x_pos = telemetry.loc[closest_idx, 'X']
                            y_pos = telemetry.loc[closest_idx, 'Y']
                        else:
                            x_pos = telemetry['X'].iloc[0]
                            y_pos = telemetry['Y'].iloc[0]
                    else:
                        x_pos = telemetry['X'].iloc[0]
                        y_pos = telemetry['Y'].iloc[0]
                    
                    # Update driver position (trace index = 2 + driver_idx)
                    # Trace 0 = circuit outline, Trace 1 = START marker, Traces 2+ = drivers
                    trace_idx = 2 + driver_idx
                    patched_figure['data'][trace_idx]['x'] = [x_pos]
                    patched_figure['data'][trace_idx]['y'] = [y_pos]
                    
                    driver_idx += 1
                    
            except Exception as e:
                logger.debug(f"Error updating position for driver {driver_num}: {e}")
                continue
        
        return patched_figure
        
    except Exception as e:
        logger.error(f"Error updating circuit map: {e}")
        raise PreventUpdate


# Callback: Toggle help modal
@callback(
    Output('help-modal', 'is_open'),
    [Input('help-btn', 'n_clicks'),
     Input('close-help-modal', 'n_clicks')],
    State('help-modal', 'is_open'),
    prevent_initial_call=True
)
def toggle_help_modal(help_clicks, close_clicks, is_open):
    """Toggle help modal visibility."""
    if help_clicks or close_clicks:
        return not is_open
    return is_open


# Callback: Toggle sidebar visibility
@callback(
    [Output('sidebar-column', 'style'),
     Output('main-content-column', 'width'),
     Output('sidebar-visible-store', 'data'),
     Output('sidebar-toggle-btn', 'children'),
     Output('sidebar-toggle-btn', 'title')],
    Input('sidebar-toggle-btn', 'n_clicks'),
    State('sidebar-visible-store', 'data'),
    prevent_initial_call=True
)
def toggle_sidebar(n_clicks, is_visible):
    """Toggle sidebar visibility."""
    if n_clicks is None:
        raise PreventUpdate
    
    # Toggle visibility
    new_visibility = not is_visible
    
    if new_visibility:
        # Show sidebar
        return {'display': 'block'}, 10, True, '<<', 'Hide sidebar'
    else:
        # Hide sidebar
        return {'display': 'none'}, 12, False, '>>', 'Show sidebar'


# ============================================================================
# AI CHAT CALLBACKS
# ============================================================================

# Rate limiting for chat requests (prevent flooding LLM API)
_last_chat_request_time: float = 0.0
_last_chat_messages: list[dict[str, Any]] = []
_last_render_signature: Optional[str] = None
_cached_ai_component: Any | None = None
_cached_ai_sig: Optional[str] = None


def _ensure_json_safe_messages(raw_messages: Any) -> list[dict]:
    """Convert incoming store data to a JSON-serializable list of messages."""
    safe_list: list[dict] = []

    # Normalize dict payloads (dcc.Store can send a dict when hydrated)
    if isinstance(raw_messages, dict):
        candidate_messages = [v for v in raw_messages.values() if v is not None]
    elif isinstance(raw_messages, list):
        candidate_messages = raw_messages
    else:
        candidate_messages = []

    def _sanitize_value(value: Any) -> Any:
        """Recursively sanitize values to make them JSON-safe."""
        if isinstance(value, float):
            if not math.isfinite(value):
                return str(value)
            return float(value)
        if isinstance(value, (int, str, bool)) or value is None:
            return value
        if isinstance(value, dict):
            return {str(k): _sanitize_value(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [_sanitize_value(v) for v in value]
        try:
            json.dumps(value)  # type: ignore[arg-type]
            return value
        except Exception:
            return str(value)

    for msg in candidate_messages:
        if not isinstance(msg, dict):
            continue
        safe_msg: dict[str, Any] = {}

        safe_msg['type'] = str(msg.get('type', 'assistant'))
        safe_msg['content'] = str(msg.get('content', ''))
        safe_msg['timestamp'] = str(msg.get('timestamp', datetime.now().isoformat()))

        metadata = msg.get('metadata', {})
        if isinstance(metadata, dict):
            safe_msg['metadata'] = _sanitize_value(metadata)
        else:
            safe_msg['metadata'] = {}

        # Preserve optional priority if present
        if 'priority' in msg:
            safe_msg['priority'] = _sanitize_value(msg['priority'])

        safe_list.append(safe_msg)

    return safe_list


@callback(
    Output('chat-messages-store', 'data', allow_duplicate=True),
    Output('chat-messages-container', 'children', allow_duplicate=True),
    Input('chat-send-btn', 'n_clicks'),
    Input('chat-input', 'n_submit'),
    Input('quick-pit-btn', 'n_clicks'),
    Input('quick-weather-btn', 'n_clicks'),
    Input('quick-gap-btn', 'n_clicks'),
    Input('quick-predict-btn', 'n_clicks'),
    State('chat-input', 'value'),
    State('chat-messages-store', 'data'),
    State('session-store', 'data'),
    State('driver-selector', 'value'),
    State('simulation-time-store', 'data'),
    prevent_initial_call=True
)
def handle_chat_send(
    send_clicks,
    input_submit,
    pit_clicks,
    weather_clicks,
    gap_clicks,
    predict_clicks,
    user_input,
    current_messages,
    session_data,
    focused_driver,
    sim_time_data
):
    """
    Handle user chat input and quick action buttons.
    Adds user message and generates AI response.
    Simple rate limiting to prevent API quota exhaustion.
    """
    global _last_chat_request_time, _last_chat_messages

    from src.dashboards_dash.ai_assistant_dashboard import AIAssistantDashboard
    
    if not ctx.triggered:
        raise PreventUpdate
    
    triggered_id = ctx.triggered_id
    
    # Ignore chat-input triggers unless they have actual content
    # This prevents the callback firing on every keystroke/focus change
    if triggered_id == 'chat-input':
        if not user_input or not user_input.strip():
            raise PreventUpdate
        # Only log actual submissions
        chat_logger.info(f"[CHAT] Text submitted via Enter: {user_input[:30]}...")
    else:
        chat_logger.info(f"[CHAT] Callback triggered by: {triggered_id}")
    
    # Normalize and JSON-sanitize incoming store data before appending
    messages = _ensure_json_safe_messages(current_messages)
    if not messages and _last_chat_messages:
        # Restore history if store was unexpectedly empty
        messages = json.loads(json.dumps(_last_chat_messages))
    
    # Simple rate limiting - only block very rapid clicks (< 0.5s)
    current_time = time.time()
    time_since_last = current_time - _last_chat_request_time
    
    chat_logger.info(f"[CHAT] Time since last: {time_since_last:.2f}s")
    
    if time_since_last < 0.5 and _last_chat_request_time > 0:
        chat_logger.info("[CHAT] Rate limited - ignoring rapid click")
        raise PreventUpdate  # Silently ignore rapid double-clicks
    
    _last_chat_request_time = current_time
    
    # Determine the query based on what was triggered
    if triggered_id in ['chat-send-btn', 'chat-input']:
        if not user_input or not user_input.strip():
            chat_logger.debug("[CHAT] Empty input, preventing update")
            raise PreventUpdate
        query = user_input.strip()
    elif triggered_id == 'quick-pit-btn':
        if not pit_clicks or pit_clicks <= 0:
            chat_logger.debug("[CHAT] Ignoring pit trigger with zero clicks")
            raise PreventUpdate
        if not session_data or not session_data.get('loaded'):
            chat_logger.info("[CHAT] Ignoring quick pit: no session loaded")
            raise PreventUpdate
        driver = focused_driver if focused_driver not in (None, 'none', '') else 'our driver'
        query = f"Should {driver} pit now? What's the optimal tire strategy?"
    elif triggered_id == 'quick-weather-btn':
        if not weather_clicks or weather_clicks <= 0:
            chat_logger.debug("[CHAT] Ignoring weather trigger with zero clicks")
            raise PreventUpdate
        query = "What's the current weather situation? Any rain expected?"
    elif triggered_id == 'quick-gap-btn':
        if not gap_clicks or gap_clicks <= 0:
            chat_logger.debug("[CHAT] Ignoring gap trigger with zero clicks")
            raise PreventUpdate
        driver = focused_driver if focused_driver not in (None, 'none', '') else 'our driver'
        query = f"What are the gaps around {driver}? Any overtake opportunities?"
    elif triggered_id == 'quick-predict-btn':
        if not predict_clicks or predict_clicks <= 0:
            chat_logger.debug("[CHAT] Ignoring predict trigger with zero clicks")
            raise PreventUpdate
        if not session_data or not session_data.get('loaded'):
            chat_logger.info("[CHAT] Ignoring quick predict: no session loaded")
            raise PreventUpdate
        driver = focused_driver if focused_driver not in (None, 'none', '') else 'our driver'
        
        # Generate prediction using overtake predictor
        try:
            from src.predictive.overtake_predictor import predict_overtake_window
            
            # Get race state snapshot for prediction
            snapshot = get_race_state_snapshot(
                session_data=session_data,
                sim_time_data=sim_time_data,
                focused_driver=focused_driver
            )
            
            if snapshot and 'error' not in snapshot:
                leaderboard = snapshot.get('leaderboard', {})
                focus = leaderboard.get('focus_driver')
                
                if focus:
                    # Parse gaps
                    ahead_gap_str = focus.get('gap_ahead', 'N/A')
                    behind_gap_str = focus.get('gap_behind', 'N/A')
                    
                    ahead_gap = None
                    behind_gap = None
                    
                    if ahead_gap_str not in ('N/A', 'CLOSED', 'LEADER'):
                        try:
                            ahead_gap = float(ahead_gap_str.replace('s', ''))
                        except (ValueError, AttributeError):
                            pass
                    
                    if behind_gap_str not in ('N/A', 'CLOSED'):
                        try:
                            behind_gap = float(behind_gap_str.replace('s', ''))
                        except (ValueError, AttributeError):
                            pass
                    
                    # Generate prediction
                    prediction = predict_overtake_window(
                        driver=driver,
                        ahead_gap=ahead_gap,
                        behind_gap=behind_gap,
                        tire_age=focus.get('age', 0),
                        track_position=focus.get('pos', 0)
                    )
                    
                    # Format query with prediction
                    query = (
                        f"🔮 Overtake Prediction for {driver}:\n"
                        f"Probability (next 5 laps): {prediction['probability']:.1%}\n"
                        f"Optimal window: Laps {prediction['optimal_laps']}\n"
                        f"Gap ahead: {ahead_gap_str}\n"
                        f"Gap behind: {behind_gap_str}\n"
                        f"Tire age: {focus.get('age')} laps\n"
                        f"Confidence: {prediction['confidence']}\n\n"
                        f"Should I attempt an overtake now or wait for a better opportunity?"
                    )
                else:
                    query = f"Cannot predict overtakes for {driver} - no position data available."
            else:
                query = f"Cannot predict overtakes for {driver} - race snapshot unavailable."
                
        except ImportError:
            chat_logger.warning("[CHAT] Predictive module not available")
            query = "🔮 Predictive AI module is not available. This feature requires the predictive package."
        except Exception as e:
            chat_logger.error(f"[CHAT] Prediction failed: {e}")
            query = f"🔮 Prediction failed: {str(e)}"
    else:
        chat_logger.debug(f"[CHAT] Unknown trigger: {triggered_id}")
        raise PreventUpdate

    chat_logger.info(f"[CHAT] Processing query: {query[:50]}...")
    # Add user message
    timestamp = datetime.now().isoformat()
    messages.append({
        'type': 'user',
        'content': query,
        'timestamp': timestamp
    })
    history_for_ai = [
        m for m in messages[-8:]
        if not m.get('metadata', {}).get('thinking')
    ]
    
    # Add "thinking" message immediately for visual feedback
    thinking_msg = {
        'type': 'assistant',
        'content': '🤔 Analyzing race data...',
        'timestamp': datetime.now().isoformat(),
        'metadata': {'thinking': True}
    }
    messages.append(thinking_msg)
    
    # Generate AI response
    chat_logger.info("[CHAT] Calling generate_ai_response...")
    try:
        response = generate_ai_response(
            query=query,
            session_data=session_data,
            focused_driver=focused_driver,
            sim_time_data=sim_time_data,
            message_history=history_for_ai
        )
        
        chat_logger.info("[CHAT] Response received successfully")
        
        # Remove the "thinking" message and add real response
        messages = [m for m in messages if not m.get('metadata', {}).get('thinking')]
        messages.append({
            'type': 'assistant',
            'content': response['content'],
            'timestamp': datetime.now().isoformat(),
            'metadata': response.get('metadata', {})
        })
    except Exception as e:
        chat_logger.error(f"[CHAT] AI response failed: {e}")
        logger.error(f"AI response generation failed: {e}", exc_info=True)
        # Remove thinking message and add error
        messages = [m for m in messages if not m.get('metadata', {}).get('thinking')]
        messages.append({
            'type': 'assistant',
            'content': (
                "I'm having trouble analyzing the data right now. "
                "Please try again in a moment."
            ),
            'timestamp': datetime.now().isoformat(),
            'metadata': {'error': str(e)}
        })
    
    # Return updated messages to store ONLY
    # The sync_store_to_container callback will update the UI
    # Ensure outgoing payload is JSON-safe to avoid silent client-side drops
    safe_messages = _ensure_json_safe_messages(messages)
    if not safe_messages and messages:
        try:
            safe_messages = json.loads(json.dumps(messages, default=str))
            chat_logger.warning(
                "[CHAT] Sanitizer produced empty list; using JSON-coerced fallback with %d messages",
                len(safe_messages)
            )
        except Exception as fallback_exc:
            chat_logger.error(f"[CHAT] Fallback serialization failed: {fallback_exc}")
            safe_messages = []
    _last_chat_messages = safe_messages
    chat_logger.info(f"[CHAT] Returning {len(safe_messages)} messages to store")
    rendered = AIAssistantDashboard.render_messages(safe_messages)
    return safe_messages, rendered


# Callback to sync store to container - THE ONLY writer to chat-messages-container
# This ensures the container always reflects the store state
@callback(
    Output('chat-messages-container', 'children', allow_duplicate=True),
    Input('chat-messages-store', 'data'),
    prevent_initial_call='initial_duplicate'
)
def sync_store_to_container(messages):
    """
    Sync chat-messages-store to chat-messages-container.
    
    This callback fires whenever the store changes (new message added).
    It's the ONLY callback that writes to chat-messages-container.
    """
    from src.dashboards_dash.ai_assistant_dashboard import AIAssistantDashboard
    global _last_chat_messages, _last_render_signature
    
    chat_logger.info(f"[SYNC] Called with messages type={type(messages)}, count={len(messages) if messages else 0}")

    def _signature(payload: Any) -> Optional[str]:
        try:
            return hashlib.sha1(
                json.dumps(payload, sort_keys=True, default=str).encode('utf-8')
            ).hexdigest()
        except Exception as exc:
            chat_logger.debug(f"[SYNC] Signature generation failed: {exc}")
            return None

    # If we receive a JSON string, try to decode it
    if isinstance(messages, str):
        try:
            decoded = json.loads(messages)
            chat_logger.warning("[SYNC] Decoded messages from JSON string payload")
            messages = decoded
        except Exception as decode_exc:
            chat_logger.error(f"[SYNC] Failed to decode string payload: {decode_exc}")
            messages = []
    
    # Handle None or empty with fallback to last known messages
    if not messages:
        if _last_chat_messages:
            sig = _signature(_last_chat_messages)
            if sig and sig == _last_render_signature:
                chat_logger.debug("[SYNC] No content change; skipping render")
                return no_update
            _last_render_signature = sig
            chat_logger.warning("[SYNC] Store empty; rendering last known chat messages (%d)", len(_last_chat_messages))
            return AIAssistantDashboard.render_messages(_last_chat_messages)
        chat_logger.info("[SYNC] Rendering empty placeholder (no messages)")
        placeholder = [
            html.Div([
                html.P([
                    html.I(className="bi bi-info-circle me-2"),
                    "AI will send proactive alerts during the race. ",
                    "You can also ask questions anytime."
                ], className="text-muted small text-center mb-0")
            ], style={"padding": "20px"})
        ]
        if _last_render_signature != 'EMPTY_PLACEHOLDER':
            _last_render_signature = 'EMPTY_PLACEHOLDER'
            return placeholder
        return no_update
    
    # Handle dict (dcc.Store serialization quirk)
    if isinstance(messages, dict):
        messages = [v for v in messages.values() if v is not None]
    
    # Filter valid messages
    messages = [m for m in messages if m is not None and isinstance(m, dict)]

    if messages:
        sig = _signature(messages)
        if sig and sig == _last_render_signature:
            chat_logger.debug("[SYNC] No content change; skipping render")
            return no_update
        _last_render_signature = sig
        _last_chat_messages = messages
    
    chat_logger.debug(f"[SYNC] Rendering {len(messages)} messages")
    return AIAssistantDashboard.render_messages(messages)


@callback(
    Output('chat-messages-store', 'data', allow_duplicate=True),
    Input('clear-chat-btn', 'n_clicks'),
    prevent_initial_call=True
)
def clear_chat(n_clicks):
    """Clear all chat messages."""
    if not n_clicks:
        raise PreventUpdate
    global _last_chat_messages
    _last_chat_messages = []
    return []


# Store to track last known context for chat clearing
_last_chat_context = {'year': None, 'circuit': None, 'session': None}


@callback(
    Output('chat-messages-store', 'data', allow_duplicate=True),
    Input('year-selector', 'value'),
    Input('circuit-selector', 'value'),
    Input('session-selector', 'value'),
    State('chat-messages-store', 'data'),
    prevent_initial_call=True
)
def clear_chat_on_context_change(year, circuit, session_type, current_messages):
    """Clear chat history when year, circuit or session changes.
    
    Only clears when there's a REAL context change, not on every trigger.
    Driver changes don't clear chat (user may be comparing drivers).
    """
    global _last_chat_context
    
    # Check if this is a real context change
    context_changed = (
        _last_chat_context['year'] is not None and (
            year != _last_chat_context['year'] or
            circuit != _last_chat_context['circuit'] or
            session_type != _last_chat_context['session']
        )
    )
    
    # Update stored context
    _last_chat_context = {
        'year': year,
        'circuit': circuit,
        'session': session_type
    }
    
    # Only clear if there was a real change AND we had previous context
    if context_changed:
        chat_logger.info(
            f"[CHAT] Context changed - clearing chat "
            f"(year={year}, circuit={circuit}, session={session_type})"
        )
        global _last_chat_messages
        _last_chat_messages = []
        return []
    
    # No change - keep existing messages
    raise PreventUpdate


@callback(
    Output('chat-input', 'value'),
    Input('chat-send-btn', 'n_clicks'),
    Input('chat-input', 'n_submit'),
    prevent_initial_call=True
)
def clear_input(send_clicks, enter_submit):
    """Clear input field after sending."""
    return ""


@callback(
    Output('chat-messages-store', 'data', allow_duplicate=True),
    Output('proactive-last-check-store', 'data'),
    Input('proactive-check-interval', 'n_intervals'),
    State('chat-messages-store', 'data'),
    State('proactive-last-check-store', 'data'),
    State('session-store', 'data'),
    State('driver-selector', 'value'),
    State('simulation-time-store', 'data'),
    prevent_initial_call=True
)
def check_proactive_alerts(
    n_intervals,
    current_messages,
    last_check_data,
    session_data,
    focused_driver,
    sim_time_data
):
    """
    Periodically check for race events and generate proactive alerts.
    
    CRITICAL: Only uses data up to current simulation time (NO FUTURE DATA).
    """
    proactive_logger.debug(
        f"[PROACTIVE] check_proactive_alerts triggered, "
        f"interval={n_intervals}, focused_driver={focused_driver}"
    )
    
    if not session_data or not session_data.get('loaded'):
        proactive_logger.debug("[PROACTIVE] No session loaded, skipping")
        raise PreventUpdate
    
    # Check if driver is selected - required for most alerts
    if not focused_driver or focused_driver == 'none':
        proactive_logger.debug("[PROACTIVE] No driver selected, skipping (select a driver to enable alerts)")
        raise PreventUpdate
    
    global _last_chat_messages

    messages = _ensure_json_safe_messages(current_messages)
    if not messages and _last_chat_messages:
        messages = json.loads(json.dumps(_last_chat_messages))
    last_lap = last_check_data.get('last_lap', 0) if last_check_data else 0
    
    try:
        # Get current simulation state
        session_key = session_data.get('session_key')
        if not session_key:
            proactive_logger.debug("[PROACTIVE] No session_key, skipping")
            raise PreventUpdate
        
        # Parse simulation time
        sim_time = sim_time_data.get('time', 0) if sim_time_data else 0
        
        # Get current lap from simulation controller
        current_lap = 1
        if simulation_controller:
            current_lap = simulation_controller.get_current_lap()
        
        proactive_logger.debug(f"[PROACTIVE] current_lap={current_lap}, last_lap={last_lap}")
        
        # Get current time from simulation
        current_time = None
        if simulation_controller:
            current_time = simulation_controller.current_time
        
        if not current_time:
            proactive_logger.debug("[PROACTIVE] No current_time, skipping")
            raise PreventUpdate
        
        proactive_logger.info(f"[PROACTIVE] Checking events at lap {current_lap}, time={current_time}")
        
        # Get focused driver number from the value format "VER_2025_1"
        driver_number = None
        if focused_driver and focused_driver != 'none':
            try:
                # focused_driver format: "CODE_YEAR_NUMBER" e.g. "VER_2025_1"
                parts = focused_driver.split('_')
                if len(parts) >= 3:
                    driver_number = int(parts[-1])  # Last part is driver number
                    proactive_logger.info(
                        f"[PROACTIVE] Tracking driver #{driver_number} ({parts[0]})"
                    )
            except (ValueError, IndexError) as e:
                proactive_logger.warning(
                    f"[PROACTIVE] Could not parse driver from {focused_driver}: {e}"
                )
        
        proactive_logger.debug(f"[PROACTIVE] focused_driver={focused_driver}, driver_number={driver_number}")
        
        # Detect events
        events = event_detector.detect_events(
            session_key=session_key,
            current_time=current_time,
            current_lap=current_lap,
            focused_driver=driver_number,
            total_laps=session_data.get('total_laps', 57)
        )
        
        if events:
            proactive_logger.info(f"[PROACTIVE] ✓ Detected {len(events)} events!")
        else:
            proactive_logger.info(f"[PROACTIVE] No events (driver={driver_number}, lap={current_lap})")
        
        # Add alerts for detected events
        for event in events:
            proactive_logger.info(f"[PROACTIVE] EVENT: {event.event_type} - {event.message[:50]}...")
            messages.append({
                'type': 'alert',
                'content': event.message,
                'timestamp': datetime.now().isoformat(),
                'priority': event.priority,
                'metadata': {
                    'event_type': event.event_type,
                    'data': event.data
                }
            })
        
        # CRITICAL: Only update store if we actually added new events
        # This prevents overwriting chat messages added by other callbacks
        if events:
            safe_messages = _ensure_json_safe_messages(messages)
            _last_chat_messages = safe_messages
            return safe_messages, {'last_lap': current_lap}
        else:
            # No events - don't touch the store, just update last_lap tracking
            return no_update, {'last_lap': current_lap}
        
    except PreventUpdate:
        raise  # Re-raise PreventUpdate without logging
    except Exception as e:
        import traceback
        proactive_logger.warning(f"[PROACTIVE] Alert check failed: {e}")
        proactive_logger.debug(f"[PROACTIVE] Traceback: {traceback.format_exc()}")
        raise PreventUpdate


@callback(
    Output('proactive-check-interval', 'disabled'),
    Input('play-btn', 'n_clicks'),
    prevent_initial_call=True
)
def toggle_proactive_interval(n_clicks):
    """Enable/disable proactive checking when simulation plays/pauses."""
    if not n_clicks:
        raise PreventUpdate
    
    # Check actual simulation state
    if simulation_controller is None:
        proactive_logger.debug("[PROACTIVE] No simulation controller, interval stays disabled")
        return True  # Keep disabled
    
    # Get actual is_playing state (after toggle_play_pause was called)
    is_playing = simulation_controller.is_playing
    
    # If playing, enable interval (disabled=False). If paused, disable (disabled=True)
    new_disabled = not is_playing
    proactive_logger.info(f"[PROACTIVE] Interval toggled: disabled={new_disabled} (is_playing={is_playing})")
    return new_disabled


# ============================================================================
# RACE STATE SNAPSHOT AND AI CONTEXT
# ============================================================================

def get_race_state_snapshot(
    session_data: Optional[Dict],
    sim_time_data: Optional[Dict],
    focused_driver: Optional[str]
) -> Dict[str, Any]:
    """
    Generate comprehensive snapshot of current race state for AI context.
    
    Args:
        session_data: Session store data (race_name, session_key, etc.)
        sim_time_data: Simulation time store data (time, timestamp)
        focused_driver: Driver identifier (e.g., "RUS_2025_63")
        
    Returns:
        Dict with race state snapshot including leaderboard, weather, flags, etc.
    """
    try:
        # Check for None values
        if not session_data or not sim_time_data:
            return {'error': 'Missing session or simulation data'}
        
        session_key = session_data.get('session_key')
        simulation_time = sim_time_data.get('time', 0)
        total_laps = session_data.get('total_laps', 57)
        
        if not session_key or simulation_controller is None:
            return {'error': 'No session loaded or controller unavailable'}
        
        # Get current lap
        current_lap = simulation_controller.get_current_lap()
        session_start_time = simulation_controller.start_time
        
        # Convert datetime to pandas Timestamp for compatibility
        import pandas as pd
        session_start_timestamp = pd.Timestamp(session_start_time)
        
        snapshot = {
            'lap': current_lap,
            'total_laps': total_laps,
            'simulation_time': simulation_time,
            'race_name': session_data.get('race_name', 'Unknown'),
            'session_type': session_data.get('session_type', 'Race')
        }
        
        # Get leaderboard summary
        try:
            cache_ready, cache_reason = race_overview_dashboard.warm_cache(session_key)
            if not cache_ready:
                logger.debug(
                    "Race overview cache not warmed (%s) before AI snapshot",
                    cache_reason,
                )
            if race_overview_dashboard._cached_positions is not None:
                leaderboard = race_overview_dashboard.get_leaderboard_summary(
                    session_key=session_key,
                    simulation_time=simulation_time,
                    session_start_time=session_start_timestamp,
                    current_lap=current_lap,
                    focused_driver=focused_driver,
                    pit_window_range=3
                )
                snapshot['leaderboard'] = leaderboard
            else:
                snapshot['leaderboard'] = {'error': 'No leaderboard data cached'}
        except Exception as e:
            logger.error(f"Error getting leaderboard summary: {e}")
            snapshot['leaderboard'] = {'error': str(e)}
        
        # Get weather summary
        try:
            from src.dashboards_dash.weather_dashboard import get_weather_summary
            weather = get_weather_summary(
                session_key=session_key,
                simulation_time=simulation_time,
                provider=openf1_provider
            )
            snapshot['weather'] = weather
        except Exception as e:
            logger.error(f"Error getting weather summary: {e}")
            snapshot['weather'] = {'error': str(e)}
        
        # Get race control status
        try:
            if race_control_dashboard._cached_messages is not None:
                status = race_control_dashboard.get_status_summary(
                    session_key=session_key,
                    simulation_time=simulation_time,
                    session_start_time=session_start_timestamp,
                    current_lap=current_lap
                )
                snapshot['race_control'] = status
            else:
                snapshot['race_control'] = {'error': 'No race control data cached'}
        except Exception as e:
            logger.error(f"Error getting race control summary: {e}")
            snapshot['race_control'] = {'error': str(e)}
        
        return snapshot
        
    except Exception as e:
        logger.error(f"Error generating race state snapshot: {e}")
        return {'error': str(e)}


def format_race_snapshot_for_ai(snapshot: dict) -> str:
    """
    Format race state snapshot as markdown for AI prompt.
    
    Args:
        snapshot: Race state snapshot dict from get_race_state_snapshot()
        
    Returns:
        Formatted markdown string for system prompt
    """
    if 'error' in snapshot:
        return f"⚠️ **No race data available**: {snapshot['error']}"
    
    lines = []
    
    # Check for Safety Car or VSC FIRST - this is critical info!
    race_control = snapshot.get('race_control', {})
    safety_car_active = race_control.get('safety_car', False)
    vsc_active = race_control.get('virtual_safety_car', False)
    flag = race_control.get('flag', 'GREEN')
    
    # PROMINENT SC/VSC WARNING AT THE TOP
    if safety_car_active or flag == 'SC':
        lines.append("## 🚨🚨🚨 SAFETY CAR DEPLOYED 🚨🚨🚨")
        lines.append("")
        lines.append("**⚠️ CRITICAL: The Safety Car is currently on track!**")
        lines.append("- **Pit window is OPEN** - Gap to cars behind is minimized")
        lines.append("- All drivers can pit with minimal time loss")
        lines.append("- Field is bunched up - positions will be closer on restart")
        lines.append("")
        lines.append("---")
        lines.append("")
    elif vsc_active or flag == 'VSC':
        lines.append("## 🟡🟡🟡 VIRTUAL SAFETY CAR ACTIVE 🟡🟡🟡")
        lines.append("")
        lines.append("**⚠️ VSC is deployed - speeds are reduced**")
        lines.append("- Pit stop time loss is reduced (~5-7 seconds)")
        lines.append("- Good opportunity to pit if strategy allows")
        lines.append("")
        lines.append("---")
        lines.append("")
    elif flag == 'RED':
        lines.append("## 🔴🔴🔴 RED FLAG 🔴🔴🔴")
        lines.append("")
        lines.append("**Race is stopped. All cars must return to pit lane.**")
        lines.append("")
        lines.append("---")
        lines.append("")
    
    lines.append("## 🏁 CURRENT RACE STATE")
    lines.append("")
    
    # Race info
    lines.append(
        f"**Race**: {snapshot.get('race_name', 'Unknown')} - "
        f"{snapshot.get('session_type', 'Race')}"
    )
    lines.append(f"**Lap**: {snapshot.get('lap', '?')}/{snapshot.get('total_laps', '?')}")
    lines.append("")
    
    # Leaderboard
    leaderboard = snapshot.get('leaderboard', {})
    if 'error' not in leaderboard:
        # Focus driver
        focus = leaderboard.get('focus_driver')
        if focus:
            lines.append(f"### 🎯 {focus['driver']} (P{focus['pos']})")
            lines.append(f"- **Gap to leader**: {focus['gap_to_leader']}")
            lines.append(f"- **Gap ahead**: {focus['gap_ahead']}")
            lines.append(f"- **Gap behind**: {focus['gap_behind']}")
            lines.append(f"- **Tire**: {focus['tire']} (Age: {focus['age']} laps)")
            lines.append(f"- **Pit stops**: {focus['stops']}")
            lines.append("")
        
        # Pit window drivers
        pit_window = leaderboard.get('pit_window', [])
        if pit_window:
            lines.append("### 🔧 Pit Window (nearby drivers)")
            lines.append("| Pos | Driver | Gap | Tire | Age | Stops |")
            lines.append("|-----|--------|-----|------|-----|-------|")
            for driver in pit_window:
                lines.append(
                    f"| P{driver['pos']} | {driver['driver']} | {driver['gap']} | "
                    f"{driver['tire']} | {driver['age']} | {driver['stops']} |"
                )
            lines.append("")
        
        # Top 10
        top_10 = leaderboard.get('top_10', [])
        if top_10 and not focus:  # Only show if no focus driver
            lines.append("### 🏆 Top 10")
            lines.append("| Pos | Driver | Gap | Tire | Age | Stops |")
            lines.append("|-----|--------|-----|------|-----|-------|")
            for driver in top_10[:5]:  # Only top 5
                lines.append(
                    f"| P{driver['pos']} | {driver['driver']} | {driver['gap']} | "
                    f"{driver['tire']} | {driver['age']} | {driver['stops']} |"
                )
            lines.append("")
    
    # Weather
    weather = snapshot.get('weather', {})
    if 'error' not in weather:
        lines.append("### 🌤️ Weather")
        lines.append(f"- **Air temp**: {weather.get('air_temp', '?')}°C")
        lines.append(f"- **Track temp**: {weather.get('track_temp', '?')}°C")
        lines.append(f"- **Wind**: {weather.get('wind_speed', '?')} km/h {weather.get('wind_direction', '')}")
        lines.append(f"- **Humidity**: {weather.get('humidity', '?')}%")
        if weather.get('rainfall'):
            lines.append(f"- **⚠️ RAINFALL DETECTED**")
        lines.append("")
    
    # Race control - show recent events (SC/VSC already shown at top)
    if 'error' not in race_control:
        recent_events = race_control.get('recent_events', [])
        if recent_events:
            lines.append("### 🚦 Recent Race Control Messages")
            for event in recent_events[:3]:
                lines.append(f"- {event}")
        lines.append("")
    
    return "\n".join(lines)


# ============================================================================
# PROACTIVE AI WARNINGS SYSTEM
# ============================================================================

# Global warning tracking to avoid spam
warning_tracker = {}


def analyze_race_state_for_warnings(
    snapshot: Dict[str, Any],
    session_data: Dict,
    focused_driver: str
) -> Optional[str]:
    """
    Analyze race state snapshot and generate proactive warnings using AI.
    
    Returns warning message if significant tactical situation detected,
    None otherwise.
    
    Checks for:
    - Undercut/overcut opportunities
    - Pit window entry/exit timing
    - Tire degradation issues
    - Safety car situations
    - Weather changes
    """
    if not snapshot:
        return None
    
    # Get current lap and driver info
    current_lap = snapshot.get('lap', 0)
    driver_code = focused_driver if focused_driver != 'none' else None
    
    if not driver_code or current_lap == 0:
        return None
    
    # Check if we've warned recently for this situation
    warning_key = f"{driver_code}_{current_lap // 3}"  # Group by 3-lap windows
    
    if warning_key in warning_tracker:
        last_warning_lap = warning_tracker[warning_key]
        if current_lap - last_warning_lap < 3:
            return None  # Don't spam warnings
    
    # Get AI-formatted snapshot
    race_context = format_race_snapshot_for_ai(snapshot)
    
    # Build prompt for tactical analysis
    analysis_prompt = (
        "You are an F1 race strategist monitoring the live race. "
        "Analyze this race state and determine if there are any "
        "CRITICAL tactical situations that require immediate attention.\n\n"
        f"Focus driver: {driver_code}\n\n"
        f"{race_context}\n\n"
        "Analyze for:\n"
        "- Undercut/overcut opportunities (cars within 3s with different tire ages)\n"
        "- Pit window timing (optimal laps to pit based on tire age and gaps)\n"
        "- Safety car/VSC situations (pit now or wait?)\n"
        "- Weather changes (tire strategy changes needed?)\n"
        "- Position battles (DRS trains, blue flags)\n\n"
        "ONLY respond if there is a CRITICAL situation requiring immediate action. "
        "If everything is normal or no urgent decisions needed, respond with: "
        "'NO_WARNING'\n\n"
        "If warning needed, respond with format:\n"
        "**WARNING:** [Brief title]\n"
        "[2-3 sentence explanation with specific numbers and recommendation]"
    )
    
    # Get LLM provider
    llm_provider = get_llm_provider()
    if not llm_provider:
        return None
    
    try:
        import asyncio
        
        async def get_warning():
            return await llm_provider.generate(
                prompt=analysis_prompt,
                system_prompt="You are an F1 race strategist providing tactical warnings."
            )
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            response: LLMResponse = loop.run_until_complete(get_warning())
        finally:
            loop.close()
        
        warning_text = response.content.strip()
        
        # Check if AI indicates no warning needed
        if 'NO_WARNING' in warning_text or len(warning_text) < 20:
            return None
        
        # Update warning tracker
        warning_tracker[warning_key] = current_lap
        
        # Clean old entries from tracker (keep last 20 laps)
        keys_to_remove = [
            k for k, v in warning_tracker.items()
            if current_lap - v > 20
        ]
        for k in keys_to_remove:
            del warning_tracker[k]
        
        return warning_text
    
    except Exception as e:
        logger.debug(f"AI warning generation failed: {e}")
        return None


# NOTE: check_proactive_ai_warnings callback DISABLED for Phase 1
# This uses LLM analysis which can block the UI. 
# Use rule-based check_proactive_alerts instead.
# Will be re-enabled in Phase 3 with async/background processing.
#
# @callback(
#     Output('chat-messages-store', 'data', allow_duplicate=True),
#     Input('proactive-check-interval', 'n_intervals'),
#     State('session-store', 'data'),
#     State('simulation-time-store', 'data'),
#     State('driver-selector', 'value'),
#     State('chat-messages-store', 'data'),
#     prevent_initial_call=True
# )
def check_proactive_ai_warnings_DISABLED(
    n_intervals,
    session_data,
    sim_time_data,
    focused_driver,
    existing_messages
):
    """
    DISABLED: Periodically check race state and generate AI-powered tactical warnings.
    
    Runs every 5 seconds (configured in proactive-check-interval).
    Only generates warnings for significant tactical situations.
    
    NOTE: This callback is disabled in Phase 1 because:
    1. LLM calls can take 2-5 seconds, blocking the UI
    2. It conflicts with check_proactive_alerts (same interval)
    3. Will be re-enabled with async processing in Phase 3
    """
    proactive_logger.debug("[PROACTIVE-LLM] Callback disabled in Phase 1")
    raise PreventUpdate
    
    # Original code preserved for Phase 3:
    if not session_data or not simulation_controller:
        raise PreventUpdate
    
    if not simulation_controller.is_playing:
        raise PreventUpdate
    
    try:
        # Get race state snapshot
        snapshot = get_race_state_snapshot(
            session_data=session_data,
            sim_time_data=sim_time_data,
            focused_driver=focused_driver
        )
        
        if not snapshot:
            raise PreventUpdate
        
        # Analyze for warnings
        warning = analyze_race_state_for_warnings(
            snapshot=snapshot,
            session_data=session_data,
            focused_driver=focused_driver
        )
        
        if not warning:
            raise PreventUpdate
        
        # Create warning message
        messages = existing_messages or []
        messages.append({
            'type': 'ai',
            'content': f"🚨 **TACTICAL ALERT**\n\n{warning}",
            'timestamp': datetime.now().isoformat(),
            'metadata': {
                'proactive': True,
                'lap': snapshot.get('lap', 0)
            }
        })
        
        return messages
        
    except Exception as e:
        proactive_logger.warning(f"[PROACTIVE-LLM] AI warning check failed: {e}")
        raise PreventUpdate


def generate_ai_response(
    query: str,
    session_data: Optional[Dict],
    focused_driver: Optional[str],
    sim_time_data: Optional[Dict],
    message_history: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Generate AI response using RAG + LLM.
    
    Process:
    1. Search RAG for relevant context documents
    2. Build context from RAG results  
    3. Send to LLM with context for intelligent response
    4. If no LLM available, return informative message
    """
    query_lower = query.lower()

    history_block = ""
    if message_history:
        trimmed_history = message_history[-8:]
        history_lines = []
        for msg in trimmed_history:
            role = str(msg.get('type', 'assistant')).lower()
            prefix = "User" if role == 'user' else "AI"
            content = str(msg.get('content', '')).strip()
            if len(content) > 280:
                content = f"{content[:277]}..."
            history_lines.append(f"- {prefix}: {content}")
        if history_lines:
            history_block = "Recent conversation:\n" + "\n".join(history_lines)
    
    # Get context info
    race_name = (
        session_data.get('race_name', 'the race') if session_data else 'the race'
    )
    driver = (
        focused_driver if focused_driver and focused_driver != 'none'
        else 'a driver'
    )
    year = session_data.get('year', 2024) if session_data else 2024
    
    # Get current lap (available whether playing or paused)
    current_lap = None
    if simulation_controller:
        openf1_lap = simulation_controller.get_current_lap()
        current_lap = openf1_lap if openf1_lap and openf1_lap > 0 else 1
    
    if current_lap:
        lap_info = "Lap 1 (untimed)" if current_lap == 1 else f"Lap {current_lap}"
    else:
        lap_info = "Pre-race"
    
    # Search RAG for context
    rag_manager = get_rag_manager()
    rag_context = ""
    rag_sources = []
    
    if rag_manager.is_context_loaded():
        # Determine category based on query
        category = None
        if any(w in query_lower for w in ['pit', 'tire', 'tyre', 'stop', 'strategy']):
            category = 'strategy'
        elif any(w in query_lower for w in ['weather', 'rain', 'wet', 'dry']):
            category = 'weather'
        elif any(w in query_lower for w in ['fia', 'rule', 'regulation', 'penalty']):
            category = 'fia'
        
        # Search RAG
        rag_results = rag_manager.search(query=query, k=5, category=category)
        
        if rag_results:
            context_parts = []
            for result in rag_results:
                source = result.get('metadata', {}).get('source', 'unknown')
                content = result.get('content', '')
                if content:
                    context_parts.append(content)
                    rag_sources.append(source)
            rag_context = "\n\n".join(context_parts)
    
    # Get live race state snapshot
    race_context = ""
    if simulation_controller and session_data and sim_time_data:
        try:
            snapshot = get_race_state_snapshot(
                session_data=session_data,
                sim_time_data=sim_time_data,
                focused_driver=focused_driver
            )
            
            if snapshot and 'error' not in snapshot:
                race_context = format_race_snapshot_for_ai(snapshot)
            else:
                logger.warning(f"No valid snapshot - error: {snapshot.get('error') if snapshot else 'None'}")
        except Exception as e:
            logger.error(f"Failed to get race snapshot: {e}")
            race_context = ""
    
    # Get LLM provider
    llm_provider = get_llm_provider()
    
    if llm_provider is not None:
        # Build system prompt for F1 strategy expert with specific guidance
        base_prompt = (
            f"You are an expert F1 race strategist. Session: {race_name} ({year}), {lap_info}. "
            f"Focused on driver: {driver}.\n\n"
            "Guidelines:\n"
            "- Provide SPECIFIC strategic recommendations (pit stops, tire strategy, overtaking)\n"
            "- Use real numbers from the live data (tire age, lap times, gaps)\n"
            "- Be concise but COMPLETE (3-5 sentences for complex questions)\n"
            "- For pit stop questions: analyze tire wear, lap delta, and track position\n"
            "- Always reference the current race situation in your answer"
        )
        
        # Add live race state if available
        if race_context:
            system_prompt = (
                f"{base_prompt}\n\n"
                f"## CURRENT RACE STATE\n{race_context}\n\n"
                f"Use this live data to provide tactical advice. Be specific and data-driven."
            )
        else:
            system_prompt = base_prompt + "\n\nNote: Limited live data available. Use general F1 strategy knowledge."
        
        # Build concise user prompt
        prompt_sections: list[str] = []
        if history_block:
            prompt_sections.append(history_block)
        if rag_context:
            prompt_sections.append(f"Context:\n{rag_context}")
            prompt_sections.append(
                f"Q: {query}\n\n"
                f"Give a brief, specific answer using the context."
            )
        else:
            prompt_sections.append(
                f"Q: {query}\n\nAnswer briefly with available general F1 knowledge."
            )
        user_prompt = "\n\n".join(prompt_sections)
        
        try:
            # Call LLM asynchronously
            import asyncio
            
            async def get_llm_response():
                return await llm_provider.generate(
                    prompt=user_prompt,
                    system_prompt=system_prompt
                )
            
            # Run async function
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                llm_response: LLMResponse = loop.run_until_complete(
                    get_llm_response()
                )
            finally:
                loop.close()
            
            # Format response with provider prefix
            response_content = llm_response.content
            
            # Add provider prefix (Claude: or Gemi:)
            provider_name = llm_response.provider.lower() if llm_response.provider else ''
            if 'claude' in provider_name or 'anthropic' in provider_name:
                provider_prefix = "**Claude:** "
            elif 'gemini' in provider_name or 'google' in provider_name:
                provider_prefix = "**Gemi:** "
            else:
                provider_prefix = ""
            
            response_content = provider_prefix + response_content
            
            # Add source attribution if RAG was used
            if rag_sources:
                unique_sources = list(set(rag_sources))
                source_text = ", ".join(unique_sources[:3])
                response_content += (
                    f"\n\n---\n"
                    f"_📚 Sources: {source_text}_"
                )
            
            return {
                'content': response_content,
                'metadata': {
                    'confidence': 0.9,
                    'agents_used': ['LLM', 'RAG'] if rag_context else ['LLM'],
                    'llm_provider': llm_response.provider,
                    'llm_model': llm_response.model,
                    'tokens_used': llm_response.total_tokens,
                    'rag_sources': len(rag_sources)
                }
            }
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            # Fall through to no-LLM response
    
    # No LLM available - show clear error
    return {
        'content': (
            f"❌ **API Key Required**\n\n"
            f"The AI Assistant needs at least one LLM API key to respond.\n\n"
            f"**Configure in sidebar → ⚙️ Configuration:**\n"
            f"• **Claude** (Anthropic): `ANTHROPIC_API_KEY`\n"
            f"• **Gemini** (Google): `GOOGLE_API_KEY`\n\n"
            f"After entering your key, click **'💾 Save Keys'**.\n\n"
            f"---\n"
            f"_Your question: \"{query}\"_"
        ),
        'metadata': {
            'confidence': 0.0,
            'agents_used': [],
            'error': 'No LLM API key configured'
        }
    }


# ============================================================================
# TELEMETRY COMPARISON DRIVER CALLBACK
# ============================================================================

@callback(
    Output('telemetry-comparison-store', 'data'),
    Input('telemetry-comparison-driver', 'value'),
    prevent_initial_call=True
)
def update_telemetry_comparison(comparison_driver):
    """Update the comparison driver for telemetry dashboard."""
    telem_logger.debug(f"Telemetry comparison driver: {comparison_driver}")
    return {'driver': comparison_driver}


if __name__ == '__main__':
    logger.info("="*60)
    logger.info("F1 STRATEGIST AI - DASH VERSION")
    logger.info("="*60)
    logger.info("Starting application...")
    logger.info("Open: http://localhost:8501")
    logger.info("="*60)

    # Initialize session with last completed race (dynamic from OpenF1)
    last_race = get_last_completed_race_context()
    session.race_context = last_race
    logger.info(
        f"Initialized with {last_race.country} GP "
        f"(Round {last_race.round_number}, {last_race.year})"
    )

    # debug=False to ensure logs appear in terminal
    app.run(debug=False, port=8501)
