# RAG Document Management System - Implementation Plan

## Overview

Sistema de gestión de documentos RAG organizado por año/circuito, con UI en sidebar
para visualizar/editar documentos, carga dinámica en ChromaDB, y generación
automática de templates basados en histórico.

---

## Directory Structure

```
data/rag/
├── global/                          # Docs aplicables a todos los años
│   └── f1_basics.md
├── 2024/
│   ├── fia_regulations.md           # Reglamento FIA 2024 (convertido de PDF)
│   ├── tire_compounds.md            # Compuestos Pirelli 2024
│   ├── circuits/
│   │   ├── bahrain/
│   │   │   ├── strategy_guide.md    # Guía de estrategia
│   │   │   ├── weather_patterns.md  # Patrones meteorológicos
│   │   │   └── tire_degradation.md  # Degradación de neumáticos
│   │   ├── saudi_arabia/
│   │   │   └── ...
│   │   └── abu_dhabi/
│   │       └── ...
├── 2025/
│   ├── fia_regulations.md
│   ├── tire_compounds.md
│   └── circuits/
│       └── ...
├── 2026/
│   ├── fia_regulations.md           # Nuevo reglamento (sin DRS, etc.)
│   └── circuits/
│       └── ...
└── templates/                       # Templates para generar docs automáticamente
    ├── strategy_template.md
    ├── weather_template.md
    └── tire_template.md
```

---

## Implementation Steps

### Step 1: Create Directory Structure

**Status:** [x] COMPLETED (2025-01-02)

Create the `data/rag/` folder hierarchy with:

- `global/` folder with placeholder `f1_basics.md`
- `templates/` folder with base templates for each agent
- Year folders (2024, 2025) with `circuits/` subfolders
- README.md explaining the structure

**Files created:**

- `data/rag/README.md` ✅
- `data/rag/global/f1_basics.md` ✅
- `data/rag/templates/strategy_template.md` ✅
- `data/rag/templates/weather_template.md` ✅
- `data/rag/templates/tire_template.md` ✅
- `data/rag/2024/fia_regulations.md` ✅
- `data/rag/2024/tire_compounds.md` ✅
- `data/rag/2024/circuits/abu_dhabi/strategy.md` ✅
- `data/rag/2024/circuits/abu_dhabi/weather.md` ✅
- `data/rag/2024/circuits/abu_dhabi/tire_analysis.md` ✅

---

### Step 2: Implement DocumentLoader

**Status:** [x] COMPLETED (2025-01-02)

Created `src/rag/document_loader.py` with:

```python
class DocumentLoader:
    """Load and chunk markdown documents for RAG."""
    
    def __init__(self, base_path: str = "data/rag"):
        self.base_path = base_path
    
    def load_documents_for_context(
        self, 
        year: int, 
        circuit: str | None = None
    ) -> list[Document]:
        """
        Load documents for a specific year and optionally circuit.
        
        Loads:
        1. global/*.md (always)
        2. {year}/*.md (year-level docs)
        3. {year}/circuits/{circuit}/*.md (if circuit specified)
        """
        pass
    
    def chunk_document(
        self, 
        content: str, 
        metadata: dict
    ) -> list[Document]:
        """Split document into chunks with metadata."""
        pass
    
    def get_available_documents(
        self, 
        year: int, 
        circuit: str | None = None
    ) -> dict[str, list[str]]:
        """List available documents organized by category."""
        pass
```

**Dependencies:**

- `langchain.text_splitter.RecursiveCharacterTextSplitter`
- Existing `src/rag/vector_store.py`

---

### Step 3: Implement RAGManager

**Status:** [x] COMPLETED (2026-01-02)

Created `src/rag/rag_manager.py` with:

```python
class RAGManager:
    """Orchestrate RAG document loading and ChromaDB management."""
    
    def __init__(self):
        self.document_loader = DocumentLoader()
        self.vector_store = ChromaVectorStore()
        self.current_context = None
    
    def load_context(self, year: int, circuit: str) -> int:
        """
        Load documents for year/circuit into ChromaDB.
        Returns number of documents loaded.
        """
        pass
    
    def reload(self) -> int:
        """Reload current context (after document edits)."""
        pass
    
    def clear_collection(self) -> None:
        """Clear all documents from ChromaDB."""
        pass
    
    def get_stats(self) -> dict:
        """Get current RAG statistics (doc count, chunks, etc.)."""
        pass
    
    def list_documents(self) -> dict[str, list[dict]]:
        """List all loaded documents with metadata."""
        pass
```

---

### Step 4: Add RAG Section to Sidebar UI

**Status:** [x] COMPLETED (2026-01-02)

Added new collapsible RAG Documents section to `app_dash.py` sidebar with:

```python
dbc.AccordionItem(
    [
        # RAG Status indicator
        html.Div(id="rag-status", className="mb-2"),
        
        # Document list by category
        html.Div([
            html.H6("📋 Strategy Agent", className="text-info"),
            html.Div(id="rag-strategy-docs"),
            
            html.H6("🌦️ Weather Agent", className="text-info mt-2"),
            html.Div(id="rag-weather-docs"),
            
            html.H6("🛞 Tire Agent", className="text-info mt-2"),
            html.Div(id="rag-tire-docs"),
            
            html.H6("📖 FIA Regulations", className="text-info mt-2"),
            html.Div(id="rag-fia-docs"),
        ]),
        
        # Action buttons
        html.Div([
            dbc.Button("🔄 Reload RAG", id="rag-reload-btn", size="sm", className="me-2"),
            dbc.Button("📝 Generate Templates", id="rag-generate-btn", size="sm"),
        ], className="mt-3"),
    ],
    title="📚 RAG Documents",
    className="mb-3"
),
```

**Callbacks needed:**

- `update_rag_document_list`: Update doc list when year/circuit changes
- `reload_rag`: Reload ChromaDB when button clicked
- `generate_templates`: Generate docs from historical data

---

### Step 5: Implement Template Generator

**Status:** [x] COMPLETED (2026-01-02)

Created `src/rag/template_generator.py` with:

- `TemplateGenerator` class with circuit data for 20+ F1 circuits
- `GeneratedDocument` dataclass for structured output
- `CIRCUIT_DATA` dict with lap length, pit loss, DRS zones, etc.
- `CIRCUIT_GROUPS` for circuit similarity mapping
- Historical data fetching from OpenF1 API
- Template variable substitution with fallback to "N/A"

**Key Features:**

- `generate_for_circuit(year, circuit)`: Generate strategy, weather, tire docs
- `_fetch_historical_data()`: Get past race data from OpenF1
- `_get_similar_circuits()`: Find similar circuits by characteristics
- `_fill_template()`: Replace {variables} with actual data
- Singleton pattern for resource reuse

**Tests:** 16 tests in `tests/test_template_generator.py` (all passing)

```python
class TemplateGenerator:
    """Generate RAG documents from templates and historical data."""
    
    def __init__(self):
        self.openf1_provider = OpenF1DataProvider()
        self.templates_path = "data/rag/templates"
    
    def generate_for_circuit(
        self, 
        year: int, 
        circuit: str,
        use_historical: bool = True
    ) -> dict[str, str]:
        """
        Generate all documents for a circuit.
        
        Args:
            year: Target year
            circuit: Circuit name (e.g., "bahrain")
            use_historical: Use historical data from OpenF1
            
        Returns:
            Dict of {filename: content}
        """
        pass
    
    def _generate_strategy_doc(
        self, 
        year: int, 
        circuit: str, 
        historical_data: dict
    ) -> str:
        """Generate strategy guide from template + data."""
        pass
    
    def _generate_weather_doc(
        self, 
        year: int, 
        circuit: str, 
        historical_data: dict
    ) -> str:
        """Generate weather patterns doc from template + data."""
        pass
    
    def _generate_tire_doc(
        self, 
        year: int, 
        circuit: str, 
        historical_data: dict
    ) -> str:
        """Generate tire degradation doc from template + data."""
        pass
    
    def _get_similar_circuits(self, circuit: str) -> list[str]:
        """Get list of similar circuits for data augmentation."""
        # Circuit similarity mapping
        pass
```

**Circuit Similarity Groups:**

| Group | Circuits | Characteristics |
|-------|----------|-----------------|
| Street | Monaco, Singapore, Baku, Jeddah, Las Vegas | Tight, low grip, safety cars |
| High-Speed | Monza, Spa, Silverstone | Long straights, low downforce |
| High-Degradation | Barcelona, Bahrain, Austin | Aggressive tire wear |
| Technical | Hungary, Zandvoort, Suzuka | High downforce, few overtakes |

---

### Step 6: FIA Regulations PDF Converter

**Status:** [x] SKIPPED - Redundant

**Reason:** `DocumentLoader` already implements PDF/DOCX conversion in `_load_pdf()` and `_load_docx()` methods:

- Uses `pymupdf4llm` for PDF → Markdown conversion
- Uses `python-docx` for DOCX → text conversion
- Automatic chunking with `_chunk_content()`

Users can simply upload FIA regulation PDFs via the existing upload mechanism, and they will be automatically converted and indexed in ChromaDB.

**No additional implementation needed.**

---

### Step 7: Connect RAG to Context Changes

**Status:** [x] COMPLETED (2026-01-02)

Add callback in `app_dash.py`:

```python
@app.callback(
    [Output("rag-status", "children"),
     Output("rag-strategy-docs", "children"),
     Output("rag-weather-docs", "children"),
     Output("rag-tire-docs", "children"),
     Output("rag-fia-docs", "children")],
    [Input("year-dropdown", "value"),
     Input("circuit-dropdown", "value")],
    prevent_initial_call=False
)
def update_rag_on_context_change(year, circuit):
    """Reload RAG documents when context changes."""
    if not year or not circuit:
        return "⚠️ Select year and circuit", [], [], [], []
    
    # Load documents into ChromaDB
    rag_manager = get_rag_manager()
    doc_count = rag_manager.load_context(year, circuit)
    
    # Get document lists
    docs = rag_manager.list_documents()
    
    # Format for display
    status = f"✅ {doc_count} documents loaded"
    strategy_list = _format_doc_list(docs.get("strategy", []))
    weather_list = _format_doc_list(docs.get("weather", []))
    tire_list = _format_doc_list(docs.get("tire", []))
    fia_list = _format_doc_list(docs.get("fia", []))
    
    return status, strategy_list, weather_list, tire_list, fia_list
```

---

### Step 8: Document Editor Modal (Optional)

**Status:** [x] COMPLETED (2026-01-02)

Added modal for in-app document editing in `app_dash.py`:

**Components:**

- `dbc.Modal` with id `doc-editor-modal` (xl size, centered)
- `dcc.Textarea` with monospace font for markdown editing
- Save/Cancel buttons
- `dcc.Store` for tracking current document path

**Callbacks:**

- `handle_document_editor`: Pattern-matching callback using `ALL`
  - Opens modal when document link/icon clicked
  - Loads document content into textarea
  - Saves edited content back to file
  - Auto-closes on save or cancel

**Features:**

- Clickable document names in sidebar (dotted underline, blue color)
- Pencil icon for explicit edit action
- Dark theme textarea matching app style
- Error handling for missing/invalid files
- Status messages for save success/failure

---

## Document Templates Content

### Strategy Template (`strategy_template.md`)

```markdown
# {circuit_name} - Strategy Guide

## Circuit Characteristics

- **Type:** {circuit_type}
- **Lap Length:** {lap_length} km
- **Total Laps:** {total_laps}
- **Pit Lane Time Loss:** {pit_loss} seconds
- **DRS Zones:** {drs_zones}

## Overtaking Opportunities

{overtaking_analysis}

## Pit Stop Windows

| Strategy | Stop 1 | Stop 2 | Compounds |
|----------|--------|--------|-----------|
| Optimal  | Lap {s1_opt} | - | {compounds_opt} |
| Aggressive | Lap {s1_agg} | Lap {s2_agg} | {compounds_agg} |

## Safety Car Probability

- **Historical SC Rate:** {sc_rate}%
- **Common SC Zones:** {sc_zones}

## Historical Winning Strategies

{historical_strategies}
```

### Weather Template (`weather_template.md`)

```markdown
# {circuit_name} - Weather Patterns

## Typical Conditions

- **Average Air Temp:** {avg_air_temp}°C
- **Average Track Temp:** {avg_track_temp}°C
- **Rain Probability:** {rain_prob}%
- **Dominant Wind Direction:** {wind_dir}

## Temperature Evolution

{temp_evolution_description}

## Rain Impact

{rain_impact_analysis}

## Historical Weather Data

| Year | Air Temp | Track Temp | Rain | Notes |
|------|----------|------------|------|-------|
{historical_weather_table}
```

### Tire Template (`tire_template.md`)

```markdown
# {circuit_name} - Tire Analysis

## Circuit Demands

- **Tire Stress Level:** {stress_level}/10
- **Front-Limited / Rear-Limited:** {limitation}
- **Key Corners for Degradation:** {key_corners}

## Compound Performance

| Compound | Optimal Window | Deg/Lap | Max Stint |
|----------|----------------|---------|-----------|
| SOFT     | {soft_window}  | {soft_deg} | {soft_max} |
| MEDIUM   | {med_window}   | {med_deg}  | {med_max} |
| HARD     | {hard_window}  | {hard_deg} | {hard_max} |

## Graining vs Degradation

{graining_analysis}

## Historical Stint Lengths

{historical_stints}
```

---

## Dependencies

Add to `requirements.txt`:

```
pymupdf4llm>=0.0.10
langchain>=0.1.0
langchain-text-splitters>=0.0.1
```

---

## Testing Plan

1. **Unit Tests:**
   - `test_document_loader.py`: Test loading and chunking
   - `test_rag_manager.py`: Test context loading/reloading
   - `test_template_generator.py`: Test doc generation

2. **Integration Tests:**
   - Load docs for Abu Dhabi 2024, verify in ChromaDB
   - Generate templates for new circuit
   - Test UI callbacks

---

## Notes

- 2026 regulations will be significantly different (no DRS, new aero)
- OpenF1 API availability for 2026 is uncertain
- Consider caching generated templates to avoid repeated API calls
- FIA PDFs are typically 100+ pages, extract only relevant sections

---

## Progress Tracking

| Step | Description | Status | Date |
|------|-------------|--------|------|
| 1 | Directory Structure | [x] | 2025-01-02 |
| 2 | DocumentLoader | [x] | 2025-01-02 |
| 3 | RAGManager | [x] | 2026-01-02 |
| 4 | Sidebar UI | [x] | 2026-01-02 |
| 5 | Template Generator | [x] | 2026-01-02 |
| 6 | PDF Converter | [x] SKIPPED | 2026-01-02 |
| 7 | Context Callbacks | [x] | 2026-01-02 |
| 8 | Document Editor | [x] | 2026-01-02 |

**✅ ALL STEPS COMPLETED (8/8)**

The RAG Document Management System is fully implemented.
