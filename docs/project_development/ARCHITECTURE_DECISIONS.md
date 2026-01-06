# Architecture Decision Record (ADR)

## Status: APPROVED
**Decision Date**: December 20, 2025  
**Decision Maker**: Jorge Rionegro  
**Status**: Planning Phase

---

## Context

The F1 Strategist AI project requires an AI orchestration framework to coordinate multiple specialized agents, integrate with data sources, and provide intelligent race strategy recommendations. Three main approaches were evaluated:

1. **Claude API Direct Integration**: Simple, low complexity
2. **MCP Server as Microservice**: RESTful API architecture
3. **LangChain with Custom Tools**: Advanced agent orchestration

---

## Decision

**Selected Architecture: Option 3 - LangChain Agent Framework**

### Rationale

After evaluating the three options, **LangChain with custom F1 tools** has been selected as the primary AI orchestration framework for the following reasons:

#### 1. **Multi-Agent Architecture Support**
- Native support for multiple specialized agents (Strategy, Weather, Performance, Race Control)
- Built-in agent coordination and communication protocols
- ReAct (Reasoning + Acting) agent pattern for complex decision-making

#### 2. **RAG System Integration**
- Seamless integration with vector databases (ChromaDB, Pinecone)
- Native support for embeddings and semantic search
- Context-aware retrieval from historical race data and F1 regulations

#### 3. **Tool Orchestration**
- Unified interface for all F1 data tools (13 MCP tools already implemented)
- Dynamic tool selection based on query requirements
- Chain-of-thought reasoning for strategy optimization

#### 4. **Extensibility**
- Easy addition of new agents without architecture changes
- Modular tool registration system
- Support for custom agent behaviors

#### 5. **Production Readiness**
- Battle-tested framework with enterprise adoption
- Active community and extensive documentation
- Monitoring and observability features (LangSmith)

---

## Hybrid LLM Architecture

### Query Routing Strategy

**Complexity-Based Routing**:
- **Simple Queries** (score < 0.4): Gemini 2.0 Flash Thinking
  - Examples: "Who won Bahrain 2024?", "What's the weather forecast?"
  - Cost: $0.00001875/1K tokens input, $0.000075/1K tokens output
  
- **Moderate Queries** (0.4 ≤ score < 0.7): Gemini 2.0 Flash Thinking
  - Examples: "Analyze Hamilton's tire strategy", "Compare lap times"
  - Thinking mode overhead: ~5% additional cost
  
- **Complex Queries** (score ≥ 0.7): Claude 3.5 Sonnet
  - Examples: "Multi-agent orchestration", "Strategic trade-off analysis"
  - Cost: $0.003/1K tokens input, $0.015/1K tokens output

**Complexity Scoring Factors**:
- Multi-agent coordination required
- Number of tool calls needed (>5 = complex)
- Context window size (>50K tokens = complex)
- Strategic reasoning depth

**Cost Savings**: ~68% reduction vs Claude-only approach

---

## Implementation Plan

### Phase 3A: LangChain Foundation (Week 5-6)

#### Objective
Establish LangChain infrastructure with basic agent orchestration

#### Components to Build

##### 1. **Base Agent Framework**
```
src/agents/
├── __init__.py
├── base_agent.py           # Abstract base class for all agents
├── orchestrator.py         # Main agent coordinator
└── tools/
    ├── __init__.py
    ├── f1_data_tools.py    # Wraps UnifiedF1DataProvider
    ├── calculation_tools.py # Strategy calculations
    └── rag_tools.py         # RAG retrieval tools
```

**Key Classes**:
- `BaseF1Agent`: Abstract class defining agent interface
- `AgentOrchestrator`: Coordinates multiple agents
- `F1ToolRegistry`: Manages all available tools

##### 2. **Tool Integration Layer**
Convert existing MCP tools to LangChain tools:

```python
# Example structure
class F1DataTools:
    """LangChain tools for F1 data access."""
    
    tools = [
        Tool(name="GetRaceResults", ...),
        Tool(name="GetTelemetry", ...),
        Tool(name="GetLapTimes", ...),
        # ... 13 total tools from MCP
    ]
```

##### 3. **Initial Agent Implementation**
Start with Strategy Agent as proof of concept:

```python
class StrategyAgent(BaseF1Agent):
    """
    Specialized agent for strategy optimization (Race & Qualifying).
    
    Race Mode Capabilities:
    - Tire strategy recommendations
    - Pit stop timing optimization
    - Fuel management calculations
    - Undercut/overcut decisions
    
    Qualifying Mode Capabilities:
    - Optimal track exit timing
    - Number of attempts strategy (1, 2, or 3 runs)
    - Fuel load optimization (minimal weight)
    - Traffic gap detection
    - Tow (slipstream) opportunities
    - Q1/Q2/Q3 progression strategy
    """
```

#### Deliverables
- ✅ LangChain installed and configured
- ✅ Base agent framework operational
- ✅ All 13 F1 tools converted to LangChain format
- ✅ SessionContext class for session type detection
- ✅ Qualifying-specific tools (gaps, tow, track evolution)
- ✅ Strategy Agent prototype functional (dual-mode: race & qualifying)
- ✅ Basic orchestrator with session-aware routing

---

### Phase 3B: RAG System Implementation (Week 6-7)

#### Objective
Build RAG system for historical context and F1 domain knowledge

#### Architecture

```
src/rag/
├── __init__.py
├── vector_store.py         # ChromaDB integration
├── embeddings.py           # Sentence transformer models
├── retriever.py            # Context retrieval logic
├── indexer.py              # Document processing and indexing
└── knowledge_base/
    ├── regulations/        # F1 regulations documents
    ├── historical/         # Past race strategies
    ├── tracks/             # Circuit characteristics
    └── teams/              # Team-specific data
```

#### Knowledge Base Content

##### 1. **F1 Regulations**
- Sporting regulations (penalties, procedures)
- Technical regulations (car specs, tire rules)
- Race procedures and protocols

##### 2. **Historical Race Data**
- Strategy patterns by circuit
- Successful pit stop windows
- Weather impact analysis
- Safety car statistics

##### 3. **Track Information**
- Circuit characteristics (high/low degradation)
- Optimal tire strategies per track
- Historical winner strategies
- Overtaking difficulty ratings

##### 4. **Team Radio Transcripts**
- Strategic decision conversations
- Driver feedback patterns
- Team communication analysis

#### RAG Pipeline

```
Query → Embedding → Vector Search → Context Retrieval → LLM Augmentation → Response
```

**Key Features**:
- **Semantic Search**: Find relevant historical strategies
- **Multi-Modal Retrieval**: Text + numerical data
- **Temporal Awareness**: Recent races weighted higher
- **Circuit-Specific Context**: Track-relevant information prioritized

#### Deliverables
- ✅ ChromaDB vector store configured
- ✅ Embeddings model selected and integrated
- ✅ Historical data indexed (2018-2025 races)
- ✅ F1 regulations documents processed
- ✅ RAG retrieval tools for agents
- ✅ Context quality evaluation metrics

---

### Phase 3C: Multi-Agent System (Week 7)

#### Objective
Implement all four specialized agents with orchestration

#### Agent Specifications

##### 1. **Strategy Agent** 🎯
**Responsibility**: Core race strategy optimization

**Tools Available**:
- GetRaceResults, GetLapTimes, GetPitStops
- GetTireStrategy, GetWeather
- RAG: Historical strategies
- Calculator: Pit window optimization

**Decision Capabilities**:
- Tire compound selection (Soft/Medium/Hard)
- Pit stop timing (lap windows)
- One-stop vs two-stop strategy
- Undercut/overcut opportunities

**Example Queries**:
- "What's the optimal tire strategy for Monaco?"
- "When should Verstappen pit given current delta?"

##### 2. **Weather Agent** ⛈️
**Responsibility**: Weather impact and adaptation

**Tools Available**:
- GetWeather (current conditions)
- External weather API (forecasts)
- RAG: Historical weather races
- Calculator: Wet tire degradation

**Decision Capabilities**:
- Rain probability assessment
- Wet/intermediate tire timing
- Track drying predictions
- Strategy adaptation for changing conditions

**Example Queries**:
- "Will it rain in the next 15 laps?"
- "Should we switch to intermediates now?"

##### 3. **Performance Agent** 📊
**Responsibility**: Real-time performance analysis

**Tools Available**:
- GetTelemetry, GetLapTimes
- GetDriverInfo, GetRaceResults
- RAG: Driver performance history
- Calculator: Pace analysis

**Decision Capabilities**:
- Lap time predictions
- Driver pace comparison
- Tire degradation tracking
- Gap management recommendations

**Example Queries**:
- "Is Hamilton faster on used mediums than Leclerc on new softs?"
- "What's Verstappen's predicted lap time in 5 laps?"

##### 4. **Race Control Agent** 🚦
**Responsibility**: Safety and regulatory monitoring

**Tools Available**:
- GetTrackStatus, GetRaceControlMessages
- GetWeather (visibility)
- RAG: Safety car statistics
- Calculator: Safety car probability

**Decision Capabilities**:
- Safety car likelihood prediction
- Virtual Safety Car timing exploitation
- Flag interpretation and response
- Incident risk assessment

**Example Queries**:
- "What's the probability of a safety car in the next 10 laps?"
- "Should we pit under this VSC?"

#### Agent Orchestration Flow

```
User Query
    ↓
Orchestrator (Analyzes query intent)
    ↓
┌───────────────┬──────────────┬───────────────┬──────────────┐
│   Strategy    │   Weather    │  Performance  │ Race Control │
│     Agent     │    Agent     │     Agent     │    Agent     │
└───────┬───────┴──────┬───────┴───────┬───────┴──────┬───────┘
        │              │               │              │
        └──────────────┴───────────────┴──────────────┘
                            ↓
                    Consensus Builder
                            ↓
                   Unified Recommendation
                            ↓
                      User Response
```

**Orchestration Logic**:
1. **Query Classification**: Determine which agents are needed
2. **Parallel Execution**: Agents work simultaneously
3. **Conflict Resolution**: Orchestrator mediates disagreements
4. **Confidence Scoring**: Each agent provides confidence level
5. **Final Synthesis**: Combined recommendation with reasoning

#### Communication Protocol

```python
class AgentResponse:
    """Standard response format for all agents."""
    
    recommendation: str          # Agent's suggestion
    confidence: float            # 0.0 to 1.0
    reasoning: str               # Explanation
    data_sources: List[str]      # Tools used
    alternative_options: List[str]  # Other possibilities
    risk_factors: List[str]      # Potential issues
```

#### Deliverables
- ✅ All four agents fully implemented
- ✅ Agent orchestration framework operational
- ✅ Inter-agent communication protocol
- ✅ Conflict resolution mechanism
- ✅ Consensus building algorithm
- ✅ Integration tests for multi-agent scenarios

---

## Technical Architecture

### System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Streamlit  │  │     Dash     │  │   FastAPI    │          │
│  │   Chatbot    │  │ Visualization│  │   REST API   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LangChain Orchestration                      │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │              Agent Orchestrator                         │    │
│  │  ┌──────────────────────────────────────────────┐      │    │
│  │  │  Query → Classify → Route → Execute → Merge │      │    │
│  │  └──────────────────────────────────────────────┘      │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Strategy │  │ Weather  │  │Performan │  │   Race   │       │
│  │  Agent   │  │  Agent   │  │ce Agent  │  │ Control  │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
│       │             │             │             │              │
│       └─────────────┴─────────────┴─────────────┘              │
│                          │                                      │
└──────────────────────────┼──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Tools Layer                               │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   F1 Data    │  │     RAG      │  │ Calculation  │         │
│  │    Tools     │  │   Retrieval  │  │    Tools     │         │
│  │  (13 tools)  │  │    Tools     │  │              │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                 │                  │                  │
└─────────┼─────────────────┼──────────────────┼──────────────────┘
          │                 │                  │
          ▼                 ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Data Layer                                │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Unified F1   │  │   ChromaDB   │  │   Cache      │         │
│  │ DataProvider │  │  Vector DB   │  │   (Redis)    │         │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┘         │
│         │                 │                                     │
│         ▼                 ▼                                     │
│  ┌──────────────┐  ┌──────────────┐                           │
│  │   FastF1     │  │  Knowledge   │                           │
│  │   OpenF1     │  │    Base      │                           │
│  └──────────────┘  └──────────────┘                           │
└─────────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Component | Technology | Justification |
|-----------|------------|---------------|
| **Agent Framework** | LangChain | Multi-agent orchestration, RAG support |
| **LLM Primary** | Claude 3.5 Sonnet | Complex queries (~30%), best reasoning |
| **LLM Secondary** | Gemini 2.0 Flash Thinking | Simple/moderate queries (~70%), cost-effective |
| **Vector DB (MVP)** | ChromaDB | Lightweight, local, free |
| **Vector DB (Prod)** | Pinecone (optional) | Scalable, configurable via settings |
| **Embeddings** | all-MiniLM-L6-v2 | 384 dims, local, universal compatibility |
| **Embeddings** | all-MiniLM-L6-v2 | Fast, efficient for semantic search |
| **Data Provider** | FastF1/OpenF1 | Already implemented, 13 tools ready |
| **Caching** | Redis (optional) | Performance optimization |
| **Monitoring** | LangSmith | Agent debugging, performance tracking |
| **Backend API** | FastAPI | Async support, auto documentation |
| **Frontend** | Streamlit/Dash | Rapid prototyping, data viz |

---

## Agent Implementation Details

### Base Agent Class

```python
"""Base agent class for all F1 agents."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from langchain.agents import Agent
from langchain.tools import Tool
from pydantic import BaseModel


class AgentResponse(BaseModel):
    """Standard response format."""
    
    recommendation: str
    confidence: float
    reasoning: str
    data_sources: List[str]
    alternative_options: List[str]
    risk_factors: List[str]


class BaseF1Agent(ABC):
    """
    Abstract base class for all F1 specialized agents.
    
    All agents must implement:
    - get_tools(): Return available tools
    - analyze(): Process query and return recommendation
    - validate(): Check if agent can handle query
    """
    
    def __init__(self, llm, tools: List[Tool], rag_retriever):
        """
        Initialize agent.
        
        Args:
            llm: Language model instance
            tools: Available tools for this agent
            rag_retriever: RAG system for context
        """
        self.llm = llm
        self.tools = tools
        self.rag_retriever = rag_retriever
        self.agent = self._create_agent()
    
    @abstractmethod
    def get_tools(self) -> List[Tool]:
        """Return tools specific to this agent."""
        pass
    
    @abstractmethod
    async def analyze(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> AgentResponse:
        """
        Analyze query and return recommendation.
        
        Args:
            query: User question
            context: Current race context
            
        Returns:
            Structured agent response
        """
        pass
    
    @abstractmethod
    def validate(self, query: str) -> bool:
        """
        Check if this agent should handle the query.
        
        Args:
            query: User question
            
        Returns:
            True if agent is relevant
        """
        pass
    
    def _create_agent(self) -> Agent:
        """Create LangChain agent instance."""
        # Implementation details
        pass
```

### Orchestrator Pattern

```python
"""Agent orchestrator for coordinating multiple agents."""

from typing import List, Dict, Any
from src.agents.base_agent import BaseF1Agent, AgentResponse


class AgentOrchestrator:
    """
    Coordinates multiple specialized agents.
    
    Responsibilities:
    - Query classification
    - Agent selection
    - Parallel execution
    - Conflict resolution
    - Response synthesis
    """
    
    def __init__(self, agents: List[BaseF1Agent]):
        """
        Initialize orchestrator.
        
        Args:
            agents: List of specialized agents
        """
        self.agents = agents
        self.query_classifier = self._create_classifier()
    
    async def process_query(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process user query through relevant agents.
        
        Steps:
        1. Classify query intent
        2. Select relevant agents
        3. Execute agents in parallel
        4. Resolve conflicts
        5. Build unified response
        
        Args:
            query: User question
            context: Current race state
            
        Returns:
            Unified recommendation with reasoning
        """
        # 1. Classify query
        intent = self._classify_query(query)
        
        # 2. Select agents
        relevant_agents = self._select_agents(intent)
        
        # 3. Execute in parallel
        responses = await self._execute_agents(
            relevant_agents,
            query,
            context
        )
        
        # 4. Resolve conflicts
        consensus = self._build_consensus(responses)
        
        # 5. Synthesize response
        final_response = self._synthesize(consensus, responses)
        
        return final_response
    
    def _classify_query(self, query: str) -> Dict[str, float]:
        """
        Classify query intent.
        
        Returns:
            Intent probabilities (e.g., {"strategy": 0.8, "weather": 0.3})
        """
        pass
    
    def _select_agents(
        self,
        intent: Dict[str, float]
    ) -> List[BaseF1Agent]:
        """Select agents based on intent scores."""
        pass
    
    async def _execute_agents(
        self,
        agents: List[BaseF1Agent],
        query: str,
        context: Dict[str, Any]
    ) -> List[AgentResponse]:
        """Execute agents in parallel."""
        pass
    
    def _build_consensus(
        self,
        responses: List[AgentResponse]
    ) -> AgentResponse:
        """
        Build consensus from agent responses.
        
        Strategy:
        - Weight by confidence scores
        - Identify agreement/disagreement
        - Handle edge cases
        """
        pass
    
    def _synthesize(
        self,
        consensus: AgentResponse,
        all_responses: List[AgentResponse]
    ) -> Dict[str, Any]:
        """Create final user-facing response."""
        pass
```

---

## RAG System Architecture

### Vector Database Schema

```python
"""ChromaDB collection structure."""

# Collection: historical_strategies
{
    "id": "2023_bahrain_verstappen_strategy",
    "metadata": {
        "year": 2023,
        "race": "Bahrain Grand Prix",
        "driver": "Max Verstappen",
        "finishing_position": 1,
        "circuit_type": "high_degradation",
        "weather": "dry",
        "strategy_type": "one_stop"
    },
    "document": """
    Max Verstappen - Bahrain GP 2023
    Strategy: One-stop (Medium → Hard)
    Pit: Lap 16
    Tire life: Medium 16 laps, Hard 42 laps
    Result: Won with 11s gap
    Key factors: Track evolution, medium degradation lower than expected
    """
}

# Collection: f1_regulations
{
    "id": "sporting_reg_pit_stop_procedure",
    "metadata": {
        "category": "sporting_regulations",
        "section": "pit_stops",
        "year": 2024
    },
    "document": """
    FIA Sporting Regulations - Pit Stop Procedure
    - Minimum pit stop time: ~2.0 seconds
    - Pit lane speed limit varies by circuit
    - Unsafe release penalties: 5-10 second time penalty
    ...
    """
}

# Collection: track_characteristics
{
    "id": "monaco_circuit_info",
    "metadata": {
        "track": "Monaco",
        "country": "Monaco",
        "degradation_level": "low",
        "overtaking_difficulty": "very_high"
    },
    "document": """
    Monaco Circuit Characteristics
    - Length: 3.337 km
    - Laps: 78
    - Degradation: Low (one-stop preferred)
    - Overtaking: Nearly impossible
    - Key strategy: Track position > tire advantage
    - Qualifying crucial
    """
}
```

### Retrieval Strategy

```python
"""RAG retrieval logic."""

class F1RAGRetriever:
    """Intelligent context retrieval for F1 queries."""
    
    def retrieve_context(
        self,
        query: str,
        context: Dict[str, Any],
        k: int = 5
    ) -> List[str]:
        """
        Retrieve relevant context for query.
        
        Strategy:
        1. Embed query
        2. Semantic search in relevant collections
        3. Apply filters (circuit, weather, year)
        4. Re-rank by relevance
        5. Return top-k documents
        
        Args:
            query: User question
            context: Current race state (circuit, weather, etc.)
            k: Number of documents to retrieve
            
        Returns:
            List of relevant documents
        """
        # 1. Determine relevant collections
        collections = self._select_collections(query, context)
        
        # 2. Build metadata filters
        filters = self._build_filters(context)
        
        # 3. Semantic search
        results = []
        for collection in collections:
            docs = collection.query(
                query_texts=[query],
                n_results=k,
                where=filters
            )
            results.extend(docs)
        
        # 4. Re-rank
        ranked_results = self._rerank(query, results)
        
        return ranked_results[:k]
```

---

## Next Steps

### Immediate Actions (This Week)
1. ✅ Document architecture decision (this file)
2. ⏳ Research LangChain agent patterns
3. ⏳ Design detailed agent interfaces
4. ⏳ Plan RAG knowledge base structure
5. ⏳ Create implementation roadmap

### Phase 3 Preparation (Next Week)
1. Install LangChain dependencies
2. Set up ChromaDB instance
3. Prepare historical data for indexing
4. Create agent framework scaffolding
5. Design tool conversion strategy

### ✅ Decisions Finalized (December 20, 2025)
- [x] **Vector Store**: ChromaDB (MVP) + Pinecone option (production, config-based)
- [x] **LLM Strategy**: Hybrid routing - Claude 3.5 Sonnet + Gemini 2.0 Flash Thinking
- [x] **Gemini Model**: `gemini-2.0-flash-thinking-exp-1219` (with reasoning mode)
- [x] **Embeddings**: all-MiniLM-L6-v2 (384 dims, local, free)
- [x] **Caching**: Parquet only (no Redis in MVP)
- [x] **Monitoring**: LangSmith from Phase 3A + LocalTokenTracker fallback
- [x] **Cost Projection**: $8.50/mo MVP, $294/mo production

---

## Alternative Approaches Considered

### Option 1: Claude API Direct
**Pros**: Simple, fast to implement  
**Cons**: No multi-agent capability, limited RAG integration  
**Verdict**: ❌ Too simplistic for project requirements

### Option 2: MCP REST API
**Pros**: Microservices architecture, scalable  
**Cons**: Complex deployment, overkill for MVP  
**Verdict**: ❌ Over-engineered for current scope

### Option 3: LangChain (SELECTED) ✅
**Pros**: Perfect fit for multi-agent + RAG requirements  
**Cons**: Steeper learning curve  
**Verdict**: ✅ Best long-term choice

---

## Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| LangChain learning curve | High | Medium | Start with tutorials, simple agents first |
| RAG quality issues | Medium | Medium | Test with diverse queries, tune retrieval |
| Agent conflict resolution | Medium | Low | Define clear priority rules, confidence scoring |
| Performance (response time) | High | Low | Implement caching, parallel execution |
| LLM API costs | Medium | Medium | Monitor usage, implement rate limiting |

---

## Success Criteria

### Technical Metrics
- ✅ All 4 agents operational
- ✅ RAG retrieval accuracy >80%
- ✅ Agent response time <3 seconds
- ✅ Multi-agent consensus working
- ✅ 100+ historical strategies indexed

### Functional Requirements
- ✅ Agents provide accurate recommendations
- ✅ RAG returns relevant historical context
- ✅ Orchestrator handles complex queries
- ✅ System scales to handle concurrent users

---

## References

- [LangChain Documentation](https://python.langchain.com/)
- [LangChain Multi-Agent Systems](https://python.langchain.com/docs/use_cases/agent_simulations/)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [ReAct Pattern Paper](https://arxiv.org/abs/2210.03629)
- [LangSmith Observability](https://docs.smith.langchain.com/)

---

## ADR-007: Proactive AI Assistant Dashboard

**Date**: January 5, 2026  
**Status**: APPROVED  
**Deciders**: Jorge Rionegro

### Context

The original AI Assistant Dashboard was a static chat interface that:

1. **Showed wrong race context** - Always displayed "Abu Dhabi GP 2025" instead of selected race
2. **Input blocked during simulation** - Dashboard regenerated every 3 seconds, making typing impossible
3. **Lost chat history** - Messages disappeared on each refresh
4. **Purely reactive** - User had to ask questions; no proactive strategy alerts

### Decision

Implement a **Proactive AI Assistant** that:

1. **Sends automatic alerts** during race simulation (pit windows, undercut risk, safety car)
2. **Allows user questions** at any time without blocking
3. **Maintains persistent history** using `dcc.Store` with session storage
4. **Shows correct race context** from `session-store` data

### Critical Constraint: NO FUTURE KNOWLEDGE

**CRITICAL**: In simulation mode, the AI must NEVER use future race data.

- All event detection filters data by `timestamp <= current_simulation_time`
- Recommendations based only on data available "at that moment"
- This preserves the integrity of strategy analysis practice

### Implementation Details

#### New Components Created

| Component | File | Purpose |
|-----------|------|---------|
| `RaceEventDetector` | `src/session/event_detector.py` | Detects pit windows, safety car, undercuts |
| `chat-messages-store` | `app_dash.py` | Persistent chat history (session storage) |
| `proactive-check-interval` | `app_dash.py` | 15-second interval for event detection |

#### Event Detection Thresholds

| Event | Condition | Priority |
|-------|-----------|----------|
| Pit Window Open | Stint age within optimal range | 3 |
| Tires Degraded | Stint age > optimal window | 4 |
| Undercut Risk | Gap < 2.5s AND car behind on aged tires | 4 |
| Safety Car | Race control message contains "SAFETY CAR" | 5 |
| VSC | Race control message contains "VSC" | 4 |
| Tire Degradation | Lap time increase > 1.0s over 5 laps | 3 |

#### Tire Compound Windows (Laps)

| Compound | Minimum | Optimal | Maximum |
|----------|---------|---------|---------|
| SOFT | 8 | 12 | 18 |
| MEDIUM | 15 | 22 | 30 |
| HARD | 25 | 35 | 45 |
| INTERMEDIATE | 10 | 20 | 35 |
| WET | 15 | 30 | 50 |

#### Undercut Alert Logic

Conservative approach - only alert when:

1. Gap to car behind < 2.5 seconds
2. Car behind has aged tires (stint > 10 laps)
3. Both cars haven't pitted recently

This avoids false positives and spam alerts.

#### Message Types and Visual Design

| Type | Color | Use Case |
|------|-------|----------|
| User | Blue gradient (#0d6efd) | User questions |
| Assistant | Gray (#2d2d2d) | AI responses to questions |
| Alert (P5) | Red gradient | Safety car, critical |
| Alert (P4) | Orange gradient | Undercut risk, tire overdue |
| Alert (P3) | Amber/Yellow gradient | Pit window open, degradation |

### Alternatives Considered

#### Option A: Keep AI inside dashboard-container (SELECTED)

- Pros: Simpler architecture, single render callback
- Cons: Must use store for persistence
- Decision: Use `chat-messages-store` with `storage_type='session'`

#### Option B: Separate AI container outside dashboard-container

- Pros: Never regenerates, cleaner separation
- Cons: More complex layout, breaks current structure
- Decision: Rejected for now, Option A sufficient

#### Option C: Full LLM integration for proactive alerts

- Pros: More natural language alerts
- Cons: High latency, cost per alert, may fail if LLM unavailable
- Decision: Use rule-based templates with fallback, LLM optional

### Consequences

#### Positive

- Users receive timely strategy alerts without asking
- Chat history persists throughout session
- Correct race context displayed
- Can still ask questions at any time

#### Negative

- Requires event detection logic maintenance
- Hardcoded thresholds may need tuning per circuit
- 15-second check interval may miss rapid events

### Future Improvements

1. **Circuit-specific thresholds** - Some circuits wear tires faster
2. **Weather-triggered alerts** - Rain probability warnings
3. **Position battle alerts** - When gap to car ahead/behind changes significantly
4. **LLM-enhanced alerts** - Use orchestrator for richer context (optional)

---

**Document Version**: 1.1  
**Last Updated**: January 5, 2026  
**Next Review**: After testing with live OpenF1 API  
**Maintained by**: Jorge Rionegro
