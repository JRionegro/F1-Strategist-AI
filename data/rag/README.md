# RAG Documents Directory

This directory contains documents for the F1 Strategist AI RAG (Retrieval-Augmented
Generation) system. Documents are organized by year and circuit to provide
context-specific information to the AI agents.

## Directory Structure

```
data/rag/
├── global/                    # Documents applicable to all years
│   └── f1_basics.md          # F1 fundamentals
├── templates/                 # Templates for auto-generating docs
│   ├── strategy_template.md
│   ├── weather_template.md
│   └── tire_template.md
├── {year}/                    # Year-specific documents
│   ├── fia_regulations.md    # FIA regulations (converted from PDF)
│   ├── tire_compounds.md     # Pirelli compounds for the year
│   └── circuits/
│       └── {circuit_name}/   # Circuit-specific docs
│           ├── strategy_guide.md
│           ├── weather_patterns.md
│           └── tire_degradation.md
```

## Supported File Formats

The DocumentLoader supports:

- **Markdown (.md)** - Primary format, directly indexed
- **PDF (.pdf)** - Converted to Markdown before indexing (FIA regulations)
- **Word (.docx)** - Converted to Markdown before indexing

## Document Categories

| Category | Agent | Description |
|----------|-------|-------------|
| `strategy` | StrategyAgent | Pit stops, race strategy, circuit characteristics |
| `weather` | WeatherAgent | Weather patterns, temperature impact, rain strategy |
| `tire` | TireAgent | Compound performance, degradation, stint lengths |
| `fia` | All Agents | Official regulations, rules, procedures |
| `global` | All Agents | F1 basics, general knowledge |

## Adding New Documents

1. Place the document in the appropriate folder
2. Use clear naming: `{topic}_{subtopic}.md`
3. Include YAML frontmatter with metadata:

```yaml
---
category: strategy|weather|tire|fia|global
circuit: bahrain|monaco|... (optional)
year: 2024|2025|... (optional)
tags: [pit-stop, undercut, safety-car]
---
```

4. Reload RAG from the UI or restart the application

## Auto-Generation

Templates in `templates/` can be used to auto-generate circuit documents
based on historical OpenF1 data. Use the "Generate Templates" button in
the RAG sidebar section.
