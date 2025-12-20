# F1 Strategist AI - Índice de Documentación

**Última Actualización**: 20 de Diciembre de 2025  
**Estado del Proyecto**: Phase 2 Completada ✅ | Phase 3A Iniciando 🔄

---

## 📖 Guías de Inicio Rápido

| Documento | Descripción | Audiencia |
|-----------|-------------|-----------|
| [README.md](../README.md) | Resumen del proyecto y quick start | Todos |
| [QUICK_START.md](./QUICK_START.md) | Instalación y configuración inicial | Desarrolladores nuevos |
| [DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md) | Workflow y convenciones de código | Desarrolladores activos |

---

## 🏗️ Arquitectura y Diseño

| Documento | Descripción | Última Actualización |
|-----------|-------------|----------------------|
| [ARCHITECTURE_DECISIONS.md](./ARCHITECTURE_DECISIONS.md) | Decisiones arquitectónicas principales (ADR) | 20/12/2025 ✅ |
| [TECH_STACK_FINAL.md](./TECH_STACK_FINAL.md) | **Stack tecnológico definitivo** | 20/12/2025 ✅ |
| [PROJECT_SPECIFICATIONS.md](./PROJECT_SPECIFICATIONS.md) | Especificaciones técnicas completas | 20/12/2025 ✅ |

---

## 🤖 Agentes y LLM

| Documento | Descripción | Estado |
|-----------|-------------|--------|
| [RACE_POSITION_AGENT_SPEC.md](./RACE_POSITION_AGENT_SPEC.md) | Especificación del 5º agente (Race Position) | Aprobado ✅ |
| [GEMINI_FLASH_THINKING_GUIDE.md](./GEMINI_FLASH_THINKING_GUIDE.md) | Guía completa de Gemini 2.0 Flash Thinking | Completo ✅ |
| **[LLM_PROVIDERS_SPEC.md]** | Implementación de providers (pendiente) | Planificado 📋 |

---

## 💾 Sistemas de Datos

| Documento | Descripción | Estado |
|-----------|-------------|--------|
| [CACHE_SYSTEM_IMPLEMENTATION.md](./CACHE_SYSTEM_IMPLEMENTATION.md) | Sistema de caché híbrido (Parquet) | Implementado ✅ |
| [MCP_API_REFERENCE.md](./MCP_API_REFERENCE.md) | Referencia completa de las 13 herramientas MCP | Completo ✅ |
| **[VECTOR_STORE_GUIDE.md]** | ChromaDB + Pinecone setup (pendiente) | Planificado 📋 |

---

## 📊 Monitoreo y Observabilidad

| Documento | Descripción | Estado |
|-----------|-------------|--------|
| [MONITORING_SETUP.md](./MONITORING_SETUP.md) | LangSmith + LocalTokenTracker | Implementado ✅ |
| **[COST_OPTIMIZATION.md]** | Estrategias de optimización de costos | Planificado 📋 |

---

## 📝 Resúmenes de Implementación

| Documento | Descripción | Estado |
|-----------|-------------|--------|
| [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md) | Resumen de trabajo completado | Actualizado ✅ |

---

## 🎯 Documentos por Fase del Proyecto

### ✅ Phase 1-2: Foundation & Data Layer (COMPLETADO)

**Documentos Clave**:
1. [MCP_API_REFERENCE.md](./MCP_API_REFERENCE.md) - 13 herramientas implementadas
2. [CACHE_SYSTEM_IMPLEMENTATION.md](./CACHE_SYSTEM_IMPLEMENTATION.md) - Sistema híbrido
3. [MONITORING_SETUP.md](./MONITORING_SETUP.md) - LangSmith + fallback

**Tests**: 81 pasando (43 MCP + 14 caché + 12 monitoring + 12 data provider)

---

### ✅ Phase 2D: Architecture Planning (COMPLETADO)

**Documentos Clave**:
1. [ARCHITECTURE_DECISIONS.md](./ARCHITECTURE_DECISIONS.md) - Framework LangChain
2. [TECH_STACK_FINAL.md](./TECH_STACK_FINAL.md) - **Stack completo aprobado**
3. [GEMINI_FLASH_THINKING_GUIDE.md](./GEMINI_FLASH_THINKING_GUIDE.md) - Guía Gemini
4. [RACE_POSITION_AGENT_SPEC.md](./RACE_POSITION_AGENT_SPEC.md) - 5º agente

**Decisiones Finales**:
- LLM: Híbrido Claude + Gemini 2.0 Flash Thinking
- Vector Store: ChromaDB (MVP) + Pinecone (prod)
- Embeddings: all-MiniLM-L6-v2
- Cache: Parquet only (sin Redis en MVP)
- Monitoring: LangSmith desde Phase 3A

---

### 🔄 Phase 3A: LangChain Foundation (ACTUAL)

**Documentos Necesarios** (pendientes de crear):
1. **LLM_PROVIDERS_SPEC.md** - Implementación de Claude y Gemini providers
2. **VECTOR_STORE_GUIDE.md** - Setup ChromaDB y Pinecone
3. **AGENT_BASE_FRAMEWORK.md** - Arquitectura base de agentes

**Tareas**:
- [ ] Implementar `src/llm/claude_provider.py`
- [ ] Implementar `src/llm/gemini_provider.py`
- [ ] Implementar `src/llm/hybrid_router.py`
- [ ] Implementar `src/rag/chromadb_store.py`
- [ ] Implementar `src/rag/factory.py`
- [ ] Tests de integración (15+)

---

### 📋 Phase 3B: Agent Implementation (PRÓXIMO)

**Documentos Planificados**:
1. **MULTI_AGENT_ORCHESTRATION.md** - Coordinación entre agentes
2. **RAG_IMPLEMENTATION.md** - Sistema RAG completo
3. **TOOL_INTEGRATION.md** - Conversión MCP → LangChain

---

### 📋 Phase 4: User Interface (FUTURO)

**Documentos Planificados**:
1. **CHATBOT_DESIGN.md** - Interface de usuario
2. **API_DOCUMENTATION.md** - API pública
3. **DEPLOYMENT_GUIDE.md** - Guía de despliegue

---

## 🔍 Guía de Búsqueda Rápida

### ¿Necesitas información sobre...?

**Configuración Inicial**:
- → [QUICK_START.md](./QUICK_START.md)
- → [config/.env.example](../config/.env.example)

**Arquitectura del Sistema**:
- → [ARCHITECTURE_DECISIONS.md](./ARCHITECTURE_DECISIONS.md)
- → [TECH_STACK_FINAL.md](./TECH_STACK_FINAL.md)

**Stack Tecnológico**:
- → [TECH_STACK_FINAL.md](./TECH_STACK_FINAL.md) ⭐ **REFERENCIA PRINCIPAL**

**LLM y Modelos**:
- → [GEMINI_FLASH_THINKING_GUIDE.md](./GEMINI_FLASH_THINKING_GUIDE.md)
- → [TECH_STACK_FINAL.md](./TECH_STACK_FINAL.md) (Sección "Estrategia LLM Híbrida")

**Agentes de IA**:
- → [RACE_POSITION_AGENT_SPEC.md](./RACE_POSITION_AGENT_SPEC.md)
- → [ARCHITECTURE_DECISIONS.md](./ARCHITECTURE_DECISIONS.md) (Phase 3B)

**Sistema de Datos**:
- → [MCP_API_REFERENCE.md](./MCP_API_REFERENCE.md)
- → [CACHE_SYSTEM_IMPLEMENTATION.md](./CACHE_SYSTEM_IMPLEMENTATION.md)

**Monitoreo y Costos**:
- → [MONITORING_SETUP.md](./MONITORING_SETUP.md)
- → [TECH_STACK_FINAL.md](./TECH_STACK_FINAL.md) (Sección "Proyecciones de Costo")

**Testing**:
- → [DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md) (Sección "Testing")
- → `tests/` directorio con 81 tests

---

## 📌 Documentos Esenciales

### ⭐ Top 3 Documentos para Nuevos Desarrolladores

1. **[TECH_STACK_FINAL.md](./TECH_STACK_FINAL.md)** - Decisiones completas del stack
2. **[QUICK_START.md](./QUICK_START.md)** - Guía de inicio rápido
3. **[MCP_API_REFERENCE.md](./MCP_API_REFERENCE.md)** - API de herramientas

### ⭐ Top 3 Documentos para Arquitectura

1. **[ARCHITECTURE_DECISIONS.md](./ARCHITECTURE_DECISIONS.md)** - ADR principal
2. **[TECH_STACK_FINAL.md](./TECH_STACK_FINAL.md)** - Stack completo
3. **[GEMINI_FLASH_THINKING_GUIDE.md](./GEMINI_FLASH_THINKING_GUIDE.md)** - LLM strategy

---

## 🔄 Estado de Actualización

| Categoría | Actualizado | Fecha |
|-----------|-------------|-------|
| **Architecture** | ✅ | 20/12/2025 |
| **Tech Stack** | ✅ | 20/12/2025 |
| **LLM Strategy** | ✅ | 20/12/2025 |
| **Data Layer** | ✅ | 15/12/2025 |
| **Monitoring** | ✅ | 15/12/2025 |
| **Agent Specs** | ✅ | 20/12/2025 |
| **API Reference** | ✅ | 10/12/2025 |
| **Testing Guide** | 🟡 Parcial | - |
| **Deployment** | ❌ Pendiente | - |

---

## 📞 Contacto y Mantenimiento

**Responsable**: Jorge Rionegro  
**Última Revisión General**: 20 de Diciembre de 2025  
**Próxima Revisión**: 3 de Enero de 2026 (Fin Phase 3A)

---

**Nota**: Este índice se actualiza con cada cambio significativo en la arquitectura o el stack tecnológico. Si encuentras información desactualizada, verifica primero [TECH_STACK_FINAL.md](./TECH_STACK_FINAL.md) que siempre contiene las decisiones más recientes.
