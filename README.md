# F1 Strategist AI

An AI-powered Formula 1 race strategy assistant that provides real-time insights, predictions, and recommendations for race strategy optimization.

## Project Overview

The F1 Strategist AI is a comprehensive system that combines multiple AI technologies to deliver strategic insights for Formula 1 racing:

- **MCP Servers**: Model Context Protocol servers for data management and AI integration
- **Intelligent Agents**: Specialized agents for different aspects of race strategy
- **RAG System**: Retrieval-Augmented Generation for historical race data analysis
- **Interactive Chatbot**: Conversational interface for strategy queries
- **Real-time Visualizations**: Dynamic visualizations for practice, qualifying, and race sessions

## Features

### Core Capabilities
- Real-time race strategy recommendations
- Historical race data analysis and simulation
- Driver and team performance tracking
- Weather impact analysis
- Tire strategy optimization
- Pit stop timing recommendations
- Fuel management calculations

### Visualization Modes
- **Practice Session**: Track conditions, lap times, sector analysis
- **Qualifying**: Timing comparisons, optimal lap predictions
- **Race**: Live position tracking, gap analysis, strategy execution

### Simulation Features
- Historical race replay and alternative strategy exploration
- Driver/team selection and comparison
- Custom objective setting (fastest lap, position gain, fuel efficiency)
- "What-if" scenario analysis

## Project Structure

```
F1 Strategist AI/
├── .github/              # GitHub workflows and configurations
├── src/                  # Source code
│   ├── mcp_servers/      # MCP server implementations
│   ├── agents/           # AI agent modules
│   ├── chatbot/          # Chatbot interface
│   ├── rag/              # RAG system components
│   ├── visualizations/   # Visualization modules
│   └── strategy/         # Core strategy algorithms
├── data/                 # Data storage
│   ├── races/            # Historical race data
│   └── telemetry/        # Telemetry data
├── tests/                # Unit and integration tests
├── docs/                 # Documentation
├── notebooks/            # Jupyter notebooks for analysis
├── config/               # Configuration files
├── venv/                 # Virtual environment (not in git)
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## Technology Stack

- **Python 3.11+** (64-bit)
- **MCP (Model Context Protocol)** for AI integration
- **LangChain** for agent orchestration
- **FastAPI** for API services
- **Streamlit/Gradio** for web interface
- **Plotly/Dash** for visualizations
- **ChromaDB/Pinecone** for vector storage (RAG)
- **FastF1** for F1 data access
- **Pandas/NumPy** for data processing

## Development Roadmap

### Phase 1: Foundation (Weeks 1-2)
1. **Environment Setup**
   - Configure Python virtual environment
   - Install core dependencies
   - Set up development tools (linting, formatting)
   
2. **Data Infrastructure**
   - Integrate FastF1 API for historical data
   - Create data ingestion pipelines
   - Set up local data storage structure

3. **Basic MCP Server**
   - Implement first MCP server for data access
   - Create basic API endpoints
   - Test data retrieval functionality

### Phase 2: Core Strategy Engine (Weeks 3-4)
4. **Strategy Algorithms**
   - Tire degradation models
   - Pit stop optimization
   - Fuel consumption calculations
   - Weather impact analysis

5. **Data Processing**
   - Telemetry data parsing
   - Race simulation engine
   - Performance metrics calculation

### Phase 3: AI Components (Weeks 5-7)
6. **RAG System**
   - Historical race data vectorization
   - Semantic search implementation
   - Context retrieval optimization

7. **Intelligent Agents**
   - Strategy Agent (pit stops, tires)
   - Weather Agent (conditions, predictions)
   - Performance Agent (lap times, sectors)
   - Race Control Agent (flags, safety cars)

8. **Agent Orchestration**
   - Multi-agent communication
   - Decision coordination
   - Conflict resolution

### Phase 4: User Interface (Weeks 8-9)
9. **Chatbot Interface**
   - Natural language processing
   - Query understanding
   - Response generation
   - Conversation history

10. **Visualization Dashboard**
    - Real-time data displays
    - Interactive charts and graphs
    - Session-specific views
    - Customizable layouts

### Phase 5: Advanced Features (Weeks 10-11)
11. **Simulation System**
    - Historical race replay
    - Alternative strategy testing
    - Driver/team comparison tools
    - Custom scenario builder

12. **Optimization & Performance**
    - Response time optimization
    - Caching strategies
    - Parallel processing
    - Resource management

### Phase 6: Testing & Deployment (Week 12)
13. **Comprehensive Testing**
    - Unit tests for all modules
    - Integration tests
    - Performance benchmarks
    - User acceptance testing

14. **Documentation & Deployment**
    - API documentation
    - User guides
    - Deployment scripts
    - CI/CD pipeline setup

## Getting Started

### Prerequisites
- Python 3.11 or higher (64-bit)
- Git
- 8GB RAM minimum (16GB recommended)
- Internet connection for data access

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd "F1 Strategist AI"
```

2. Create and activate virtual environment:
```bash
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows PowerShell
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp config/.env.example config/.env
# Edit config/.env with your settings
```

5. Initialize the database:
```bash
python src/scripts/init_db.py
```

6. Run the application:
```bash
python src/main.py
```

## Usage Examples

### Query Strategy via Chatbot
```python
from src.chatbot import F1Chatbot

bot = F1Chatbot()
response = bot.ask("What is the optimal pit stop strategy for a dry race at Monaco?")
print(response)
```

### Run Race Simulation
```python
from src.strategy import RaceSimulator

simulator = RaceSimulator()
result = simulator.simulate_race(
    circuit="monaco",
    year=2023,
    driver="verstappen",
    strategy="two_stop"
)
```

### Visualize Live Race Data
```python
from src.visualizations import RaceDashboard

dashboard = RaceDashboard()
dashboard.show_live_race(year=2024, race="bahrain")
```

## Configuration

Key configuration files in `config/`:
- `settings.py` - Application settings
- `agents.yaml` - Agent configurations
- `mcp_servers.json` - MCP server definitions
- `.env` - Environment variables

## Testing

Run tests with pytest:
```bash
pytest tests/
```

Run with coverage:
```bash
pytest --cov=src tests/
```

## Contributing

This is a personal project, but suggestions and feedback are welcome.
Please follow PEP 8 guidelines and ensure all tests pass before submitting changes.

## License

MIT License - See LICENSE file for details

## Acknowledgments

- FastF1 for F1 data access
- OpenAI/Anthropic for AI models
- Formula 1 community for inspiration

## Contact

Project maintained by: Jorge G.

---

**Note**: This project is for educational and research purposes.
It is not affiliated with Formula 1 or any F1 teams.
