# Race Control Dashboard Implementation

**Date**: 2025-12-26  
**Status**: Implementation Complete  
**Developer**: AI Assistant + Jorge Rionegro

---

## Overview

Implementation of a real-time Race Control Dashboard synchronized with simulation/live timing, displaying flags, Safety Car status, penalties, and race incidents using OpenF1 API.

---

## Technical Specifications

### File Location
- **Path**: `src/dashboards_dash/race_control_dashboard.py`
- **Class**: `RaceControlDashboard`
- **Pattern**: Class-based dashboard with caching (follows `RaceOverviewDashboard` pattern)

### Data Sources

#### Primary API Endpoint
- **Method**: `OpenF1DataProvider.get_race_control_messages(session_key)`
- **Endpoint**: `https://api.openf1.org/v1/race_control`
- **Returns**: DataFrame with columns:
  - `Time` (datetime) - Timestamp of message
  - `Category` (str) - Message category/type
  - `Message` (str) - Full race control message text
  - `Flag` (str) - Flag status if applicable

#### Supporting Data
- **Method**: `OpenF1DataProvider.get_drivers(session_key)`
- **Purpose**: Map driver numbers to names for display

---

## Dashboard Structure

### Layout Dimensions (Standardized)
- **Height**: `620px` with `overflow: auto`
- **Width**: 4-column grid (33.3% of row)
- **CardHeader**: `className="py-1"`, `fontSize: "1.2rem"`
- **Icon**: 🚦 Race Control

### UI Components (Top to Bottom)

#### 1. Current Status Panel (~80px)
- **Purpose**: Show current track status at simulation time
- **Elements**:
  - Current flag badge (🟢 Green / 🟡 Yellow / 🔴 Red / 🚗 SC / 🟡 VSC)
  - DRS status (Enabled/Disabled)
  - Current lap number
  - Safety Car lap counter (if SC/VSC active)
- **Styling**: Compact badges, single-row layout

#### 2. Messages Timeline (~540px, scrollable)
- **Purpose**: Chronological log of all race control messages
- **Format**: `[LAP X] HH:MM:SS | Message text`
- **Features**:
  - Color-coded by type (SC=warning, Penalty=info, Red=danger)
  - Small font (`fontSize: 0.75rem`) for density
  - Limit to last 100 messages for performance
- **Styling**: Alternating row colors for readability

---

## Time Synchronization

### Simulation Time Integration
```python
def render(
    self,
    session_key: Optional[int] = None,
    simulation_time: Optional[float] = None,  # Seconds from session start
    session_start_time: Optional[pd.Timestamp] = None  # Absolute start time
):
    # Calculate current time in simulation
    if simulation_time and session_start_time:
        current_time = session_start_time + timedelta(seconds=simulation_time)
        
        # Filter messages up to current time
        filtered_messages = messages[messages['Time'] <= current_time]
```

### Refresh Strategy
- **Interval**: 3 seconds (via `dcc.Interval` in app_dash.py)
- **Caching**: Fetch race control messages once per session
- **Filtering**: Filter by time on each refresh (fast operation)

---

## Integration with App

### Dashboard Registration
**Location**: `app_dash.py`

- Import `RaceControlDashboard`
- Initialize with `openf1_provider`
- Add to selector (default checked)
- Wire callback handler

### Default Activation
- Dashboard checked by default in sidebar menu
- Positioned alongside Race Overview, Weather, AI Assistant
- Appears in 4-column layout with vertical separators

---

## Message Classification Logic

### Rule-Based Parser
Priority levels:
1. Red Flag (danger) - Session stopped
2. Safety Car (warning) - Bunched field
3. VSC (warning) - Reduced speed
4. Yellow Flag (warning) - Local incident
5. Penalty (info) - Driver sanctions
6. Investigation (secondary) - Under review
7. Green Flag (success) - All clear
8. Other (light) - General messages

---

*Last Updated: 2025-12-26*
