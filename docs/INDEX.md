# F1 Strategist AI - Documentation Index

**Last Updated**: January 18, 2026  
**Project Status**: Production Ready ✅

---

## 📖 Main Documentation

| Document | Description |
|----------|-------------|
| [README.md](README.md) | Complete project overview, architecture, and technology stack |
| [QUICK_START.md](QUICK_START.md) | Installation and setup guide |

---

## 🚀 Development Documentation

All technical specifications, implementation details, and architectural decisions
are located in the [project_development/](project_development/) folder.

### Architecture and Specifications

| Document | Description |
|----------|-------------|
| [TECH_STACK_FINAL.md](project_development/TECH_STACK_FINAL.md) | Technology decisions and stack |
| [PROJECT_SPECIFICATIONS.md](project_development/PROJECT_SPECIFICATIONS.md) | Technical specifications |
| [ARCHITECTURE_DECISIONS.md](project_development/ARCHITECTURE_DECISIONS.md) | ADRs (Architecture Decision Records) |
| [AGENTS_ARCHITECTURE.md](project_development/AGENTS_ARCHITECTURE.md) | Multi-agent system design |

### API and Data

| Document | Description |
|----------|-------------|
| [MCP_API_REFERENCE.md](project_development/MCP_API_REFERENCE.md) | MCP Server API (19 tools) |
| [OPENF1_MIGRATION.md](project_development/OPENF1_MIGRATION.md) | OpenF1 data provider |

### User Interface

| Document | Description |
|----------|-------------|
| [UI_UX_SPECIFICATION.md](project_development/UI_UX_SPECIFICATION.md) | Dashboard and interface specs |
| [LIVE_LEADERBOARD_IMPLEMENTATION.md](project_development/LIVE_LEADERBOARD_IMPLEMENTATION.md) | Leaderboard implementation |

### RAG System

| Document | Description |
|----------|-------------|
| [RAG_DOCUMENT_MANAGEMENT_PLAN.md](project_development/RAG_DOCUMENT_MANAGEMENT_PLAN.md) | RAG implementation plan |
| [PHASE_3A_LLM_RAG.md](project_development/PHASE_3A_LLM_RAG.md) | LLM and RAG integration |

### Development Guides

| Document | Description |
|----------|-------------|
| [DEVELOPMENT_GUIDE.md](project_development/DEVELOPMENT_GUIDE.md) | Development workflow and logging system |
| [PYTHON_ENVIRONMENTS.md](project_development/PYTHON_ENVIRONMENTS.md) | Python 3.13 setup |
| [PROJECT_STATUS.md](project_development/PROJECT_STATUS.md) | Current status and progress |

### Phase Reports

| Document | Description |
|----------|-------------|
| [PHASE_1_2_FOUNDATION.md](project_development/PHASE_1_2_FOUNDATION.md) | Foundation and Data Layer |
| [PHASE_2C_CACHE_SYSTEM.md](project_development/PHASE_2C_CACHE_SYSTEM.md) | Cache system implementation |
| [PHASE_2D_ARCHITECTURE_PLANNING.md](project_development/PHASE_2D_ARCHITECTURE_PLANNING.md) | Architecture planning |
| [PHASE_3B_IMPLEMENTATION.md](project_development/PHASE_3B_IMPLEMENTATION.md) | Multi-agent implementation |
| [PHASE_3B_MULTIAGENT.md](project_development/PHASE_3B_MULTIAGENT.md) | Multi-agent system details |
| [PHASE_4_PREDICTIVE_AI.md](project_development/PHASE_4_PREDICTIVE_AI.md) | Predictive AI roadmap with test gates |

---

## 🎯 Quick Links

### Getting Started

- **New to the project?** → Start with [README.md](README.md)
- **Want to run it?** → Follow [QUICK_START.md](QUICK_START.md)

### Understanding the System

- **How does the AI work?** → [AGENTS_ARCHITECTURE.md](project_development/AGENTS_ARCHITECTURE.md)
- **What data is available?** → [MCP_API_REFERENCE.md](project_development/MCP_API_REFERENCE.md)
- **How does RAG help?** → [RAG_DOCUMENT_MANAGEMENT_PLAN.md](project_development/RAG_DOCUMENT_MANAGEMENT_PLAN.md)

### Technical Deep Dives

- **Technology choices** → [TECH_STACK_FINAL.md](project_development/TECH_STACK_FINAL.md)
- **Architecture decisions** → [ARCHITECTURE_DECISIONS.md](project_development/ARCHITECTURE_DECISIONS.md)
- **UI/UX design** → [UI_UX_SPECIFICATION.md](project_development/UI_UX_SPECIFICATION.md)
- **Logging & Debugging** → [DEVELOPMENT_GUIDE.md#logging-system](project_development/DEVELOPMENT_GUIDE.md#logging-system)

### 🆕 Latest Update (January 2026)

- Race overview and track map dashboards now consume a shared retirement map, keeping DNF timing and formatting consistent across the UI. See [PROJECT_STATUS.md](project_development/PROJECT_STATUS.md#-recent-achievements-january-18-2026) for details.

---

## 📊 Project Summary

### Components

| Component | Status | Description |
|-----------|--------|-------------|
| Multi-Agent System | ✅ | 5 specialized agents + orchestrator |
| RAG System | ✅ | ChromaDB with document upload UI |
| AI Chatbot | ✅ | Real LLM integration (Claude/Gemini) with RAG |
| MCP Server | ✅ | 19 tools for F1 data access |
| Dash UI | ✅ | Live and Simulation modes |
| Retirement Sync | ✅ | Track map and race overview share FastF1-derived DNF metadata |
| Cache System | ✅ | Parquet-based with >90% hit rate |

### Technology Stack

| Layer | Technologies |
|-------|--------------|
| Frontend | Dash, Plotly, Bootstrap |
| LLM | Claude (Sonnet/Opus), Gemini 2.0 Flash |
| Vector Store | ChromaDB, all-MiniLM-L6-v2 |
| Data | OpenF1 API, Parquet cache |
| Language | Python 3.13 |

---

## 📁 Repository Structure

```
docs/
├── README.md              # Project overview (CAPSTONE)
├── QUICK_START.md         # Installation guide
├── INDEX.md               # This file
└── project_development/   # Technical documentation
    ├── Architecture specs
    ├── API references
    ├── Phase reports
    └── Development guides
```
