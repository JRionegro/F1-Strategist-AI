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
- **LLM Hybrid**: Claude (Opus/Sonnet/Haiku) + Gemini 2.0 Flash Thinking (68% cost savings)
- **Vector Store**: ChromaDB (MVP) + Pinecone option (production)
- **Embeddings**: all-MiniLM-L6-v2 (384 dims, local, free)
- **Cost Projection**: $8.50/mo MVP, $294/mo production
- **Claude Models**: Full support for Opus (complex), Sonnet (balanced), Haiku (fast)

### ✅ Phase 3A: LangChain Foundation (COMPLETED)

- **LLM Providers**: 15/15 tests passing (Claude, Gemini, Hybrid Router)
- **RAG Module**: VectorStore interface, ChromaDB implementation
- **Unit Tests**: 15/15 passing (with mocks)
- **Integration Tests**: 3/3 passing (Python 3.13)

### 🔄 Phase 4: Dash UI Implementation (Current)

- **Dash Framework**: Multi-dashboard container application
- **Active Dashboards**: 
  - ✅ AI Assistant (Priority 1)
  - ✅ Race Overview with team colors (Priority 2)
  - ✅ Weather (Priority 3)
  - ✅ Telemetry (Priority 4)
  - ✅ Race Control (Priority 5)
- **AI Chatbot Features** 🆕:
  - ✅ Real LLM integration (Claude + Gemini)
  - ✅ HybridRouter for smart query routing
  - ✅ RAG-powered context-aware responses
  - ✅ API key configuration via sidebar UI
  - ✅ Auto-clear chat on context change
  - ✅ Proactive alerts during simulation
  - ✅ Quick Actions: AI Gaps, Tire Status, Pit Window, **Overtake Prediction** 🆕
- **RAG Document Management** 🆕:
  - ✅ One-click document upload (PDF, DOCX, Markdown)
  - ✅ 7 document categories (Global, Strategy, Weather, etc.)
  - ✅ AI-powered category suggestion using LLM
  - ✅ Automatic PDF/DOCX to Markdown conversion
  - ✅ Real-time ChromaDB indexing
  - ✅ Document backup and version control
- **Predictive AI** 🆕:
  - ✅ Overtake probability prediction (heuristic model)
  - ✅ Integrated into AI Assistant quick actions
  - 📋 Advanced ML models (see Roadmap below)
- **Live Mode**: 
  - ✅ Automatic availability detection (±3 hours window)
  - ✅ Context controls locking when Live mode active
  - ✅ Driver selector remains active for focus
  - ✅ Real-time data updates (<5s latency)
- **Layout**: 65%/35% column split with responsive grid
- **Simulation Mode**: Full playback controls with speed adjustment

See [UI_UX_SPECIFICATION.md](docs/project_development/UI_UX_SPECIFICATION.md) for complete UI documentation.

---

## 🚧 MVP Pending Features

### Dashboards Not Yet Implemented

- **📊 Tire Strategy Dashboard**: Visual tire compound analysis, degradation tracking, compound comparison
- **⏱️ Lap Analysis Dashboard**: Sector times breakdown, stint progression analysis, pace comparison
- **🏁 Qualifying Dashboard**: Qualifying session progression, elimination tracking, best lap highlights
- **🎯 Track Map (Interactive)**: Enhanced 3D track visualization with driver positions overlay
- **📈 Performance Trends**: Long-term driver/team performance analytics across multiple races

### Predictive AI Expansion

Current implementation uses heuristic-based models. Future ML integration:

- **Pit Stop Timing Predictor**: Train on historical pit window data (FastF1 2018-2022)
- **Overtake Probability Model**: ML classifier using gap, tire age, DRS availability
- **Tire Degradation Model**: Predict compound lifespan per circuit/driver
- **Race Result Predictor**: Monte Carlo simulation with ML-powered probability distributions
- **Safety Car Predictor**: Incident probability based on historical race control patterns

See [PHASE_4_PREDICTIVE_AI.md](docs/project_development/PHASE_4_PREDICTIVE_AI.md) for detailed roadmap.

### FastF1 Integration for Pre-2023 Data

Current data coverage: **OpenF1 API (2023-present only)**

Planned hybrid data layer:

- **OpenF1 Primary**: Live sessions + 2023+ historical data
- **FastF1 Fallback**: 2018-2022 historical race data
- **Unified Interface**: Seamless provider switching based on year
- **Cache Strategy**: Parquet format for both sources
- **Telemetry Enhancement**: High-frequency telemetry data from FastF1 cache

Benefits:
- 5+ years of additional historical data
- Enhanced telemetry resolution for analysis
- Training data for predictive ML models
- Comparative analysis across regulation eras

### Known Limitations

- **Data Coverage**: Limited to 2023+ (OpenF1 API constraint)
- **Telemetry Frequency**: Lower resolution than FastF1 for recent seasons
- **Predictive Models**: Currently heuristic-based, not ML-trained
- **Real-Time Latency**: 5-second update interval (OpenF1 API limitation)
- **Track Map**: Static images, no real-time driver animation yet

---

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
- **RAG Integration** - ChromaDB for circuit/strategy knowledge
- **AI Chatbot Modes**:
  - Single provider (Claude or Gemini only)
  - Hybrid mode (both keys, smart routing)
  - API keys configurable via UI sidebar

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

### 📋 Phase 4: User Interface (Weeks 11-12) - IN PROGRESS

**Active Dashboards (Phase 1)**:
1. ✅ **AI Assistant** - Multi-agent chatbot (MVP - Active)
2. ✅ **Race Overview** - Live race tracking (MVP - Active)
3. 🔄 **Weather** - Track conditions (In Development)
4. 🔄 **Telemetry** - Multi-driver comparison (In Development)
5. 🔄 **Race Control** - Flags and messages (In Development)

**Phase 2 Dashboards** (Coming Soon):
- 📋 Tire Strategy
- ⏱️ Lap Analysis
- 🏁 Qualifying Progress

13. **Chatbot Interface**
    - [x] Natural language processing (AI Assistant active)
    - [x] Multi-turn conversations
    - [x] Context management

14. **Visualization Dashboard**
    - [x] Real-time displays (Race Overview active)
    - [ ] Interactive charts (In development)
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
- F1 Race Replay by Benjamin Sloane (MIT License) for the track map visualization inspiration (https://github.com/bmsloane/f1-race-replay)

## Contact

Project maintained by: Jorge G.

---

**Note**: This project is for educational and research purposes.
It is not affiliated with Formula 1 or any F1 teams.
