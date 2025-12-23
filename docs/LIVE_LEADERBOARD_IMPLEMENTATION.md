# Live Leaderboard Dashboard Implementation

## Overview

Successfully implemented a real-time live leaderboard dashboard using OpenF1 APIs in the F1 Strategist AI Dash application.

## Implementation Date

December 23, 2025

## Features Implemented

### 1. Real-Time Position Tracking
- **API Used**: `get_positions()`, `get_intervals()`
- Live position updates for all drivers
- Time gaps to leader and car ahead
- Position change indicators

### 2. Tire Strategy Display
- **API Used**: `get_stints()`
- Current tire compound (Soft/Medium/Hard/Intermediate/Wet)
- Color-coded tire badges:
  - SOFT: Red (#FF0000)
  - MEDIUM: Yellow (#FFF200)
  - HARD: White (#FFFFFF)
  - INTERMEDIATE: Green (#00FF00)
  - WET: Blue (#0000FF)
- Stint information (lap count)

### 3. Overtaking Moves
- **API Used**: `get_overtakes()`
- Display of recent overtaking moves
- Shows driver making overtake and driver being overtaken
- Lap number reference

### 4. Race Control Messages
- **API Used**: `get_race_control_messages()`
- Real-time flags and safety car notifications
- Track status updates
- Critical race information

### 5. Auto-Refresh Capability
- Configurable refresh intervals (1-10 seconds)
- Toggle auto-refresh on/off
- Manual refresh button
- Last update timestamp

### 6. Session Selection
- Year dropdown (2023-2025, OpenF1 data range)
- Meeting/Grand Prix dropdown
- Session type dropdown (Practice, Qualifying, Race)
- Load Session button

## Technical Architecture

### File Structure

```
src/dashboards_dash/
└── live_leaderboard_dashboard.py (586 lines)
    ├── LiveLeaderboardDashboard class
    ├── Layout methods
    ├── Callback handlers
    └── Helper methods
```

### Key Components

#### Class: `LiveLeaderboardDashboard`

**Constructor:**
```python
def __init__(self, provider: OpenF1DataProvider):
    self.provider = provider
    self.current_session_key = None
```

**Layout Method:**
```python
def create_layout(self) -> dbc.Container:
    """Create the complete dashboard layout."""
```

**Callback Methods:**
1. `update_meetings()`: Load meetings for selected year
2. `update_sessions()`: Load sessions for selected meeting
3. `control_auto_refresh()`: Enable/disable auto-refresh
4. `update_leaderboard()`: Main data refresh callback

**Helper Methods:**
1. `_get_latest_positions()`: Fetch current positions
2. `_get_latest_intervals()`: Fetch time gaps
3. `_get_current_stints()`: Get tire information
4. `_get_recent_overtakes()`: Fetch last 10 overtakes
5. `_get_race_control_messages()`: Fetch recent alerts
6. `_build_leaderboard_table()`: Construct HTML table
7. `_build_overtakes_card()`: Format overtake display
8. `_build_race_control_card()`: Format race control alerts

### Integration with Main App

**Changes to `app_dash.py`:**

1. **Import Statement (Line 35):**
```python
from src.dashboards_dash.live_leaderboard_dashboard import (
    LiveLeaderboardDashboard
)
```

2. **Dashboard Instantiation (Line 47):**
```python
# Initialize Live Leaderboard Dashboard
leaderboard_dashboard = LiveLeaderboardDashboard(openf1_provider)
```

3. **Dashboard Selector Option (Line 264):**
```python
{"label": " Live Leaderboard", "value": "live_leaderboard"},
```

4. **Dashboard Handler in Callback (Line 1031):**
```python
elif dashboard_id == "live_leaderboard":
    # Live Leaderboard Dashboard (OpenF1 real-time data)
    try:
        logger.info("Rendering live leaderboard dashboard...")
        leaderboard_content = leaderboard_dashboard.create_layout()
        dashboards.append(leaderboard_content)
        logger.info("Live leaderboard dashboard rendered successfully")
    except Exception as e:
        logger.error(f"Error creating live leaderboard dashboard: {e}", exc_info=True)
        dashboards.append(
            dbc.Card([
                dbc.CardHeader(html.H5("🏎️ Live Leaderboard")),
                dbc.CardBody([
                    html.P(
                        f"Error loading live leaderboard: {str(e)}",
                        className="text-danger"
                    )
                ])
            ], className="mb-3")
        )
```

5. **Callback Registration (Line 1533):**
```python
# Register leaderboard callbacks
logger.info("Registering live leaderboard callbacks...")
leaderboard_dashboard.setup_callbacks(app)
```

## API Fixes Applied

### Issue: Incorrect Method Names

**Problem:** Initial implementation used incorrect OpenF1DataProvider method names:
- `get_sessions()` → should be `get_session()`
- `get_race_control()` → should be `get_race_control_messages()`

**Solution:** Updated all method calls to use correct names.

### Issue: Direct API Queries

**Problem:** Some queries needed direct API access (meeting_key, session_key filters).

**Solution:** Used `provider._request()` method directly:
```python
sessions_data = self.provider._request(
    "sessions", {"meeting_key": meeting_key}
)
```

### Issue: Field Name Consistency

**Problem:** OpenF1 API uses snake_case field names.

**Solution:** Updated all field references:
- `SessionName` → `session_name`
- `SessionKey` → `session_key`
- `Circuit` → `circuit_short_name`

## Testing Results

### Application Startup
✅ Successfully starts on `http://127.0.0.1:8501/`
✅ No Pylance type checking errors
✅ All dashboards load without errors
✅ Leaderboard callbacks registered successfully

### Dashboard Functionality
✅ Appears in dashboard selector
✅ Year dropdown populated (2023-2025)
✅ Meeting selection works
✅ Session selection works
✅ Auto-refresh toggle functional
✅ Refresh interval slider works

## Usage Instructions

### For Users

1. **Open Application:**
   - Navigate to `http://localhost:8501`

2. **Select Live Leaderboard:**
   - Check "Live Leaderboard" in the sidebar dashboard selector

3. **Select Session:**
   - Choose Year (2023-2025)
   - Select Meeting/Grand Prix
   - Pick Session Type
   - Click "Load Session"

4. **Configure Auto-Refresh:**
   - Toggle "Enable Auto-Refresh"
   - Adjust refresh interval (1-10 seconds)
   - Or use "Refresh Now" for manual updates

5. **View Data:**
   - Main leaderboard table shows positions, gaps, tires
   - Recent overtakes displayed below
   - Race control messages at bottom

### For Developers

**Running the Application:**
```bash
cd "c:\Users\jorgeg\OneDrive - CEGID\Desarrollador 10x con IA\CAPSTON PROJECT\F1\F1 Strategist AI"
& "C:\Users\jorgeg\OneDrive - CEGID\Desarrollador 10x con IA\CAPSTON PROJECT\F1\F1 Strategist AI\venv\Scripts\python.exe" app_dash.py
```

**Adding New Features:**
1. Add helper methods to `LiveLeaderboardDashboard` class
2. Update layout in `create_layout()` method
3. Add callbacks in `setup_callbacks()` method
4. Use `self.provider` for OpenF1 API access

## Performance Considerations

### Auto-Refresh
- Default: Disabled (user must enable)
- Recommended interval: 2-5 seconds for races
- Rate limiting: OpenF1 API includes 0.5s delay between requests

### Data Volume
- Positions: ~20 drivers × 60 laps = 1200 records per race
- Intervals: Similar volume to positions
- Stints: ~3-5 stints per driver = 60-100 records
- Overtakes: Typically 50-150 per race
- Race Control: 20-50 messages per race

### Optimization
- Fetch only recent data (last 10 overtakes, last 10 messages)
- Use Dash caching where possible
- Limit auto-refresh to necessary updates

## Team Color Mapping

```python
TEAM_COLORS = {
    "Red Bull Racing": "#3671C6",
    "Ferrari": "#E8002D",
    "Mercedes": "#27F4D2",
    "McLaren": "#FF8000",
    "Aston Martin": "#229971",
    "Alpine": "#FF87BC",
    "Williams": "#64C4FF",
    "AlphaTauri": "#5E8FAA",
    "Alfa Romeo": "#C92D4B",
    "Haas F1 Team": "#B6BABD",
    "RB": "#6692FF",
    "Kick Sauber": "#52E252"
}
```

## Future Enhancements

### Short-Term
1. Add driver name resolution (currently shows driver numbers)
2. Display team colors in leaderboard table
3. Add fastest lap indicator
4. Show pit stop count per driver

### Medium-Term
1. Historical position chart (line graph)
2. Gap to leader over time visualization
3. Tire degradation tracking
4. Weather integration overlay

### Long-Term
1. Predictive strategy recommendations
2. Multi-session comparison
3. Driver-specific detailed view
4. Export session data to CSV

## Related Documentation

- [OpenF1 API Reference](MCP_API_REFERENCE.md)
- [Main Application Documentation](../README.md)
- [Dashboard Architecture](AGENTS_ARCHITECTURE.md)
- [Development Guide](project_development/DEVELOPMENT_GUIDE.md)

## Changelog

### Version 1.0.0 (December 23, 2025)
- ✅ Initial implementation
- ✅ Real-time position tracking
- ✅ Tire strategy display
- ✅ Overtaking moves
- ✅ Race control messages
- ✅ Auto-refresh capability
- ✅ Session selection
- ✅ Integration with main Dash app

## Known Issues

None reported as of December 23, 2025.

## Support

For issues or questions, please refer to:
- Project documentation in `docs/` directory
- OpenF1 API documentation: https://openf1.org
- GitHub repository (if applicable)

---

**Last Updated:** December 23, 2025  
**Status:** ✅ Production Ready  
**Maintainer:** F1 Strategist AI Team
