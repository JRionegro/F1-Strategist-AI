# Tech Stack - Final Decisions

**Decision Date**: December 20, 2025  
**Status**: APPROVED ✅

---

## Executive Summary

Optimized technology stack for **F1 Strategist AI** focusing on:
- **Cost**: 68% reduction through hybrid LLM
- **Performance**: Local ChromaDB for MVP, optional Pinecone for production
- **Maintainability**: No Redis in MVP, simple architecture
- **Scalability**: Progressive migration to production

---

## 🎯 Key Decisions

### 1. Hybrid LLM Strategy

| Component | Technology | Usage | Cost |
|------------|-----------|-----|-------|
| **Primary LLM** | Claude 3.5 Sonnet | Complex queries (~30%) | $3/1M in, $15/1M out |
| **Secondary LLM** | Gemini 2.0 Flash Thinking | Simple/moderate queries (~70%) | $0.01875/1M in, $0.075/1M out |
| **Gemini Model** | `gemini-2.0-flash-thinking-exp-1219` | With reasoning mode | +5% overhead |

**Routing by Complexity**:
```python
if complexity_score < 0.4:
    # Gemini 2.0 Flash Thinking (simple)
    llm = gemini_provider
elif complexity_score < 0.7:
    # Gemini 2.0 Flash Thinking (moderate with thinking)
    llm = gemini_provider.with_thinking_mode()
else:
    # Claude 3.5 Sonnet (complex)
    llm = claude_provider
```

**Estimated Savings**: 68% vs Claude only

---

### 2. Vector Store

| Environment | Technology | Justification |
|---------|-----------|---------------|
| **MVP** | ChromaDB | Local, free, no infrastructure |
| **Production** | Pinecone (optional) | Scalable, configurable via settings |

**Configuration**:
```env
VECTOR_STORE_PROVIDER=chromadb  # Change to 'pinecone' in prod
```

**Factory Pattern**:
```python
def get_vector_store(provider: str):
    if provider == "chromadb":
        return ChromaDBStore()
    elif provider == "pinecone":
        return PineconeStore()
```

---

### 3. Embeddings

| Model | Dimensions | Location | Cost |
|--------|-------------|-----------|-------|
| **all-MiniLM-L6-v2** | 384 | Local | Free |

**Advantages**:
- ✅ Compatible with ChromaDB and Pinecone
- ✅ No API calls required
- ✅ Sufficient for F1 domain
- ✅ Fast (~0.1s per document)

---

### 4. Cache

| Component | Technology | Justification |
|------------|-----------|---------------|
| **MVP** | Parquet only | Sufficient, 100ms read |
| **Production** | Optional Redis | If <10ms required |

**Current Policy**:
```python
USE_REDIS=false  # MVP
# Change to true only if metrics indicate need
```

---

### 5. Monitoring

| Component | Technology | Mode |
|------------|-----------|------|
| **Primary** | LangSmith | Cloud-based |
| **Fallback** | LocalTokenTracker | Offline |

**Since Phase 3A**:
```python
if langsmith_available():
    monitor = LangSmith()
else:
    monitor = LocalTokenTracker()
```

---

## 📊 Proyecciones de Costo

### MVP (100 queries/día)

| Componente | Costo Mensual |
|------------|---------------|
| Claude 3.5 Sonnet | $5.40 |
| Gemini 2.0 Flash Thinking | $2.10 |
| LangSmith | $1.00 |
| ChromaDB | $0.00 |
| **Total MVP** | **$8.50/mes** |

### Producción (1000 queries/día)

| Componente | Costo Mensual |
|------------|---------------|
| Claude 3.5 Sonnet | $162.00 |
| Gemini 2.0 Flash Thinking | $63.00 |
| LangSmith | $29.00 |
| Pinecone (opcional) | $40.00 |
| **Total Producción** | **$294/mes** |

**Comparación**: Solo Claude sería ~$500/mes (ahorro 41%)

---

## 🏭️ 5-Agent Architecture

| Agent | Responsibility | Typical LLM |
|--------|-----------------|------------|
| **Strategy Agent** | Race: Pit stops, tires / Quali: Timing, attempts | Claude |
| **Weather Agent** | Race: Forecasts / Quali: Optimal window, rain risk | Gemini |
| **Performance Agent** | Race: Lap times / Quali: Sector analysis, gaps | Gemini |
| **Race Control Agent** | Race: SC, flags / Quali: Red flags, track limits | Gemini |
| **Race Position Agent** | Race: Gaps, DRS / Quali: Traffic gaps, slipstream | Gemini |

**Orchestration**: LangChain with custom routing

---

## 🔧 Environment Configuration

### Critical Variables

```env
# LLM
LLM_PROVIDER=hybrid
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
GEMINI_MODEL=gemini-2.0-flash-thinking-exp-1219

# Vector Store
VECTOR_STORE_PROVIDER=chromadb
EMBEDDINGS_MODEL=all-MiniLM-L6-v2

# Cache
USE_REDIS=false

# Monitoring
LANGCHAIN_TRACING_V2=true
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=f1-strategist-ai
LOCAL_TOKEN_TRACKING=true
```

---

## 📈 Success Metrics

### MVP Phase 3
- [ ] Functional hybrid routing (70% Gemini, 30% Claude)
- [ ] ChromaDB with >1000 indexed documents
- [ ] Responses <3s (P95)
- [ ] RAG accuracy >80%
- [ ] 5 operational agents

### Production Phase 4
- [ ] Actual cost <$300/month
- [ ] Migration to Pinecone without downtime
- [ ] Active LangSmith monitoring
- [ ] Public API with rate limiting

---

## 🚀 Migration Plan

### From MVP to Production

1. **Vector Store**:
   ```bash
   # Export from ChromaDB
   python scripts/export_chromadb.py
   
   # Import to Pinecone
   python scripts/import_pinecone.py
   
   # Change config
   VECTOR_STORE_PROVIDER=pinecone
   ```

2. **Redis (if needed)**:
   ```bash
   # Evaluate metrics
   python scripts/analyze_cache_latency.py
   
   # If P95 > 100ms, enable Redis
   USE_REDIS=true
   ```

3. **Monitoring**:
   ```bash
   # Already configured since Phase 3A
   # Only verify LangSmith dashboard
   ```

---

## 📚 Technical References

### Official Documentation
- [Claude API](https://docs.anthropic.com/claude/reference/)
- [Gemini 2.0 Flash Thinking](https://ai.google.dev/gemini-api/docs/thinking-mode)
- [ChromaDB](https://docs.trychroma.com/)
- [Pinecone](https://docs.pinecone.io/)
- [LangSmith](https://docs.smith.langchain.com/)

### Internal Documentation
- [ARCHITECTURE_DECISIONS.md](./ARCHITECTURE_DECISIONS.md)
- [GEMINI_FLASH_THINKING_GUIDE.md](./GEMINI_FLASH_THINKING_GUIDE.md)
- [MONITORING_SETUP.md](./MONITORING_SETUP.md)
- [RACE_POSITION_AGENT_SPEC.md](./RACE_POSITION_AGENT_SPEC.md)

---

## ✅ Implementation Checklist

### Phase 3A (Week 5-6)
- [ ] `src/llm/claude_provider.py` - Claude provider
- [ ] `src/llm/gemini_provider.py` - Gemini provider with thinking mode
- [ ] `src/llm/hybrid_router.py` - Complexity-based router
- [ ] `src/rag/chromadb_store.py` - Local store
- [ ] `src/rag/pinecone_store.py` - Stub for migration
- [ ] `src/rag/factory.py` - Factory pattern
- [ ] Integration tests (15+ tests)

### Phase 3B (Week 7-8)
- [ ] 5 operational LangChain agents
- [ ] RAG system with >80% accuracy
- [ ] Multi-agent orchestrator
- [ ] End-to-end tests (20+ tests)

---

**Status**: ✅ Complete and approved documentation  
**Next Step**: Implement Phase 3A (LLM providers + Vector store)  
**Responsible**: Jorge Rionegro  
**Phase 3A Deadline**: January 3, 2026
