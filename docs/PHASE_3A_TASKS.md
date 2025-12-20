# Phase 3A: LangChain Foundation - Task Plan

**Period**: Weeks 5-6 (December 21, 2025 - January 3, 2026)  
**Objective**: Establish LLM and Vector Store infrastructure  
**Status**: 🔄 IN PROGRESS

---

## 📋 Executive Summary

| Metric | Value |
|--------|-------|
| **Total Tasks** | 15 |
| **Completed** | 0 |
| **In Progress** | 0 |
| **Pending** | 15 |
| **Required Tests** | 15+ |
| **Deadline** | January 3, 2026 |

---

## 🎯 Phase 3A Objectives

1. ✅ Implement abstraction layer for LLMs
2. ✅ Integrate Claude 3.5 Sonnet provider
3. ✅ Integrate Gemini 2.0 Flash Thinking provider
4. ✅ Create hybrid router with complexity analysis
5. ✅ Implement ChromaDB store (MVP)
6. ✅ Create Pinecone stub (production preparation)
7. ✅ Factory pattern for vector stores
8. ✅ 15+ integration tests

---

## 📝 Tasks Ordered by Priority

### 🔴 HIGH PRIORITY - Week 1 (December 21-27)

#### Task 1: Abstract LLM Provider Interface ⭐ FOUNDATIONAL
**File**: `src/llm/provider.py` (already exists partially)  
**Estimated Duration**: 2 hours  
**Dependencies**: None  
**Status**: ⬜ Pending

**Subtasks**:
- [ ] Review existing interface in `provider.py`
- [ ] Add missing methods:
  - `generate_with_thinking()` for Gemini
  - `estimate_complexity()` for routing
  - `get_cost_estimate()` for tracking
- [ ] Define `LLMConfig` dataclass
- [ ] Document with complete docstrings
- [ ] Create basic unit tests (3 tests)

**Expected Output**:
```python
class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        pass
    
    @abstractmethod
    async def generate_with_thinking(self, prompt: str) -> LLMResponse:
        pass
    
    @abstractmethod
    def estimate_complexity(self, prompt: str) -> float:
        pass
```

---

#### Task 2: Claude 3.5 Sonnet Provider
**File**: `src/llm/claude_provider.py` (new)  
**Estimated Duration**: 4 hours  
**Dependencies**: Task 1  
**Status**: ⬜ Pending

**Subtasks**:
- [ ] Create class `ClaudeProvider(LLMProvider)`
- [ ] Implement authentication with Anthropic API
- [ ] Implement `generate()` with Claude 3.5 Sonnet
- [ ] Error handling (rate limits, API errors)
- [ ] Token counting and cost estimation
- [ ] Retry logic with exponential backoff
- [ ] Integration tests (5 tests):
  - Authentication test
  - Basic generation test
  - Error handling test
  - Cost estimation test
  - Retry logic test

**Required Configuration**:
```env
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-3-5-sonnet-20241022
CLAUDE_MAX_TOKENS=4096
CLAUDE_TEMPERATURE=0.7
```

---

#### Task 3: Gemini 2.0 Flash Thinking Provider
**File**: `src/llm/gemini_provider.py` (new)  
**Estimated Duration**: 5 hours  
**Dependencies**: Task 1  
**Status**: ⬜ Pending

**Subtasks**:
- [ ] Create class `GeminiProvider(LLMProvider)`
- [ ] Implement authentication with Google AI
- [ ] Implement `generate()` normal mode
- [ ] Implement `generate_with_thinking()` reasoning mode
- [ ] Detect and extract thinking blocks
- [ ] Token counting and cost estimation
- [ ] Integration tests (6 tests):
  - Authentication test
  - Normal mode test
  - Thinking mode test
  - Thinking blocks extraction test
  - Cost estimation test (compare normal vs thinking)
  - Fallback test (thinking → normal)

**Required Configuration**:
```env
GOOGLE_API_KEY=AIza...
GEMINI_MODEL=gemini-2.0-flash-thinking-exp-1219
GEMINI_ENABLE_THINKING=true
GEMINI_MAX_TOKENS=8192
GEMINI_TEMPERATURE=0.7
```

**Referencia**: [GEMINI_FLASH_THINKING_GUIDE.md](./GEMINI_FLASH_THINKING_GUIDE.md)

---

#### Task 4: Complexity Analyzer
**File**: `src/llm/complexity_analyzer.py` (new)  
**Estimated Duration**: 3 hours  
**Dependencies**: None  
**Status**: ⬜ Pending

**Subtasks**:
- [ ] Create class `ComplexityAnalyzer`
- [ ] Implement scoring based on:
  - Prompt length (>1000 tokens = +0.2)
  - Complex keywords ("analyze", "compare", "strategize")
  - Number of tools required (>5 = +0.3)
  - Multi-step reasoning needed
- [ ] Calibrate thresholds (0.4 and 0.7)
- [ ] Unit tests (4 tests):
  - Test simple queries (score < 0.4)
  - Test moderate queries (0.4 ≤ score < 0.7)
  - Test complex queries (score ≥ 0.7)
  - Test edge cases

**Scoring Examples**:
```python
# Simple (score: 0.2)
"Who won Bahrain 2024?" 

# Moderate (score: 0.5)
"Analyze Hamilton's tire strategy in Monaco 2024"

# Complex (score: 0.8)
"Compare optimal pit strategies across all 2024 races considering weather"
```

---

### 🟡 MEDIUM PRIORITY - Week 2 (December 28 - January 3)

#### Task 5: Hybrid Router
**File**: `src/llm/hybrid_router.py` (new)  
**Estimated Duration**: 4 hours  
**Dependencies**: Tasks 2, 3, 4  
**Status**: ⬜ Pending

**Subtasks**:
- [ ] Create class `HybridLLMRouter`
- [ ] Implement routing logic:
  ```python
  if complexity < 0.4:
      return gemini_provider.generate()
  elif complexity < 0.7:
      return gemini_provider.generate_with_thinking()
  else:
      return claude_provider.generate()
  ```
- [ ] Logging of routing decisions
- [ ] Usage metrics (% per provider)
- [ ] Automatic fallback (Gemini → Claude if fails)
- [ ] Integration tests (5 tests):
  - Test simple routing → Gemini normal
  - Test moderate routing → Gemini thinking
  - Test complex routing → Claude
  - Test fallback logic
  - Test usage metrics

**Configuration**:
```env
LLM_PROVIDER=hybrid
COMPLEXITY_THRESHOLD_SIMPLE=0.4
COMPLEXITY_THRESHOLD_COMPLEX=0.7
ENABLE_FALLBACK=true
```

---

#### Task 6: ChromaDB Vector Store Implementation
**File**: `src/rag/chromadb_store.py` (new)  
**Estimated Duration**: 5 hours  
**Dependencies**: None  
**Status**: ⬜ Pending

**Subtasks**:
- [ ] Install chromadb: `pip install chromadb`
- [ ] Create class `ChromaDBStore(VectorStore)`
- [ ] Implement methods:
  - `add_documents(documents, embeddings)`
  - `search(query_embedding, top_k=5)`
  - `delete(document_ids)`
  - `get_collection_stats()`
- [ ] Configure persistent storage
- [ ] Implement metadata filtering
- [ ] Integration tests (6 tests):
  - Test add documents
  - Test search similarity
  - Test metadata filtering
  - Test persistence (reload)
  - Test collection stats
  - Test delete operations

**Configuration**:
```env
VECTOR_STORE_PROVIDER=chromadb
CHROMADB_PATH=./chroma_data
CHROMADB_COLLECTION=f1_races
```

---

#### Task 7: Embeddings Service
**File**: `src/rag/embeddings.py` (new)  
**Estimated Duration**: 3 hours  
**Dependencies**: None  
**Status**: ⬜ Pending

**Subtasks**:
- [ ] Install sentence-transformers: `pip install sentence-transformers`
- [ ] Create class `EmbeddingsService`
- [ ] Load model all-MiniLM-L6-v2
- [ ] Implement `embed_text(text) -> np.ndarray`
- [ ] Implement `embed_batch(texts) -> List[np.ndarray]`
- [ ] In-memory embeddings cache (LRU)
- [ ] Unit tests (4 tests):
  - Test embed single text
  - Test embed batch
  - Test dimensions (384)
  - Test cache hit/miss

**Configuration**:
```env
EMBEDDINGS_MODEL=all-MiniLM-L6-v2
EMBEDDINGS_CACHE_SIZE=1000
EMBEDDINGS_DEVICE=cpu  # or 'cuda' if available
```

---

#### Task 8: Pinecone Store Stub
**File**: `src/rag/pinecone_store.py` (new)  
**Estimated Duration**: 2 hours  
**Dependencies**: None  
**Status**: ⬜ Pending

**Subtasks**:
- [ ] Create class `PineconeStore(VectorStore)` with stub methods
- [ ] Implement methods that return `NotImplementedError`
- [ ] Document TODOs for future implementation
- [ ] Comments with future usage examples
- [ ] Test that validates it's configured as stub

**Note**: Do not implement real functionality, only prepare structure for future migration.

```python
class PineconeStore(VectorStore):
    def add_documents(self, documents, embeddings):
        raise NotImplementedError(
            "Pinecone store will be implemented in Phase 3C. "
            "Use ChromaDB for MVP."
        )
```

---

#### Task 9: Vector Store Factory
**File**: `src/rag/factory.py` (new)  
**Estimated Duration**: 2 hours  
**Dependencies**: Tasks 6, 8  
**Status**: ⬜ Pending

**Subtasks**:
- [ ] Create function `get_vector_store(provider: str) -> VectorStore`
- [ ] Implement factory pattern:
  ```python
  if provider == "chromadb":
      return ChromaDBStore()
  elif provider == "pinecone":
      return PineconeStore()
  else:
      raise ValueError(f"Unknown provider: {provider}")
  ```
- [ ] Configuration validation
- [ ] Unit tests (3 tests):
  - Test get ChromaDB store
  - Test get Pinecone store (must return stub)
  - Test unknown provider (ValueError)

---

### 🟢 PRIORIDAD BAJA - Testing & Documentation

#### Tarea 10: Integration Tests Suite
**Archivo**: `tests/test_llm_integration.py` (nuevo)  
**Duración Estimada**: 3 horas  
**Dependencias**: Tareas 2, 3, 5  
**Estado**: ⬜ Pendiente

**Subtareas**:
- [ ] Test end-to-end query routing
- [ ] Test cost tracking (LangSmith + local)
- [ ] Test error handling y retries
- [ ] Test fallback scenarios
- [ ] Mocks para APIs externas (pytest-mock)

**Total Tests**: 8 tests de integración

---

#### Tarea 11: Vector Store Integration Tests
**Archivo**: `tests/test_vector_store_integration.py` (nuevo)  
**Duración Estimada**: 2 horas  
**Dependencias**: Tareas 6, 7, 9  
**Estado**: ⬜ Pendiente

**Subtareas**:
- [ ] Test embeddings + ChromaDB workflow
- [ ] Test search relevance
- [ ] Test factory pattern con diferentes providers
- [ ] Test persistence y reload

**Total Tests**: 5 tests de integración

---

#### Tarea 12: Performance Benchmarks
**Archivo**: `tests/test_performance.py` (nuevo)  
**Duración Estimada**: 2 horas  
**Dependencias**: Todas las tareas anteriores  
**Estado**: ⬜ Pendiente

**Subtareas**:
- [ ] Benchmark: Claude response time
- [ ] Benchmark: Gemini normal vs thinking response time
- [ ] Benchmark: Embeddings generation time
- [ ] Benchmark: ChromaDB search time
- [ ] Validar targets:
  - LLM response < 3s (P95)
  - Embeddings < 0.1s per document
  - Vector search < 100ms

---

#### Tarea 13: Documentation Updates
**Archivos**: Múltiples  
**Duración Estimada**: 2 horas  
**Dependencias**: Tareas 1-11  
**Estado**: ⬜ Pendiente

**Subtareas**:
- [ ] Crear `docs/LLM_PROVIDERS_IMPLEMENTATION.md`
- [ ] Crear `docs/VECTOR_STORE_SETUP.md`
- [ ] Actualizar `README.md` con Phase 3A status
- [ ] Documentar API de cada provider
- [ ] Ejemplos de uso en notebooks

---

#### Tarea 14: Configuration Validation
**Archivo**: `src/config/validation.py` (nuevo)  
**Duración Estimada**: 2 horas  
**Dependencias**: Ninguna  
**Estado**: ⬜ Pendiente

**Subtareas**:
- [ ] Validar que todas las API keys están presentes
- [ ] Validar configuración de LLM provider
- [ ] Validar configuración de vector store
- [ ] Script de diagnóstico: `python scripts/validate_config.py`
- [ ] Tests de validación

---

#### Tarea 15: Cost Tracking Integration
**Archivo**: `src/utils/cost_tracker.py` (actualizar)  
**Duración Estimada**: 2 horas  
**Dependencias**: Tareas 2, 3, 5  
**Estado**: ⬜ Pendiente

**Subtareas**:
- [ ] Integrar con hybrid router
- [ ] Tracking separado por provider (Claude vs Gemini)
- [ ] Tracking thinking mode overhead
- [ ] Dashboard de costos diarios/mensuales
- [ ] Alertas si se excede budget

---

## 📊 Dependency Diagram

```
Task 1 (Abstract Interface)
  ├─→ Task 2 (Claude Provider)
  └─→ Task 3 (Gemini Provider)
        └─→ Task 5 (Hybrid Router)
              └─→ Task 10 (Integration Tests)

Task 4 (Complexity Analyzer)
  └─→ Task 5 (Hybrid Router)

Task 6 (ChromaDB Store)
  └─→ Task 9 (Factory)
        └─→ Task 11 (Vector Store Tests)

Task 7 (Embeddings)
  └─→ Task 11 (Vector Store Tests)

Task 8 (Pinecone Stub)
  └─→ Task 9 (Factory)

Tasks 1-11
  └─→ Task 12 (Performance)
  └─→ Task 13 (Documentation)
```

---

## ⏱️ Suggested Schedule

### Week 1: December 21-27

| Day | Tasks | Hours |
|-----|--------|-------|
| **Mon 21** | Task 1 (Abstract Interface) | 2h |
| **Tue 22** | Task 2 (Claude Provider) | 4h |
| **Wed 23** | Task 3 (Gemini Provider) | 5h |
| **Thu 24** | Task 4 (Complexity Analyzer) | 3h |
| **Fri 25** | 🎄 Christmas - Break | - |
| **Sat 26** | Task 7 (Embeddings) | 3h |
| **Sun 27** | Buffer / Review | 2h |

**Week 1 Total**: ~19 hours

---

### Week 2: December 28 - January 3

| Day | Tasks | Hours |
|-----|--------|-------|
| **Mon 28** | Task 5 (Hybrid Router) | 4h |
| **Tue 29** | Task 6 (ChromaDB Store) | 5h |
| **Wed 30** | Task 8 + 9 (Pinecone Stub + Factory) | 4h |
| **Thu 31** | 🎉 New Year - Break | - |
| **Fri 1** | Task 10 + 11 (Integration Tests) | 5h |
| **Sat 2** | Task 12 + 14 + 15 (Performance, Config, Cost) | 6h |
| **Sun 3** | Task 13 (Documentation) + Final Review | 3h |

**Week 2 Total**: ~27 hours

**PHASE 3A TOTAL**: ~46 hours (~23 hours/week)

---

## ✅ Completion Checklist

### Code
- [ ] 6 new files in `src/llm/`
- [ ] 4 new files in `src/rag/`
- [ ] 2 new files in `src/config/`
- [ ] 5 new files in `tests/`
- [ ] 0 linting errors (flake8)
- [ ] 0 type errors (mypy)

### Tests
- [ ] 15+ integration tests passing
- [ ] Coverage > 85% on new code
- [ ] Performance benchmarks within targets

### Documentation
- [ ] 2 new documents in `docs/`
- [ ] README.md updated
- [ ] Complete API documentation
- [ ] Usage examples

### Configuration
- [ ] .env.example updated
- [ ] Functional validation script
- [ ] Cost tracking operational

### Final Validation
- [ ] Simple query → Gemini normal (working)
- [ ] Moderate query → Gemini thinking (working)
- [ ] Complex query → Claude (working)
- [ ] ChromaDB search < 100ms
- [ ] Embeddings generation < 0.1s/doc
- [ ] Cost tracking recording correctly

---

## 🎯 Success Criteria

| Metric | Target | Validation |
|---------|--------|------------|
| **Tests Passing** | 15+ | pytest -v |
| **Code Coverage** | >85% | pytest --cov |
| **LLM Response Time** | <3s (P95) | Performance tests |
| **Vector Search** | <100ms | Benchmark tests |
| **Embeddings** | <0.1s/doc | Benchmark tests |
| **Cost Tracking** | 100% queries | Dashboard validation |
| **Documentation** | Complete | Manual review |

---

## 🚨 Identified Risks

| Risk | Probability | Impact | Mitigation |
|--------|--------------|---------|------------|
| API rate limits (Gemini) | Medium | High | Implement retry with exponential backoff |
| Thinking mode slower than expected | Medium | Medium | Adjust complexity thresholds |
| ChromaDB performance on large datasets | Low | Medium | Early benchmark, consider indexes |
| Holidays (24-25, 31-1) | High | Medium | Buffer time included in schedule |
| Changes in Gemini API (experimental) | Low | High | Document exact version, have fallback |

---

## 📞 Resources and References

### APIs and SDKs
- [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python)
- [Google AI Python SDK](https://github.com/google/generative-ai-python)
- [ChromaDB Docs](https://docs.trychroma.com/)
- [Sentence Transformers](https://www.sbert.net/)

### Internal Documentation
- [TECH_STACK_FINAL.md](./TECH_STACK_FINAL.md) - Complete decisions
- [GEMINI_FLASH_THINKING_GUIDE.md](./GEMINI_FLASH_THINKING_GUIDE.md) - Gemini guide
- [ARCHITECTURE_DECISIONS.md](./ARCHITECTURE_DECISIONS.md) - Main ADR

### Example Notebooks
- `notebooks/test_claude_integration.ipynb` (to create)
- `notebooks/test_gemini_thinking.ipynb` (to create)
- `notebooks/benchmark_embeddings.ipynb` (to create)

---

## 🔄 Daily Progress Tracking

Update daily:

### December 21
- [ ] Tasks completed:
- [ ] Blockers:
- [ ] Next session:

### December 22
- [ ] Tasks completed:
- [ ] Blockers:
- [ ] Next session:

*(continue for each day)*

---

**Last Update**: December 20, 2025, 2:30 PM  
**Next Review**: December 27, 2025 (end of Week 1)  
**Responsible**: Jorge Rionegro

---

## 🚀 Ready to Start!

To begin implementation:

```bash
# 1. Verify environment
python scripts/validate_config.py

# 2. Create working branch
git checkout -b feature/phase-3a-llm-foundation

# 3. Start with Task 1
cd src/llm
# Edit provider.py

# 4. Test driven development
pytest tests/test_llm_providers.py -v --watch
```

**Good luck with Phase 3A!** 🎯
