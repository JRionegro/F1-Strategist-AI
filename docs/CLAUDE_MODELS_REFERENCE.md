# Claude Models Quick Reference

## Model Comparison

| Model | Input | Output | Speed | Use Case |
|-------|-------|--------|-------|----------|
| **Opus** | $15/1M | $75/1M | Slow | Critical analysis |
| **Sonnet** | $3/1M | $15/1M | Medium | Default (balanced) |
| **Haiku** | $0.25/1M | $1.25/1M | Fast | Quick lookups |

## Quick Start

### 1. Environment Setup

```env
# .env file
ANTHROPIC_API_KEY=sk-ant-...

# Choose default model (optional)
CLAUDE_MODEL=claude-3-5-sonnet-20241022  # Default
# CLAUDE_MODEL=claude-3-opus-20240229     # For Opus
# CLAUDE_MODEL=claude-3-haiku-20240307    # For Haiku
```

### 2. Basic Usage

```python
from src.llm.config import get_claude_config, get_claude_opus_config
from src.llm.claude_provider import ClaudeProvider

# Use default (Sonnet)
provider = ClaudeProvider(get_claude_config())

# Use Opus specifically
provider = ClaudeProvider(get_claude_opus_config())

# Override at runtime
config = get_claude_config(model_override="claude-3-haiku-20240307")
provider = ClaudeProvider(config)
```

### 3. With Agents

```python
from src.agents.base_agent import AgentConfig
from src.agents.strategy_agent import StrategyAgent

# Create agent with Opus
agent_config = AgentConfig(
    name="OpusStrategyAgent",
    description="High-capability strategy agent",
    llm_provider=ClaudeProvider(get_claude_opus_config())
)

agent = StrategyAgent(agent_config)
```

## Decision Tree

```
Query Complexity?
├─ Simple factual lookup → Haiku ($0.25-$1.25/1M)
├─ Standard analysis → Sonnet ($3-$15/1M) ✓ Default
└─ Critical/complex reasoning → Opus ($15-$75/1M)
```

## Cost Examples

### Typical Query (~2000 tokens)

| Model | Input | Output | Total |
|-------|-------|--------|-------|
| Haiku | $0.0005 | $0.0025 | **$0.003** |
| Sonnet | $0.006 | $0.030 | **$0.036** |
| Opus | $0.030 | $0.150 | **$0.180** |

**Opus is 5x more expensive than Sonnet, 60x more than Haiku**

### Monthly Costs (500 queries)

| Model | Cost |
|-------|------|
| Haiku | $1.50 |
| Sonnet | $18.00 |
| Opus | $90.00 |

## When to Use Each Model

### 🟢 Haiku - Quick & Cheap

```python
# Good for:
"What's the fastest lap time?"
"Who won the 2023 Monaco GP?"
"List all pit stops for VER"

# Bad for:
"Analyze optimal strategy considering..."
"Compare degradation patterns across..."
```

### 🟡 Sonnet - Balanced (Default)

```python
# Good for:
"Analyze Hamilton's tire strategy"
"Compare lap times between drivers"
"Explain the safety car impact"

# Bad for:
"Just get the lap count"  # Use Haiku
"Multi-scenario 3-stop optimization"  # Use Opus
```

### 🔴 Opus - Maximum Capability

```python
# Good for:
"Optimize 2-stop vs 3-stop with SC probability"
"Analyze tire deg considering fuel load, track evolution, weather"
"Multi-variable scenario planning with uncertainty quantification"

# Bad for:
Simple queries (waste of money)
High-volume routine tasks
```

## Configuration Reference

### All Available Models

```python
# In src/llm/claude_provider.py
MODEL_PRICING = {
    "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-5-sonnet-20240620": {"input": 3.00, "output": 15.00},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
}
```

### Environment Variables

```env
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Optional
CLAUDE_MODEL=claude-3-5-sonnet-20241022
CLAUDE_MAX_TOKENS=4096
CLAUDE_TEMPERATURE=0.7
CLAUDE_TIMEOUT=30
CLAUDE_MAX_RETRIES=3
```

## Monitoring Costs

```python
response = await provider.generate(prompt)

print(f"Model: {response.model}")
print(f"Tokens: {response.tokens_input} in, {response.tokens_output} out")
print(f"Cost: ${response.total_cost:.4f}")
print(f"Latency: {response.latency_ms:.0f}ms")
```

## See Also

- [Full Guide](./CLAUDE_OPUS_GUIDE.md)
- [Examples](../examples/claude_opus_example.py)
- [Tech Stack](./TECH_STACK_FINAL.md)
