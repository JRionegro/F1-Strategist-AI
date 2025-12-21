"""Data models for LLM providers."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class LLMConfig:
    """Configuration for LLM providers."""

    model_name: str
    api_key: str
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: int = 30
    max_retries: int = 3
    extra_params: Dict = field(default_factory=dict)


@dataclass
class LLMResponse:
    """Response from LLM provider."""

    content: str
    model: str
    provider: str
    tokens_input: int
    tokens_output: int
    cost_input: float
    cost_output: float
    latency_ms: float
    thinking_process: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def total_tokens(self) -> int:
        """Total tokens used in request."""
        return self.tokens_input + self.tokens_output

    @property
    def total_cost(self) -> float:
        """Total cost of request in USD."""
        return self.cost_input + self.cost_output
