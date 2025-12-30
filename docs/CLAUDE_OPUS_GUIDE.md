# Claude Opus Integration Guide

## Overview

Claude Opus is now available in the F1 Strategist AI system as the most capable Claude model for complex strategic analysis.

## Available Claude Models

| Model | Input Cost | Output Cost | Best For |
|-------|------------|-------------|----------|
| **Claude 3 Opus** | $15/1M tokens | $75/1M tokens | Complex reasoning, multi-step analysis |
| **Claude 3.5 Sonnet** | $3/1M tokens | $15/1M tokens | Balanced performance (default) |
| **Claude 3 Haiku** | $0.25/1M tokens | $1.25/1M tokens | Fast, simple queries |

## When to Use Claude Opus

### ✅ Use Opus For

- **Complex Strategy Analysis**: Multi-variable race strategy optimization
- **High-Stakes Decisions**: Critical pit stop timing during safety cars
- **Scenario Planning**: Evaluating multiple race scenarios with uncertainty
- **Deep Technical Analysis**: Tire degradation models, fuel calculations
- **Multi-Step Reasoning**: When you need the agent to think through complex problems

### ⚠️ Don't Use Opus For

- Simple data lookups
- Standard lap time queries
- Quick factual questions
- High-volume routine queries (use Sonnet or Haiku)

## Configuration

### Method 1: Environment Variable

Set in your `.env` file:

```env
# Use Opus for all Claude calls
CLAUDE_MODEL=claude-3-opus-20240229

# Or use Sonnet (default)
CLAUDE_MODEL=claude-3-5-sonnet-20241022

# Or use Haiku (fast)
CLAUDE_MODEL=claude-3-haiku-20240307
```

### Method 2: Programmatic Configuration

```python
from src.llm.config import get_claude_opus_config
from src.llm.claude_provider import ClaudeProvider

# Get Opus-specific configuration
config = get_claude_opus_config()
provider = ClaudeProvider(config)

# Use with agent
from src.agents.base_agent import AgentConfig
from src.agents.strategy_agent import StrategyAgent

agent_config = AgentConfig(
    name="OpusStrategyAgent",
    description="F1 Strategy Agent with Claude Opus",
    llm_provider=provider,
    temperature=0.7,
    max_tokens=4096
)

agent = StrategyAgent(agent_config)
```

### Method 3: Override at Runtime

```python
from src.llm.config import get_claude_config
from src.llm.claude_provider import ClaudeProvider

# Override with specific model
opus_config = get_claude_config(model_override="claude-3-opus-20240229")
sonnet_config = get_claude_config(model_override="claude-3-5-sonnet-20241022")
haiku_config = get_claude_config(model_override="claude-3-haiku-20240307")

opus_provider = ClaudeProvider(opus_config)
```

## Usage Examples

### Example 1: Complex Strategy Analysis

```python
import asyncio
from src.llm.config import get_claude_opus_config
from src.llm.claude_provider import ClaudeProvider

async def analyze_strategy():
    config = get_claude_opus_config()
    provider = ClaudeProvider(config)
    
    prompt = """
    Analyze the optimal two-stop strategy for a wet-to-dry race at 
    Silverstone considering:
    - Track drying rate (intermediate to slick transition)
    - Tire compound performance windows
    - Safety car probability in mixed conditions
    - Fuel load impact on intermediate tire wear
    
    Provide timing windows for each pit stop with confidence levels.
    """
    
    response = await provider.generate(
        prompt=prompt,
        system_prompt="You are an expert F1 strategist."
    )
    
    print(f"Cost: ${response.total_cost:.4f}")
    print(f"Analysis: {response.content}")

asyncio.run(analyze_strategy())
```

### Example 2: Comparing Models

```python
import asyncio
from src.llm.config import get_claude_config, get_claude_opus_config
from src.llm.claude_provider import ClaudeProvider

async def compare_models():
    prompt = "Explain tire deg at Monaco"
    
    # Test both models
    for name, config_func in [
        ("Sonnet", get_claude_config),
        ("Opus", get_claude_opus_config)
    ]:
        provider = ClaudeProvider(config_func())
        response = await provider.generate(prompt)
        
        print(f"\n{name}:")
        print(f"  Cost: ${response.total_cost:.4f}")
        print(f"  Tokens: {response.total_tokens}")
        print(f"  Time: {response.latency_ms:.0f}ms")

asyncio.run(compare_models())
```

### Example 3: Using with Hybrid Router

The hybrid router can automatically select Opus for complex queries:

```python
from src.llm.config import get_claude_config, get_gemini_config
from src.llm.hybrid_router import HybridRouter

# Initialize hybrid router
router = HybridRouter(
    claude_config=get_claude_opus_config(),  # Use Opus for complex queries
    gemini_config=get_gemini_config(),
    complexity_threshold_high=0.7  # Opus kicks in above 0.7
)

# Simple query → Gemini
response = await router.generate("What's the lap record at Monaco?")

# Complex query → Opus
response = await router.generate("""
    Analyze multi-stop strategy scenarios for a safety car period
    with degraded tires and fuel load considerations...
""")
```

## Cost Management

### Estimated Costs

For a typical F1 race analysis session:

| Query Type | Model | Tokens | Cost |
|-----------|-------|--------|------|
| Simple lookup | Haiku | 500 | $0.0003 |
| Standard analysis | Sonnet | 2000 | $0.03 |
| Complex strategy | Opus | 4000 | $0.36 |

### Best Practices

1. **Use the Right Model**: Default to Sonnet, upgrade to Opus only when needed
2. **Leverage Hybrid Router**: Let complexity scoring automatically select the model
3. **Cache Responses**: Store common analysis to avoid repeated expensive calls
4. **Monitor Usage**: Track costs using response metadata

```python
response = await provider.generate(prompt)
print(f"This query cost: ${response.total_cost:.4f}")
print(f"Pricing: ${provider.COST_PER_1M_INPUT}/${provider.COST_PER_1M_OUTPUT} per 1M tokens")
```

## Testing

Run the example to see Opus in action:

```bash
cd "c:\Users\jorgeg\OneDrive - CEGID\Desarrollador 10x con IA\CAPSTON PROJECT\F1\F1 Strategist AI"
python examples/claude_opus_example.py
```

## API Reference

### `get_claude_opus_config()`

Returns a `LLMConfig` configured specifically for Claude Opus.

**Returns**: `LLMConfig` with Opus model settings

**Example**:
```python
from src.llm.config import get_claude_opus_config

config = get_claude_opus_config()
# config.model_name = "claude-3-opus-20240229"
```

### `ClaudeProvider.MODEL_PRICING`

Dictionary containing pricing for all Claude models.

**Structure**:
```python
{
    "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25}
}
```

## Troubleshooting

### Model Not Found Error

If you see warnings about unknown models:
```
WARNING: Unknown Claude model: claude-3-opus-latest. Using Sonnet 3.5 pricing as fallback.
```

**Solution**: Use the exact model identifier:
- ✅ `claude-3-opus-20240229`
- ❌ `claude-3-opus`
- ❌ `claude-opus`

### High Costs

If costs are too high:

1. **Check model selection**: Ensure you're not using Opus for simple queries
2. **Enable hybrid routing**: Let the system automatically select models
3. **Reduce max_tokens**: Lower the output limit
4. **Use streaming**: Process responses incrementally (future feature)

## See Also

- [LLM Configuration Guide](./TECH_STACK_FINAL.md#llm-providers)
- [Hybrid Router Documentation](./TECH_STACK_FINAL.md#hybrid-router)
- [Agent Architecture](./AGENTS_ARCHITECTURE.md)
- [Example Scripts](../examples/)
