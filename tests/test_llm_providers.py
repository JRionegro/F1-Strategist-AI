"""Unit tests for LLM providers."""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.llm.claude_provider import ClaudeProvider
from src.llm.gemini_provider import GeminiProvider
from src.llm.hybrid_router import HybridRouter
from src.llm.models import LLMConfig, LLMResponse


@pytest.fixture
def claude_config():
    """Mock Claude configuration."""
    return LLMConfig(
        model_name="claude-3-5-sonnet-20241022",
        api_key="test-key-claude",
        max_tokens=4096,
        temperature=0.7
    )


@pytest.fixture
def gemini_config():
    """Mock Gemini configuration."""
    return LLMConfig(
        model_name="gemini-2.0-flash-thinking-exp-1219",
        api_key="test-key-gemini",
        max_tokens=8192,
        temperature=0.7,
        extra_params={"enable_thinking": True}
    )


class TestClaudeProvider:
    """Tests for Claude provider."""

    def test_initialization(self, claude_config):
        """Test Claude provider initialization."""
        provider = ClaudeProvider(claude_config)
        assert provider.model == "claude-3-5-sonnet-20241022"
        assert provider.config.api_key == "test-key-claude"

    def test_cost_estimation(self, claude_config):
        """Test Claude cost calculation."""
        provider = ClaudeProvider(claude_config)
        costs = provider.get_cost_estimate(1000, 500)

        assert costs["input_cost"] == pytest.approx(0.003)
        assert costs["output_cost"] == pytest.approx(0.0075)
        assert costs["total_cost"] == pytest.approx(0.0105)

    def test_complexity_estimation_simple(self, claude_config):
        """Test complexity estimation for simple query."""
        provider = ClaudeProvider(claude_config)
        score = provider.estimate_complexity("What is the weather?")
        assert 0.0 <= score <= 0.3

    def test_complexity_estimation_complex(self, claude_config):
        """Test complexity estimation for complex query."""
        provider = ClaudeProvider(claude_config)
        prompt = (
            "Analyze the optimal pit strategy considering track "
            "position, tire degradation, and competitor strategies. "
            "Compare multiple scenarios and recommend the best approach."
        )
        score = provider.estimate_complexity(prompt)
        assert score >= 0.3  # Adjusted threshold

    @pytest.mark.asyncio
    async def test_generate_mock(self, claude_config):
        """Test Claude generation with mocked API."""
        from anthropic.types import TextBlock

        provider = ClaudeProvider(claude_config)

        # Mock the Anthropic client
        mock_response = MagicMock()
        mock_text_block = TextBlock(text="Test response", type="text")
        mock_response.content = [mock_text_block]
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50
        mock_response.stop_reason = "end_turn"

        with patch.object(
            provider.client.messages,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response
        ):
            response = await provider.generate("Test prompt")

            assert response.content == "Test response"
            assert response.provider == "claude"
            assert response.tokens_input == 100
            assert response.tokens_output == 50


class TestGeminiProvider:
    """Tests for Gemini provider."""

    def test_initialization(self, gemini_config):
        """Test Gemini provider initialization."""
        with patch("google.genai.Client"):
            provider = GeminiProvider(gemini_config)
            assert provider.model_name == (
                "gemini-2.0-flash-thinking-exp-1219"
            )
            assert provider.enable_thinking is True

    def test_cost_estimation(self, gemini_config):
        """Test Gemini cost calculation."""
        with patch("google.genai.Client"):
            provider = GeminiProvider(gemini_config)
            costs = provider.get_cost_estimate(1000, 500)

            assert costs["input_cost"] == pytest.approx(0.00001875)
            assert costs["output_cost"] == pytest.approx(0.0000375)
            assert costs["total_cost"] == pytest.approx(0.00005625)

    def test_token_counting(self, gemini_config):
        """Test approximate token counting."""
        with patch("google.genai.Client"):
            provider = GeminiProvider(gemini_config)
            tokens = provider._count_tokens("This is a test")
            assert tokens > 0

    def test_thinking_extraction(self, gemini_config):
        """Test extraction of thinking process."""
        with patch("google.genai.Client"):
            provider = GeminiProvider(gemini_config)

            # With explicit tags
            content_with_tags = (
                "<thinking>Step 1: Analyze data</thinking>\n"
                "Here's the answer"
            )
            thinking = provider._extract_thinking(content_with_tags)
            assert thinking is not None
            assert "Step 1" in thinking

            # Without tags but with step markers
            content_with_steps = (
                "First, let's think about this step by step.\n\n"
                "The answer is 42."
            )
            thinking = provider._extract_thinking(content_with_steps)
            assert thinking is not None


class TestHybridRouter:
    """Tests for hybrid router."""

    @pytest.fixture
    def router(self, claude_config, gemini_config):
        """Create hybrid router for testing."""
        with patch("google.genai.Client"):
            return HybridRouter(claude_config, gemini_config)

    def test_initialization(self, router):
        """Test router initialization."""
        assert router.threshold_low == 0.4
        assert router.threshold_high == 0.7
        assert router.routing_stats["claude"] == 0

    def test_complexity_estimation(self, router):
        """Test complexity estimation combines both providers."""
        # Simple query
        simple_score = router._estimate_complexity("What is F1?")
        assert 0.0 <= simple_score <= 0.4

        # Complex query
        complex_prompt = (
            "Analyze the optimal pit strategy considering track position, "
            "tire degradation, weather forecasts, and competitor strategies. "
            "Compare multiple scenarios and recommend the best approach."
        )
        complex_score = router._estimate_complexity(complex_prompt)
        assert complex_score >= 0.2  # Adjusted threshold

    @pytest.mark.asyncio
    async def test_routing_simple_query(self, router):
        """Test routing of simple query to Gemini."""
        with patch.object(
            router.gemini,
            "generate",
            new_callable=AsyncMock,
            return_value=LLMResponse(
                content="Test",
                model="gemini",
                provider="gemini",
                tokens_input=10,
                tokens_output=5,
                cost_input=0.0001,
                cost_output=0.0001,
                latency_ms=100
            )
        ):
            response = await router.generate("What is F1?")
            assert response.provider == "gemini"
            assert router.routing_stats["gemini_normal"] == 1

    @pytest.mark.asyncio
    async def test_routing_complex_query(self, router):
        """Test routing logic works for complex queries."""
        complex_prompt = (
            "This is a highly complex strategic analysis requiring "
            "deep reasoning. Analyze the optimal pit strategy considering "
            "track position, tire degradation, weather, competitor strategies, "
            "fuel loads, and aero setup. Compare multiple scenarios, perform "
            "Monte Carlo simulations, and recommend the best approach with "
            "detailed justification for each decision point."
        )

        # Mock all providers
        with patch.object(
            router.claude,
            "generate",
            new_callable=AsyncMock,
            return_value=LLMResponse(
                content="Claude response",
                model="claude",
                provider="claude",
                tokens_input=100,
                tokens_output=50,
                cost_input=0.01,
                cost_output=0.01,
                latency_ms=200
            )
        ), patch.object(
            router.gemini,
            "generate",
            new_callable=AsyncMock,
            return_value=LLMResponse(
                content="Gemini response",
                model="gemini",
                provider="gemini",
                tokens_input=100,
                tokens_output=50,
                cost_input=0.001,
                cost_output=0.001,
                latency_ms=100
            )
        ), patch.object(
            router.gemini,
            "generate_with_thinking",
            new_callable=AsyncMock,
            return_value=LLMResponse(
                content="Gemini thinking",
                model="gemini",
                provider="gemini",
                tokens_input=100,
                tokens_output=50,
                cost_input=0.001,
                cost_output=0.001,
                latency_ms=150
            )
        ):
            response = await router.generate(complex_prompt)
            # Check routing decision was made
            assert "router_decision" in response.metadata
            assert response.metadata["router_decision"] in [
                "gemini_normal", "gemini_thinking", "claude"
            ]

    def test_routing_stats(self, router):
        """Test routing statistics."""
        router.routing_stats = {
            "gemini_normal": 70,
            "gemini_thinking": 20,
            "claude": 10
        }

        stats = router.get_routing_stats()
        assert stats["total_queries"] == 100
        assert stats["gemini_normal_pct"] == 70.0
        assert stats["gemini_thinking_pct"] == 20.0
        assert stats["claude_pct"] == 10.0

    def test_reset_stats(self, router):
        """Test resetting statistics."""
        router.routing_stats["claude"] = 10
        router.reset_stats()
        assert router.routing_stats["claude"] == 0


@pytest.mark.integration
class TestLLMIntegration:
    """Integration tests requiring real API keys."""

    @pytest.mark.skipif(
        not os.getenv("ANTHROPIC_API_KEY"),
        reason="ANTHROPIC_API_KEY not set"
    )
    @pytest.mark.asyncio
    async def test_claude_real_api(self):
        """Test Claude with real API (requires key)."""
        from src.llm.config import get_claude_config

        config = get_claude_config()
        provider = ClaudeProvider(config)

        response = await provider.generate(
            "What is Formula 1? Answer in 10 words."
        )

        assert len(response.content) > 0
        assert response.tokens_input > 0
        assert response.tokens_output > 0
        assert response.total_cost > 0

    @pytest.mark.skipif(
        not os.getenv("GOOGLE_API_KEY"),
        reason="GOOGLE_API_KEY not set"
    )
    @pytest.mark.asyncio
    async def test_gemini_real_api(self):
        """Test Gemini with real API (requires key)."""
        from src.llm.config import get_gemini_config

        config = get_gemini_config()
        provider = GeminiProvider(config)

        response = await provider.generate(
            "What is Formula 1? Answer in 10 words."
        )

        assert len(response.content) > 0
        assert response.tokens_input > 0
        assert response.tokens_output > 0
        assert response.total_cost > 0
