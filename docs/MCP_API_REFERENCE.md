# F1 Data MCP Server - Complete API Reference

## Overview

The F1 Data MCP Server provides comprehensive access to Formula 1 race data through the Model Context Protocol (MCP). It combines historical data from FastF1 and real-time data from OpenF1.

**Server Name**: `f1-data-server`  
**Version**: 1.0.0  
**Protocol**: MCP (Model Context Protocol)

---

## 🏁 Available Tools (13 Total)

### 1. get_race_results
Get race results for a specific year and round.

**Response**: Driver positions, points, status

### 2. get_telemetry
Get detailed telemetry data for a specific driver.

**Response**: Speed, throttle, brake, gear, DRS data

### 3. get_qualifying_results
Get qualifying session results.

**Response**: Q1, Q2, Q3 times, grid positions

### 4. get_season_schedule
Get complete season calendar.

**Response**: Race dates, locations, circuit information

### 5. get_lap_times ⭐ NEW
Get lap-by-lap times for all drivers.

**Response**: Lap times, sector times, compound, personal best

### 6. get_pit_stops ⭐ NEW
Get pit stop data and strategy.

**Response**: Pit in/out times, compound changes, tire life

### 7. get_weather ⭐ NEW
Get weather conditions during the race.

**Response**: Temperature, humidity, wind, rainfall

### 8. get_tire_strategy ⭐ NEW
Get tire compound usage and strategy.

**Response**: Compound per lap, tire life, stint numbers

### 9. get_practice_results ⭐ NEW
Get practice session results (FP1/FP2/FP3).

**Response**: Driver positions, team names

### 10. get_sprint_results ⭐ NEW
Get sprint race results.

**Response**: Positions, points awarded, status

### 11. get_driver_info ⭐ NEW
Get driver information and details.

**Response**: Names, team, number, country, team color

### 12. get_track_status ⭐ NEW
Get track status and flags during the race.

**Response**: Flags, safety car periods, track conditions

### 13. get_race_control_messages ⭐ NEW
Get race control messages and decisions.

**Response**: Penalties, investigations, steward decisions

---

## 📊 Usage Examples

### Get Latest Race Results
```python
result = await client.call_tool(
    "get_race_results",
    {"year": 2024, "round_number": 24}
)
```

### Analyze Pit Stop Strategy
```python
pit_stops = await client.call_tool(
    "get_pit_stops",
    {"year": 2024, "round_number": 1}
)
```

### Weather Impact Analysis
```python
weather = await client.call_tool(
    "get_weather",
    {"year": 2024, "round_number": 1}
)
```

---

## 📚 Related Documentation

- [FastF1 Documentation](https://docs.fastf1.dev/)
- [OpenF1 API](https://openf1.org/)
- [MCP Protocol](https://modelcontextprotocol.io/)

**Last Updated**: December 20, 2025
