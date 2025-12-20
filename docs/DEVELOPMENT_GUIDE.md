# Development Guide

## Getting Started

### 1. Environment Setup

Create and activate the virtual environment:

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

### 2. Project Configuration

Create environment configuration:

```powershell
# Copy example environment file
Copy-Item config\.env.example config\.env

# Edit with your settings
notepad config\.env
```

Required environment variables:
```env
# LLM Configuration
ANTHROPIC_API_KEY=your_anthropic_key
GOOGLE_API_KEY=your_google_key
LLM_PROVIDER=hybrid
GEMINI_MODEL=gemini-2.0-flash-thinking-exp-1219

# Vector Store
VECTOR_STORE_PROVIDER=chromadb
EMBEDDINGS_MODEL=all-MiniLM-L6-v2

# Monitoring
LANGSMITH_API_KEY=your_langsmith_key
LANGCHAIN_TRACING_V2=true
LOCAL_TOKEN_TRACKING=true

# Data & Cache
F1_DATA_PATH=./data/races
CACHE_DIR=./cache
USE_REDIS=false
LOG_LEVEL=INFO
```

## Development Workflow

### Step-by-Step Build Order

#### ✅ Phase 1-2: Foundation & Data Layer (COMPLETED)

**Weeks 1-4: Data Pipeline & MCP Server**

1. **Data Integration** ✅
   - FastF1 + OpenF1 unified provider
   - 13 MCP tools operational
   - Hybrid cache system (historical + live)

2. **Testing Infrastructure** ✅
   - 81 tests passing (100% coverage)
   - Monitoring system (LangSmith + local)

#### ✅ Phase 2D: Architecture Planning (COMPLETED)

**Week 5: Tech Stack Decisions**

3. **Technology Selection** ✅
   - LLM: Hybrid Claude + Gemini 2.0 Flash Thinking
   - Vector Store: ChromaDB (MVP) + Pinecone (production)
   - Embeddings: all-MiniLM-L6-v2
   - 5-agent architecture finalized

#### 🔄 Phase 3A: LangChain Foundation (CURRENT - Weeks 5-6)

**LLM Providers Implementation**

4. **Build LLM abstraction layer**
   ```python
   # src/llm/provider.py - Abstract interface
   # src/llm/claude_provider.py - Claude 3.5 Sonnet
   # src/llm/gemini_provider.py - Gemini 2.0 Flash Thinking
   # src/llm/hybrid_router.py - Complexity-based routing
   ```

5. **Vector Store Factory**
   ```python
   # src/rag/chromadb_store.py - ChromaDB implementation
   # src/rag/pinecone_store.py - Pinecone stub
   # src/rag/factory.py - Factory pattern
   ```

6. **Testing LLM Integration**
   ```python
   # tests/test_llm_providers.py
   # tests/test_hybrid_router.py
   # tests/test_vector_stores.py
   ```

#### 📋 Phase 3B: Agent Implementation (Weeks 7-8)

**Multi-Agent System**

7. **Base Agent Framework**
   ```python
   # src/agents/base_agent.py - Abstract base
   # src/agents/orchestrator.py - Coordinator
   ```

8. **Implement 5 Specialized Agents**
   ```python
   # src/agents/strategy_agent.py - Pit stops, tires
   # src/agents/weather_agent.py - Weather impact
   # src/agents/performance_agent.py - Lap analysis
   # src/agents/race_control_agent.py - Flags, incidents
   # src/agents/race_position_agent.py - Gaps, positions
   ```

9. **RAG System**
   ```python
   # src/rag/indexer.py - Document indexing
   # src/rag/retriever.py - Semantic search
   ```

#### 📋 Phase 3C: Advanced Features (Weeks 9-10)

**Tool Integration & Optimization**

10. **LangChain Tool Wrapper**
    ```python
    # src/agents/tools/f1_data_tools.py
    # Convert 13 MCP tools to LangChain format
    ```

11. **Agent Orchestration**
    ```python
    # src/agents/orchestrator.py
    # Multi-agent coordination logic
    ```

12. **Performance Optimization**
    ```python
    # Parallel tool execution
    # Response caching
    # Token usage optimization
    ```

#### 📋 Phase 4: User Interface (Weeks 11-12)

**Chatbot & Dashboards**

13. **Build Chatbot Interface**
    ```python
    # src/chatbot/bot.py
    # src/chatbot/message_handler.py
    ```

14. **Create Visualizations**
    ```python
    # src/visualizations/dashboard.py
    # src/visualizations/charts.py
    ```

15. **Deploy MVP**
    ```bash
    # Production configuration
    # API deployment
    # Monitoring dashboard
    ```

## Code Style Guidelines

Follow PEP 8 and project conventions:

```python
# Good example
def calculate_pit_window(
    lap: int,
    tire_deg: float,
    fuel_load: float
) -> tuple[int, int]:
    """
    Calculate optimal pit stop window.
    
    Args:
        lap: Current lap number
        tire_deg: Tire degradation percentage
        fuel_load: Current fuel load in kg
        
    Returns:
        Tuple of (earliest_lap, latest_lap)
    """
    # Implementation
    pass
```

## Testing

Run tests regularly:

```powershell
# All tests
pytest

# With coverage
pytest --cov=src tests/

# Specific module
pytest tests/test_strategy.py

# Linting
flake8 src/
black src/ --check
mypy src/
```

## Git Workflow

```bash
# Create feature branch
git checkout -b feature/pit-optimizer

# Make changes and commit
git add .
git commit -m "feat: implement pit stop optimizer"

# Push to remote
git push origin feature/pit-optimizer

# Merge to main after review
git checkout main
git merge feature/pit-optimizer
```

## Debugging Tips

1. **Enable debug logging**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Use breakpoints**
   ```python
   breakpoint()  # Python 3.7+
   ```

3. **Check FastF1 cache**
   ```python
   import fastf1
   fastf1.Cache.enable_cache('cache/')
   ```

## Common Issues

### FastF1 data not loading
```python
# Clear cache
import shutil
shutil.rmtree('cache/')
```

### MCP server not responding
```bash
# Check if server is running
netstat -an | findstr :8000
```

### Virtual environment issues
```powershell
# Recreate environment
Remove-Item -Recurse -Force venv
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Resources

- [FastF1 Documentation](https://docs.fastf1.dev/)
- [OpenF1 APIs Doc] (https://openf1.org/#api-endpoints)
- [LangChain Docs](https://python.langchain.com/)
- [MCP Specification](https://modelcontextprotocol.io/)
- [Plotly Documentation](https://plotly.com/python/)

## Next Steps

After completing setup:
1. Read through [PROJECT_SPECIFICATIONS.md](PROJECT_SPECIFICATIONS.md)
2. Start with Phase 1: Foundation
3. Test data ingestion with a sample race
4. Move to Phase 2 once data pipeline is stable

---

Happy coding! 🏎️💨
