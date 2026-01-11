"""
Centralized logging configuration for F1 Strategist AI.

This module provides categorized loggers that can be enabled/disabled
independently for debugging specific features without flooding the console.

Categories:
- STARTUP: Application initialization and loading (always enabled)
- SIMULATION: Simulation controller, time updates, lap tracking
- DASHBOARD: Dashboard rendering and updates
- TELEMETRY: Car telemetry data and DRS
- RACE_OVERVIEW: Race overview dashboard, positions, intervals
- RACE_CONTROL: Race control messages, flags, penalties
- WEATHER: Weather data and forecasts
- RAG: Document loading, embeddings, vector store
- API: External API calls (OpenF1, etc.)
- CHAT: AI chat and LLM interactions

Usage:
    from src.utils.logging_config import get_logger, LogCategory, set_category_level

    # Get a categorized logger
    logger = get_logger(LogCategory.TELEMETRY)
    logger.info("DRS zone detected")  # Only logs if TELEMETRY is enabled

    # Enable/disable categories at runtime
    set_category_level(LogCategory.TELEMETRY, logging.DEBUG)
    set_category_level(LogCategory.SIMULATION, logging.WARNING)  # Disable INFO
"""

import logging
from enum import Enum
from typing import Dict, Optional


class LogCategory(Enum):
    """Log categories for different app components."""
    STARTUP = "f1.startup"           # App init - always visible
    SIMULATION = "f1.simulation"     # Simulation timing/laps
    DASHBOARD = "f1.dashboard"       # Dashboard rendering
    TELEMETRY = "f1.telemetry"       # Car telemetry, DRS
    RACE_OVERVIEW = "f1.race_overview"  # Leaderboard, positions
    RACE_CONTROL = "f1.race_control"    # Flags, penalties
    WEATHER = "f1.weather"           # Weather data
    RAG = "f1.rag"                   # RAG/embeddings
    API = "f1.api"                   # External API calls
    CHAT = "f1.chat"                 # AI chat/LLM
    DATA = "f1.data"                 # Data providers


# Default log levels per category
# INFO = show messages, WARNING = hide INFO messages
DEFAULT_LEVELS: Dict[LogCategory, int] = {
    LogCategory.STARTUP: logging.INFO,       # Always show startup
    LogCategory.SIMULATION: logging.WARNING,  # Hide frequent updates
    LogCategory.DASHBOARD: logging.WARNING,   # Hide render messages
    LogCategory.TELEMETRY: logging.WARNING,   # Hide telemetry spam
    LogCategory.RACE_OVERVIEW: logging.WARNING,  # Hide overview updates
    LogCategory.RACE_CONTROL: logging.WARNING,   # Hide control messages
    LogCategory.WEATHER: logging.WARNING,     # Hide weather updates
    LogCategory.RAG: logging.INFO,            # Show RAG loading
    LogCategory.API: logging.WARNING,         # Hide API calls
    LogCategory.CHAT: logging.INFO,           # Show chat activity
    LogCategory.DATA: logging.WARNING,        # Hide data loading
}

# Store for category loggers
_category_loggers: Dict[LogCategory, logging.Logger] = {}


def setup_logging(
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
    log_file: Optional[str] = None
) -> None:
    """
    Initialize the logging system with categorized loggers.

    Args:
        console_level: Base level for console output
        file_level: Base level for file output (if log_file provided)
        log_file: Optional path to log file
    """
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture everything

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler with custom format
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)

    # Optional file handler
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(file_level)
        file_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_format)
        root_logger.addHandler(file_handler)

    # Initialize category loggers with default levels
    for category in LogCategory:
        logger = logging.getLogger(category.value)
        logger.setLevel(DEFAULT_LEVELS.get(category, logging.INFO))
        _category_loggers[category] = logger

    # Quiet down noisy third-party libraries
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('chromadb').setLevel(logging.WARNING)
    logging.getLogger('sentence_transformers').setLevel(logging.WARNING)
    logging.getLogger('dash').setLevel(logging.WARNING)  # Quiet Dash startup msg
    logging.getLogger('dash.dash').setLevel(logging.WARNING)

    # Log startup message
    startup_logger = get_logger(LogCategory.STARTUP)
    startup_logger.info("=" * 60)
    startup_logger.info("F1 Strategist AI - Logging initialized")
    startup_logger.info("=" * 60)


def get_logger(category: LogCategory) -> logging.Logger:
    """
    Get a logger for a specific category.

    Args:
        category: The log category

    Returns:
        A configured logger for the category
    """
    if category not in _category_loggers:
        logger = logging.getLogger(category.value)
        logger.setLevel(DEFAULT_LEVELS.get(category, logging.INFO))
        _category_loggers[category] = logger
    return _category_loggers[category]


def set_category_level(category: LogCategory, level: int) -> None:
    """
    Set the log level for a specific category.

    Args:
        category: The log category to configure
        level: The logging level (logging.DEBUG, INFO, WARNING, etc.)
    """
    logger = get_logger(category)
    logger.setLevel(level)

    startup_logger = get_logger(LogCategory.STARTUP)
    level_name = logging.getLevelName(level)
    startup_logger.info(f"Log level for {category.value}: {level_name}")


def enable_category(category: LogCategory) -> None:
    """Enable INFO level logging for a category."""
    set_category_level(category, logging.DEBUG)


def disable_category(category: LogCategory) -> None:
    """Disable INFO level logging for a category (only WARNING+)."""
    set_category_level(category, logging.WARNING)


def enable_all_categories() -> None:
    """Enable INFO logging for all categories (verbose mode)."""
    for category in LogCategory:
        set_category_level(category, logging.INFO)


def disable_all_categories() -> None:
    """Disable INFO logging for all categories (quiet mode)."""
    for category in LogCategory:
        if category != LogCategory.STARTUP:  # Keep startup visible
            set_category_level(category, logging.WARNING)


def get_category_status() -> Dict[str, str]:
    """
    Get the current status of all log categories.

    Returns:
        Dictionary of category names to their current level names
    """
    status = {}
    for category in LogCategory:
        logger = get_logger(category)
        status[category.value] = logging.getLevelName(logger.level)
    return status


# Convenience function to enable specific debugging
def enable_debug_mode(categories: list[LogCategory]) -> None:
    """
    Enable DEBUG level for specific categories.

    Args:
        categories: List of categories to enable DEBUG for
    """
    for cat in categories:
        set_category_level(cat, logging.DEBUG)


# Pre-defined debug profiles
DEBUG_PROFILES = {
    'telemetry': [LogCategory.TELEMETRY, LogCategory.API],
    'simulation': [LogCategory.SIMULATION, LogCategory.DASHBOARD],
    'race': [LogCategory.RACE_OVERVIEW, LogCategory.RACE_CONTROL],
    'rag': [LogCategory.RAG, LogCategory.CHAT],
    'all': list(LogCategory),
}


def apply_debug_profile(profile_name: str) -> None:
    """
    Apply a pre-defined debug profile.

    Args:
        profile_name: One of 'telemetry', 'simulation', 'race', 'rag', 'all'
    """
    if profile_name not in DEBUG_PROFILES:
        startup_logger = get_logger(LogCategory.STARTUP)
        startup_logger.warning(
            f"Unknown debug profile: {profile_name}. "
            f"Available: {list(DEBUG_PROFILES.keys())}"
        )
        return

    # First disable all (except STARTUP)
    disable_all_categories()

    # Then enable the profile categories
    for category in DEBUG_PROFILES[profile_name]:
        enable_category(category)

    startup_logger = get_logger(LogCategory.STARTUP)
    startup_logger.info(f"Debug profile applied: {profile_name}")
