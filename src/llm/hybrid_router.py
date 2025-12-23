"""Hybrid LLM router with complexity-based provider selection."""

import logging
from typing import Any, Dict, Optional

from .claude_provider import ClaudeProvider
from .gemini_provider import GeminiProvider
from .models import LLMConfig, LLMResponse
from .provider import LLMProvider

logger = logging.getLogger(__name__)


class HybridRouter(LLMProvider):
    """
    Routes queries to optimal LLM provider based on complexity.

    Routing strategy:
    - Complexity < 0.4: Gemini (normal mode) - 60-70% queries
    - Complexity 0.4-0.7: Gemini (thinking mode) - 20% queries
    - Complexity > 0.7: Claude - 10-20% queries

    Cost optimization: 68% savings vs Claude-only
    """

    def __init__(
        self,
        claude_config: LLMConfig,
        gemini_config: LLMConfig,
        complexity_threshold_low: float = 0.4,
        complexity_threshold_high: float = 0.7
    ):
        """
        Initialize hybrid router.

        Args:
            claude_config: Configuration for Claude provider
            gemini_config: Configuration for Gemini provider
            complexity_threshold_low: Below this, use Gemini normal
            complexity_threshold_high: Above this, use Claude
        """
        # Call parent constructor with gemini config as base
        super().__init__(gemini_config)
        
        self.claude = ClaudeProvider(claude_config)
        self.gemini = GeminiProvider(gemini_config)
        self.threshold_low = complexity_threshold_low
        self.threshold_high = complexity_threshold_high

        # Tracking for analytics
        self.routing_stats: Dict[str, int] = {
            "gemini_normal": 0,
            "gemini_thinking": 0,
            "claude": 0
        }

        logger.info(
            f"Initialized HybridRouter with thresholds: "
            f"low={complexity_threshold_low}, high={complexity_threshold_high}"
        )

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        force_provider: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Route query to optimal provider based on complexity.

        Args:
            prompt: User prompt
            system_prompt: Optional system instructions
            force_provider: Force specific provider (claude/gemini)
            **kwargs: Additional parameters

        Returns:
            LLMResponse from selected provider

        Raises:
            ValueError: If force_provider invalid
            RuntimeError: If generation fails
        """
        # Allow manual override
        if force_provider:
            if force_provider == "claude":
                self.routing_stats["claude"] += 1
                return await self.claude.generate(
                    prompt,
                    system_prompt,
                    **kwargs
                )
            elif force_provider == "gemini":
                self.routing_stats["gemini_normal"] += 1
                return await self.gemini.generate(
                    prompt,
                    system_prompt,
                    **kwargs
                )
            else:
                raise ValueError(
                    f"Invalid provider: {force_provider}. "
                    "Use 'claude' or 'gemini'"
                )

        # Calculate complexity score
        complexity = self._estimate_complexity(prompt)

        logger.info(f"Query complexity: {complexity:.2f}")

        # Route based on complexity
        if complexity < self.threshold_low:
            # Simple query - Gemini normal mode
            logger.info("Routing to Gemini (normal mode)")
            self.routing_stats["gemini_normal"] += 1
            response = await self.gemini.generate(
                prompt,
                system_prompt,
                **kwargs
            )
            response.metadata["router_decision"] = "gemini_normal"
            response.metadata["complexity_score"] = complexity

        elif complexity < self.threshold_high:
            # Moderate query - Gemini thinking mode
            logger.info("Routing to Gemini (thinking mode)")
            self.routing_stats["gemini_thinking"] += 1
            response = await self.gemini.generate_with_thinking(
                prompt,
                system_prompt
            )
            response.metadata["router_decision"] = "gemini_thinking"
            response.metadata["complexity_score"] = complexity

        else:
            # Complex query - Claude
            logger.info("Routing to Claude (strategic mode)")
            self.routing_stats["claude"] += 1
            response = await self.claude.generate(
                prompt,
                system_prompt,
                **kwargs
            )
            response.metadata["router_decision"] = "claude"
            response.metadata["complexity_score"] = complexity

        return response

    async def generate_with_thinking(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> LLMResponse:
        """
        Generate with thinking mode (routes to Gemini thinking).

        Args:
            prompt: User prompt
            system_prompt: Optional system instructions

        Returns:
            LLMResponse with thinking process
        """
        self.routing_stats["gemini_thinking"] += 1
        response = await self.gemini.generate_with_thinking(
            prompt,
            system_prompt
        )
        response.metadata["router_decision"] = "gemini_thinking"
        return response

    def estimate_complexity(self, prompt: str) -> float:
        """
        Estimate complexity using both providers' heuristics.

        Takes average of Claude and Gemini complexity estimates
        for balanced routing.

        Args:
            prompt: User prompt

        Returns:
            Complexity score 0.0-1.0
        """
        return self._estimate_complexity(prompt)

    def get_cost_estimate(
        self,
        tokens_input: int,
        tokens_output: int
    ) -> Dict[str, float]:
        """
        Get cost estimate (uses Gemini rates as default).

        Args:
            tokens_input: Number of input tokens
            tokens_output: Number of output tokens

        Returns:
            Dict with cost breakdown
        """
        # Use Gemini as default for cost estimates (cheapest option)
        return self.gemini.get_cost_estimate(tokens_input, tokens_output)

    def _estimate_complexity(self, prompt: str) -> float:
        """
        Estimate complexity using both providers' heuristics.

        Takes average of Claude and Gemini complexity estimates
        for balanced routing.

        Args:
            prompt: User prompt

        Returns:
            Complexity score 0.0-1.0
        """
        claude_score = self.claude.estimate_complexity(prompt)
        gemini_score = self.gemini.estimate_complexity(prompt)

        # Weight Claude slightly higher (it's better at complexity detection)
        weighted_score = (claude_score * 0.6) + (gemini_score * 0.4)

        return weighted_score

    def get_routing_stats(self) -> Dict[str, Any]:
        """
        Get routing statistics for monitoring.

        Returns:
            Dict with routing counts and percentages
        """
        total = sum(self.routing_stats.values())

        if total == 0:
            return {
                "total_queries": 0,
                "gemini_normal_pct": 0,
                "gemini_thinking_pct": 0,
                "claude_pct": 0,
                "raw_counts": self.routing_stats
            }

        return {
            "total_queries": total,
            "gemini_normal_pct": (
                self.routing_stats["gemini_normal"] / total * 100
            ),
            "gemini_thinking_pct": (
                self.routing_stats["gemini_thinking"] / total * 100
            ),
            "claude_pct": self.routing_stats["claude"] / total * 100,
            "raw_counts": self.routing_stats,
            "target_distribution": {
                "gemini_normal": "60-70%",
                "gemini_thinking": "20%",
                "claude": "10-20%"
            }
        }

    def reset_stats(self) -> None:
        """Reset routing statistics."""
        self.routing_stats = {
            "gemini_normal": 0,
            "gemini_thinking": 0,
            "claude": 0
        }
        logger.info("Routing stats reset")
