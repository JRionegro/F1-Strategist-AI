"""LiteLLM provider implementation — unified gateway to any LLM backend."""

import asyncio
import logging
import time
from typing import Any, Dict, Optional

from .models import LLMConfig, LLMResponse
from .provider import LLMProvider

logger = logging.getLogger(__name__)


class LiteLLMProvider(LLMProvider):
    """
    LiteLLM provider: a single interface for 100+ LLM backends
    (OpenAI, Mistral, Ollama, local proxies, etc.).

    Required env vars:
    - LITELLM_MODEL   e.g. "gpt-4o-mini", "ollama/llama3", "openai/gpt-4"
    - LITELLM_API_KEY (optional when using a local proxy or Ollama)
    - LITELLM_BASE_URL (optional proxy URL, e.g. http://localhost:4000)

    Nickname in chat responses: **Chico**
    """

    COST_PER_1M_INPUT = 0.0   # Varies by backend; billed externally.
    COST_PER_1M_OUTPUT = 0.0

    # ------------------------------------------------------------------ #
    # Initialisation                                                       #
    # ------------------------------------------------------------------ #

    def __init__(self, config: LLMConfig):
        """Initialise LiteLLM provider."""
        # Skip base-class api_key validation — proxy mode needs no key.
        self.config = config
        if config.max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        if not 0 <= config.temperature <= 2:
            raise ValueError("temperature must be between 0 and 2")

        try:
            import litellm as _litellm  # type: ignore[import-untyped]
            self._litellm = _litellm
        except ImportError as exc:
            raise ImportError(
                "litellm is not installed. "
                "Add it with: pip install litellm"
            ) from exc

        self.model = config.model_name or "gpt-4o-mini"
        raw_url: Optional[str] = config.extra_params.get("base_url")

        # Enforce https — Inditex WAF blocks plain http
        if raw_url and raw_url.startswith("http://"):
            raw_url = "https://" + raw_url[len("http://"):]
        self._base_url: Optional[str] = raw_url or None

        # Suppress verbose litellm logging
        self._litellm.suppress_debug_info = True
        logging.getLogger("LiteLLM").setLevel(logging.WARNING)

        logger.info(
            "Initialized LiteLLMProvider — model: %s, base_url: %s, "
            "api_key_set: %s",
            self.model,
            self._base_url or "(default)",
            bool(config.api_key),
        )

    # ------------------------------------------------------------------ #
    # LLMProvider abstract interface                                       #
    # ------------------------------------------------------------------ #

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Generate a completion via LiteLLM.

        Args:
            prompt: User prompt.
            system_prompt: Optional system instructions.
            **kwargs: Extra params forwarded to litellm.acompletion
                      (e.g. temperature, max_tokens).

        Returns:
            LLMResponse with the model reply.

        Raises:
            RuntimeError: If all retry attempts fail.
        """
        start_time = time.time()

        messages: list[dict] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        call_kwargs: dict = {
            "model": self.model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get(
                "temperature", self.config.temperature
            ),
            "timeout": self.config.timeout,
        }
        if self._base_url:
            call_kwargs["base_url"] = self._base_url
        # Always pass api_key so LiteLLM builds the Authorization header.
        # Passing None lets LiteLLM fall back to env-var auto-detection.
        call_kwargs["api_key"] = self.config.api_key or None

        for attempt in range(self.config.max_retries):
            try:
                response = await self._litellm.acompletion(**call_kwargs)

                resp: Any = response
                latency_ms = (time.time() - start_time) * 1000
                choices = resp.choices or []
                content = (
                    choices[0].message.content or ""
                    if choices else ""
                )
                usage = resp.usage
                tokens_in = getattr(usage, "prompt_tokens", 0)
                tokens_out = getattr(usage, "completion_tokens", 0)

                logger.info(
                    "LiteLLM response: %d in / %d out — %.0f ms",
                    tokens_in,
                    tokens_out,
                    latency_ms,
                )

                return LLMResponse(
                    content=content,
                    model=getattr(response, "model", None) or self.model,
                    provider="litellm",
                    tokens_input=tokens_in,
                    tokens_output=tokens_out,
                    cost_input=0.0,
                    cost_output=0.0,
                    latency_ms=latency_ms,
                    metadata={"attempt": attempt + 1},
                )

            except Exception as exc:
                logger.warning(
                    "LiteLLM attempt %d/%d failed: %s",
                    attempt + 1,
                    self.config.max_retries,
                    exc,
                )
                if attempt == self.config.max_retries - 1:
                    raise RuntimeError(
                        f"LiteLLM generation failed after "
                        f"{self.config.max_retries} attempts: {exc}"
                    ) from exc
                await asyncio.sleep(2 ** attempt)

        raise RuntimeError("LiteLLM generation failed unexpectedly")

    async def generate_with_thinking(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        """
        Generate with step-by-step reasoning (simulated).

        LiteLLM backends vary in thinking support; we simulate it
        by prepending reasoning instructions.
        """
        thinking_system = (
            "Think step-by-step before answering. "
            "Show your reasoning process explicitly."
        )
        if system_prompt:
            thinking_system = f"{system_prompt}\n\n{thinking_system}"

        enhanced_prompt = (
            f"{prompt}\n\n"
            "Please think through this step-by-step."
        )
        return await self.generate(
            enhanced_prompt, system_prompt=thinking_system
        )

    def estimate_complexity(self, prompt: str) -> float:
        """
        Estimate prompt complexity for routing (0.0 simple → 1.0 complex).

        Mirrors the heuristic used by ClaudeProvider.
        """
        score = 0.0
        if len(prompt) > 1000:
            score += 0.2
        elif len(prompt) > 500:
            score += 0.1

        strategic_keywords = [
            "strategy", "analyze", "compare", "optimize", "evaluate",
            "recommend", "complex", "multi-step", "considering",
        ]
        score += min(
            sum(1 for kw in strategic_keywords if kw in prompt.lower()) * 0.1,
            0.3,
        )

        if any(ind in prompt.lower() for ind in ["first", "then", "finally"]):
            score += 0.2
        if prompt.count("?") > 1:
            score += 0.1

        return min(score, 1.0)

    def get_cost_estimate(
        self,
        tokens_input: int,
        tokens_output: int,
    ) -> Dict[str, float]:
        """Return zero-cost estimates (billing handled externally)."""
        return {"input_cost": 0.0, "output_cost": 0.0, "total_cost": 0.0}

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _validate_config(self) -> None:
        """Override base validation — api_key is optional for proxy mode."""
        if self.config.max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        if not 0 <= self.config.temperature <= 2:
            raise ValueError("temperature must be between 0 and 2")
