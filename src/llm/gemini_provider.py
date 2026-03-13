"""Gemini 2.0 Flash Thinking provider implementation."""

import asyncio
import logging
import re
import time
from typing import Dict, Optional

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    genai = None  # type: ignore
    types = None  # type: ignore
    GENAI_AVAILABLE = False

from .models import LLMConfig, LLMResponse
from .provider import LLMProvider

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """
    Gemini 2.0 Flash Thinking provider for simple/moderate queries.

    Cost: $0.01875/1M input, $0.075/1M output (thinking mode)
    Context: 1M tokens
    Best for: Fast responses, simple queries, cost-sensitive operations
    """

    # Pricing per million tokens (USD)
    COST_PER_1M_INPUT = 0.01875
    COST_PER_1M_OUTPUT = 0.075

    def __init__(self, config: LLMConfig):
        """Initialize Gemini provider with Google AI client."""
        super().__init__(config)
        if not GENAI_AVAILABLE or genai is None or types is None:
            raise ImportError(
                "google-genai not installed. "
                "Install with: pip install google-genai"
            )

        self.client = genai.Client(api_key=config.api_key)
        self.model_name = (
            config.model_name or "gemini-2.0-flash-exp"
        )
        self.enable_thinking = config.extra_params.get(
            "enable_thinking",
            True
        )
        logger.info(
            f"Initialized GeminiProvider with model: {self.model_name}, "
            f"thinking={self.enable_thinking}"
        )

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate completion using Gemini (normal mode).

        Args:
            prompt: User prompt
            system_prompt: Optional system instructions
            **kwargs: Additional parameters

        Returns:
            LLMResponse with completion

        Raises:
            RuntimeError: If API call fails after retries
        """
        start_time = time.time()

        # Build full prompt with system instructions
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        for attempt in range(self.config.max_retries):
            try:
                # Generate content using new API
                if types is None:
                    raise RuntimeError("types module not available")

                config = types.GenerateContentConfig(
                    temperature=kwargs.get(
                        "temperature",
                        self.config.temperature
                    ),
                    max_output_tokens=kwargs.get(
                        "max_tokens",
                        self.config.max_tokens
                    ),
                )

                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model_name,
                    contents=full_prompt,
                    config=config
                )

                latency_ms = (time.time() - start_time) * 1000

                # Extract content
                content = response.text or ""

                # Token counting (approximate)
                tokens_input = self._count_tokens(full_prompt)
                tokens_output = self._count_tokens(content)

                costs = self.get_cost_estimate(tokens_input, tokens_output)

                logger.info(
                    f"Gemini response: {tokens_input} in, "
                    f"{tokens_output} out, "
                    f"${costs['total_cost']:.4f}, {latency_ms:.0f}ms"
                )

                return LLMResponse(
                    content=content,
                    model=self.model_name,
                    provider="gemini",
                    tokens_input=tokens_input,
                    tokens_output=tokens_output,
                    cost_input=costs["input_cost"],
                    cost_output=costs["output_cost"],
                    latency_ms=latency_ms,
                    metadata={
                        "finish_reason": (
                            str(response.candidates[0].finish_reason)
                            if response.candidates
                            else "unknown"
                        ),
                        "attempt": attempt + 1,
                        "thinking_mode": False
                    }
                )

            except Exception as e:
                logger.warning(
                    f"Gemini attempt {attempt + 1}/"
                    f"{self.config.max_retries} failed: {e}"
                )
                if attempt == self.config.max_retries - 1:
                    raise RuntimeError(
                        f"Gemini generation failed after "
                        f"{self.config.max_retries} attempts: {e}"
                    )
                await asyncio.sleep(2 ** attempt)

        raise RuntimeError("Gemini generation failed unexpectedly")

    async def generate_with_thinking(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> LLMResponse:
        """
        Generate with native thinking mode.

        Gemini 2.0 Flash Thinking has built-in reasoning mode
        that shows step-by-step thinking process.

        Args:
            prompt: User prompt
            system_prompt: Optional system instructions

        Returns:
            LLMResponse with thinking process extracted
        """
        if not self.enable_thinking:
            logger.warning(
                "Thinking mode disabled, falling back to normal mode"
            )
            return await self.generate(prompt, system_prompt)

        # Use thinking mode prompt structure
        thinking_prompt = (
            f"{prompt}\n\n"
            "Think through this step-by-step and explain your reasoning."
        )

        if system_prompt:
            thinking_prompt = f"{system_prompt}\n\n{thinking_prompt}"

        response = await self.generate(thinking_prompt, system_prompt=None)

        # Extract thinking process from response
        thinking_process = self._extract_thinking(response.content)

        if thinking_process:
            response.thinking_process = thinking_process
            response.metadata["thinking_mode"] = True
            logger.debug(f"Extracted thinking: {thinking_process[:100]}...")

        return response

    def _extract_thinking(self, content: str) -> Optional[str]:
        """
        Extract thinking blocks from Gemini response.

        Gemini thinking mode typically outputs reasoning before answer.
        Pattern: <thinking>...</thinking> or explicit step markers.

        Args:
            content: Full response content

        Returns:
            Thinking process or None
        """
        # Try to find explicit thinking tags
        thinking_match = re.search(
            r"<thinking>(.*?)</thinking>",
            content,
            re.DOTALL
        )
        if thinking_match:
            return thinking_match.group(1).strip()

        # Try to find step-by-step reasoning (first paragraph)
        lines = content.split("\n\n")
        if len(lines) > 1:
            first_para = lines[0]
            if any(
                kw in first_para.lower()
                for kw in ["step", "first", "let's think", "reasoning"]
            ):
                return first_para

        return None

    def _count_tokens(self, text: str) -> int:
        """
        Approximate token count.

        Gemini tokenizer not directly accessible, use approximation:
        ~4 characters per token for English text.

        Args:
            text: Text to count

        Returns:
            Approximate token count
        """
        return max(1, len(text) // 4)

    def estimate_complexity(self, prompt: str) -> float:
        """
        Estimate query complexity.

        Gemini is good for simple/moderate queries.
        Use lower scores to route more traffic here.

        Returns:
            Score 0.0-1.0
        """
        score = 0.0

        # Length factor (Gemini handles longer context well)
        if len(prompt) > 2000:
            score += 0.15
        elif len(prompt) > 1000:
            score += 0.1

        # Complex keywords
        complex_keywords = [
            "complex", "intricate", "sophisticated", "comprehensive"
        ]
        if any(kw in prompt.lower() for kw in complex_keywords):
            score += 0.2

        # Strategic analysis (better for Claude)
        strategic_keywords = ["strategy", "optimize", "analyze deeply"]
        strategic_count = sum(
            1 for kw in strategic_keywords if kw in prompt.lower()
        )
        score += min(strategic_count * 0.15, 0.3)

        return min(score, 1.0)

    def get_cost_estimate(
        self,
        tokens_input: int,
        tokens_output: int
    ) -> Dict[str, float]:
        """
        Calculate cost for token usage.

        Args:
            tokens_input: Input tokens
            tokens_output: Output tokens

        Returns:
            Dict with cost breakdown
        """
        input_cost = (tokens_input / 1_000_000) * self.COST_PER_1M_INPUT
        output_cost = (tokens_output / 1_000_000) * self.COST_PER_1M_OUTPUT

        return {
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": input_cost + output_cost
        }
