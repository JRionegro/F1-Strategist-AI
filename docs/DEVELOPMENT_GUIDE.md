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
```
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
F1_DATA_PATH=./data/races
CACHE_DIR=./cache
LOG_LEVEL=INFO
```

## Development Workflow

### Step-by-Step Build Order

#### Week 1-2: Foundation

1. **Set up data pipeline**
   ```python
   # src/data/ingestion.py
   # Implement FastF1 data fetching
   ```

2. **Create basic MCP server**
   ```python
   # src/mcp_servers/data_server.py
   # Implement data access MCP server
   ```

3. **Test data retrieval**
   ```python
   # tests/test_data_ingestion.py
   # Verify data pipeline works
   ```

#### Week 3-4: Strategy Engine

4. **Implement tire models**
   ```python
   # src/strategy/tire_model.py
   ```

5. **Build pit stop optimizer**
   ```python
   # src/strategy/pit_optimizer.py
   ```

6. **Create race simulator**
   ```python
   # src/strategy/race_simulator.py
   ```

#### Week 5-7: AI Components

7. **Set up RAG system**
   ```python
   # src/rag/vector_store.py
   # src/rag/embeddings.py
   ```

8. **Create Strategy Agent**
   ```python
   # src/agents/strategy_agent.py
   ```

9. **Implement other agents**
   ```python
   # src/agents/weather_agent.py
   # src/agents/performance_agent.py
   # src/agents/race_control_agent.py
   ```

#### Week 8-9: User Interface

10. **Build chatbot**
    ```python
    # src/chatbot/bot.py
    # src/chatbot/nlp.py
    ```

11. **Create visualizations**
    ```python
    # src/visualizations/dashboard.py
    # src/visualizations/charts.py
    ```

#### Week 10-11: Advanced Features

12. **Add simulations**
    ```python
    # src/strategy/simulation.py
    ```

13. **Optimize performance**
    ```python
    # Implement caching, parallel processing
    ```

#### Week 12: Testing & Deployment

14. **Write tests**
    ```python
    # Complete test coverage
    ```

15. **Deploy**
    ```bash
    # Set up production environment
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
