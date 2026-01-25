# F1 Strategist AI - Quick Start Guide

## Running the Application 🏎️

### Launch Dash UI

#### Windows (PowerShell)

```powershell
# Using launcher script
.\run_app.ps1

# OR manually
.\venv\Scripts\Activate.ps1
python app_dash.py
```

#### Windows (Command Prompt)

```cmd
# Using launcher script
run_app.bat

# OR manually
.\venv\Scripts\activate.bat
python app_dash.py
```

#### Linux/macOS

```bash
# Using launcher script (first time: chmod +x run_app.sh)
./run_app.sh

# OR manually
source venv/bin/activate
python app_dash.py
```

**Application URL**: `http://localhost:8501`

### Interface Overview

The application features:
- **Mode Selector**: Switch between Live (🔴) and Simulation (🔵) modes
- **Context Panel**: Select Year, Circuit, Session, and Driver focus
- **Dashboard Selection**: Toggle multiple dashboards (AI Assistant, Race Overview, Weather, etc.)
- **Configuration Sidebar**: Configure API keys and settings
- **AI Chatbot**: Intelligent assistant with RAG-powered responses
- **Live Mode Features**:
  - Automatically detects active F1 sessions (±3 hours window)
  - Locks Context controls to current session
  - Real-time data updates every 5 seconds
- **Simulation Mode Features**:
  - Historical data replay with playback controls
  - Speed adjustment (1x to 3x)
  - Jump to specific laps or time points

### AI Chatbot Configuration 🤖 **NEW!**

The AI Chatbot uses real LLM providers (Claude and/or Gemini) for intelligent F1 strategy responses.

#### Setting Up API Keys via UI

1. **Open Configuration Panel**: Click the ⚙️ gear icon in the sidebar
2. **Enter API Keys**:
   - `Anthropic API Key`: For Claude (complex queries)
   - `Google API Key`: For Gemini (simple/moderate queries)
3. **Click Save**: Keys are stored securely in `.env` file
4. **Feedback**: A toast notification shows which provider(s) are active

#### Provider Behavior

| Keys Configured | Provider Used | Routing Behavior |
|-----------------|---------------|------------------|
| None | Error | Shows setup instructions in chat |
| Only Claude | ClaudeProvider | All queries go to Claude |
| Only Gemini | GeminiProvider | All queries go to Gemini |
| Both | HybridRouter | Complex → Claude, Simple → Gemini |

**HybridRouter** analyzes query complexity and routes accordingly:
- **Claude**: Multi-step analysis, strategic recommendations, comparisons
- **Gemini**: Quick lookups, simple facts, status queries

#### Chat Behavior

- **Auto-clear**: Chat history clears when you change Year, Circuit, Session, or Driver
- **Manual clear**: Use the "🗑️ Clear" button to reset conversation
- **Session-aware**: Responses include context from the selected session
- **RAG-enhanced**: Uses circuit-specific knowledge from the knowledge base

### AI Quick Actions 🚀

The chatbot includes one-click quick actions for common queries:

| Button | Description | Feature |
|--------|-------------|----------|
| **📊 AI Gaps** | Current gaps to cars ahead/behind focus driver | Live/Simulation |
| **🔧 Tire Status** | Tire compound, age, and degradation for focus driver | Live/Simulation |
| **🏁 Pit Window** | Optimal pit window recommendation | Simulation |
| **🔮 Predict** 🆕 | Overtake probability for next 5-10 laps | Simulation |

**Overtake Prediction** uses a heuristic model analyzing:
- Gap to car ahead
- Tire age differential
- Current tire compounds
- Track characteristics

Future versions will use ML models trained on historical overtake data.

### Managing RAG Documents 📚 **NEW!**

The application includes an integrated document management system to enhance AI responses with custom knowledge.

#### Uploading Documents

1. **Locate RAG Documents Section**: Scroll to the "📚 RAG Documents" section in the sidebar
2. **Choose Category**: Find the appropriate category for your document:
   - **🌐 Global**: General F1 knowledge (always loaded)
   - **📋 Strategy**: Tire strategy, pit stop tactics
   - **🌦️ Weather**: Weather impact, rain strategies
   - **⚡ Performance**: Car performance, lap time analysis
   - **🚩 Race Control**: Flags, penalties, regulations
   - **📊 Race Position**: Overtaking, race position strategies
   - **⚖️ FIA**: Official FIA regulations by year

3. **Click ➕ Button**: Next to the category name
4. **Select File**: Choose a PDF, DOCX, or Markdown file (max 10MB)
5. **Review AI Suggestion**: The system analyzes your document and suggests the best category
6. **Preview Content**: Check the document preview before uploading
7. **Confirm Upload**: Click "Upload Document" to process and index

#### Document Processing

- **PDF/DOCX Conversion**: Automatically converted to Markdown format
- **Chunking**: Split into 1000-character chunks with 200-character overlap
- **Embedding**: Vectorized using all-MiniLM-L6-v2 model
- **Indexing**: Stored in ChromaDB for semantic search
- **Backup**: Existing documents are backed up before overwriting

#### Supported File Formats

| Format | Extension | Auto-Convert | Max Size |
|--------|-----------|--------------|----------|
| Markdown | `.md` | No (native) | 10MB |
| PDF | `.pdf` | Yes (pymupdf) | 10MB |
| Word | `.docx` | Yes (python-docx) | 10MB |

#### Document Organization

Uploaded documents are stored in:
```
data/rag/
├── global/                # Global documents
├── {year}/
│   ├── fia_regulations.md # FIA regulations per year
│   └── circuits/
│       └── {circuit}/
│           ├── strategy.md
│           ├── weather.md
│           ├── performance.md
│           ├── race_control.md
│           └── race_position.md
```

#### Viewing & Editing Documents

- **View Document List**: Expand any category to see uploaded documents
- **Edit Existing**: Click on a document name to open it in the editor modal
- **Delete Document**: Use the "🗑️" button next to a document (not yet implemented)
- **Refresh Context**: RAG context is automatically reloaded when you change Year/Circuit

## Project Structure 📁

Your F1 Strategist AI project has been set up with the following structure:

```
F1 Strategist AI/
├── .github/                  # GitHub configurations and copilot instructions
├── .git/                     # Git repository (initialized)
├── src/                      # Source code
│   ├── mcp_servers/          # MCP server implementations
│   ├── agents/               # AI agent modules
│   ├── chatbot/              # Chatbot interface
│   ├── rag/                  # RAG system components
│   ├── visualizations/       # Visualization modules
│   ├── strategy/             # Core strategy algorithms
│   ├── __init__.py
│   └── main.py              # Application entry point
├── data/                     # Data storage
│   ├── races/                # Historical race data
│   └── telemetry/            # Telemetry data
├── tests/                    # Unit and integration tests
├── docs/                     # Documentation
│   ├── PROJECT_SPECIFICATIONS.md  # Detailed project specs
│   └── DEVELOPMENT_GUIDE.md       # Development workflow
├── notebooks/                # Jupyter notebooks for analysis
├── config/                   # Configuration files
│   └── .env.example         # Environment variables template
├── .gitignore               # Git ignore rules
├── requirements.txt         # Python dependencies
└── README.md               # Project overview
```

## Next Steps

### 1. Create Virtual Environment

```powershell
# Navigate to project directory
cd "c:\Users\jorgeg\OneDrive - CEGID\Desarrollador 10x con IA\CAPSTON PROJECT\F1\F1 Strategist AI"

# Create virtual environment
python -m venv venv

# Activate it
.\venv\Scripts\Activate.ps1

# Verify activation (you should see (venv) in prompt with Python 3.13)
python --version
```

### 2. Install Dependencies

```powershell
# Upgrade pip first
python -m pip install --upgrade pip

# Install all requirements
pip install -r requirements.txt
```

### 3. Configure Environment

```powershell
# Copy example config
Copy-Item config\.env.example config\.env

# Edit with your API keys
notepad config\.env
```

**Required API Keys**:
- `ANTHROPIC_API_KEY`: For Claude 3.5 Sonnet (complex queries)
- `GOOGLE_API_KEY`: For Gemini 2.0 Flash Thinking (simple/moderate queries)
- `LANGSMITH_API_KEY`: For monitoring (optional, has local fallback)

> 💡 **Tip**: You can also configure API keys directly in the application!
> Open the ⚙️ Configuration panel in the sidebar to set up your keys without editing files.

**Key Configuration Variables**:
```env
# LLM Configuration
LLM_PROVIDER=hybrid  # Routes queries between Claude and Gemini
GEMINI_MODEL=gemini-2.0-flash-thinking-exp-1219

# Vector Store
VECTOR_STORE_PROVIDER=chromadb  # Use 'pinecone' for production
EMBEDDINGS_MODEL=all-MiniLM-L6-v2

# Caching
USE_REDIS=false  # MVP uses Parquet only

# Monitoring
LANGCHAIN_TRACING_V2=true
LANGSMITH_PROJECT=f1-strategist-ai
```

### 4. Test Installation

```powershell
# Run the main application
python src/main.py
```

## Development Phases

The project is organized into 6 phases over 12 weeks:

### ✅ Phase 0: Project Setup (COMPLETED)
- [x] Git repository initialized
- [x] Folder structure created
- [x] Documentation written
- [x] Configuration files created

### 📋 Phase 1: Foundation (Weeks 1-2)
- [ ] Set up virtual environment
- [ ] Install and test FastF1
- [ ] Create data ingestion pipeline
- [ ] Build basic MCP server

### 📋 Phase 2: Strategy Engine (Weeks 3-4)
- [ ] Implement tire degradation models
- [ ] Build pit stop optimizer
- [ ] Create fuel consumption calculator
- [ ] Develop race simulator

### 📋 Phase 3: AI Components (Weeks 5-7)
- [ ] Set up RAG system with ChromaDB
- [ ] Create Strategy Agent
- [ ] Implement Weather Agent
- [ ] Build Performance Agent
- [ ] Add Race Control Agent

### 📋 Phase 4: User Interface (Weeks 8-9)
- [ ] Develop chatbot interface
- [ ] Create visualization dashboard
- [ ] Build session-specific views
- [ ] Implement responsive design

### 📋 Phase 5: Advanced Features (Weeks 10-11)
- [ ] Add race simulation system
- [ ] Implement "what-if" scenarios
- [ ] Create comparison tools
- [ ] Optimize performance

### 📋 Phase 6: Testing & Deployment (Week 12)
- [ ] Write comprehensive tests
- [ ] Create documentation
- [ ] Set up CI/CD
- [ ] Deploy application

## Key Documents

| Document | Purpose |
|----------|---------|
| [README.md](../README.md) | Project overview and quick reference |
| [PROJECT_SPECIFICATIONS.md](PROJECT_SPECIFICATIONS.md) | Detailed technical specifications |
| [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md) | Development workflow and guidelines |
| [requirements.txt](../requirements.txt) | Python dependencies |
| [.env.example](../config/.env.example) | Environment configuration template |

## Important Commands

### Virtual Environment
```powershell
# Activate
.\venv\Scripts\Activate.ps1

# Deactivate
deactivate
```

### Git Commands
```powershell
# Check status
git status

# Create branch for new feature
git checkout -b feature/your-feature-name

# Commit changes
git add .
git commit -m "feat: your feature description"

# Push changes
git push origin feature/your-feature-name
```

### Testing
```powershell
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/test_strategy.py
```

### Code Quality
```powershell
# Format code
black src/

# Check linting
flake8 src/

# Type checking
mypy src/
```

## Resources

- **FastF1 Documentation**: https://docs.fastf1.dev/
- **LangChain Documentation**: https://python.langchain.com/
- **MCP Specification**: https://modelcontextprotocol.io/
- **Plotly Documentation**: https://plotly.com/python/
- **Streamlit Documentation**: https://docs.streamlit.io/

## Getting Help

1. Check [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md) for common issues
2. Review [PROJECT_SPECIFICATIONS.md](PROJECT_SPECIFICATIONS.md) for technical details
3. Look at example code in the `notebooks/` folder (to be created)

## Tips for Success

1. **Start Small**: Begin with Phase 1 and build incrementally
2. **Test Often**: Run tests after each significant change
3. **Document**: Add docstrings to all functions and classes
4. **Commit Regularly**: Make small, focused commits
5. **Follow PEP 8**: Use black and flake8 to maintain code quality

## Current Status (MVP - January 2026)

### ✅ Completed Phases

- ✅ **Phase 1-2: Foundation & Data Layer** - OpenF1 unified data source, hybrid cache system
- ✅ **Phase 2D: Architecture Planning** - 5-agent system, LLM hybrid router, RAG with ChromaDB
- ✅ **Phase 3A: LangChain Foundation** - LLM providers, vector store, 79/81 tests passing
- ✅ **Phase 4: Dash UI** - 5 active dashboards, AI chatbot with RAG, live/simulation modes

### 🚀 Ready to Use

The application is **fully functional** and ready for:
- Historical race analysis (2023+)
- Live race monitoring (±3 hours detection window)
- AI-powered strategy recommendations
- Multi-dashboard visualization
- Custom RAG document integration

### 🚧 Pending Features (Post-MVP)

See [README.md](../README.md#-mvp-pending-features) for detailed roadmap:
- Additional dashboards (Tire Strategy, Lap Analysis, Qualifying)
- ML-based predictive models (currently heuristic)
- FastF1 integration for pre-2023 historical data

## Next Immediate Steps

### For First-Time Users

1. **Activate virtual environment** (Python 3.13 required)
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

2. **Install dependencies** (if not already done)
   ```powershell
   pip install -r requirements.txt
   ```

3. **Configure API keys** (via UI or .env file)
   - Anthropic API Key for Claude
   - Google API Key for Gemini (optional but recommended)

4. **Launch the application**
   ```powershell
   python app_dash.py
   ```
   Open [http://localhost:8050](http://localhost:8050) in your browser

5. **Try it out!**
   - Select a recent race (e.g., Qatar 2025)
   - Choose a driver to focus on
   - Use AI quick actions or ask questions in chat
   - Toggle dashboards to explore different views

### For Developers

- Review [DEVELOPMENT_GUIDE.md](project_development/DEVELOPMENT_GUIDE.md) for coding standards
- Check [APPENDIX_DASH_SKILL.md](project_development/APPENDIX_DASH_SKILL.md) for dashboard development rules
- See [PHASE_4_PREDICTIVE_AI.md](project_development/PHASE_4_PREDICTIVE_AI.md) for ML integration roadmap

---

**MVP Complete - Ready for F1 Strategy Analysis! 🏁🚀**
