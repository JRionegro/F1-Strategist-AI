"""Utility to load LLM configuration from environment."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from .models import LLMConfig

# Load environment variables from config/ directory
config_dir = Path(__file__).parent.parent.parent / "config"
load_dotenv(config_dir / ".env")


def get_claude_config() -> LLMConfig:
    """
    Load Claude configuration from environment.

    Required env vars:
    - ANTHROPIC_API_KEY

    Optional:
    - CLAUDE_MODEL
    - CLAUDE_MAX_TOKENS
    - CLAUDE_TEMPERATURE

    Returns:
        LLMConfig for Claude

    Raises:
        ValueError: If ANTHROPIC_API_KEY not set
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY not set in environment. "
            "Get key from: https://console.anthropic.com/"
        )

    return LLMConfig(
        model_name=os.getenv(
            "CLAUDE_MODEL",
            "claude-3-5-sonnet-20241022"
        ),
        api_key=api_key,
        max_tokens=int(os.getenv("CLAUDE_MAX_TOKENS", "4096")),
        temperature=float(os.getenv("CLAUDE_TEMPERATURE", "0.7")),
        timeout=int(os.getenv("CLAUDE_TIMEOUT", "30")),
        max_retries=int(os.getenv("CLAUDE_MAX_RETRIES", "3"))
    )


def get_gemini_config() -> LLMConfig:
    """
    Load Gemini configuration from environment.

    Required env vars:
    - GOOGLE_API_KEY

    Optional:
    - GEMINI_MODEL
    - GEMINI_MAX_TOKENS
    - GEMINI_TEMPERATURE
    - GEMINI_ENABLE_THINKING

    Returns:
        LLMConfig for Gemini

    Raises:
        ValueError: If GOOGLE_API_KEY not set
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY not set in environment. "
            "Get key from: https://makersuite.google.com/app/apikey"
        )

    return LLMConfig(
        model_name=os.getenv(
            "GEMINI_MODEL",
            "gemini-2.0-flash-thinking-exp-1219"
        ),
        api_key=api_key,
        max_tokens=int(os.getenv("GEMINI_MAX_TOKENS", "8192")),
        temperature=float(os.getenv("GEMINI_TEMPERATURE", "0.7")),
        timeout=int(os.getenv("GEMINI_TIMEOUT", "30")),
        max_retries=int(os.getenv("GEMINI_MAX_RETRIES", "3")),
        extra_params={
            "enable_thinking": os.getenv(
                "GEMINI_ENABLE_THINKING",
                "true"
            ).lower() == "true"
        }
    )


def get_hybrid_router_config() -> dict:
    """
    Load hybrid router configuration.

    Optional env vars:
    - COMPLEXITY_THRESHOLD_LOW (default: 0.4)
    - COMPLEXITY_THRESHOLD_HIGH (default: 0.7)

    Returns:
        Dict with threshold configuration
    """
    return {
        "complexity_threshold_low": float(
            os.getenv("COMPLEXITY_THRESHOLD_LOW", "0.4")
        ),
        "complexity_threshold_high": float(
            os.getenv("COMPLEXITY_THRESHOLD_HIGH", "0.7")
        )
    }
