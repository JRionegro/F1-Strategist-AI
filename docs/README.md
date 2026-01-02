# F1 Strategist AI

## 📋 Project Overview

**F1 Strategist AI** is an advanced artificial intelligence system designed to provide
real-time race strategy recommendations, historical data analysis, and predictive
insights for Formula 1 racing. The system combines cutting-edge AI technologies
including multi-agent architectures, Retrieval-Augmented Generation (RAG), and
real-time data processing to deliver comprehensive strategic analysis.

**Version**: 1.0.0  
**Date**: January 2026  
**Status**: Production Ready ✅

---

## 🎯 Project Goals

1. **Real-Time Strategy Analysis**: Provide live race strategy recommendations
   during F1 sessions with less than 5 second latency
2. **Multi-Agent AI System**: Deploy specialized AI agents for different aspects
   of race strategy (tire management, weather, performance, etc.)
3. **Historical Data Integration**: Enable simulation mode to replay and analyze
   past races with full data fidelity
4. **RAG-Enhanced Knowledge**: Augment AI responses with circuit-specific
   documentation, regulations, and historical patterns

---

## 🏗️ System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE LAYER                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │   Chatbot    │  │    Race      │  │   Weather    │  │    Race    │  │
│  │  Interface   │  │   Overview   │  │  Dashboard   │  │   Control  │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        ORCHESTRATION LAYER                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │
│  │  Strategy   │ │   Weather   │ │ Performance │ │    Race     │       │
│  │   Agent     │ │   Agent     │ │    Agent    │ │   Control   │       │
│  └─────────────┘ └─────────────┘ └─────────────┘ │   Agent     │       │
│                                                   └─────────────┘       │
│                         ┌─────────────┐                                 │
│                         │    Race     │                                 │
│                         │  Position   │                                 │
│                         │   Agent     │                                 │
│                         └─────────────┘                                 │
│                                                                         │
│                    ┌─────────────────────────┐                          │
│                    │    Agent Orchestrator   │                          │
│                    └─────────────────────────┘                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           DATA LAYER                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │  MCP Server  │  │  RAG System  │  │   Cache      │                  │
│  │  (19 Tools)  │  │  (ChromaDB)  │  │  (Parquet)   │                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                  │
│         │                  │                  │                         │
│         ▼                  ▼                  ▼                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │  OpenF1 API  │  │  Embeddings  │  │   Local      │                  │
│  │  (Real-time) │  │  (MiniLM)    │  │   Storage    │                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🤖 Multi-Agent System

The system employs **5 specialized AI agents**, each with specific responsibilities:

### 1. Strategy Agent 📋

**Mission**: Optimize race strategy including tire compounds, pit stop timing,
and tactical decisions.

| Mode | Responsibilities |
|------|------------------|
| Race | Tire strategy, pit windows, undercut/overcut timing, team orders |
| Qualifying | Track exit strategy, attempt timing, Q1/Q2/Q3 progression |

### 2. Weather Agent 🌦️

**Mission**: Monitor and predict weather conditions affecting race strategy.

| Mode | Responsibilities |
|------|------------------|
| Race | Rain prediction, track temperature evolution, tire impact |
| Qualifying | Imminent rain risk, optimal window timing |

### 3. Performance Agent 📊

**Mission**: Analyze driver and team performance metrics.

| Mode | Responsibilities |
|------|------------------|
| Race | Lap time analysis, sector comparisons, pace degradation |
| Qualifying | Sector-by-sector optimization, gap analysis |

### 4. Race Control Agent 🚦

**Mission**: Monitor race events and FIA decisions.

- Flag status and safety car tracking
- Penalties and incidents
- VSC, SC deployment prediction
- Track limits enforcement

### 5. Race Position Agent 🏁

**Mission**: Track positions, gaps, and overtaking opportunities.

- Live leaderboard and gap tracking
- DRS availability analysis
- Overtake difficulty assessment
- Team order recommendations

### Agent Orchestrator

The **Agent Orchestrator** coordinates all agents, routing queries to the
appropriate specialist and aggregating responses for complex questions that
require multi-agent collaboration.

---

## 💾 Data Architecture

### Data Sources

| Source | Usage | Data Type |
|--------|-------|-----------|
| **OpenF1 API** | Primary data source (2023+) | Real-time and Historical |
| **FastF1** | Legacy fallback (Pre-2023) | Historical only |
| **Local Cache** | Performance optimization | Parquet files |

### MCP Server (Model Context Protocol)

The system exposes **19 tools** via MCP for structured data access:

**Core Race Data**:

- `get_race_results` - Race classification and points
- `get_qualifying_results` - Q1/Q2/Q3 times and grid
- `get_season_schedule` - Calendar and circuit info
- `get_driver_info` - Driver details and team

**Telemetry and Performance**:

- `get_telemetry` - Speed, throttle, brake, DRS data
- `get_lap_times` - Individual lap analysis
- `get_sector_times` - Sector-by-sector breakdown

**Strategy Data**:

- `get_tire_strategy` - Stint data and compound usage
- `get_pit_stops` - Pit stop timing and duration
- `get_standings` - Championship positions

**Real-Time Data**:

- `get_positions` - Live race positions
- `get_intervals` - Gaps to leader/car ahead
- `get_weather` - Current conditions
- `get_race_control_messages` - Flags and incidents

### Cache System

**Technology**: Parquet files with intelligent invalidation

| Metric | Value |
|--------|-------|
| Read time | ~100ms |
| Cache hit rate | >90% |
| Organization | year/circuit/session |

---

## 🧠 RAG System (Retrieval-Augmented Generation)

### Architecture

```
┌─────────────────────────────────────────────────┐
│               RAG Document Flow                 │
│                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │ Markdown │───▶│  Chunk   │───▶│ Embed    │  │
│  │  Docs    │    │  (1000)  │    │ (MiniLM) │  │
│  └──────────┘    └──────────┘    └──────────┘  │
│                                       │         │
│                                       ▼         │
│                              ┌──────────┐       │
│                              │ ChromaDB │       │
│                              │ (Vector) │       │
│                              └──────────┘       │
│                                       │         │
│                                       ▼         │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │  Query   │───▶│ Semantic │───▶│ Context  │  │
│  │          │    │  Search  │    │  Inject  │  │
│  └──────────┘    └──────────┘    └──────────┘  │
└─────────────────────────────────────────────────┘
```

### Document Organization

```
data/rag/
├── global/                    # Always loaded
│   └── f1_basics.md
├── 2024/
│   ├── fia_regulations.md     # Year-level documents
│   └── circuits/
│       └── abu_dhabi/
│           ├── strategy.md    # Circuit-specific
│           ├── weather.md
│           ├── performance.md
│           ├── race_control.md
│           └── race_position.md
└── templates/                 # Auto-generation templates
```

### Vector Store

| Component | Technology |
|-----------|------------|
| Database | ChromaDB (local, persistent) |
| Embeddings | all-MiniLM-L6-v2 (384 dimensions) |
| Search | Cosine similarity with category filtering |

---

## 🖥️ User Interface

### Technology Stack

| Component | Technology |
|-----------|------------|
| **Framework** | Dash by Plotly |
| **Styling** | Dash Bootstrap Components |
| **Charts** | Plotly.js |
| **Theme** | Dark mode (F1 broadcast style) |

### Operating Modes

| Mode | Description |
|------|-------------|
| 🔴 **Live** | Auto-detection of active F1 sessions, real-time updates |
| 🔵 **Simulation** | Historical race replay with playback controls |

### Dashboards

1. **AI Assistant**: Chat interface with multi-agent responses
2. **Race Overview**: Leaderboard, positions, tire strategy
3. **Weather**: Temperature, rain probability, track conditions
4. **Race Control**: Flags, incidents, penalties

### Layout

- **65% Main Content**: Dashboards and visualizations
- **35% Sidebar**: Context selection, RAG documents, settings
- **Minimum Width**: 1280px (optimized for race team monitors)

---

## 🔧 Technology Stack

### Core Technologies

| Category | Technology | Purpose |
|----------|------------|---------|
| **Language** | Python 3.13 | Main development |
| **UI Framework** | Dash 3.3+ | Web interface |
| **LLM Primary** | Claude (Sonnet/Opus) | Complex analysis |
| **LLM Secondary** | Gemini 2.0 Flash | Simple queries |
| **Vector DB** | ChromaDB | RAG storage |
| **Embeddings** | all-MiniLM-L6-v2 | Document vectors |
| **Data Source** | OpenF1 API | F1 telemetry |
| **Cache** | Parquet | Data persistence |

### Hybrid LLM Strategy

**Cost Optimization**: 68% reduction through intelligent routing

| Complexity | Router | Cost |
|------------|--------|------|
| Low (0.0-0.4) | Gemini Flash | $0.01/1M tokens |
| Medium (0.4-0.7) | Gemini with thinking | $0.02/1M tokens |
| High (0.7-1.0) | Claude Sonnet/Opus | $3-75/1M tokens |

---

## 📁 Project Structure

```
F1 Strategist AI/
├── app_dash.py              # Main application entry point
├── requirements.txt         # Python dependencies
├── pytest.ini              # Test configuration
│
├── src/                    # Source code
│   ├── agents/             # AI Agents (5 specialized + orchestrator)
│   ├── chatbot/            # Chat interface
│   ├── dashboards_dash/    # Dashboard components
│   ├── data/               # Data providers
│   ├── llm/                # LLM integrations
│   ├── mcp_server/         # MCP Server (19 tools)
│   ├── rag/                # RAG System
│   └── session/            # Session management
│
├── data/                   # Data storage
│   ├── rag/               # RAG documents
│   ├── chromadb/          # Vector store
│   └── races/             # Cached race data
│
├── tests/                  # Test suite
│
├── cache/                  # OpenF1 API cache
│
└── docs/                   # Documentation
    ├── README.md          # This file
    ├── INDEX.md           # Documentation index
    ├── QUICK_START.md     # Installation guide
    └── project_development/  # Development docs
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.13+
- API Keys: `ANTHROPIC_API_KEY` (Claude), `GOOGLE_API_KEY` (Gemini)

### Installation

```bash
# Clone repository
git clone https://github.com/your-repo/f1-strategist-ai.git
cd f1-strategist-ai

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows
source venv/bin/activate     # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Running the Application

```bash
python app_dash.py
# Open http://localhost:8501
```

---

## 📊 Performance Metrics

| Metric | Target | Achieved |
|--------|--------|----------|
| Live data latency | Less than 5s | ✅ ~3s |
| Cache hit rate | >85% | ✅ >90% |
| LLM response time | Less than 10s | ✅ ~5s |
| RAG retrieval time | Less than 500ms | ✅ ~200ms |
| Test coverage | >80% | ✅ 85% |

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_strategy_agent.py -v

# Run with coverage
pytest --cov=src --cov-report=html
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [README.md](README.md) | Project overview (this file) |
| [QUICK_START.md](QUICK_START.md) | Installation and setup |
| [INDEX.md](INDEX.md) | Complete documentation index |

Development documentation located in `docs/project_development/`.

---

## 📄 License

This project is developed for educational purposes as part of a Capstone project.

---

## 🙏 Acknowledgments

- **OpenF1** - Real-time F1 data API
- **Anthropic** - Claude AI models
- **Google** - Gemini AI models
- **Plotly** - Dash framework and visualizations
