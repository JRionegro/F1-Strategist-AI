# F1 Strategist AI

An AI-powered Formula 1 race strategy assistant with unified OpenF1 data source for both historical simulations and real-time monitoring.

## 🎯 Project Status

### ✅ Phase 1-2: Foundation & Data Layer (COMPLETED)

- **Data Source**: Unified OpenF1 API (2023+ coverage, historical + live)
- **Cache System**: Hybrid system (historical + live) with Parquet
- **Monitoring**: LangSmith + LocalTokenTracker fallback
- **Data Provider**: OpenF1 with FastF1-compatible adapter layer
- **Migration**: Completed from FastF1 to OpenF1 (Dec 2025)

### ✅ Phase 2D: Architecture & Tech Stack (FINALIZED)

- **5-Agent Architecture**: Strategy, Weather, Performance, Race Control, Race Position
- **LLM Hybrid**: Claude 3.5 Sonnet + Gemini 2.0 Flash Thinking (68% cost savings)
- **Vector Store**: ChromaDB (MVP) + Pinecone option (production)
- **Embeddings**: all-MiniLM-L6-v2 (384 dims, local, free)
- **Cost Projection**: $8.50/mo MVP, $294/mo production

### ✅ Phase 3A: LangChain Foundation (COMPLETED)

- **LLM Providers**: 15/15 tests passing (Claude, Gemini, Hybrid Router)
- **RAG Module**: VectorStore interface, ChromaDB implementation
- **Unit Tests**: 15/15 passing (with mocks)
- **Integration Tests**: 3/3 passing (Python 3.13)

### 🔄 Next: Phase 3B - LangChain Agents (Week 7-8)

See [TECH_STACK_FINAL.md](docs/TECH_STACK_FINAL.md) for complete decisions.

---

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone [repo-url]
cd "F1 Strategist AI"

# Activate virtual environment (Python 3.13)
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### Basic Usage

```python
from src.data import OpenF1DataProvider
from src.data.openf1_adapter import get_session

# Initialize OpenF1 provider
provider = OpenF1DataProvider()

# Get session (FastF1-compatible interface)
session = get_session(2024, 1, "R", provider)  # Bahrain Race
session.load()

# Access data
laps = session.laps
results = session.results
weather = session.weather_data
```

### Utility Scripts

```bash
# View cache statistics
python scripts/cache_stats.py

# Preload season
python scripts/preload_season.py 2024

# Clean old data
python scripts/clean_cache.py --types telemetry
```

---

## 📊 Core Features

### Unified Data Architecture

- **Single API**: OpenF1 for both historical (2023+) and live data
- **No Translation**: Eliminates FastF1/OpenF1 format conflicts
- **Native Timestamps**: Real datetime instead of Timedelta issues
- **Streaming Ready**: Built for real-time race monitoring
- **Performance**: Direct API access with intelligent caching

### OpenF1 Data Endpoints

1. `get_laps` - Lap times and metadata
2. `get_drivers` - Driver information
3. `get_positions` - Real-time position updates
4. `get_stints` - Tire strategy and stints
5. `get_pit_stops` - Pit stop analysis
6. `get_weather` - Weather conditions
7. `get_race_control_messages` - Flags, SC, VSC
8. `get_session` - Session metadata
9. `stream_live_data` - Real-time streaming (future)

**Coverage**: All F1 seasons from 2023 onwards
11. `get_track_status` - Estados de pista
12. `get_race_control_messages` - Mensajes de dirección
13. `get_season_schedule` - Calendario de temporada

### Real-Time Monitoring (Live Sessions)

- Actualización incremental cada 5 segundos
- Tracking de stints en curso
- Eventos de carrera (pit stops, flags)
- Estado de posiciones en tiempo real

---

## 📁 Project Structure

```
F1 Strategist AI/
├── src/
│   ├── data/                    # Data layer (IMPLEMENTED ✅)
│   │   ├── cache_config.py      # Cache configuration
│   │   ├── cache_manager.py     # Hybrid manager
│   │   ├── f1_data_provider.py  # Unified provider
│   │   ├── live_session_monitor.py  # Real-time monitor
│   │   └── models.py            # F1 dataclasses
│   ├── mcp_server/              # MCP Server (IMPLEMENTED ✅)
│   │   └── f1_data_server.py    # 13 MCP tools
│   ├── agents/                  # AI Agents (PENDING)
│   ├── rag/                     # RAG System (PENDING)
│   ├── chatbot/                 # Chatbot (PENDING)
│   └── visualizations/          # Dashboards (PENDING)
├── data/                        # Data storage
│   ├── races/                   # Historical race data
│   ├── telemetry/               # Telemetry by driver
│   └── live/                    # Active sessions
├── scripts/                     # Utility scripts
│   ├── cache_stats.py
│   ├── clean_cache.py
│   └── preload_season.py
├── tests/                       # Test suite
│   ├── test_mcp_server.py       # 39 tests ✅
│   └── test_cache_system.py     # 14 tests ✅
└── docs/                        # Documentation
    ├── CACHE_SYSTEM_IMPLEMENTATION.md
    ├── MCP_API_REFERENCE.md
    └── ARCHITECTURE_DECISIONS.md
```
│   └── telemetry/        # Telemetry data
├── tests/                # Unit and integration tests
├── docs/                 # Documentation
├── notebooks/            # Jupyter notebooks for analysis
├── config/               # Configuration files
├── venv/                 # Virtual environment Python 3.13 (not in git)
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## Technology Stack

### Core Framework
- **Python 3.13** (64-bit)
- **LangChain** for multi-agent orchestration
- **MCP (Model Context Protocol)** for tool integration

### AI/LLM Layer
- **Claude 3.5 Sonnet** - Primary LLM (complex queries, ~30%)
- **Gemini 2.0 Flash Thinking** - Secondary LLM (simple/moderate, ~70%)
  - Model: `gemini-2.0-flash-thinking-exp-1219`
  - Reasoning mode for enhanced accuracy
- **Hybrid Router** - Complexity-based query routing

### Data & Storage
- **FastF1** + **OpenF1** - F1 data providers
- **Parquet** - Historical cache format
- **ChromaDB** - Vector store (MVP, local)
- **Pinecone** - Vector store (production option, configurable)
- **all-MiniLM-L6-v2** - Embeddings model (384 dims)

### Monitoring & Observability
- **LangSmith** - Production monitoring with local fallback
- **LocalTokenTracker** - Offline usage tracking

### APIs & Interfaces
- **FastAPI** - API services
- **Streamlit/Gradio** - Web interface
- **Plotly/Dash** - Visualizations
- **Pandas/NumPy** for data processing

## Development Roadmap

### ✅ Phase 1: Foundation (Weeks 1-2) - COMPLETED
1. **Environment Setup** ✅
   - Python virtual environment configured
   - Dependencies installed
   - Development tools (pytest, flake8, black)
   
2. **Data Infrastructure** ✅
   - FastF1 + OpenF1 integration complete
   - Hybrid cache system (historical + live)
   - Parquet-based storage with TTL policies

3. **MCP Server** ✅
   - 13 tools operational (100% coverage)
   - 43 tests passing
   - API reference documentation

### ✅ Phase 2: Data Layer & Monitoring (Weeks 3-4) - COMPLETED
4. **Cache System** ✅
   - Historical mode: Permanent Parquet storage
   - Live mode: Real-time OpenF1 monitoring
   - 100ms read performance vs 10s API calls
   - 14 tests passing

5. **Monitoring Infrastructure** ✅
   - LangSmith integration with local fallback
   - LocalTokenTracker for offline usage
   - Cost tracking and optimization
   - 12 tests passing

6. **Architecture Planning** ✅
   - 5-agent architecture finalized
   - Tech stack decisions documented
   - Cost projections: $8.50/mo MVP, $294/mo prod

### ✅ Phase 3A: LangChain Foundation (Weeks 5-6) - COMPLETED
7. **LLM Providers** ✅
   - [x] Claude 3.5 Sonnet provider
   - [x] Gemini 2.0 Flash Thinking provider
   - [x] Hybrid router (complexity-based)
   - [x] 15/17 integration tests passing

8. **Vector Store Abstraction** ✅
   - [x] ChromaDB implementation (MVP)
   - [x] VectorStore interface
   - [x] all-MiniLM-L6-v2 embeddings
   - [x] 18/18 unit tests + 3/3 integration tests
   - [x] **Total: 79/81 tests passing (97.5%)**

### 🔄 Phase 3B: Agent Implementation (Weeks 7-8) - CURRENT
9. **Multi-Agent System**
   - [ ] Base agent framework
   - [ ] Strategy Agent (pit stops, tires)
   - [ ] Weather Agent (forecasts, adaptation)
   - [ ] Performance Agent (lap analysis)
   - [ ] Race Control Agent (flags, incidents)
   - [ ] Race Position Agent (gaps, positions)
   - [ ] Agent orchestrator

10. **RAG System**
    - [ ] Document indexing
    - [ ] Semantic retrieval
    - [ ] Context augmentation
    - [ ] >80% accuracy target

### 📋 Phase 3C: Tool Integration (Weeks 9-10) - PLANNED
11. **LangChain Tool Wrapper**
    - [ ] Convert 13 MCP tools to LangChain format
    - [ ] Dynamic tool selection
    - [ ] Parallel execution

12. **Optimization**
    - [ ] Response time <3s (P95)
    - [ ] Token usage tracking
    - [ ] Cache strategy refinement

### 📋 Phase 4: User Interface (Weeks 11-12) - PLANNED
13. **Chatbot Interface**
    - [ ] Natural language processing
    - [ ] Multi-turn conversations
    - [ ] Context management

14. **Visualization Dashboard**
    - [ ] Real-time displays
    - [ ] Interactive charts
    - [ ] Custom layouts

15. **Deployment**
    - [ ] API documentation
    - [ ] Production configuration
    - [ ] CI/CD pipeline

---

## 📚 Documentation

### Essential Guides
- **[📖 Documentation Index](docs/INDEX.md)** - Complete documentation map
- **[🚀 Quick Start](docs/QUICK_START.md)** - Installation and setup
- **[🔧 Development Guide](docs/DEVELOPMENT_GUIDE.md)** - Coding standards and workflow

### Architecture & Design
- **[🏗️ Architecture Decisions](docs/ARCHITECTURE_DECISIONS.md)** - ADR and framework selection
- **[⭐ Tech Stack Final](docs/TECH_STACK_FINAL.md)** - Complete technology decisions
- **[📋 Project Specifications](docs/PROJECT_SPECIFICATIONS.md)** - Technical specifications

### AI & Agents
- **[🤖 Gemini Flash Thinking Guide](docs/GEMINI_FLASH_THINKING_GUIDE.md)** - LLM implementation guide
- **[🏁 Race Position Agent Spec](docs/RACE_POSITION_AGENT_SPEC.md)** - 5th agent specification

### Data & Systems
- **[💾 Cache System Implementation](docs/CACHE_SYSTEM_IMPLEMENTATION.md)** - Hybrid cache details
- **[🔌 MCP API Reference](docs/MCP_API_REFERENCE.md)** - 13 tools documentation
- **[📊 Monitoring Setup](docs/MONITORING_SETUP.md)** - LangSmith + local tracking

---

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
# Requiere Python 3.13
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
