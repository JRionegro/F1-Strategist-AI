"""
Example: Using Claude Opus with F1 Strategist AI Agents

This example demonstrates how to use Claude Opus (the most capable
Claude model) with the F1 strategy agents for complex analysis.
"""

import asyncio
import logging

from src.llm.config import get_claude_opus_config, get_claude_config
from src.llm.claude_provider import ClaudeProvider
from src.agents.base_agent import AgentConfig
from src.agents.strategy_agent import StrategyAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def compare_opus_vs_sonnet():
    """Compare Claude Opus vs Sonnet for strategic analysis."""
    
    # Initialize both models
    opus_config = get_claude_opus_config()
    sonnet_config = get_claude_config()  # Defaults to Sonnet
    
    opus_provider = ClaudeProvider(opus_config)
    sonnet_provider = ClaudeProvider(sonnet_config)
    
    # Complex strategy question
    prompt = """
    Analyze the optimal pit stop strategy for the Monaco Grand Prix 
    considering:
    - Track evolution throughout the race
    - Tire degradation on this unique circuit
    - Historical safety car probability (>60%)
    - Undercut/overcut effectiveness
    - Track position value vs tire age trade-off
    
    Provide a comprehensive multi-scenario strategy recommendation.
    """
    
    system_prompt = (
        "You are an expert F1 strategy analyst with deep knowledge "
        "of race dynamics, tire management, and tactical decision-making."
    )
    
    # Test Opus
    logger.info("=" * 60)
    logger.info("Testing Claude Opus (most capable)")
    logger.info("=" * 60)
    
    opus_response = await opus_provider.generate(
        prompt=prompt,
        system_prompt=system_prompt
    )
    
    logger.info(f"\nOpus Response ({opus_response.total_tokens} tokens):")
    logger.info(f"Cost: ${opus_response.total_cost:.4f}")
    logger.info(f"Latency: {opus_response.latency_ms:.0f}ms")
    logger.info(f"\nContent preview: {opus_response.content[:200]}...")
    
    # Test Sonnet
    logger.info("\n" + "=" * 60)
    logger.info("Testing Claude Sonnet (balanced)")
    logger.info("=" * 60)
    
    sonnet_response = await sonnet_provider.generate(
        prompt=prompt,
        system_prompt=system_prompt
    )
    
    logger.info(f"\nSonnet Response ({sonnet_response.total_tokens} tokens):")
    logger.info(f"Cost: ${sonnet_response.total_cost:.4f}")
    logger.info(f"Latency: {sonnet_response.latency_ms:.0f}ms")
    logger.info(f"\nContent preview: {sonnet_response.content[:200]}...")
    
    # Compare
    logger.info("\n" + "=" * 60)
    logger.info("Comparison")
    logger.info("=" * 60)
    logger.info(f"Cost difference: ${opus_response.total_cost - sonnet_response.total_cost:.4f}")
    logger.info(f"Opus is {opus_response.total_cost / sonnet_response.total_cost:.1f}x more expensive")
    logger.info(f"Speed difference: {opus_response.latency_ms - sonnet_response.latency_ms:.0f}ms")


async def use_opus_with_agent():
    """Use Claude Opus with a Strategy Agent."""
    
    opus_config = get_claude_opus_config()
    opus_provider = ClaudeProvider(opus_config)
    
    # Configure agent with Opus
    agent_config = AgentConfig(
        name="OpusStrategyAgent",
        description="F1 Strategy Agent powered by Claude Opus",
        llm_provider=opus_provider,
        temperature=0.7,
        max_tokens=4096,
        enable_rag=False,  # Simplified for example
        enable_tools=False
    )
    
    # Note: This is a simplified example
    # In production, you'd initialize with RAG and MCP tools
    logger.info("=" * 60)
    logger.info("Claude Opus Strategy Agent Initialized")
    logger.info("=" * 60)
    logger.info(f"Model: {opus_provider.model}")
    logger.info(f"Cost: ${opus_provider.COST_PER_1M_INPUT}/${opus_provider.COST_PER_1M_OUTPUT} per 1M tokens")
    logger.info("=" * 60)


async def when_to_use_opus():
    """Guidelines on when to use Claude Opus."""
    
    guidelines = """
    # When to Use Claude Opus
    
    ## USE OPUS FOR:
    ✅ Complex multi-step race strategy analysis
    ✅ High-stakes decision making (pit stop timing during SC)
    ✅ Analyzing multiple interacting variables
    ✅ Scenario planning with uncertainty
    ✅ Deep technical analysis requiring reasoning
    
    ## USE SONNET FOR:
    ✅ Standard race queries and lap time analysis
    ✅ Historical data lookups
    ✅ Simple comparisons
    ✅ Real-time commentary
    ✅ 80% of typical queries (cost-effective)
    
    ## USE HAIKU FOR:
    ✅ Quick factual lookups
    ✅ Simple data retrieval
    ✅ Fast responses needed
    ✅ High-volume simple queries
    
    ## Cost Comparison (per 1M tokens):
    - Haiku:  $0.25 / $1.25   (fastest, cheapest)
    - Sonnet: $3.00 / $15.00  (balanced, default)
    - Opus:   $15.00 / $75.00 (most capable, expensive)
    
    ## Configuration:
    Set in environment (.env):
    CLAUDE_MODEL=claude-3-opus-20240229
    
    Or programmatically:
    from src.llm.config import get_claude_opus_config
    config = get_claude_opus_config()
    """
    
    print(guidelines)


if __name__ == "__main__":
    # Show guidelines
    asyncio.run(when_to_use_opus())
    
    print("\n" + "=" * 60)
    print("Running Examples...")
    print("=" * 60 + "\n")
    
    # Run examples
    # Uncomment to test (requires ANTHROPIC_API_KEY in environment)
    
    # asyncio.run(compare_opus_vs_sonnet())
    # asyncio.run(use_opus_with_agent())
    
    print("\nTo run live examples, uncomment the asyncio.run() calls")
    print("and ensure ANTHROPIC_API_KEY is set in your environment.")
