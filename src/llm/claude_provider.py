"""Claude 3.5 Sonnet provider implementation."""

import asyncio
import logging
import time
from typing import Dict, Optional

from anthropic import AsyncAnthropic
from anthropic.types import MessageParam, TextBlock

from .models import LLMConfig, LLMResponse
from .provider import LLMProvider

logger = logging.getLogger(__name__)


class ClaudeProvider(LLMProvider):
    """
    Claude provider supporting multiple models (Opus, Sonnet, Haiku).

    Models:
    - claude-3-opus-20240229: Most capable, $15/$75 per 1M tokens
    - claude-3-5-sonnet-20241022: Balanced, $3/$15 per 1M tokens
    - claude-3-haiku-20240307: Fast & cheap, $0.25/$1.25 per 1M tokens

    Context: 200K tokens (Opus/Sonnet), 128K tokens (Haiku)
    Best for: Complex reasoning, strategic analysis, code generation
    """

    # Pricing per million tokens (USD) by model
    MODEL_PRICING = {
        "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
        "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
        "claude-3-5-sonnet-20240620": {"input": 3.00, "output": 15.00},
        "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
    }
    
    # Default pricing (fallback)
    COST_PER_1M_INPUT = 3.00
    COST_PER_1M_OUTPUT = 15.00

    def __init__(self, config: LLMConfig):
        """Initialize Claude provider with Anthropic client."""
        super().__init__(config)
        self.client = AsyncAnthropic(api_key=config.api_key)
        self.model = config.model_name or "claude-3-5-sonnet-20241022"
        
        # Validate model and set pricing
        if self.model not in self.MODEL_PRICING:
            logger.warning(
                f"Unknown Claude model: {self.model}. "
                "Using Sonnet 3.5 pricing as fallback."
            )
            self.COST_PER_1M_INPUT = 3.00
            self.COST_PER_1M_OUTPUT = 15.00
        else:
            pricing = self.MODEL_PRICING[self.model]
            self.COST_PER_1M_INPUT = pricing["input"]
            self.COST_PER_1M_OUTPUT = pricing["output"]
        
        logger.info(
            f"Initialized ClaudeProvider with model: {self.model} "
            f"(${self.COST_PER_1M_INPUT}/${self.COST_PER_1M_OUTPUT} "
            "per 1M tokens)"
        )

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate completion using Claude.

        Args:
            prompt: User prompt
            system_prompt: Optional system instructions
            **kwargs: Additional parameters (tools, etc.)

        Returns:
            LLMResponse with completion

        Raises:
            RuntimeError: If API call fails after retries
        """
        start_time = time.time()

        for attempt in range(self.config.max_retries):
            try:
                messages: list[MessageParam] = [
                    {"role": "user", "content": prompt}
                ]

                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                    temperature=kwargs.get(
                        "temperature",
                        self.config.temperature
                    ),
                    system=system_prompt or "",
                    messages=messages,
                    timeout=self.config.timeout
                )

                latency_ms = (time.time() - start_time) * 1000

                tokens_input = response.usage.input_tokens
                tokens_output = response.usage.output_tokens

                costs = self.get_cost_estimate(tokens_input, tokens_output)

                # Extract text from response blocks
                content = ""
                for block in response.content:
                    if isinstance(block, TextBlock):
                        content += block.text

                logger.info(
                    f"Claude response: {tokens_input} in, "
                    f"{tokens_output} out, "
                    f"${costs['total_cost']:.4f}, {latency_ms:.0f}ms"
                )

                return LLMResponse(
                    content=content,
                    model=self.model,
                    provider="claude",
                    tokens_input=tokens_input,
                    tokens_output=tokens_output,
                    cost_input=costs["input_cost"],
                    cost_output=costs["output_cost"],
                    latency_ms=latency_ms,
                    metadata={
                        "stop_reason": response.stop_reason,
                        "attempt": attempt + 1
                    }
                )

            except Exception as e:
                logger.warning(
                    f"Claude attempt {attempt + 1}/{self.config.max_retries} "
                    f"failed: {e}"
                )
                if attempt == self.config.max_retries - 1:
                    raise RuntimeError(
                        f"Claude generation failed after "
                        f"{self.config.max_retries} attempts: {e}"
                    )
                await asyncio.sleep(2 ** attempt)
        
        raise RuntimeError("Claude generation failed unexpectedly")

    async def generate_with_thinking(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> LLMResponse:
        """
        Generate with simulated thinking process.

        Claude doesn't have native thinking mode like Gemini,
        but we can simulate by adding reasoning instructions.

        Args:
            prompt: User prompt
            system_prompt: Optional system instructions

        Returns:
            LLMResponse with thinking simulation
        """
        thinking_system = (
            "Think step-by-step before answering. "
            "Show your reasoning process explicitly."
        )

        if system_prompt:
            thinking_system = f"{system_prompt}\n\n{thinking_system}"

        enhanced_prompt = (
            f"{prompt}\n\n"
            "Please think through this step-by-step and show your reasoning."
        )

        response = await self.generate(
            enhanced_prompt,
            system_prompt=thinking_system
        )

        # Extract thinking process if present (heuristic)
        content = response.content
        thinking_process = None

        if "step" in content.lower() or "reasoning" in content.lower():
            lines = content.split("\n")
            thinking_lines = [
                l for l in lines[:5]
                if any(
                    kw in l.lower()
                    for kw in ["step", "first", "reasoning", "think"]
                )
            ]
            if thinking_lines:
                thinking_process = "\n".join(thinking_lines)

        response.thinking_process = thinking_process
        return response

    def estimate_complexity(self, prompt: str) -> float:
        """
        Estimate query complexity for routing.

        Factors:
        - Length (>1000 chars = +0.2)
        - Strategic keywords (+0.1 each)
        - Multi-step indicators (+0.2)

        Returns:
            Score 0.0-1.0
        """
        score = 0.0

        # Length factor
        if len(prompt) > 1000:
            score += 0.2
        elif len(prompt) > 500:
            score += 0.1

        # Strategic keywords
        strategic_keywords = [
            "strategy", "analyze", "compare", "optimize", "evaluate",
            "recommend", "complex", "multi-step", "considering"
        ]
        keyword_count = sum(
            1 for kw in strategic_keywords if kw in prompt.lower()
        )
        score += min(keyword_count * 0.1, 0.3)

        # Multi-step indicators
        multi_step_indicators = ["first", "then", "finally", "step"]
        if any(ind in prompt.lower() for ind in multi_step_indicators):
            score += 0.2

        # Question complexity
        if prompt.count("?") > 1:
            score += 0.1

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
