# F1 Strategist AI

An AI-powered Formula 1 race strategy assistant with hybrid caching system for historical analysis and real-time monitoring.

## 🎯 Project Status

### ✅ Phase 1-2: Foundation & Data Layer (COMPLETED)

- **MCP Server**: 13 herramientas operativas (100% cobertura FastF1/OpenF1)
- **Cache System**: Sistema híbrido con modos historical y live
- **Data Provider**: Integración completa con FastF1 y OpenF1
- **Tests**: 53 tests pasando (39 MCP + 14 caché)

### 📋 Next: Phase 3 - AI Agents & RAG

Ver [ARCHITECTURE_DECISIONS.md](docs/ARCHITECTURE_DECISIONS.md) para el plan de implementación.

---

## 🚀 Quick Start

### Instalación

```bash
# Clonar repositorio
git clone [repo-url]
cd "F1 Strategist AI"

# Activar entorno virtual
.\venv\Scripts\Activate.ps1

# Instalar dependencias (si es necesario)
pip install -r requirements.txt
```

### Uso Básico

```python
from src.data import UnifiedF1DataProvider

# Inicializar con caché inteligente
provider = UnifiedF1DataProvider(use_smart_cache=True)

# Obtener resultados (rápido con caché)
results = provider.get_race_results(2024, 1)  # Bahrain
telemetry = provider.get_telemetry(2024, 1, "VER")
```

### Scripts de Utilidad

```bash
# Ver estadísticas de caché
python scripts/cache_stats.py

# Precargar temporada
python scripts/preload_season.py 2024

# Limpiar datos antiguos
python scripts/clean_cache.py --types telemetry
```

---

## 📊 Core Features

### Hybrid Cache System

- **Historical Mode**: Datos permanentes con Parquet optimizado
- **Live Mode**: Sesiones en tiempo real con OpenF1
- **Smart Retention**: Políticas automáticas por tipo de dato
- **Performance**: 100ms vs 10s (FastF1 directo)

### MCP Tools (13 Available)

1. `get_race_results` - Resultados oficiales
2. `get_qualifying_results` - Clasificación
3. `get_telemetry` - Telemetría detallada
4. `get_lap_times` - Tiempos por vuelta
5. `get_pit_stops` - Análisis de boxes
6. `get_weather` - Condiciones meteorológicas
7. `get_tire_strategy` - Estrategia de neumáticos
8. `get_practice_results` - Entrenamientos libres
9. `get_sprint_results` - Carreras sprint
10. `get_driver_info` - Información de pilotos
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
│   │   ├── cache_config.py      # Configuración de caché
│   │   ├── cache_manager.py     # Gestor híbrido
│   │   ├── f1_data_provider.py  # Provider unificado
│   │   ├── live_session_monitor.py  # Monitor tiempo real
│   │   └── models.py            # Dataclasses F1
│   ├── mcp_server/              # MCP Server (IMPLEMENTED ✅)
│   │   └── f1_data_server.py    # 13 herramientas MCP
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
