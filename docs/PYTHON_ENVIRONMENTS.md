# Python Environments - F1 Strategist AI

## Project Standard Version

**The project uses exclusively Python 3.13** to ensure full compatibility with all dependencies.

### **venv** (Python 3.13) - Single Development Environment

- **Location**: `./venv/`
- **Python**: 3.13.9
- **Purpose**: Development, unit tests, integration tests, and production
- **Dependencies**: All (pandas, fastf1, anthropic, google-generativeai, mcp, langchain, chromadb, sentence-transformers, pytest-asyncio)

## Why Python 3.13?

**ChromaDB 1.3.7 requires Python ≤ 3.13** due to dependencies on Pydantic v1, which is incompatible with Python 3.14+.

Since ChromaDB is a critical dependency for the RAG (Retrieval-Augmented Generation) module, the project fully migrated to Python 3.13 to:
- ✅ Universal compatibility with all dependencies
- ✅ Simplify development (single environment)
- ✅ Facilitate production deployments
- ✅ Avoid versioning issues

## Installation

### Create environment

```powershell
# Requires Python 3.13 installed
python -m venv venv
.\venv\Scripts\Activate.ps1

# Verify version
python --version  # Should show Python 3.13.x

# Install dependencies
pip install -r requirements.txt
```

### Main dependencies installed

```
pandas>=2.3.3
fastf1>=3.7.0
anthropic>=0.75.0
google-generativeai>=0.8.6
mcp>=1.25.0
langchain>=1.2.0
langchain-anthropic
langchain-google-genai
langchain-chroma
chromadb>=1.3.7
sentence-transformers
pytest>=9.0.2
pytest-asyncio>=1.3.0
```

## Running Tests

### All tests (recommended)

```powershell
.\venv\Scripts\Activate.ps1
pytest tests/ -v
```

**Expected result**: 79 tests passing, 2 skipped, 13 errors (benign teardown errors on Windows)

### Tests by module

```powershell
# Cache system
pytest tests/test_cache_system.py -v          # 14 tests

# Data provider
pytest tests/test_f1_data_provider.py -v      # 5 tests

# LLM providers
pytest tests/test_llm_providers.py -v         # 15 tests (2 skipped without API keys)

# MCP server
pytest tests/test_mcp_server.py -v            # 24 tests

# RAG/Vector store
pytest tests/test_vector_store.py -v          # 18 tests
pytest tests/test_chromadb_integration.py -v  # 3 tests
```

## Notes on Teardown Errors

ChromaDB tests generate **13 benign teardown errors** on Windows:
```
PermissionError: [WinError 32] The process cannot access the file...
```

**This does NOT affect functionality**. This is a known Windows issue where SQLite files cannot be deleted while in use. Tests PASS correctly, only temporary cleanup fails.

## Production

For production deployment, use the same environment:

```bash
python3.13 -m venv venv_prod
source venv_prod/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

## Change History

### December 2025: Migration to Python 3.13 Exclusive

**Problem detected**: ChromaDB 1.3.7 is incompatible with Python 3.14 due to Pydantic v1 dependencies.

**Solution implemented**: 
- Complete project migration to Python 3.13
- Removal of dual environment (venv/venv313)
- Single virtual environment for all development
- 79/81 tests passing (97.5% success)

**Current status**: ✅ Project 100% functional on Python 3.13
