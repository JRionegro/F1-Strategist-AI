# F1 Strategist AI - Architecture Restructuring

**Date**: December 22, 2025  
**Status**: ✅ Completed  
**Version**: 2.0 (Container Architecture)

---

## 📋 Overview

Successfully restructured the application from a **single-dashboard chat app** to a **multi-dashboard container platform** following the UI/UX specifications.

---

## 🎯 What Changed

### Before (Version 1.0)
```
app.py (monolithic)
├── Agent initialization
├── Chat interface (hardcoded)
└── Single view only
```

### After (Version 2.0)
```
app.py (main container)
├── Global session management
├── Top menu (mode, config, help)
├── Dashboard selector
├── Simulation controls
└── Dynamic dashboard rendering

src/
├── session/
│   ├── global_session.py (shared state)
│   └── simulation_controller.py (playback)
├── ui/
│   ├── top_menu.py (navigation)
│   └── simulation_controls.py (playback UI)
└── dashboards/
    └── ai_assistant_dashboard.py (modular)
```

---

## 🏗️ New Architecture Components

### 1. Session Management (`src/session/`)

**`global_session.py`**:
- `GlobalSession`: Central state container
  - Mode (Live/Simulation)
  - Race context (year, circuit, session, driver, team)
  - Simulation state (speed, paused, current_time)
  - UI preferences (visible dashboards)
- `SessionMode`: Enum for LIVE | SIMULATION
- `SessionType`: Enum for FP1/FP2/FP3/Qualifying/Sprint/Race
- `RaceContext`: Complete session information

**`simulation_controller.py`**:
- `SimulationController`: Time progression management
  - Play/Pause control
  - Speed adjustment (1x - 3x)
  - Time jumps (forward/backward)
  - Lap jumps
  - Progress tracking

### 2. UI Components (`src/ui/`)

**`top_menu.py`**:
- `TopMenu`: Navigation and configuration
  - Mode selector (Live/Simulation)
  - Main menu (Dashboards/Configuration/Help)
  - Dashboard visibility toggles
  - Configuration panel (API keys, LLM settings)
  - Help documentation

**`simulation_controls.py`**:
- `SimulationControls`: Playback interface
  - Play/Pause button
  - Speed selector (1x-3x)
  - Progress bar
  - Time indicators
  - Advanced controls (lap jump, time jump)

### 3. Dashboard Modules (`src/dashboards/`)

**`ai_assistant_dashboard.py`**:
- `AIAssistantDashboard`: Modular chat interface
  - Receives global context
  - Independent session state
  - Reusable component
  - Can be shown/hidden dynamically

---

## 🔄 Migration Path

### Files Created
1. ✅ `src/session/__init__.py`
2. ✅ `src/session/global_session.py` (191 lines)
3. ✅ `src/session/simulation_controller.py` (214 lines)
4. ✅ `src/ui/__init__.py`
5. ✅ `src/ui/top_menu.py` (225 lines)
6. ✅ `src/ui/simulation_controls.py` (170 lines)
7. ✅ `src/dashboards/__init__.py`
8. ✅ `src/dashboards/ai_assistant_dashboard.py` (179 lines)
9. ✅ `app.py` (new container, 416 lines)

### Files Backed Up
- ✅ `app_old.py` (original monolithic version)

### Files Updated
- ✅ `docs/UI_UX_SPECIFICATION.md` (added architecture section)

---

## 🎮 Key Features Implemented

### 1. Global Session Management
- ✅ Single source of truth for all dashboards
- ✅ Automatic context inheritance
- ✅ Persistent state across dashboard switches

### 2. Dual Mode Support
- ✅ Live Mode (🔴): Real-time data (with auto-detection placeholder)
- ✅ Simulation Mode (🔵): Historical replay with controls

### 3. Simulation Controls
- ✅ Play/Pause functionality
- ✅ Speed adjustment (1x, 1.25x, 1.5x, 1.75x, 2x, 2.5x, 3x)
- ✅ Time scrubbing (forward/backward)
- ✅ Lap jumping
- ✅ Progress tracking

### 4. Dashboard Management
- ✅ Dynamic show/hide dashboards
- ✅ Multiple dashboards support
- ✅ Currently implemented: AI Assistant
- 🔄 Coming soon: 7 more dashboards

### 5. Context Selection
- ✅ Year selector (2018-2025)
- ✅ Circuit selector (10+ circuits)
- ✅ Session type selector (FP1/2/3, Qualifying, Sprint, Race)
- ✅ Driver focus
- ✅ Team focus

### 6. Top Menu
- ✅ Horizontal navigation
- ✅ Mode switcher
- ✅ Dashboard selector
- ✅ Configuration panel
- ✅ Help documentation

---

## 📊 Current Status

### Completed ✅
- [x] Session management infrastructure
- [x] Global state container
- [x] Simulation controller with time controls
- [x] Top menu component
- [x] Simulation controls UI
- [x] AI Assistant dashboard (modularized)
- [x] Main app container
- [x] Dashboard selector
- [x] Context inheritance
- [x] UI/UX specification update

### Remaining 🔄
- [ ] Live session auto-detection implementation
- [ ] Circuit & Positions dashboard
- [ ] Telemetry Comparison dashboard
- [ ] Tire Strategy dashboard
- [ ] Weather dashboard
- [ ] Lap Analysis dashboard
- [ ] Race Control dashboard
- [ ] Qualifying Progress dashboard
- [ ] Layout presets (Race Day, Qualifying, Practice)
- [ ] Multi-monitor support

---

## 🚀 How to Use

### Starting the Application

```powershell
# Activate virtual environment
venv\Scripts\Activate.ps1

# Run Streamlit app
streamlit run app.py
```

### Using the Interface

1. **Select Mode**: 🔴 Live or 🔵 Simulation
2. **Set Context**: Choose year, circuit, session in sidebar
3. **Optional**: Focus on specific driver/team
4. **Choose Dashboards**: Toggle which dashboards to display
5. **Simulation Mode**: Use playback controls
6. **Interact**: Use AI Assistant or explore data

---

## 📁 Project Structure

```
F1 Strategist AI/
├── app.py                          # Main container (new)
├── app_old.py                      # Backup of original
├── .env.example                    # Environment template
├── requirements.txt                # Dependencies
│
├── src/
│   ├── session/                    # NEW: Session management
│   │   ├── __init__.py
│   │   ├── global_session.py       # Global state
│   │   └── simulation_controller.py # Playback control
│   │
│   ├── ui/                         # NEW: UI components
│   │   ├── __init__.py
│   │   ├── top_menu.py             # Navigation
│   │   └── simulation_controls.py  # Playback UI
│   │
│   ├── dashboards/                 # NEW: Dashboard modules
│   │   ├── __init__.py
│   │   └── ai_assistant_dashboard.py # Chat interface
│   │
│   ├── agents/                     # Existing: AI agents
│   │   ├── orchestrator.py
│   │   ├── strategy_agent.py
│   │   ├── weather_agent.py
│   │   ├── performance_agent.py
│   │   ├── race_control_agent.py
│   │   └── race_position_agent.py
│   │
│   ├── chatbot/                    # Existing: Chat infrastructure
│   │   ├── session_manager.py
│   │   ├── message_handler.py
│   │   └── chat_interface.py
│   │
│   ├── llm/                        # Existing: LLM providers
│   │   ├── hybrid_router.py
│   │   ├── claude_provider.py
│   │   └── gemini_provider.py
│   │
│   ├── data/                       # Existing: Data access
│   │   └── f1_data_provider.py
│   │
│   └── rag/                        # Existing: RAG system
│       └── chromadb_store.py
│
└── docs/
    ├── UI_UX_SPECIFICATION.md      # UPDATED: Architecture section
    └── project_development/
        └── ARCHITECTURE_RESTRUCTURING.md # This file
```

---

## 🎨 Visual Changes

### Before
```
Simple chat interface only
No mode selection
No simulation controls
Single view
```

### After
```
┌─────────────────────────────────────────────────────┐
│ 🏎️ F1 STRATEGIST AI                                │
│ [🔵 SIMULATION]  [Dashboards▼] [Config] [Help]     │
├─────────────────────────────────────────────────────┤
│ 🔵 2023 Bahrain | Race | Lap 18/57                 │
│ ⚡ Playback: ▶️ Playing (2x)                        │
├─────────────────────────────────────────────────────┤
│ 🎮 SIMULATION CONTROLS                              │
│ [▶️] [⏮️] [2x] [⏪] [⏩]  ████████░░░ 65%           │
├─────────────────────────────────────────────────────┤
│ 🤖 AI Assistant Dashboard                           │
│ (Chat interface...)                                 │
│                                                     │
│ 🏎️ Circuit & Positions (Coming Soon)              │
│ 📈 Telemetry Comparison (Coming Soon)              │
└─────────────────────────────────────────────────────┘
```

---

## 🔍 Technical Details

### State Management

**Streamlit Session State Keys**:
- `global_session`: GlobalSession instance
- `ai_assistant_messages`: Chat history for AI Assistant

**Global Session Attributes**:
```python
session.mode                    # SessionMode enum
session.race_context            # RaceContext with all details
session.simulation_speed        # 1.0 - 3.0
session.simulation_paused       # bool
session.simulation_current_time # datetime
session.visible_dashboards      # List[str]
session.active_dashboard        # str
```

### Context Propagation

1. User selects context in sidebar
2. `GlobalSession.race_context` updated
3. `AgentContext` created from `RaceContext`
4. Dashboard receives context via `render(context)`
5. All dashboards use same context automatically

### Simulation Time Flow

```
User clicks Play
    ↓
SimulationController.play()
    ↓
update() called regularly
    ↓
current_time += (real_elapsed * speed)
    ↓
Callback triggers session update
    ↓
UI reflects new time
```

---

## 🐛 Known Issues & Future Work

### TODO
1. **Live Session Detection**
   - Implement F1 calendar API integration
   - Auto-detect sessions within 3-hour window
   - Switch to live mode automatically

2. **Simulation Time Integration**
   - Connect SimulationController to F1DataProvider
   - Update data based on simulation time
   - Synchronize all dashboards with current time

3. **Layout Persistence**
   - Save user's dashboard layout
   - Remember visible dashboards
   - Restore on app restart

4. **Additional Dashboards**
   - Implement remaining 7 dashboards
   - Follow modular pattern
   - Test with global context

5. **Performance Optimization**
   - Dashboard lazy loading
   - Data caching improvements
   - Reduce re-renders

---

## ✅ Testing Checklist

- [x] App starts without errors
- [x] Mode selector works
- [x] Context selection updates
- [x] Dashboard selector toggles visibility
- [x] Simulation controls render (in simulation mode)
- [x] AI Assistant dashboard works
- [x] Top menu navigation functions
- [x] Configuration panel displays
- [x] Help panel shows documentation
- [ ] Live mode detection (placeholder)
- [ ] Simulation time progression (needs integration)
- [ ] Multiple dashboards simultaneously (only AI available now)

---

## 📚 Related Documentation

- [UI/UX Specification](../UI_UX_SPECIFICATION.md)
- [Phase 3B Implementation](PHASE_3B_IMPLEMENTATION.md)
- [Project Status](PROJECT_STATUS.md)

---

## 👥 Contributors

- Architecture redesign based on UI/UX specifications
- Implemented by GitHub Copilot with user guidance
- Date: December 22, 2025
