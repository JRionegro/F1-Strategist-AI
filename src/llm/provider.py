"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod
from typing import Dict, Optional

from .models import LLMConfig, LLMResponse


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    Provides interface for different LLM implementations:
    - Claude (Anthropic)
    - Gemini (Google)
    - Future providers (OpenAI, etc.)
    """

    def __init__(self, config: LLMConfig):
        """
        Initialize LLM provider.

        Args:
            config: Configuration for the LLM provider
        """
        self.config = config
        self._validate_config()

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate completion from prompt.

        Args:
            prompt: User prompt to complete
            system_prompt: Optional system instructions
            **kwargs: Additional provider-specific parameters

        Returns:
            LLMResponse with completion and metadata

        Raises:
            ValueError: If prompt is invalid
            RuntimeError: If API call fails after retries
        """
        pass

    @abstractmethod
    async def generate_with_thinking(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> LLMResponse:
        """
        Generate completion with reasoning/thinking mode.

        Used for complex queries requiring step-by-step reasoning.
        Providers like Gemini 2.0 Flash Thinking have native support.
        Others may simulate thinking process.

        Args:
            prompt: User prompt to complete
            system_prompt: Optional system instructions

        Returns:
            LLMResponse with thinking process included

        Raises:
            NotImplementedError: If thinking mode not supported
        """
        pass

    @abstractmethod
    def estimate_complexity(self, prompt: str) -> float:
        """
        Estimate complexity score for routing decisions.

        Score range: 0.0 (simple) to 1.0 (very complex)

        Factors considered:
        - Prompt length
        - Technical keywords
        - Multi-step reasoning requirements
        - Number of tools needed

        Args:
            prompt: User prompt to analyze

        Returns:
            Complexity score between 0.0 and 1.0
        """
        pass

    @abstractmethod
    def get_cost_estimate(
        self,
        tokens_input: int,
        tokens_output: int
    ) -> Dict[str, float]:
        """
        Estimate cost for token usage.

        Args:
            tokens_input: Number of input tokens
            tokens_output: Number of output tokens

        Returns:
            Dict with 'input_cost', 'output_cost', 'total_cost' in USD
        """
        pass

    def _validate_config(self) -> None:
        """
        Validate provider configuration.

        Raises:
            ValueError: If configuration is invalid
        """
        if not self.config.api_key:
            raise ValueError(f"API key required for {self.__class__.__name__}")
        if self.config.max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        if not 0 <= self.config.temperature <= 2:
            raise ValueError("temperature must be between 0 and 2")

    @property
    def name(self) -> str:
        """Provider name for logging/monitoring."""
        return self.__class__.__name__
