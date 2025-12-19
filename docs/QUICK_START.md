# F1 Strategist AI - Quick Start Guide

## Project Successfully Initialized! 🏎️

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

# Verify activation (you should see (venv) in prompt)
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

## Current Status

- ✅ Project structure created
- ✅ Git repository initialized
- ✅ Documentation written
- ✅ Configuration files created
- ⏳ Ready to start Phase 1: Foundation

## Next Immediate Steps

1. **Create virtual environment** (see instructions above)
2. **Install dependencies** from requirements.txt
3. **Configure environment** variables in config/.env
4. **Start Phase 1** following the DEVELOPMENT_GUIDE.md

---

**Ready to build something amazing! 🚀**

Good luck with your F1 Strategist AI project!
