"""Utility to load LLM configuration from environment."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from .models import LLMConfig

# Centralized environment file lives in config/.env
config_dir = Path(__file__).parent.parent.parent / "config"
load_dotenv(config_dir / ".env", override=True)


def get_claude_config(model_override: Optional[str] = None) -> LLMConfig:
    """
    Load Claude configuration from environment.

    Required env vars:
    - ANTHROPIC_API_KEY

    Optional:
    - CLAUDE_MODEL (default: claude-3-5-sonnet-20241022)
      Available models:
        - claude-3-opus-20240229 (most capable)
        - claude-3-5-sonnet-20241022 (balanced)
        - claude-3-haiku-20240307 (fast & cheap)
    - CLAUDE_MAX_TOKENS
    - CLAUDE_TEMPERATURE

    Args:
        model_override: Optional model name to override env/default

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

    model_name = (
        model_override or
        os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
    )

    return LLMConfig(
        model_name=model_name,
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
        model_name=os.getenv("GEMINI_MODEL") or "",  # set GEMINI_MODEL in .env
        api_key=api_key,
        max_tokens=int(os.getenv("GEMINI_MAX_TOKENS", "8192")),
        temperature=float(os.getenv("GEMINI_TEMPERATURE", "0.7")),
        timeout=int(os.getenv("GEMINI_TIMEOUT", "30")),
        max_retries=int(os.getenv("GEMINI_MAX_RETRIES", "3")),
        extra_params={
            "enable_thinking": os.getenv(
                "GEMINI_ENABLE_THINKING",
                "false"
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


def get_claude_opus_config() -> LLMConfig:
    """
    Get Claude Opus configuration specifically.

    Claude Opus is the most capable model, best for:
    - Complex strategic analysis
    - Multi-step reasoning
    - High-stakes decision making

    Cost: $15/$75 per 1M tokens (5x more than Sonnet)

    Returns:
        LLMConfig configured for Claude Opus
    """
    return get_claude_config(model_override="claude-3-opus-20240229")


def get_litellm_config() -> LLMConfig:
    """
    Load LiteLLM configuration from environment.

    Optional env vars:
    - LITELLM_API_KEY  (omit or leave empty for local proxy / Ollama)
    - LITELLM_MODEL    (default: gpt-4o-mini)
    - LITELLM_BASE_URL (proxy URL, e.g. http://localhost:4000)
    - LITELLM_MAX_TOKENS
    - LITELLM_TEMPERATURE

    Returns:
        LLMConfig for LiteLLM
    """
    api_key = os.getenv("LITELLM_API_KEY", "").strip()

    return LLMConfig(
        model_name=os.getenv("LITELLM_MODEL") or "",  # set LITELLM_MODEL in .env
        api_key=api_key,
        max_tokens=int(os.getenv("LITELLM_MAX_TOKENS", "2048")),
        temperature=float(os.getenv("LITELLM_TEMPERATURE", "0.7")),
        timeout=int(os.getenv("LITELLM_TIMEOUT", "60")),
        max_retries=int(os.getenv("LITELLM_MAX_RETRIES", "3")),
        extra_params={
            "base_url": os.getenv("LITELLM_BASE_URL", "").strip() or None
        },
    )
