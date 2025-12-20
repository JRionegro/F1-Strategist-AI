# 📚 Documentación F1 Strategist AI

**Última Actualización**: 20 de Diciembre de 2025  
**Estado**: ✅ Completa y Validada

---

## 🎯 Inicio Rápido

¿Primera vez en el proyecto? Comienza aquí:

1. **[UPDATE_SUMMARY.md](./UPDATE_SUMMARY.md)** - Resumen de últimas actualizaciones
2. **[INDEX.md](./INDEX.md)** - Mapa completo de documentación
3. **[QUICK_START.md](./QUICK_START.md)** - Guía de instalación

---

## 📖 Documentos por Categoría

### 🎯 Esenciales (Lectura Obligatoria)

| Documento | Descripción | Para Quién |
|-----------|-------------|------------|
| **[TECH_STACK_FINAL.md](./TECH_STACK_FINAL.md)** ⭐ | Stack tecnológico completo | Todos |
| **[ARCHITECTURE_DECISIONS.md](./ARCHITECTURE_DECISIONS.md)** | Decisiones arquitectónicas (ADR) | Arquitectos/Devs |
| **[INDEX.md](./INDEX.md)** | Índice de toda la documentación | Nuevos usuarios |

### 🚀 Getting Started

| Documento | Descripción |
|-----------|-------------|
| [QUICK_START.md](./QUICK_START.md) | Instalación y configuración inicial |
| [DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md) | Workflow y convenciones |
| [PROJECT_SPECIFICATIONS.md](./PROJECT_SPECIFICATIONS.md) | Especificaciones técnicas |

### 🏗️ Arquitectura y Diseño

| Documento | Descripción |
|-----------|-------------|
| [ARCHITECTURE_DECISIONS.md](./ARCHITECTURE_DECISIONS.md) | ADR principal |
| [TECH_STACK_FINAL.md](./TECH_STACK_FINAL.md) | Stack completo aprobado |
| [PROJECT_STATUS.md](./PROJECT_STATUS.md) | Estado actual del proyecto |

### 🤖 AI y Agentes

| Documento | Descripción |
|-----------|-------------|
| [GEMINI_FLASH_THINKING_GUIDE.md](./GEMINI_FLASH_THINKING_GUIDE.md) | Guía completa Gemini 2.0 |
| [RACE_POSITION_AGENT_SPEC.md](./RACE_POSITION_AGENT_SPEC.md) | Especificación 5º agente |

### 💾 Sistemas de Datos

| Documento | Descripción |
|-----------|-------------|
| [CACHE_SYSTEM_IMPLEMENTATION.md](./CACHE_SYSTEM_IMPLEMENTATION.md) | Sistema caché híbrido |
| [MCP_API_REFERENCE.md](./MCP_API_REFERENCE.md) | 13 herramientas MCP |

### 📊 Monitoreo

| Documento | Descripción |
|-----------|-------------|
| [MONITORING_SETUP.md](./MONITORING_SETUP.md) | LangSmith + local fallback |

### ✅ Validación

| Documento | Descripción |
|-----------|-------------|
| [DOCUMENTATION_VALIDATION.md](./DOCUMENTATION_VALIDATION.md) | Validación de consistencia |
| [UPDATE_SUMMARY.md](./UPDATE_SUMMARY.md) | Resumen de actualizaciones |
| [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md) | Resumen de implementación |

---

## 🔍 Búsqueda Rápida

### "¿Cómo empiezo?"
→ [QUICK_START.md](./QUICK_START.md)

### "¿Qué tecnologías usamos?"
→ [TECH_STACK_FINAL.md](./TECH_STACK_FINAL.md)

### "¿Cómo funciona el sistema?"
→ [ARCHITECTURE_DECISIONS.md](./ARCHITECTURE_DECISIONS.md)

### "¿Cuánto cuesta?"
→ [TECH_STACK_FINAL.md](./TECH_STACK_FINAL.md) - Sección "Proyecciones de Costo"

### "¿Qué agentes hay?"
→ [RACE_POSITION_AGENT_SPEC.md](./RACE_POSITION_AGENT_SPEC.md)

### "¿Cómo uso el caché?"
→ [CACHE_SYSTEM_IMPLEMENTATION.md](./CACHE_SYSTEM_IMPLEMENTATION.md)

### "¿Qué herramientas MCP hay?"
→ [MCP_API_REFERENCE.md](./MCP_API_REFERENCE.md)

### "¿Cómo configuro Gemini?"
→ [GEMINI_FLASH_THINKING_GUIDE.md](./GEMINI_FLASH_THINKING_GUIDE.md)

---

## 📊 Estado de Documentación

| Fase | Documentación | Estado |
|------|---------------|--------|
| **Phase 1-2** | Data Layer | ✅ 100% |
| **Phase 2D** | Architecture | ✅ 100% |
| **Phase 3A** | LangChain | ✅ Planificado |
| **Phase 3B** | Agents | 📋 Pendiente |
| **Phase 4** | UI/API | 📋 Pendiente |

**Total**: 12 documentos completos (~25,000 palabras)

---

## 🎯 Decisiones Clave

### LLM Strategy
- **Primary**: Claude 3.5 Sonnet (~30%)
- **Secondary**: Gemini 2.0 Flash Thinking (~70%)
- **Model**: `gemini-2.0-flash-thinking-exp-1219`
- **Routing**: Complexity-based

### Vector Store
- **MVP**: ChromaDB (local, free)
- **Production**: Pinecone (optional)

### Embeddings
- **Model**: all-MiniLM-L6-v2 (384 dims)

### Cache
- **MVP**: Parquet only
- **Redis**: Optional for production

### Monitoring
- **Primary**: LangSmith
- **Fallback**: LocalTokenTracker

### Architecture
- **Agents**: 5 especializados
- **Framework**: LangChain

### Costs
- **MVP**: $8.50/mes
- **Production**: $294/mes

---

## 📝 Convenciones

### Símbolos Usados
- ✅ Completado
- 🔄 En progreso
- 📋 Planificado
- ⭐ Nuevo/Importante
- ❌ Descartado/Deprecated

### Estructura de Docs
- **README.md** en raíz: Overview general
- **docs/**: Documentación técnica
- **[nombre]_SPEC.md**: Especificaciones
- **[nombre]_GUIDE.md**: Guías prácticas
- **[nombre]_IMPLEMENTATION.md**: Detalles de implementación

---

## 🔄 Actualizaciones Recientes

### 20/12/2025 - Major Update
- ✅ Stack tecnológico finalizado
- ✅ 11 documentos actualizados
- ✅ 4 documentos nuevos
- ✅ Validación completa

Ver [UPDATE_SUMMARY.md](./UPDATE_SUMMARY.md) para detalles.

---

## 📞 Soporte

**Responsable**: Jorge Rionegro  
**Mantenimiento**: Actualizado con cada cambio significativo  
**Próxima Revisión**: 3 de Enero de 2026

---

## 📌 Nota Importante

**Este directorio contiene la documentación oficial del proyecto.**  
Todos los documentos están sincronizados y validados.

Si encuentras inconsistencias:
1. Verifica primero [TECH_STACK_FINAL.md](./TECH_STACK_FINAL.md) (siempre actualizado)
2. Consulta [DOCUMENTATION_VALIDATION.md](./DOCUMENTATION_VALIDATION.md)
3. Revisa [UPDATE_SUMMARY.md](./UPDATE_SUMMARY.md) para cambios recientes

---

**¡Bienvenido al proyecto F1 Strategist AI! 🏎️💨**
