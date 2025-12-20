# Tech Stack - Decisiones Finales

**Fecha de Decisión**: 20 de Diciembre de 2025  
**Estado**: APROBADO ✅

---

## Resumen Ejecutivo

Stack tecnológico optimizado para **F1 Strategist AI** con enfoque en:
- **Costo**: Reducción del 68% mediante LLM híbrido
- **Rendimiento**: ChromaDB local para MVP, Pinecone opcional para producción
- **Mantenibilidad**: Sin Redis en MVP, arquitectura simple
- **Escalabilidad**: Migración progresiva a producción

---

## 🎯 Decisiones Clave

### 1. Estrategia LLM Híbrida

| Componente | Tecnología | Uso | Costo |
|------------|-----------|-----|-------|
| **LLM Principal** | Claude 3.5 Sonnet | Queries complejas (~30%) | $3/1M in, $15/1M out |
| **LLM Secundario** | Gemini 2.0 Flash Thinking | Queries simples/moderadas (~70%) | $0.01875/1M in, $0.075/1M out |
| **Modelo Gemini** | `gemini-2.0-flash-thinking-exp-1219` | Con modo reasoning | +5% overhead |

**Routing por Complejidad**:
```python
if complexity_score < 0.4:
    # Gemini 2.0 Flash Thinking (simple)
    llm = gemini_provider
elif complexity_score < 0.7:
    # Gemini 2.0 Flash Thinking (moderado con thinking)
    llm = gemini_provider.with_thinking_mode()
else:
    # Claude 3.5 Sonnet (complejo)
    llm = claude_provider
```

**Ahorro Estimado**: 68% vs solo Claude

---

### 2. Vector Store

| Entorno | Tecnología | Justificación |
|---------|-----------|---------------|
| **MVP** | ChromaDB | Local, gratuito, sin infraestructura |
| **Producción** | Pinecone (opcional) | Escalable, configurable vía settings |

**Configuración**:
```env
VECTOR_STORE_PROVIDER=chromadb  # Cambiar a 'pinecone' en prod
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

| Modelo | Dimensiones | Ubicación | Costo |
|--------|-------------|-----------|-------|
| **all-MiniLM-L6-v2** | 384 | Local | Gratis |

**Ventajas**:
- ✅ Compatible con ChromaDB y Pinecone
- ✅ No requiere API calls
- ✅ Suficiente para dominio F1
- ✅ Rápido (~0.1s por documento)

---

### 4. Caché

| Componente | Tecnología | Justificación |
|------------|-----------|---------------|
| **MVP** | Solo Parquet | Suficiente, 100ms read |
| **Producción** | Redis opcional | Si se requiere <10ms |

**Política Actual**:
```python
USE_REDIS=false  # MVP
# Cambiar a true solo si métricas indican necesidad
```

---

### 5. Monitoreo

| Componente | Tecnología | Modo |
|------------|-----------|------|
| **Primario** | LangSmith | Cloud-based |
| **Fallback** | LocalTokenTracker | Offline |

**Desde Phase 3A**:
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

## 🏗️ Arquitectura de 5 Agentes

| Agente | Responsabilidad | LLM Típico |
|--------|-----------------|------------|
| **Strategy Agent** | Pit stops, neumáticos | Claude |
| **Weather Agent** | Pronósticos, adaptación | Gemini |
| **Performance Agent** | Lap times, telemetría | Gemini |
| **Race Control Agent** | Banderas, incidentes | Gemini |
| **Race Position Agent** | Gaps, posiciones | Gemini |

**Orquestación**: LangChain con custom routing

---

## 🔧 Configuración de Entorno

### Variables Críticas

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

## 📈 Métricas de Éxito

### MVP Phase 3
- [ ] Routing híbrido funcional (70% Gemini, 30% Claude)
- [ ] ChromaDB con >1000 documentos indexados
- [ ] Respuestas <3s (P95)
- [ ] Precisión RAG >80%
- [ ] 5 agentes operativos

### Producción Phase 4
- [ ] Costo real <$300/mes
- [ ] Migración a Pinecone sin downtime
- [ ] Monitoring LangSmith activo
- [ ] API pública con rate limiting

---

## 🚀 Plan de Migración

### De MVP a Producción

1. **Vector Store**:
   ```bash
   # Exportar de ChromaDB
   python scripts/export_chromadb.py
   
   # Importar a Pinecone
   python scripts/import_pinecone.py
   
   # Cambiar config
   VECTOR_STORE_PROVIDER=pinecone
   ```

2. **Redis (si necesario)**:
   ```bash
   # Evaluar métricas
   python scripts/analyze_cache_latency.py
   
   # Si P95 > 100ms, habilitar Redis
   USE_REDIS=true
   ```

3. **Monitoreo**:
   ```bash
   # Ya configurado desde Phase 3A
   # Solo verificar dashboard LangSmith
   ```

---

## 📚 Referencias Técnicas

### Documentación Oficial
- [Claude API](https://docs.anthropic.com/claude/reference/)
- [Gemini 2.0 Flash Thinking](https://ai.google.dev/gemini-api/docs/thinking-mode)
- [ChromaDB](https://docs.trychroma.com/)
- [Pinecone](https://docs.pinecone.io/)
- [LangSmith](https://docs.smith.langchain.com/)

### Documentación Interna
- [ARCHITECTURE_DECISIONS.md](./ARCHITECTURE_DECISIONS.md)
- [GEMINI_FLASH_THINKING_GUIDE.md](./GEMINI_FLASH_THINKING_GUIDE.md)
- [MONITORING_SETUP.md](./MONITORING_SETUP.md)
- [RACE_POSITION_AGENT_SPEC.md](./RACE_POSITION_AGENT_SPEC.md)

---

## ✅ Checklist de Implementación

### Phase 3A (Semana 5-6)
- [ ] `src/llm/claude_provider.py` - Provider de Claude
- [ ] `src/llm/gemini_provider.py` - Provider de Gemini con thinking mode
- [ ] `src/llm/hybrid_router.py` - Router por complejidad
- [ ] `src/rag/chromadb_store.py` - Store local
- [ ] `src/rag/pinecone_store.py` - Stub para migración
- [ ] `src/rag/factory.py` - Factory pattern
- [ ] Tests de integración (15+ tests)

### Phase 3B (Semana 7-8)
- [ ] 5 agentes LangChain operativos
- [ ] Sistema RAG con >80% precisión
- [ ] Orquestador multi-agente
- [ ] Tests end-to-end (20+ tests)

---

**Estado**: ✅ Documentación completa y aprobada  
**Siguiente Paso**: Implementar Phase 3A (LLM providers + Vector store)  
**Responsable**: Jorge Rionegro  
**Fecha Límite Phase 3A**: 3 de Enero de 2026
