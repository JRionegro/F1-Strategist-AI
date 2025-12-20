# F1 Strategist AI - UI/UX Specification

**Version**: 1.0  
**Date**: December 20, 2025  
**Status**: Initial Design

---

## 📋 Index

1. [Overview](#overview)
2. [Interface Architecture](#interface-architecture)
3. [Main Dashboards](#main-dashboards)
4. [Advanced Dashboards](#advanced-dashboards)
5. [Top Menu](#top-menu)

---

## 🎯 Overview

F1 Strategist AI provides a comprehensive interface for strategy engineers enabling real-time analysis (Live) and historical simulations. The interface is designed to maximize visible information while maintaining usability during high-pressure situations.

**Target Users**: Strategy engineers, performance analysts, race teams

**Usage Contexts**:
- **Live Race/Qualifying**: Real-time decisions (<5s latency)
- **Race Weekend Analysis**: Between-session analysis (practice, qualifying, race)
- **Historical Simulation**: Post-race analysis, training, research

---

## 🏗️ Interface Architecture

### Main Components

```
┌─────────────────────────────────────────────────────────────────┐
│  TOP MENU: Live/Sim | Config | Dashboards | Settings            │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│              DASHBOARD AREA (Multi-panel)                        │
│                                                                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐ │
│  │   Dashboard 1    │  │   Dashboard 2    │  │  Dashboard 3  │ │
│  │                  │  │                  │  │               │ │
│  └──────────────────┘  └──────────────────┘  └───────────────┘ │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 Main Dashboards

### 1. AI Assistant / Chatbot 🤖

**Mission**: Conversational interface with 5 specialized agents for strategic queries in natural language.

**MCP Tools**:
- All tools (13 tools)
- Access to 5 agents: Strategy, Weather, Performance, Race Control, Race Position

**Features**:
- Chat with conversational history
- Responses with embedded charts
- Contextual suggestions ("What would you ask now?")
- Automatic qualifying vs race mode detection
- Conversation export

**Availability**: ✅ Live | ✅ Simulation

**Priority**: 🔴 MVP - CRITICAL

#### Wireframe ASCII

```
┌────────────────────────────────────────────────────────────────────────────┐
│  F1 STRATEGIST AI - CHAT ASSISTANT                    [Mode: RACE] 🔴     │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │  🧠 Strategy Agent                                                    │ │
│  │  What's the optimal pit window for VER considering track position?   │ │
│  │  ─────────────────────────────────────────────────────────────────   │ │
│  │  Based on current pace and tire degradation, optimal window is       │ │
│  │  Laps 22-25. Current gap to HAM is 3.2s - undercut viable.          │ │
│  │                                                                       │ │
│  │  📊 [Pit Window Chart]  🔴 Soft: 18 laps  ⚪ Medium: 28 laps         │ │
│  │                                                                       │ │
│  │  ⏰ 14:32:15                                                          │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │  👤 You (Engineer)                                                    │ │
│  │  What if we extend to lap 26 to cover HAM's stop?                   │ │
│  │  ⏰ 14:32:45                                                          │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │  🧠 Strategy Agent                                                    │ │
│  │  Extending to L26 adds 0.8s degradation risk. If HAM stops L24,     │ │
│  │  we'd emerge behind by ~1.2s. Recommend L23 stop for clean track.   │ │
│  │                                                                       │ │
│  │  💡 Alternative: 1-stop Medium (L18) → Hard (finish)                 │ │
│  │  ⏰ 14:33:02                                                          │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
├────────────────────────────────────────────────────────────────────────────┤
│  💭 Suggestions:                                                           │
│  • "Weather impact on tire degradation?"  • "HAM's tire life remaining?"  │
│  • "Show undercut/overcut calculation"    • "SC probability next 10 laps?"│
├────────────────────────────────────────────────────────────────────────────┤
│  Type your question...                                    [📎] [🎤] [Send]│
└────────────────────────────────────────────────────────────────────────────┘

Features Visible:
• Agent identification (icon + name)
• Timestamp per message
• Embedded charts/visualizations
• Contextual suggestions below chat
• Input area with attachments/voice/send
• Session mode indicator (RACE/QUALIFYING)
```

---

### 2. Weather & Meteorological Conditions 🌦️

**Mission**: Climate conditions monitoring with satellite rain radar and strategy impact prediction.

**MCP Tools**:
- `get_weather`: Temperature, humidity, wind, rain
- `get_track_status`: Track status (dry, damp, wet)

**Features**:
- Rain radar with animation (last 60 minutes)
- Forecast for next 30/60/90 minutes
- Track vs air temperature (temporal chart)
- Wind rose by circuit sector
- Condition change alerts

**Availability**: ✅ Live | ⚠️ Simulation (limited historical)

**Priority**: 🟡 Phase 3B

#### Wireframe ASCII

```
┌────────────────────────────────────────────────────────────────────────────┐
│  WEATHER & TRACK CONDITIONS                           14:35:22  🌦️ LIVE  │
├─────────────────────────────────┬──────────────────────────────────────────┤
│  🌧️ RAIN RADAR (Satellite)     │  📊 TEMPERATURE EVOLUTION                │
│  ┌───────────────────────────┐  │  ┌────────────────────────────────────┐ │
│  │         NW ↗               │  │  │ 45°C┤                              │ │
│  │    ░░▒▒▓▓█  Circuit        │  │  │ 40°C┤  ╱─╲                   Track│ │
│  │   ░░▒▒▓▓██ ◉─────┐         │  │  │ 35°C┤ ╱   ╲   ╱─╲          Surface│ │
│  │  ░░▒▒▓▓███ │     │         │  │  │ 30°C┤╱     ╲ ╱   ╲    ╱─╲        │ │
│  │   ░▒▒▓▓██  └─────┘         │  │  │ 25°C┼───────▼─────╲──╱───╲─ Air  │ │
│  │    ░▒▓███     SE ↓         │  │  │ 20°C┤                    Temp     │ │
│  │     ░▒▓██                  │  │  │     └─────┬─────┬─────┬─────┬────│ │
│  └───────────────────────────┘  │  │        13:00  14:00  15:00  16:00  │ │
│                                  │  └────────────────────────────────────┘ │
│  🌧️ Rain approaching from NW    │                                          │
│  ⏰ ETA: 18-22 minutes           │  🌡️ Track: 38.5°C  Air: 24.2°C         │
│  📏 Distance: 12 km              │  💧 Humidity: 68%  ☁️ Cloud: 75%        │
│  💨 Speed: 35 km/h               │  🌊 Pressure: 1013 hPa                  │
│                                  │                                          │
│  Legend:                         │  ⚠️ ALERTS                              │
│  ░ Light  ▒ Moderate  ▓ Heavy   │  • Track temp dropping (-2°C/30min)     │
│  █ Very Heavy                    │  • Rain forecast: 30% (30m), 65% (60m)  │
├─────────────────────────────────┴──────────────────────────────────────────┤
│  💨 WIND CONDITIONS BY SECTOR                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  S1 (Start-T3):  12 km/h SW ↙  Impact: Low (Tailwind T1-T2)        │  │
│  │  S2 (T4-T9):     18 km/h W  ←  Impact: Medium (Crosswind T7)        │  │
│  │  S3 (T10-Finish): 8 km/h NW ↖  Impact: Low (Following corners)      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
├────────────────────────────────────────────────────────────────────────────┤
│  🎯 STRATEGY IMPACT                                                         │
│  • Current: Slicks optimal (dry track, no rain imminent)                   │
│  • If rain arrives L12-15: Prepare Inters, monitor Turn 7 (standing water)│
│  • Tire pressure: Increase +0.2 PSI (cooling track)                        │
└────────────────────────────────────────────────────────────────────────────┘

Features Visible:
• Live satellite rain radar with movement animation
• Temperature dual-line graph (track vs air)
• Wind direction by circuit sector
• Rain probability forecast timeline
• Strategic impact recommendations
• Visual alerts for condition changes
```

---

### 3. Circuit & Track Positions 🏎️

**Mission**: Circuit view with real-time positions of all drivers and gaps.

**MCP Tools**:
- `get_race_results`: Current positions
- `get_lap_times`: Calculated gaps
- `get_driver_info`: Team colors
- Position telemetry (future OpenF1 integration)

**Features**:
- Circuit map with positioned cars
- Side panel with classification:
  - Position | Driver | Gap to next | Gap to leader
- Team colors
- DRS detection zones
- Pit stop in progress indicators

**Availability**: ✅ Live | ✅ Simulation

**Priority**: 🔴 MVP - CRITICAL

#### Wireframe ASCII

```
┌────────────────────────────────────────────────────────────────────────────┐
│  CIRCUIT MAP & POSITIONS              Lap 18/57  📍 Bahrain International │
├───────────────────────────────────┬────────────────────────────────────────┤
│  TRACK VIEW                        │  LIVE STANDINGS                       │
│                                    │  ┌──────────────────────────────────┐ │
│        T4 🔵1                      │  │ P │ Driver│ Gap Next│ Gap Leader │ │
│         ╱                          │  ├───┼───────┼─────────┼────────────┤ │
│    T3 ╱  ╲                         │  │🥇│ VER █ │ Leader  │    ---     │ │
│       │   ╲T5                      │  │🥈│ HAM █ │ +3.245s │  +3.245s   │ │
│   T2 │     ╲  🔴2                  │  │🥉│ LEC █ │ +0.892s │  +4.137s   │ │
│      │      ╲                      │  │ 4│ RUS █ │ +1.654s │  +5.791s   │ │
│  T1 ─┘       ╲T6                   │  │ 5│ PER █ │ +2.108s │  +7.899s   │ │
│  🏁START       ╲                   │  │ 6│ SAI █ │ +1.223s │  +9.122s   │ │
│  🟢3 DRS-1      ╲T7                │  │ 7│ NOR █ │ +0.987s │ +10.109s   │ │
│  ┊┊┊┊┊┊┊┊       │                  │  │ 8│ ALO █ │ +3.445s │ +13.554s   │ │
│                T8│                  │  │ 9│ OCO █ │ +0.556s │ +14.110s   │ │
│              ╱  │  🟡4              │  │10│ GAS █ │ +1.892s │ +16.002s   │ │
│         T11╱    │                   │  │11│ TSU █ │ +2.334s │ +18.336s   │ │
│       ╱        T9                   │  │12│ STR █ │ +0.778s │ +19.114s   │ │
│  T12╱      DRS-2 ╲                 │  │13│ MAG █ │ +4.223s │ +23.337s   │ │
│  │         ┊┊┊┊   ╲                │  │14│ BOT █ │ +1.554s │ +24.891s   │ │
│  │  T13           T10               │  │15│ ZHO █ │ +0.887s │ +25.778s   │ │
│  └────┐                             │  │16│ HUL █ │ +2.112s │ +27.890s   │ │
│  T15  │T14                          │  │17│ ALB █ │ +1.445s │ +29.335s   │ │
│       └──────────                   │  │18│ SAR █ │ +0.992s │ +30.327s   │ │
│                                    │  │19│ DEV 🔧│  PIT IN │     ---     │ │
│  Legend:                            │  │20│ RIC █ │ +5.221s │ +35.548s   │ │
│  █ Car (Team Color)                │  └──────────────────────────────────┘ │
│  🔵 Red Bull  🔴 Ferrari            │                                       │
│  🟢 Mercedes  🟡 McLaren            │  🎯 KEY BATTLES                      │
│  ┊┊┊ DRS Detection Zone            │  • P1-P2: VER vs HAM (+3.2s - DRS)   │
│  🔧 Pit Stop in progress            │  • P5-P6: PER vs SAI (+1.2s)         │
│                                    │  • P9-P11: OCO-GAS-TSU (DRS train)   │
└───────────────────────────────────┴────────────────────────────────────────┘

Features Visible:
• Circuit layout with all corners labeled
• Live car positions color-coded by team
• DRS detection zones highlighted
• Live standings table with real-time gaps
• Pit stop indicators
• Key battles highlighted
• Podium positions with medals
```

---

### 4. Multi-Driver Telemetry Comparison 📈

**Mission**: Visual telemetry comparison between selected drivers (speed, throttle, brake, gear, DRS).

**MCP Tools**:
- `get_telemetry`: Complete data per driver
- `get_lap_times`: Best lap selection

**Features**:
- Driver selector (up to 4 simultaneous)
- Overlaid charts with distinctive colors:
  - Speed (km/h)
  - Throttle (0-100%)
  - Brake (0-100%)
  - Gear (1-8)
  - DRS (on/off)
- Circuit distance synchronization
- Zoom on specific sectors
- Delta time overlay

**Availability**: ✅ Live | ✅ Simulation

**Priority**: 🔴 MVP - CRITICAL

#### Wireframe ASCII

```
┌────────────────────────────────────────────────────────────────────────────┐
│  TELEMETRY COMPARISON                    Lap 23  |  Best Lap Analysis      │
├────────────────────────────────────────────────────────────────────────────┤
│  Drivers: [✓] VER (Red Bull)  [✓] HAM (Mercedes)  [ ] LEC  [ ] RUS        │
├────────────────────────────────────────────────────────────────────────────┤
│  SPEED (km/h)                                                               │
│  350├─────────────────────────────────────────────────────────────────────┤│
│  320│         ╱──────╲                  ╱────────╲                         ││
│  290│       ╱          ╲              ╱            ╲                       ││
│  260│     ╱    VER ══   ╲          ╱    HAM ──     ╲                      ││
│  230│   ╱                 ╲      ╱                   ╲                     ││
│  200│ ╱                     ╲  ╱                       ╲                   ││
│  170├┴───┬────┬────┬────┬────┬────┬────┬────┬────┬────┬───────┬─────────┤│
│      T1   T3   T5   T7   T9  T11  T13  T15  DRS                           │
│                                                                             │
│  THROTTLE (%)                                                               │
│  100├══════╗         ╔══════╗         ╔══════╗          ╔════════         ││
│   80│      ║         ║      ║         ║      ║          ║                 ││
│   60│      ║         ║      ║         ║      ║          ║                 ││
│   40│      ╚═        ╚══    ╚═        ╚══    ╚══        ╚                 ││
│   20│                                                                      ││
│    0├─────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬───────┬─────────┤│
│                                                                             │
│  BRAKE (%)                                                                  │
│  100├     ╔╗      ╔╗      ╔╗      ╔╗      ╔╗      ╔╗                      ││
│   80│     ║║      ║║      ║║      ║║      ║║      ║║                      ││
│   60│     ║║      ║║      ║║      ║║      ║║      ║║                      ││
│   40│     ║║      ║║      ║║      ║║      ║║      ║║                      ││
│   20│     ╚╝      ╚╝      ╚╝      ╚╝      ╚╝      ╚╝                      ││
│    0├─────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬───────┬─────────┤│
│                                                                             │
│  GEAR                                                                       │
│    8├    ════     ════     ════     ════     ════     ════                ││
│    7│   ╱    ╲   ╱    ╲   ╱    ╲   ╱    ╲   ╱    ╲   ╱    ╲              ││
│    6│  ╱      ╲ ╱      ╲ ╱      ╲ ╱      ╲ ╱      ╲ ╱      ╲             ││
│    5│ ╱        V        V        V        V        V        V             ││
│  3-4├─────────────────────────────────────────────────────────            ││
│    0├─────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬───────┬─────────┤│
│      0m   500m  1km  1.5km 2km  2.5km 3km  3.5km 4km  4.5km  5km    5.4km │
├────────────────────────────────────────────────────────────────────────────┤
│  ⏱️ DELTA TIME (VER vs HAM)                                                │
│  +0.5s│                          ╱──VER faster──╲                          │
│  +0.0s├──────────────────────────┼───────────────┼──────────────────────  │
│  -0.5s│  ╲──HAM faster──╱                        ╲──HAM faster──╱         │
│                                                                             │
│  📊 SECTOR TIMES         S1          S2          S3        TOTAL           │
│  VER (Red Bull)      18.234s     28.445s     22.891s    1:09.570          │
│  HAM (Mercedes)      18.299s     28.402s     22.934s    1:09.635  +0.065s │
│                                                                             │
│  🎯 KEY DIFFERENCES                                                         │
│  • T4-T5: HAM gains 0.043s (better entry speed)                            │
│  • T9-T11: VER gains 0.089s (later braking, higher apex speed)            │
│  • DRS Zone: VER gains 0.034s (better traction out of T13)                │
└────────────────────────────────────────────────────────────────────────────┘

Features Visible:
• Multi-driver selection (up to 4)
• Synchronized telemetry charts (Speed, Throttle, Brake, Gear)
• Distance-based X-axis alignment
• Delta time comparison overlay
• Sector time breakdown
• Key differences analysis with turn-by-turn insights
```

---

### 5. Raw Data Analysis (Raw Data Comparison) 📊

**Mission**: Comparative table of raw data between drivers for detailed difference analysis.

**MCP Tools**:
- `get_telemetry`: All fields
- `get_lap_times`: Sector times

**Features**:
- Table with data per measurement point:
  - Distance | Speed | Throttle | Brake | Gear | RPM | DRS
- Columns per selected driver
- Calculated differences (Δ)
- Extreme value highlighting:
  - Green: faster / better
  - Red: slower / worse
- CSV export
- Filtering by sector or distance range

**Availability**: ✅ Live | ✅ Simulation

**Priority**: 🟡 Phase 3B

#### Wireframe ASCII

```
┌────────────────────────────────────────────────────────────────────────────┐
│  RAW DATA COMPARISON                          [Export CSV] [Filter: All]   │
├────────────────────────────────────────────────────────────────────────────┤
│  Drivers: VER (Red Bull) vs HAM (Mercedes)           Lap 23 - Best Lap     │
├────────────────────────────────────────────────────────────────────────────┤
│  Filter: [All Sectors ▼] | Distance: [0m] ──────●──────── [5412m]         │
├───┬──────┬────────┬────────┬─────┬────────┬────────┬─────┬────────┬───────┤
│Loc│ Dist │  VER   │  HAM   │  Δ  │  VER   │  HAM   │  Δ  │  VER   │  HAM │
│   │  (m) │ Speed  │ Speed  │Speed│Throttle│Throttle│Throt│ Brake  │ Brake│
├───┼──────┼────────┼────────┼─────┼────────┼────────┼─────┼────────┼──────┤
│T1 │   0  │  298   │  295   │ +3  │  100%  │  100%  │  0  │   0%   │  0%  │
│   │  50  │  304   │  302   │ +2  │  100%  │  100%  │  0  │   0%   │  0%  │
│   │ 100  │  312   │  308   │ +4  │  100%  │  100%  │  0  │   0%   │  0%  │
│   │ 150  │  318   │  316   │ +2  │  100%  │  100%  │  0  │   0%   │  0%  │
│   │ 200  │  289   │  292   │ -3  │   42%  │   48%  │ -6  │  85%   │ 79% │
│T2 │ 250  │  198   │  205   │ -7  │    8%  │   12%  │ -4  │  95%   │ 92% │
│   │ 300  │  156   │  163   │ -7  │    0%  │    0%  │  0  │  78%   │ 71% │
│   │ 350  │  142   │  148   │ -6  │   28%  │   35%  │ -7  │  42%   │ 38% │
│   │ 400  │  167   │  171   │ -4  │   65%  │   68%  │ -3  │   0%   │  0%  │
│   │ 450  │  198   │  199   │ -1  │   89%  │   91%  │ -2  │   0%   │  0%  │
│T3 │ 500  │  234   │  232   │ +2  │  100%  │  100%  │  0  │   0%   │  0%  │
│   │ 550  │  267   │  263   │ +4  │  100%  │  100%  │  0  │   0%   │  0%  │
│   │ 600  │  289   │  285   │ +4  │  100%  │  100%  │  0  │   0%   │  0%  │
│   │ 650  │  301   │  298   │ +3  │  100%  │  100%  │  0  │   0%   │  0%  │
│T4 │ 700  │  273   │  278   │ -5  │   38%  │   42%  │ -4  │  88%   │ 82% │
│   │ 750  │  189   │  196   │ -7  │    5%  │    8%  │ -3  │  92%   │ 89% │
│   │ 800  │  134   │  142   │ -8  │    0%  │    0%  │  0  │  65%   │ 58% │
│   │ ▼    │   ▼    │   ▼    │  ▼  │   ▼    │   ▼    │  ▼  │   ▼    │  ▼  │
│   │[Show more rows...]                                                     │
├───┴──────┴────────┴────────┴─────┴────────┴────────┴─────┴────────┴──────┤
│  📊 STATISTICS                                                              │
│  ┌─────────────────┬────────────┬────────────┬──────────────────────────┐ │
│  │     Metric      │    VER     │    HAM     │      Δ (VER - HAM)       │ │
│  ├─────────────────┼────────────┼────────────┼──────────────────────────┤ │
│  │ Avg Speed       │  243 km/h  │  241 km/h  │  +2 km/h  (better)       │ │
│  │ Max Speed       │  328 km/h  │  326 km/h  │  +2 km/h  (better)       │ │
│  │ Max Brake       │   98%      │   95%      │  +3%      (harder)       │ │
│  │ Avg Throttle    │   76%      │   74%      │  +2%      (aggressive)   │ │
│  │ Braking Points  │    14      │    14      │  0        (same)         │ │
│  │ Time on Throttle│  58.2s     │  57.8s     │  +0.4s    (more)         │ │
│  │ Time on Brake   │  11.4s     │  11.8s     │  -0.4s    (less)         │ │
│  └─────────────────┴────────────┴────────────┴──────────────────────────┘ │
│                                                                             │
│  🎯 KEY FINDINGS                                                            │
│  • T2 (200-450m): HAM faster through corner (+0.089s) - earlier throttle   │
│  • T4-T5 (700-1200m): HAM better entry (+0.043s) - smoother brake release  │
│  • T9-T11 (2400-3100m): VER gains back (+0.134s) - later braking, apex    │
│  • Overall: VER wins on straights, HAM better in slow corners              │
└────────────────────────────────────────────────────────────────────────────┘

Features Visible:
• Raw telemetry data table (scrollable)
• Color coding: Green (advantage), Red (disadvantage)
• Delta columns showing differences
• Distance-based filtering slider
• Statistics summary with averages
• Key findings analysis with turn references
• CSV export capability
```

---

## 🎯 Dashboards Avanzados

### 6. Tire Strategy 🔴⚪🟡

**Mission**: Visualization and analysis of tire strategies, pit stop windows and degradation.

**MCP Tools**:
- `get_tire_strategy`: Compound usage per lap
- `get_pit_stops`: Stop times
- `get_lap_times`: Degradation per stint

**Features**:
- Horizontal timeline per driver (colors by compound)
- Tire life and predicted degradation
- Undercut/overcut windows
- Comparison 1-stop vs 2-stop vs 3-stop
- Competitor pit stop prediction
- Compound availability tracker

**Availability**: ✅ Live | ✅ Simulation

**Priority**: 🔴 MVP - CRITICAL

#### Wireframe ASCII

```
┌────────────────────────────────────────────────────────────────────────────┐
│  TIRE STRATEGY & PIT STOP ANALYSIS              Lap 18/57  🏁 Bahrain GP  │
├────────────────────────────────────────────────────────────────────────────┤
│  TIRE USAGE TIMELINE (by Driver)                                           │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                    Lap: 1    5    10   15   20   25   30   35   40  │ │
│  │ P1 VER ┤🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴│⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪│...    │ │
│  │         └──── S (18L) ────────┘└── M (24L) ────┘ ← Current           │ │
│  │         ↑ Pit: 3.2s                                                   │ │
│  │                                                                       │ │
│  │ P2 HAM ┤🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴│⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪│...   │ │
│  │         └───── S (19L) ─────────┘└─── M (22L) ──┘ ← Current          │ │
│  │          ↑ Pit: 3.5s                                                  │ │
│  │                                                                       │ │
│  │ P3 LEC ┤⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪│🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴│...   │ │
│  │         └──── M (18L) ────────┘└─── S (24L) ───┘ ← Current           │ │
│  │          ↑ Pit: 3.8s                                                  │ │
│  │                                                                       │ │
│  │ P4 RUS ┤⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪│🟡🟡🟡🟡🟡🟡🟡🟡🟡🟡🟡🟡🟡│...   │ │
│  │         └──── M (18L) ────────┘└─── H (30L est)──┘ ← Current         │ │
│  │          ↑ Pit: 4.1s                                                  │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  Legend: 🔴 Soft  ⚪ Medium  🟡 Hard  ⚫ Wet  🔵 Inter                      │
├─────────────────────────────────┬──────────────────────────────────────────┤
│  🔴 VER - CURRENT STRATEGY      │  📊 DEGRADATION ANALYSIS                │
│  ┌───────────────────────────┐  │  ┌────────────────────────────────────┐ │
│  │ Compound: Medium          │  │  │ 1:34.0┤                            │ │
│  │ Stint: 2 (of 2-3)         │  │  │ 1:33.5┤  ●                         │ │
│  │ Age: 22 laps              │  │  │ 1:33.0┤    ● ●                     │ │
│  │ Predicted Life: 28L       │  │  │ 1:32.5┤      ● ●  ← Predicted      │ │
│  │ Remaining: 6L             │  │  │ 1:32.0┤        ● ●●●●●●●●●●       │ │
│  │                           │  │  │ 1:31.5┤  ←─ Current pace           │ │
│  │ ⚠️ Status: OPTIMAL        │  │  │       └─┬──┬──┬──┬──┬──┬──┬──┬───│ │
│  │                           │  │  │        18 20 22 24 26 28 30 32    │ │
│  │ 🎯 Next Pit Window:       │  │  │           Lap Number               │ │
│  │    Laps 23-26 (optimal)   │  │  └────────────────────────────────────┘ │
│  │    Laps 27-30 (backup)    │  │                                         │
│  └───────────────────────────┘  │  🔄 UNDERCUT/OVERCUT ANALYSIS           │
│                                  │  ┌────────────────────────────────────┐ │
│  💡 STRATEGY RECOMMENDATIONS    │  │ If VER pits L23:                   │ │
│  ┌───────────────────────────┐  │  │ • Undercut HAM: +1.8s (viable)     │ │
│  │ Option A: 2-stop           │  │  │ • Out position: P2 (behind LEC)    │ │
│  │   S(18) → M(24) → H(15)    │  │  │ • Clean air: 3 laps guaranteed     │ │
│  │   Total time: 1:34:22.4    │  │  │                                    │ │
│  │   ⭐ RECOMMENDED            │  │  │ If VER pits L25:                   │ │
│  │                            │  │  │ • Overcut HAM: +0.4s (marginal)    │ │
│  │ Option B: 1-stop (risky)   │  │  │ • Out position: P3 (behind HAM)    │ │
│  │   S(18) → M(39)            │  │  │ • Tire delta: -4 laps (older)      │ │
│  │   Total time: 1:34:28.1    │  │  └────────────────────────────────────┘ │
│  │   ⚠️ High deg risk          │  │                                         │
│  │                            │  │  🔢 COMPOUND AVAILABILITY               │
│  │ Option C: 3-stop (aggr.)   │  │  VER: 🔴 0  ⚪ 1  🟡 2  (2 sets left)   │
│  │   S(12) → M(15) → M(15)    │  │  HAM: 🔴 0  ⚪ 2  🟡 1  (3 sets left)   │
│  │   → S(15)                  │  │  LEC: 🔴 1  ⚪ 0  🟡 2  (3 sets left)   │
│  │   Total time: 1:34:35.7    │  │                                         │
│  │   ❌ Too slow               │  │                                         │
│  └───────────────────────────┘  │                                         │
└─────────────────────────────────┴──────────────────────────────────────────┘

Features Visible:
• Tire usage timeline for multiple drivers
• Pit stop times and positions marked
• Live degradation curve with prediction
• Undercut/overcut analysis with time deltas
• Multiple strategy options comparison
• Compound availability tracker per driver
• Optimal pit window recommendations
```

---

### 7. Flags and Track Status 🚩

**Mission**: Monitoring of track status, flags, incidents and Race Control messages.

**MCP Tools**:
- `get_track_status`: Flags (yellow, VSC, SC, red)
- `get_race_control_messages`: Official messages

**Features**:
- Event timeline (flags, incidents)
- Circuit map with affected sectors
- Real-time Race Control messages
- Ongoing investigations (pending penalties)
- Safety Car prediction (agent-based)
- Safety Car lap counter

**Availability**: ✅ Live | ✅ Simulation

**Priority**: 🟡 Phase 3B

#### Wireframe ASCII

```
┌────────────────────────────────────────────────────────────────────────────┐
│  TRACK STATUS & RACE CONTROL                  Lap 18/57  🟢 GREEN FLAG    │
├────────────────────────────────────────────────────────────────────────────┤
│  LIVE STATUS                                                                │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │  Current: 🟢 GREEN FLAG - Racing                                     │ │
│  │  Track Condition: DRY                                                │ │
│  │  Safety Car: Standby (not deployed)                                  │ │
│  │  VSC: Inactive                                                       │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────┬──────────────────────────────────────────┤
│  CIRCUIT SECTOR STATUS           │  EVENT TIMELINE                         │
│                                  │  ┌────────────────────────────────────┐ │
│         ╱─T5                     │  │ Lap│Time │Event                    │ │
│     T3╱   ╲                      │  ├────┼─────┼─────────────────────────┤ │
│      │     ╲T7 🟡               │  │ 18 │14:35│🟡 Yellow S2 - Debris    │ │
│  T1 ─┘      │                    │  │ 17 │14:33│📋 DEV Under Investig.  │ │
│  🏁          │                    │  │ 15 │14:28│⚠️ ALB Track Limits (3) │ │
│  START      T9                    │  │ 12 │14:22│🟢 Green - SC Ended     │ │
│              ╲                    │  │ 10 │14:18│🚗 Safety Car In        │ │
│          T11╱  ╲                  │  │  9 │14:16│🟡 VSC - Accident T4    │ │
│        ╱        T10               │  │  9 │14:16│❌ RIC Retired (Crash)  │ │
│   T12╱                            │  │  7 │14:12│🟡 Yellow S1 - Incident │ │
│   │                               │  │  5 │14:08│📋 MAG + HUL Investig.  │ │
│   │  T13                          │  │  1 │14:00│🏁 Race Start           │ │
│   └────┐                          │  └────┴─────┴─────────────────────────┘ │
│   T15  │T14                       │                                         │
│        └──────────                │  🚨 ACTIVE INCIDENTS                    │
│                                   │  ┌────────────────────────────────────┐ │
│  Sectors:                         │  │ T7 - Debris (Turn 7)               │ │
│  S1 (T1-T4):   🟢 Clear           │  │ • Yellow Flag S2                   │ │
│  S2 (T5-T10):  🟡 Yellow (T7)     │  │ • Marshals clearing                │ │
│  S3 (T11-T15): 🟢 Clear           │  │ • ETA clear: 2 laps                │ │
│                                   │  │                                    │ │
│                                   │  │ ⚠️ SC Probability: 35%             │ │
│                                   │  │ (if not cleared by L20)            │ │
│                                   │  └────────────────────────────────────┘ │
└─────────────────────────────────┴──────────────────────────────────────────┘
│  📋 RACE CONTROL MESSAGES                                                   │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │ 14:35:12 │ YELLOW FLAG SECTOR 2 - DEBRIS ON TRACK AT TURN 7        │ │
│  │ 14:33:45 │ CAR 21 (DEV) - UNDER INVESTIGATION - LEAVING TRACK      │ │
│  │          │ AND GAINING ADVANTAGE (LAP 17, TURN 4)                   │ │
│  │ 14:32:18 │ CAR 23 (ALB) - WARNING - TRACK LIMITS (3RD OFFENSE)     │ │
│  │ 14:22:34 │ SAFETY CAR IN THIS LAP                                   │ │
│  │ 14:21:56 │ GREEN FLAG - RACING RESUMED                              │ │
│  │ 14:18:22 │ SAFETY CAR DEPLOYED - INCIDENT TURN 4                   │ │
│  │ 14:16:45 │ VIRTUAL SAFETY CAR - ACCIDENT AT TURN 4                 │ │
│  │ 14:16:40 │ RED FLAG - SESSION STOPPED                               │ │
│  │ 14:16:38 │ CAR 3 (RIC) - RETIRED - ACCIDENT                        │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
├────────────────────────────────────────────────────────────────────────────┤
│  ⚖️ INVESTIGATIONS & PENALTIES                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │ PENDING:                                                             │ │
│  │ • CAR 21 (DEV) - Leaving track & gaining advantage (L17)            │ │
│  │   Status: Under Investigation                                        │ │
│  │   Possible Penalty: 5s time penalty                                  │ │
│  │                                                                      │ │
│  │ • CAR 5 (VET) & CAR 14 (ALO) - Incident L12 T3                     │ │
│  │   Status: No further action                                          │ │
│  │                                                                      │ │
│  │ APPLIED:                                                             │ │
│  │ ✓ CAR 20 (MAG) - 5s penalty (causing collision L5)                 │ │
│  │ ✓ CAR 27 (HUL) - 10s penalty (unsafe release L3)                   │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────────┘

Features Visible:
• Live track status with flag colors
• Circuit map with sector-by-sector status
• Event timeline scrollable with all incidents
• Race Control messages in real-time
• Active incidents panel with SC probability
• Investigations & penalties tracker
• Yellow flag sectors highlighted on map
```

---

### 8. Lap Analysis (Lap Analysis) ⏱️

**Mission**: Heatmap and temporal analysis of lap times, sectors and track evolution.

**MCP Tools**:
- `get_lap_times`: Complete times and by sector

**Features**:
- Time heatmap (lap × driver)
- Track evolution graph (lap-to-lap improvement)
- Sectors gained/lost vs competitor
- Purple sector highlighting (personal bests)
- Anomaly detection:
  - Traffic (lap +2s slower)
  - Driver error
  - Yellow flag
- Consistency analysis (standard deviation)

**Availability**: ✅ Live | ✅ Simulation

**Priority**: 🟡 Phase 3B

#### Wireframe ASCII

```
┌────────────────────────────────────────────────────────────────────────────┐
│  LAP TIME ANALYSIS                                        Laps 1-18 of 57  │
├────────────────────────────────────────────────────────────────────────────┤
│  LAP TIME HEATMAP (by Driver & Lap)                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │ Driver│ 1  │ 2  │ 3  │ 4  │ 5  │ 6  │ 7  │ 8  │ 9  │ 10 │...│ 18 │   │ │
│  ├───────┼────┼────┼────┼────┼────┼────┼────┼────┼────┼────┼───┼────┤   │ │
│  │ VER   │1:36│1:33│1:32│1:32│1:32│1:31│1:31│1:32│1:31│1:31│...│1:33│   │ │
│  │       │░░░ │▒▒▒ │▓▓▓ │▓▓▓ │▓▓▓ │███ │███ │▒▒▒ │███ │███ │   │▒▒▒ │   │ │
│  │ HAM   │1:37│1:33│1:33│1:32│1:32│1:32│1:32│1:31│1:32│1:32│...│1:33│   │ │
│  │       │░░░ │▒▒▒ │▒▒▒ │▓▓▓ │▓▓▓ │▓▓▓ │▓▓▓ │███ │▓▓▓ │▓▓▓ │   │▒▒▒ │   │ │
│  │ LEC   │1:37│1:34│1:33│1:33│1:32│1:32│1:32│1:32│1:31│1:32│...│1:32│   │ │
│  │       │░░░ │▒▒▒ │▒▒▒ │▒▒▒ │▓▓▓ │▓▓▓ │▓▓▓ │▓▓▓ │███ │▓▓▓ │   │▓▓▓ │   │ │
│  │ RUS   │1:38│1:34│1:33│1:33│1:33│1:32│1:32│1:33│1:32│1:32│...│1:33│   │ │
│  │       │░░░ │▒▒▒ │▒▒▒ │▒▒▒ │▒▒▒ │▓▓▓ │▓▓▓ │▒▒▒ │▓▓▓ │▓▓▓ │   │▒▒▒ │   │ │
│  │ PER   │1:38│1:35│1:34│1:33│1:33│1:33│1:33│1:34│1:45│1:33│...│1:34│   │ │
│  │       │░░░ │░░░ │▒▒▒ │▒▒▒ │▒▒▒ │▒▒▒ │▒▒▒ │▒▒▒ │⚠️  │▒▒▒ │   │▒▒▒ │   │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│  Legend: ███ Fast (top 3) ▓▓▓ Good ▒▒▒ Average ░░░ Slow ⚠️ Anomaly        │
├─────────────────────────────────┬──────────────────────────────────────────┤
│  TRACK EVOLUTION                 │  SECTOR COMPARISON (VER vs HAM)         │
│  ┌───────────────────────────┐  │  ┌────────────────────────────────────┐ │
│  │1:33.5┤                     │  │  │ Sector│ VER  │ HAM  │  Δ   │Winner│ │
│  │1:33.0┤ ●●                  │  │  ├───────┼──────┼──────┼──────┼──────┤ │
│  │1:32.5┤     ●●              │  │  │  S1   │18.234│18.299│-0.065│ VER  │ │
│  │1:32.0┤       ●●●           │  │  │  S2   │28.445│28.402│+0.043│ HAM  │ │
│  │1:31.5┤          ●●●●●●●    │  │  │  S3   │22.891│22.934│-0.043│ VER  │ │
│  │1:31.0┤                 ●●  │  │  │ TOTAL │1:09.57│1:09.64│-0.065│ VER │ │
│  │      └┬──┬──┬──┬──┬──┬──┬─│  │  └────────────────────────────────────┘ │
│  │       1  3  5  7  9  12 15│  │                                         │
│  │         Lap Number         │  │  🟣 PURPLE SECTORS (Personal Best)      │
│  └───────────────────────────┘  │  • L6: VER - S1 (18.234)                │
│                                  │  • L8: HAM - S2 (28.402)                │
│  Track improving -0.8s per 5 laps│  • L9: LEC - S3 (22.801)                │
│                                  │                                         │
├─────────────────────────────────┴──────────────────────────────────────────┤
│  🔍 ANOMALY DETECTION                                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │ Lap│Driver│  Time  │Δ Avg│ Reason              │Affected Sectors    │ │
│  ├────┼──────┼────────┼─────┼─────────────────────┼────────────────────┤ │
│  │  9 │ PER  │1:45.234│+12.1│🚗 Traffic (behind BOT)│ S2 (+8.2s), S3 │ │
│  │ 12 │ RUS  │1:39.567│ +7.3│🟡 Yellow Flag (S2)   │ S2 (+7.1s)     │ │
│  │ 15 │ LEC  │1:38.123│ +6.0│❌ Error (Turn 4 lock)│ S1 (+5.8s)     │ │
│  │ 18 │ All  │  +1.5s │ +1.5│⛽ Fuel saving mode   │ All sectors    │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
├────────────────────────────────────────────────────────────────────────────┤
│  📊 CONSISTENCY ANALYSIS                                                    │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │ Driver│Avg Time│Best Lap│Std Dev│Consistency│ Rating                │ │
│  ├───────┼────────┼────────┼───────┼───────────┼───────────────────────┤ │
│  │ VER   │1:31.892│1:31.234│ 0.423s│  98.7%    │ ⭐⭐⭐⭐⭐ Excellent    │ │
│  │ HAM   │1:32.104│1:31.567│ 0.512s│  97.8%    │ ⭐⭐⭐⭐⭐ Excellent    │ │
│  │ LEC   │1:32.345│1:31.889│ 0.678s│  96.2%    │ ⭐⭐⭐⭐ Very Good      │ │
│  │ RUS   │1:32.567│1:32.123│ 0.891s│  94.5%    │ ⭐⭐⭐⭐ Very Good      │ │
│  │ PER   │1:33.234│1:32.890│ 1.234s│  91.3%    │ ⭐⭐⭐ Good (traffic)  │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  🎯 KEY INSIGHTS                                                            │
│  • VER most consistent (σ=0.423s) with fastest average pace                │
│  • Track evolution: -0.8s per 5 laps (improving grip)                      │
│  • HAM faster in S2 (slow corners) consistently                            │
│  • L18: All drivers fuel saving (+1.5s average) for tire management        │
└────────────────────────────────────────────────────────────────────────────┘

Features Visible:
• Lap time heatmap with color coding (fast to slow)
• Track evolution graph showing improvement
• Sector comparison between drivers
• Purple sector highlights (personal bests)
• Anomaly detection table with reasons
• Consistency analysis with ratings
• Key insights summary
```

---

### 9. Gestión de Carrera (Race Management) 📊

**Misión**: Overview estratégico de la carrera con pace analysis, cambios de posición y escenarios.

**Herramientas MCP**:
- `get_race_results`: Posiciones actuales
- `get_lap_times`: Race pace
- `get_pit_stops`: Estrategias ejecutadas

**Funcionalidades**:
- **Race Pace Chart**: Ritmo promedio por stint (box plot)
- **Position Changes Graph**: Evolución de posiciones (time series)
- **Overtake Probability**: Basado en gaps y DRS
- **Points Scoring Scenarios**: "¿Qué pasa si...?" simulations
- **Alternative Strategies**: Comparación en tiempo real
- Gap analysis to key competitors

**Disponibilidad**: ✅ Live | ✅ Simulación

**Prioridad**: 🟢 Phase 4 - NICE TO HAVE

#### Wireframe ASCII

```
┌────────────────────────────────────────────────────────────────────────────┐
│  RACE MANAGEMENT OVERVIEW                        Lap 18/57  🏁 Bahrain GP │
├─────────────────────────────────┬──────────────────────────────────────────┤
│  POSITION EVOLUTION              │  RACE PACE BY STINT                     │
│  ┌───────────────────────────┐  │  ┌────────────────────────────────────┐ │
│  │P1├─VER═══════════════════  │  │  │1:34.0┤                            │ │
│  │P2├─HAM═══════╗             │  │  │1:33.5┤    ┬                       │ │
│  │P3├─LEC══╗    ║             │  │  │1:33.0┤ ┬  │  ┬                    │ │
│  │P4├─────╫────╫─RUS══════    │  │  │1:32.5┤┌┼┐┌┼┐┌┼┐  VER Stint 1&2    │ │
│  │P5├─PER═╝    ╚═══════════   │  │  │1:32.0┤└┼┘└┼┘└┼┘                   │ │
│  │P6├─SAI════════════════════  │  │  │1:31.5┤ │  │  │                    │ │
│  │P7├─NOR════════════════════  │  │  │      └─┴──┴──┴─────────────────  │ │
│  │P8├─ALO════════════════════  │  │  │       S1  S2  S3                  │ │
│  │  └┬──┬──┬──┬──┬──┬──┬──┬──│  │  │                                    │ │
│  │   1  3  6  9  12 15 18 21 │  │  │ Avg Pace: 1:32.234 (VER fastest)   │ │
│  │        Lap Number          │  │  └────────────────────────────────────┘ │
│  └───────────────────────────┘  │                                         │
│                                  │  🎯 OVERTAKE PROBABILITY                │
│  Key Position Changes:           │  ┌────────────────────────────────────┐ │
│  • L6: LEC overtakes PER (T4)    │  │ Battle    │ Gap   │ DRS │Prob.    │ │
│  • L12: HAM overtakes LEC (pit)  │  ├───────────┼───────┼─────┼─────────┤ │
│                                  │  │ VER→HAM   │+3.245s│ No  │  12%    │ │
│                                  │  │ HAM→LEC   │+0.892s│ Yes │  68%    │ │
│                                  │  │ LEC→RUS   │+1.654s│ Yes │  45%    │ │
│                                  │  │ PER→SAI   │+1.223s│ Yes │  52%    │ │
│                                  │  └────────────────────────────────────┘ │
├─────────────────────────────────┴──────────────────────────────────────────┤
│  🏆 POINTS SCORING SCENARIOS ("What if...?")                                │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │ Current Projection (if positions hold):                              │ │
│  │ P1 VER (25pts) │ P2 HAM (18pts) │ P3 LEC (15pts) │ P4 RUS (12pts)   │ │
│  │ ────────────────────────────────────────────────────────────────────│ │
│  │ Scenario A: VER pits L23, loses P1 to HAM                           │ │
│  │ P1 HAM (25pts) │ P2 VER (18pts) │ P3 LEC (15pts) │ Impact: -7pts   │ │
│  │ Probability: 35% │ Risk: Medium                                      │ │
│  │ ────────────────────────────────────────────────────────────────────│ │
│  │ Scenario B: LEC overtakes HAM + fastest lap                         │ │
│  │ P1 VER (25pts) │ P2 LEC (19pts) │ P3 HAM (15pts) │ Impact: +4pts   │ │
│  │ Probability: 22% │ Risk: Low                                         │ │
│  │ ────────────────────────────────────────────────────────────────────│ │
│  │ Scenario C: Safety Car L25-30, mixed strategies                     │ │
│  │ Unpredictable │ Multiple position changes possible                  │ │
│  │ Probability: 18% │ Risk: High (prepare for SC stop)                 │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
├────────────────────────────────────────────────────────────────────────────┤
│  🔄 ALTERNATIVE STRATEGY COMPARISON                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │         │ Current  │ Alt A (1-stop) │ Alt B (3-stop) │ Alt C (Hold) │ │
│  │         │ Strategy │    Extension   │   Aggressive   │   & React    │ │
│  ├─────────┼──────────┼────────────────┼────────────────┼──────────────┤ │
│  │ Stops   │    2     │       1        │       3        │      2       │ │
│  │ Next Pit│  L23-26  │   Never (39L)  │    L20-22      │   L26-30     │ │
│  │ End Tire│  Hard    │    Medium      │     Soft       │    Hard      │ │
│  │ Est.Time│1:34:22.4 │  1:34:28.1     │  1:34:35.7     │  1:34:19.8   │ │
│  │ End Pos │   P1     │   P2 (risky)   │   P1 (unlikely)│   P1         │ │
│  │ Risk    │  Medium  │     High       │     High       │    Low       │ │
│  │ Recommend│   ⭐⭐   │      ❌        │      ❌        │    ⭐⭐⭐    │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  💡 STRATEGIC RECOMMENDATION                                                │
│  Hold current position. Monitor HAM pace on L20-22. If gap drops <2.5s,   │
│  consider early stop L23 to secure track position. Alt C (reactive) gives  │
│  best risk/reward if SC deployed. Maintain 3.2s gap minimum for safety.    │
└────────────────────────────────────────────────────────────────────────────┘

Features Visible:
• Position evolution graph showing all overtakes
• Race pace box plots by stint
• Overtake probability with DRS factors
• Points scoring scenarios with probabilities
• Alternative strategy comparison table
• Strategic recommendation with real-time updates
• "What if?" simulations
```

---

### 10. Qualifying Progress 🏁

**Mission**: Qualifying tracking with cutoff time prediction and elimination zone.

**MCP Tools**:
- `get_qualifying_results`: Q1/Q2/Q3 times
- `get_lap_times`: Progression analysis
- Performance Agent (Qualifying mode): Cutoff prediction

**Features**:
- **Cutoff Time Tracker**: Real-time P10/P15 prediction
- **Elimination Zone**: Color coding by risk
  - 🔴 Red: High elimination probability
  - 🟡 Yellow: Borderline
  - 🟢 Green: Safe
- **Track Evolution Graph**: Lap-to-lap time improvement
- **Tow Opportunities**: Available slipstream heatmap
- **Queue Management**: Optimal exit timing
- Time remaining counter per session

**Availability**: ✅ Live | ✅ Simulation

**Priority**: 🟡 Phase 3B

#### Wireframe ASCII

```
┌────────────────────────────────────────────────────────────────────────────┐
│  QUALIFYING PROGRESS - Q2                          ⏱️ 4:23 remaining       │
├────────────────────────────────────────────────────────────────────────────┤
│  LIVE ELIMINATION ZONE TRACKER                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │ P │Driver│  Time   │ Gap to P10│ Status      │ Trend │ Tires Left  │ │
│  ├───┼──────┼─────────┼───────────┼─────────────┼───────┼─────────────┤ │
│  │🟢1│ VER  │1:12.234 │  -1.567s  │ SAFE        │  ══   │ 🔴🔴 (2)    │ │
│  │🟢2│ HAM  │1:12.345 │  -1.456s  │ SAFE        │  ↗    │ 🔴🔴⚪ (3)  │ │
│  │🟢3│ LEC  │1:12.456 │  -1.345s  │ SAFE        │  ══   │ 🔴🔴 (2)    │ │
│  │🟢4│ RUS  │1:12.567 │  -1.234s  │ SAFE        │  ↗    │ 🔴⚪⚪ (3)  │ │
│  │🟢5│ PER  │1:12.678 │  -1.123s  │ SAFE        │  ══   │ 🔴🔴 (2)    │ │
│  │🟢6│ SAI  │1:12.789 │  -1.012s  │ SAFE        │  ↗    │ 🔴⚪ (2)    │ │
│  │🟢7│ NOR  │1:12.890 │  -0.911s  │ SAFE        │  ══   │ 🔴🔴⚪ (3)  │ │
│  │🟢8│ ALO  │1:12.998 │  -0.803s  │ SAFE        │  ↗    │ 🔴⚪ (2)    │ │
│  │🟢9│ OCO  │1:13.234 │  -0.567s  │ SAFE        │  ↗    │ 🔴⚪ (2)    │ │
│  │🟢10│GAS  │1:13.567 │  -0.234s  │ BORDERLINE  │  ══   │ 🔴 (1)      │ │
│  │ ──┼──────┼─────────┼───────────┼─────────────┼───────┼─────────────┤ │
│  │   │      │ CUTOFF: 1:13.801 (predicted) ± 0.089s                   │ │
│  │ ──┼──────┼─────────┼───────────┼─────────────┼───────┼─────────────┤ │
│  │🟡11│TSU  │1:13.889 │  +0.088s  │ DANGER      │  ↗    │ 🔴⚪ (2)    │ │
│  │🔴12│STR  │1:14.012 │  +0.211s  │ ELIMINATION │  ↘    │ 🔴 (1)      │ │
│  │🔴13│MAG  │1:14.234 │  +0.433s  │ ELIMINATION │  ══   │ ⚪ (1)      │ │
│  │🔴14│BOT  │1:14.456 │  +0.655s  │ ELIMINATION │  ↘    │ 🔴 (1)      │ │
│  │🔴15│ZHO  │1:14.678 │  +0.877s  │ ELIMINATION │  ══   │ ⚪ (1)      │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│  Legend: 🟢 Safe  🟡 Borderline  🔴 Danger | ↗ Improving ↘ Declining ══ Stable│
├─────────────────────────────────┬──────────────────────────────────────────┤
│  CUTOFF TIME PREDICTION          │  TRACK EVOLUTION                        │
│  ┌───────────────────────────┐  │  ┌────────────────────────────────────┐ │
│  │ P10 Cutoff (Predicted)    │  │  │1:15.0┤                            │ │
│  │ 1:13.801s ± 0.089s        │  │  │1:14.5┤ ●●                         │ │
│  │                           │  │  │1:14.0┤   ●●                       │ │
│  │ Confidence: 82%           │  │  │1:13.5┤     ●●●                    │ │
│  │ Based on:                 │  │  │1:13.0┤        ●●●                 │ │
│  │ • Track evolution: -0.15s │  │  │1:12.5┤           ●●●●●●●         │ │
│  │ • 5 drivers improving     │  │  │1:12.0┤                            │ │
│  │ • Fresh tires available   │  │  │      └┬───┬───┬───┬───┬───┬─────│ │
│  │ • 4:23 remaining          │  │  │       1   2   3   4   5   Now    │ │
│  │                           │  │  │           Attempts                 │ │
│  │ Range:                    │  │  └────────────────────────────────────┘ │
│  │ Best case: 1:13.712s      │  │                                         │
│  │ Worst case: 1:13.890s     │  │  Improvement rate: -0.12s per attempt  │
│  └───────────────────────────┘  │                                         │
│                                  │  🚗 TOW OPPORTUNITIES                   │
│  ⚠️ CRITICAL DECISIONS          │  ┌────────────────────────────────────┐ │
│  ┌───────────────────────────┐  │  │ If you go out now:                 │ │
│  │ P11 TSU: Must improve     │  │  │ • Available tow from: GAS, NOR    │ │
│  │   Target: -0.200s         │  │  │ • Clean gap in: 35-45 seconds     │ │
│  │   Probability: 68%        │  │  │ • Queue in pits: 3 cars           │ │
│  │   Action: GO OUT NOW      │  │  │ • Estimated loss: 8-12s (queue)   │ │
│  │                           │  │  │                                    │ │
│  │ P12 STR: Critical         │  │  │ RECOMMENDATION:                    │ │
│  │   Target: -0.320s         │  │  │ • Wait 25s for clean track        │ │
│  │   Probability: 42%        │  │  │ • Exit behind NOR for tow         │ │
│  │   Action: URGENT OUT      │  │  │ • 2 flying laps possible          │ │
│  └───────────────────────────┘  │  └────────────────────────────────────┘ │
├─────────────────────────────────┴──────────────────────────────────────────┤
│  📊 SESSION STATISTICS                                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │ Cars on Track: 4          Attempts Completed: 67 / 75 total          │ │
│  │ Track Status: GREEN       Average Improvement: -0.234s per attempt   │ │
│  │ Traffic Level: MODERATE   Invalidated Laps: 3 (track limits)         │ │
│  │ Fastest Sector Times: S1: VER (18.234) S2: HAM (28.402) S3: LEC     │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  🎯 STRATEGIC INSIGHTS                                                      │
│  • Track still improving - expect P10 cutoff to drop another 0.10-0.15s   │
│  • TSU P11: 68% chance to advance if goes out now (needs -0.2s)           │
│  • STR P12: Critical - 42% chance, requires perfect lap (-0.32s)           │
│  • Fresh soft tires advantage: ~0.15s vs used sets                         │
│  • Traffic clearing in 25s - optimal exit window approaching               │
└────────────────────────────────────────────────────────────────────────────┘

Features Visible:
• Live elimination zone with color-coded risk levels
• Predicted cutoff time with confidence intervals
• Track evolution graph showing improvement
• Critical decisions panel for at-risk drivers
• Tow opportunities and queue management
• Real-time strategic insights
• Time remaining countdown
• Tire availability per driver
```

---

### 11. Practice Analysis (Practice Analysis) 🔧

**Mission**: Practice session analysis for setup work and qualifying prediction.

**MCP Tools**:
- `get_practice_results`: FP1/FP2/FP3 results
- `get_lap_times`: Long run pace analysis
- `get_tire_strategy`: Tire testing programs

**Features**:
- **Long Run Pace**: Pace analysis with high fuel load
- **Setup Evolution**: Changes between sessions
- **Correlation Analysis**: FP3 → Qualifying prediction
- **Program Tracking**: 
  - Aero tests
  - Tire tests
  - Race simulation
- **Competitor Watch**: Rival programs
- Fuel-corrected lap times

**Availability**: ✅ Live | ✅ Simulation

**Priority**: 🟢 Phase 4 - NICE TO HAVE

#### Wireframe ASCII

```
┌────────────────────────────────────────────────────────────────────────────┐
│  PRACTICE SESSION ANALYSIS                    FP3  ⏱️ 52:34 elapsed        │
├─────────────────────────────────┬──────────────────────────────────────────┤
│  SESSION SUMMARY                 │  QUALIFYING PREDICTION                  │
│  ┌───────────────────────────┐  │  ┌────────────────────────────────────┐ │
│  │ Session: FP3              │  │  │ Based on FP3 correlation:          │ │
│  │ Duration: 60 min          │  │  │                                    │ │
│  │ Laps Completed: 234       │  │  │ Predicted Q3 Top 10:               │ │
│  │ Red Flags: 0              │  │  │ 1. VER  1:11.8  (FP3: 1:12.2)     │ │
│  │ Track Temp: 42°C          │  │  │ 2. HAM  1:11.9  (FP3: 1:12.3)     │ │
│  │ Air Temp: 28°C            │  │  │ 3. LEC  1:12.0  (FP3: 1:12.4)     │ │
│  │                           │  │  │ 4. RUS  1:12.1  (FP3: 1:12.5)     │ │
│  │ Focus: Quali sims         │  │  │ 5. PER  1:12.2  (FP3: 1:12.6)     │ │
│  └───────────────────────────┘  │  │                                    │ │
│                                  │  │ Correlation: 94.2% (strong)        │ │
│  📊 DRIVER PROGRAMS              │  │ Typical improvement: -0.4s         │ │
│  ┌───────────────────────────┐  │  └────────────────────────────────────┘ │
│  │Driver│Program    │Laps│%  │  │                                         │
│  ├──────┼───────────┼────┼───┤  │  🏁 RACE SIMULATION PACE               │
│  │ VER  │Quali sim  │ 8  │35%│  │  ┌────────────────────────────────────┐ │
│  │      │Race sim   │12  │52%│  │  │ Driver│ Stint │Avg Pace│Fuel Load │ │
│  │      │Aero test  │ 3  │13%│  │  ├───────┼───────┼────────┼──────────┤ │
│  │ HAM  │Quali sim  │ 6  │30%│  │  │ VER   │ 1-12  │1:33.234│ 50kg     │ │
│  │      │Race sim   │10  │50%│  │  │ HAM   │ 1-10  │1:33.456│ 50kg     │ │
│  │      │Setup test │ 4  │20%│  │  │ LEC   │ 1-11  │1:33.567│ 50kg     │ │
│  │ LEC  │Race sim   │14  │70%│  │  │ RUS   │ 1-9   │1:33.789│ 50kg     │ │
│  │      │Tire test  │ 6  │30%│  │  │                                    │ │
│  └──────┴───────────┴────┴───┘  │  │ Fuel corrected (to race start)     │ │
│                                  │  │ VER fastest long-run pace          │ │
├─────────────────────────────────┴──────────────────────────────────────────┤
│  📈 LONG RUN PACE COMPARISON (Fuel Corrected)                              │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │1:34.5┤                                                               │ │
│  │1:34.0┤        RUS ────────────                                       │ │
│  │1:33.5┤    LEC ═══════════════                                        │ │
│  │1:33.0┤  HAM ═══════════════════                                      │ │
│  │1:32.5┤VER ═══════════════════════                                    │ │
│  │1:32.0┤                                                               │ │
│  │      └┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬───                        │ │
│  │       1  2  3  4  5  6  7  8  9  10 11 12   Lap                     │ │
│  │                                                                       │ │
│  │ VER: Most consistent, fastest avg (1:32.891 corrected)               │ │
│  │ HAM: Strong pace, slight degradation L8+ (+0.3s)                     │ │
│  │ LEC: Moderate pace, high fuel testing                                │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
├────────────────────────────────────────────────────────────────────────────┤
│  🔧 SETUP EVOLUTION (FP1 → FP2 → FP3)                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │ VER (Red Bull)                                                       │ │
│  │ ┌────────┬──────────┬──────────┬──────────┬─────────────────────┐  │ │
│  │ │ Setup  │   FP1    │   FP2    │   FP3    │ Change Direction    │  │ │
│  │ ├────────┼──────────┼──────────┼──────────┼─────────────────────┤  │ │
│  │ │Balance │ Neutral  │Oversteer │ Neutral  │ ← Back to FP1       │  │ │
│  │ │ Ride H.│  High    │  Medium  │  Medium  │ ↓ Lowered           │  │ │
│  │ │ Wing   │    7     │    6     │    6     │ ↓ Less downforce    │  │ │
│  │ │Best Lap│ 1:12.567 │ 1:12.345 │ 1:12.234 │ ✓ Improved -0.333s  │  │ │
│  │ └────────┴──────────┴──────────┴──────────┴─────────────────────┘  │ │
│  │                                                                       │ │
│  │ Key Changes:                                                          │ │
│  │ • FP2: Reduced wing, caused oversteer - rejected                     │ │
│  │ • FP3: Reverted balance, kept low wing - optimal compromise          │ │
│  │ • Ride height reduction successful (better aero efficiency)           │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
├────────────────────────────────────────────────────────────────────────────┤
│  🔍 COMPETITOR WATCH                                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │ Team/Driver     │ Focus Area        │ Observations                   │ │
│  ├─────────────────┼───────────────────┼────────────────────────────────┤ │
│  │ Mercedes (HAM)  │ High fuel runs    │ Strong race pace, slight deg   │ │
│  │ Ferrari (LEC)   │ Tire testing      │ Testing all compounds, setup   │ │
│  │ Mercedes (RUS)  │ Aero evaluation   │ New floor tested, mixed results│ │
│  │ McLaren (NOR)   │ Setup window      │ Struggling with balance        │ │
│  │ Aston (ALO)     │ Qualifying focus  │ Short run pace competitive     │ │
│  └─────────────────┴───────────────────┴────────────────────────────────┘ │
│                                                                             │
│  💡 STRATEGIC INSIGHTS                                                      │
│  • VER setup converged - expect strong qualifying performance              │
│  • HAM race pace competitive but tire degradation higher than VER          │
│  • LEC focusing on race - may sacrifice quali for Sunday setup             │
│  • Track evolution +0.6s since FP1 (rubber laid down)                      │
│  • Prediction: VER pole position (94% confidence based on FP3 correlation) │
└────────────────────────────────────────────────────────────────────────────┘

Features Visible:
• Session summary with track conditions
• Driver program breakdown (quali sim, race sim, tests)
• Qualifying prediction based on FP3 correlation
• Long run pace comparison with fuel correction
• Setup evolution tracking across sessions
• Competitor watch with focus areas
• Strategic insights for race weekend
```

---

### 12. Detailed Environmental Conditions 🌡️

**Mission**: Deep analysis of environmental conditions and their impact on performance.

**MCP Tools**:
- `get_weather`: Complete meteorological data

**Features**:
- **Track Temperature Evolution**: Next hour prediction
- **Asphalt vs Air Temperature**: Temporal chart and tire impact
- **Wind Rose**: Direction and intensity by sector
- **Humidity & Pressure**: Correlation with available grip
- **Rain Probability Forecast**: 30/60/90 minutes
- Historical comparison (same circuit previous years)

**Availability**: ✅ Live | ⚠️ Simulation (limited)

**Priority**: 🟢 Phase 4 - NICE TO HAVE

#### Wireframe ASCII

```
┌────────────────────────────────────────────────────────────────────────────┐
│  ENVIRONMENTAL CONDITIONS ANALYSIS                14:35:22  🌤️ Partly Cloudy│
├─────────────────────────────────┬──────────────────────────────────────────┤
│  TEMPERATURE EVOLUTION           │  WIND ANALYSIS BY SECTOR                │
│  ┌───────────────────────────┐  │  ┌────────────────────────────────────┐ │
│  │ 50°C┤                     │  │  │         N                          │ │
│  │ 45°C┤  ╱──╲   Track       │  │  │         ↑                          │ │
│  │ 40°C┤ ╱    ╲  Surface     │  │  │    NW ↖ │ ↗ NE                   │ │
│  │ 35°C┤╱      ╲             │  │  │       ╲ │ ╱                      │ │
│  │ 30°C┼────────╲────Air     │  │  │    W ← ═●═ → E    15 km/h SW     │ │
│  │ 25°C┤        ╲   Temp     │  │  │       ╱ │ ╲                      │ │
│  │ 20°C┤         ╲           │  │  │    SW ↙ │ ↘ SE                   │ │
│  │     └┬───┬───┬───┬───┬───│  │  │         ↓                          │ │
│  │     13:00 14:00 15:00 16:00│  │  │         S                          │ │
│  │         Time               │  │  └────────────────────────────────────┘ │
│  └───────────────────────────┘  │                                         │
│                                  │  🎯 SECTOR IMPACT ANALYSIS              │
│  Current:                        │  ┌────────────────────────────────────┐ │
│  🌡️ Track: 38.5°C               │  │ Sector│Direction│Speed│ Impact     │ │
│  🌡️ Air: 24.2°C                 │  ├───────┼─────────┼─────┼────────────┤ │
│  Δ: 14.3°C (optimal)            │  │  S1   │   SW    │ 12  │ Tailwind   │ │
│                                  │  │ (T1-4)│   ↙     │km/h │ +0.05s gain│ │
│  Prediction (+60min):            │  │  S2   │    W    │ 18  │ Crosswind  │ │
│  Track: 36.2°C (-2.3°C)         │  │ (T5-10)│   ←     │km/h │ -0.12s loss│ │
│  Air: 23.8°C (-0.4°C)           │  │  S3   │   NW    │  8  │ Minimal    │ │
│                                  │  │(T11-15)│   ↖     │km/h │ +0.02s     │ │
├─────────────────────────────────┴──────────────────────────────────────────┤
│  💧 HUMIDITY & ATMOSPHERIC PRESSURE                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │ Humidity (%)           │  Pressure (hPa)                              │ │
│  │  80%┤                  │ 1020├─────────────────                       │ │
│  │  75%┤                  │ 1015├──────────────────                      │ │
│  │  70%┤  ╱─╲             │ 1010├────────────────────  ← Current         │ │
│  │  65%┤ ╱   ╲            │ 1005├                                        │ │
│  │  60%┤╱     ╲──         │ 1000├                                        │ │
│  │     └┬──┬──┬──┬───     │     └┬──┬──┬──┬───                          │ │
│  │     13 14 15 16        │     13 14 15 16                              │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  Current: 68% humidity | 1013 hPa pressure                                 │
│  Impact: Moderate grip level (optimal: 40-60% humidity)                    │
│          Rising humidity → expect grip to decrease slightly                │
├────────────────────────────────────────────────────────────────────────────┤
│  🌧️ RAIN FORECAST & PROBABILITY                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │ Time Window    │ Probability │ Intensity  │ Confidence              │ │
│  ├────────────────┼─────────────┼────────────┼─────────────────────────┤ │
│  │ Next 30 min    │    30%      │ Light      │ ████████░░ 80%          │ │
│  │ 30-60 min      │    65%      │ Moderate   │ ███████░░░ 75%          │ │
│  │ 60-90 min      │    80%      │ Heavy      │ ██████░░░░ 65%          │ │
│  │ 90-120 min     │    55%      │ Moderate   │ █████░░░░░ 55%          │ │
│  └────────────────┴─────────────┴────────────┴─────────────────────────┘ │
│                                                                             │
│  ⚠️ ALERT: Rain likely in 40-70 minutes (65% probability)                 │
│           Prepare intermediate tires. Monitor Turn 7 (standing water risk) │
├────────────────────────────────────────────────────────────────────────────┤
│  📊 TIRE PERFORMANCE CORRELATION                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │ Compound    │ Optimal Track Temp │ Current Status  │ Performance   │ │
│  ├─────────────┼────────────────────┼─────────────────┼───────────────┤ │
│  │ 🔴 Soft     │    35-45°C         │ 38.5°C ✓        │ ⭐⭐⭐⭐⭐    │ │
│  │ ⚪ Medium   │    30-40°C         │ 38.5°C ⚠️       │ ⭐⭐⭐⭐      │ │
│  │ 🟡 Hard     │    25-35°C         │ 38.5°C ❌       │ ⭐⭐⭐        │ │
│  │ 🟢 Inter    │    15-25°C (wet)   │ Not applicable  │ N/A           │ │
│  │ 🔵 Wet      │    10-20°C (wet)   │ Not applicable  │ N/A           │ │
│  └─────────────┴────────────────────┴─────────────────┴───────────────┘ │
│                                                                             │
│  Recommendation: Soft tires optimal. Medium acceptable but slightly warm.  │
│                  Avoid Hard compound (too cool, low grip).                 │
├────────────────────────────────────────────────────────────────────────────┤
│  📈 HISTORICAL COMPARISON (Same Circuit, Last 3 Years)                      │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │ Year │ Session │ Track Temp │ Air Temp │ Conditions │ Fastest Lap  │ │
│  ├──────┼─────────┼────────────┼──────────┼────────────┼──────────────┤ │
│  │ 2024 │ Race    │   42.5°C   │  26.3°C  │ Dry/Hot    │  1:31.447    │ │
│  │ 2023 │ Race    │   38.2°C   │  24.8°C  │ Dry        │  1:31.895    │ │
│  │ 2022 │ Race    │   35.6°C   │  23.1°C  │ Dry/Cool   │  1:32.334    │ │
│  │ 2025 │ Today   │   38.5°C ← Current                                  │ │
│  └──────┴─────────┴────────────┴──────────┴────────────┴──────────────┘ │
│                                                                             │
│  Analysis: Current conditions similar to 2023. Expect lap times ~1:31.8    │
│           Track 0.3°C cooler than 2023 → slightly less grip available      │
├────────────────────────────────────────────────────────────────────────────┤
│  💡 STRATEGIC IMPACT SUMMARY                                                │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │ Factor          │ Status        │ Impact                              │ │
│  ├─────────────────┼───────────────┼─────────────────────────────────────┤ │
│  │ Track Temp      │ Optimal ✓     │ Good tire working range             │ │
│  │ Air Temp        │ Comfortable   │ Engine cooling adequate             │ │
│  │ Wind            │ Moderate      │ -0.05s net (S2 crosswind impact)    │ │
│  │ Humidity        │ Elevated ⚠️   │ Slight grip reduction expected      │ │
│  │ Pressure        │ Normal        │ No significant impact               │ │
│  │ Rain Risk       │ High (65%)    │ Monitor closely, prepare inters     │ │
│  │ Grip Level      │ Good          │ Track evolution favorable           │ │
│  └─────────────────┴───────────────┴─────────────────────────────────────┘ │
│                                                                             │
│  🎯 RECOMMENDATION:                                                         │
│  Current conditions favor dry racing with soft compound. Monitor rain      │
│  radar closely - 65% chance of rain in 40-70 min window. If rain arrives,  │
│  expect 2-3 lap transition period before full wet conditions. Track Temp   │
│  dropping may reduce grip slightly over next hour (-0.1s to -0.2s impact). │
└────────────────────────────────────────────────────────────────────────────┘

Features Visible:
• Temperature evolution graphs (track vs air)
• Wind rose with sector-by-sector impact analysis
• Humidity and atmospheric pressure trends
• Rain forecast with probability and confidence levels
• Tire performance correlation with current conditions
• Historical comparison (same circuit, previous years)
• Strategic impact summary with recommendations
• Real-time alerts for changing conditions
```

---

## 🎛️ Menú Superior

### Estructura del Menú

```
┌────────────────────────────────────────────────────────────────────┐
│ [LIVE / SIMULATION] | [⚙️ CONFIG] | [📊 DASHBOARDS] | [👤 USER]   │
└────────────────────────────────────────────────────────────────────┘
```

### Menu Sections

#### 1. **Operation Mode**
- **Live Mode**: 
  - Connect to OpenF1 real-time
  - Current active session selection
  - Latency indicator (<5s target)
- **Simulation Mode**:
  - Year selector (2018-2024)
  - Round selector (1-24)
  - Session selector (FP1/FP2/FP3/Q/R/Sprint)
  - Time scrubbing controls

#### 2. **⚙️ Configuration (CONFIG)**
- **API Keys**:
  - OpenF1 API Key (Live mode)
  - Claude API Key (Agents)
  - Gemini API Key (Agents)
  - LangSmith API Key (Monitoring)
- **Data Sources**:
  - FastF1 cache directory
  - Vector store selection (ChromaDB/Pinecone)
- **LLM Settings**:
  - Provider selection (Claude/Gemini/Hybrid)
  - Temperature settings
  - Max tokens

#### 3. **📊 Dashboards**
- **Layout Presets**:
  - Race Day: Chatbot + Circuit + Tire Strategy
  - Qualifying: Chatbot + Qualifying Progress + Circuit
  - Practice Analysis: Practice + Telemetry + Weather
  - Strategy Deep Dive: Tire Strategy + Race Management + Lap Analysis
- **Custom Layout**:
  - Drag & drop dashboard arrangement
  - Save custom layouts
  - Multi-monitor support

#### 4. **👤 User**
- Session history
- Saved queries
- Preferences
- About / Help

---

## 📋 Priorities Summary

### 🔴 MVP - Phase 3A/3B (Critical)
1. AI Assistant / Chatbot
2. Circuit & Positions
3. Telemetry Comparison
4. Tire Strategy

### 🟡 Phase 3B (Important)
5. Weather & Conditions
6. Raw Data Comparison
7. Flags and Track Status
8. Lap Analysis
9. Qualifying Progress

### 🟢 Phase 4 (Nice to Have)
10. Race Management
11. Practice Analysis
12. Detailed Environmental Conditions

---

## 📊 Compatibility Matrix

| Dashboard | Live | Simulation | MCP Tools | Agents |
|-----------|------|------------|-----------|--------|
| AI Assistant | ✅ | ✅ | All (13) | All (5) |
| Weather | ✅ | ⚠️ | get_weather, get_track_status | Weather |
| Circuit | ✅ | ✅ | get_race_results, get_lap_times | Race Position |
| Telemetry | ✅ | ✅ | get_telemetry, get_lap_times | Performance |
| Raw Data | ✅ | ✅ | get_telemetry | Performance |
| Tires | ✅ | ✅ | get_tire_strategy, get_pit_stops | Strategy |
| Flags | ✅ | ✅ | get_track_status, get_race_control | Race Control |
| Lap Analysis | ✅ | ✅ | get_lap_times | Performance |
| Race Management | ✅ | ✅ | get_race_results, get_lap_times | Strategy |
| Qualifying | ✅ | ✅ | get_qualifying_results | Performance |
| Practice | ✅ | ✅ | get_practice_results | Performance |
| Environmental | ✅ | ⚠️ | get_weather | Weather |

**Legend**:
- ✅ Fully functional
- ⚠️ Limited functionality (depends on historical data)
- ❌ Not available

---

## 🎨 Color Themes

### Dark Mode (Primary Theme)

**Background Colors**:
- Primary Background: `#0D0D0D` (Near black)
- Secondary Background: `#1A1A1A` (Dark gray)
- Card/Panel Background: `#242424` (Lighter gray)
- Hover/Active: `#2E2E2E` (Subtle highlight)

**Text Colors**:
- Primary Text: `#FFFFFF` (White)
- Secondary Text: `#B0B0B0` (Light gray)
- Disabled Text: `#666666` (Medium gray)

**Accent Colors (F1 Official)**:
- F1 Red: `#E10600` (Primary brand color)
- F1 Red Hover: `#FF1E00` (Interactive states)
- F1 Black: `#15151E` (Headers, emphasis)
- F1 White: `#FFFFFF` (Contrast elements)

**Functional Colors**:
- Success/Green: `#00D25B` (Positive actions, improvements)
- Warning/Yellow: `#FFAB00` (Cautions, track limits)
- Danger/Red: `#FF4B4B` (Errors, critical warnings)
- Info/Blue: `#0090FF` (Information, neutral alerts)

**Tire Compound Colors**:
- Soft (C5): `#FF0000` (Red)
- Medium (C4-C3): `#FFFF00` (Yellow)
- Hard (C2-C1): `#FFFFFF` (White)
- Intermediate: `#00FF00` (Green)
- Wet: `#0000FF` (Blue)

**Session Status Colors**:
- Live/Active: `#00FF00` (Green pulse)
- Qualifying: `#FFAB00` (Yellow)
- Race: `#E10600` (F1 Red)
- Practice: `#0090FF` (Blue)
- Ended: `#666666` (Gray)

**Chart Colors**:
- Line Chart Primary: `#E10600` (F1 Red)
- Line Chart Secondary: `#0090FF` (Blue)
- Line Chart Tertiary: `#00D25B` (Green)
- Grid Lines: `#333333` (Dark gray)
- Axis Labels: `#B0B0B0` (Light gray)

---

### Light Mode (Alternative Theme)

**Background Colors**:
- Primary Background: `#FFFFFF` (White)
- Secondary Background: `#F5F5F5` (Light gray)
- Card/Panel Background: `#FAFAFA` (Off-white)
- Hover/Active: `#EEEEEE` (Subtle highlight)

**Text Colors**:
- Primary Text: `#1A1A1A` (Near black)
- Secondary Text: `#666666` (Dark gray)
- Disabled Text: `#B0B0B0` (Light gray)

**Accent Colors (F1 Official)**:
- F1 Red: `#E10600` (Primary brand color)
- F1 Red Hover: `#CC0500` (Darker on light)
- F1 Black: `#15151E` (Headers, emphasis)
- F1 Gray: `#38383F` (Supporting elements)

**Functional Colors**:
- Success/Green: `#00A947` (Darker for readability)
- Warning/Yellow: `#FF9500` (Adjusted for contrast)
- Danger/Red: `#E10600` (F1 Red)
- Info/Blue: `#0070D2` (Darker blue)

**Tire Compound Colors**: (Same as Dark Mode)
- Soft (C5): `#FF0000` (Red)
- Medium (C4-C3): `#FFFF00` (Yellow with dark border)
- Hard (C2-C1): `#FFFFFF` (White with dark border)
- Intermediate: `#00DD00` (Green)
- Wet: `#0000FF` (Blue)

**Session Status Colors**:
- Live/Active: `#00A947` (Green)
- Qualifying: `#FF9500` (Orange)
- Race: `#E10600` (F1 Red)
- Practice: `#0070D2` (Blue)
- Ended: `#999999` (Gray)

**Chart Colors**:
- Line Chart Primary: `#E10600` (F1 Red)
- Line Chart Secondary: `#0070D2` (Blue)
- Line Chart Tertiary: `#00A947` (Green)
- Grid Lines: `#DDDDDD` (Light gray)
- Axis Labels: `#666666` (Dark gray)

---

### Accessibility Considerations

**WCAG 2.1 Compliance**: All color combinations meet AA standard (4.5:1 contrast ratio for normal text, 3:1 for large text)

**Color Blind Friendly**:
- Red/Green combinations avoid critical information encoding
- Additional indicators (icons, patterns) supplement color coding
- High contrast mode available for extreme visibility needs

**Visual Hierarchy**:
- F1 Red reserved for primary actions and critical alerts
- Consistent use of color across all dashboards
- Semantic color coding (green=good, red=danger, yellow=warning)

---

## 💻 UI Technology Decision

### **Selected: Streamlit** ✅

**Decision Date**: December 20, 2025  
**Status**: APPROVED for MVP (Phase 3A/3B)

#### Rationale

**Why Streamlit**:
- **Rapid development**: MVP dashboard deliverable in 2 weeks (Phase 3A timeline)
- **Python-native**: Perfect integration with FastF1, LangChain, and MCP server
- **Minimal code**: ~100 lines per dashboard vs 500+ in alternatives
- **Live streaming**: Native `st.chat_message` with LLM streaming support
- **F1 community**: Extensive telemetry visualization examples
- **Built-in features**: Plotly integration, caching (`@st.cache_data`), session state
- **Easy deployment**: Streamlit Cloud or simple Docker container

**Trade-offs Accepted**:
- Limited layout customization (acceptable for MVP)
- Full page refresh on interactions (mitigated with caching)
- Not ideal for >1000 concurrent users (not needed in MVP)

#### Technology Stack

```python
# Core UI Framework
streamlit==1.31.0

# Visualization
plotly==5.18.0
altair==5.2.0

# Layout Components
streamlit-option-menu==0.3.6  # Navigation
streamlit-extras==0.3.6        # Additional widgets
```

#### Multi-Dashboard Implementation

```python
# app.py - Main entry point
import streamlit as st
from streamlit_option_menu import option_menu

st.set_page_config(layout="wide", page_title="F1 Strategist AI")

# Sidebar navigation
with st.sidebar:
    selected = option_menu(
        "F1 Strategist AI",
        ["Chat Assistant", "Circuit", "Telemetry", "Weather", 
         "Tire Strategy", "Lap Analysis", "Race Management"],
        icons=["chat", "map", "graph-up", "cloud", 
               "circle", "stopwatch", "flag"],
        default_index=0
    )

# Dynamic page loading
if selected == "Chat Assistant":
    import pages.chat_assistant
    chat_assistant.render()
elif selected == "Circuit":
    import pages.circuit
    circuit.render()
# ... etc
```

#### Live Updates Strategy

```python
# Live mode with auto-refresh
if st.session_state.mode == "LIVE":
    # Auto-refresh every 5 seconds
    st_autorefresh(interval=5000, key="live_refresh")
    
    # Fetch latest data
    latest_data = get_live_data()
    
    # Update dashboards
    render_live_dashboard(latest_data)
```

#### Migration Path

If future requirements demand more control:
- **Phase 4+**: Evaluate Dash (Python ecosystem) or React (full control)
- **Criteria for migration**: >500 concurrent users, mobile app requirement, or advanced customization needs
- **Strategy**: Streamlit backend remains; only frontend changes

---

## 🎨 Next Steps

1. ✅ **UI technology selected** (Streamlit)
2. ✅ **Color themes defined** (Dark/Light mode with F1 branding)
3. **Responsive layout implementation** (desktop/tablet)
4. **Interactivity patterns** (filters, zoom, time scrubbing)
5. **Functional prototype** (Phase 3A deliverable)

---

**Last Update**: December 20, 2025  
**Author**: F1 Strategist AI Team  
**Status**: ✅ Dashboards defined - Wireframes completed
