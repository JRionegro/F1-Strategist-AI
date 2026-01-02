# F1 Data MCP Server - Complete API Reference

## Overview

The F1 Data MCP Server provides comprehensive access to Formula 1 race data through the Model Context Protocol (MCP). It integrates **OpenF1 API** for real-time and historical data with **FastF1** as fallback for legacy seasons.

**Server Name**: `f1-data-server`  
**Version**: 2.0.0  
**Protocol**: MCP (Model Context Protocol)  
**Primary Data Source**: OpenF1 API (2023+)  
**Secondary Data Source**: FastF1 (Pre-2023)

---

## 🏁 Available Tools (19 Total)

### Core Race Data

#### 1. get_race_results
Get race results for a specific year and round.

**Input Parameters**:
- `year` (integer, required): Season year (2018-2025)
- `round_number` (integer, required): Race round (1-24)
- `use_realtime` (boolean, optional): Use OpenF1 real-time data

**Response**: Driver positions, points, status, team information

---

#### 2. get_qualifying_results
Get qualifying session results.

**Input Parameters**:
- `year` (integer, required): Season year (2018-2025)
- `round_number` (integer, required): Race round (1-24)
- `use_realtime` (boolean, optional): Use OpenF1 real-time data

**Response**: Q1, Q2, Q3 times, grid positions

---

#### 3. get_season_schedule
Get complete season calendar.

**Input Parameters**:
- `year` (integer, required): Season year (2018-2025)

**Response**: Race dates, locations, circuit information, country names

---

#### 4. get_driver_info
Get driver information and details.

**Input Parameters**:
- `year` (integer, required): Season year (2018-2025)
- `round_number` (integer, required): Race round (1-24)

**Response**: Names, team, number, abbreviation, team color, country

---

### Telemetry & Performance

#### 5. get_telemetry
Get detailed car telemetry data for a specific driver.

**Input Parameters**:
- `year` (integer, required): Season year (2018-2025)
- `round_number` (integer, required): Race round (1-24)
- `driver` (string, required): Driver code (VER, HAM, LEC, etc.)
- `use_realtime` (boolean, optional): Use OpenF1 real-time data

**Response**: Speed, throttle, brake, gear, DRS, RPM data

**OpenF1 Source**: `/car_data` endpoint

---

#### 6. get_lap_times
Get lap-by-lap times for all drivers.

**Input Parameters**:
- `year` (integer, required): Season year (2018-2025)
- `round_number` (integer, required): Race round (1-24)
- `session_type` (string, optional): "R", "Q", "FP1", "FP2", "FP3" (default: "R")

**Response**: Lap times, sector times, compound, stint info, lap end times

**OpenF1 Source**: `/laps` endpoint

---

### Race Position & Timing

#### 7. get_positions ⭐ CRITICAL
Get real-time race positions (NOT calculated from lap times).

**Input Parameters**:
- `session_key` (integer, required): OpenF1 session identifier
- `driver_number` (integer, optional): Filter by specific driver

**Response**: Position (P1, P2, P3...), DriverNumber, Timestamp

**OpenF1 Source**: `/position` endpoint

**Usage**: This is the **correct** way to get race positions during simulation. Do NOT calculate positions from cumulative lap times.

---

#### 8. get_intervals ⭐ NEW
Get time gaps between drivers (intervals and gap to leader).

**Input Parameters**:
- `session_key` (integer, required): OpenF1 session identifier
- `driver_number` (integer, optional): Filter by specific driver

**Response**: GapToLeader, Interval (to car ahead), DriverNumber, Timestamp

**OpenF1 Source**: `/intervals` endpoint

**Usage**: Display gaps like "Leader", "+2.534s", "+5.892s" in leaderboard

---

### Strategy & Pit Stops

#### 9. get_pit_stops
Get pit stop data and strategy.

**Input Parameters**:
- `year` (integer, required): Season year (2018-2025)
- `round_number` (integer, required): Race round (1-24)

**Response**: Pit in/out times, compound changes, pit duration, lap number

**OpenF1 Source**: `/pit` endpoint

---

#### 10. get_tire_strategy
Get tire compound usage and stint information.

**Input Parameters**:
- `year` (integer, required): Season year (2018-2025)
- `round_number` (integer, required): Race round (1-24)

**Response**: Compound per stint, tire age, stint start/end laps

**OpenF1 Source**: `/stints` endpoint

---

### Weather & Track Conditions

#### 11. get_weather
Get weather conditions during the session.

**Input Parameters**:
- `year` (integer, required): Season year (2018-2025)
- `round_number` (integer, required): Race round (1-24)

**Response**: Air temperature, track temperature, humidity, wind speed, wind direction, rainfall, pressure

**OpenF1 Source**: `/weather` endpoint

---

#### 12. get_track_status
Get track status and flags during the race.

**Input Parameters**:
- `year` (integer, required): Season year (2018-2025)
- `round_number` (integer, required): Race round (1-24)

**Response**: Flags (yellow, red, green), safety car periods, VSC, track conditions

**OpenF1 Source**: `/race_control` endpoint (filtered for track status)

---

#### 13. get_race_control_messages
Get race control messages and steward decisions.

**Input Parameters**:
- `year` (integer, required): Season year (2018-2025)
- `round_number` (integer, required): Race round (1-24)

**Response**: Penalties, investigations, steward decisions, flag notifications

**OpenF1 Source**: `/race_control` endpoint

---

### Additional Sessions

#### 14. get_practice_results
Get practice session results (FP1/FP2/FP3).

**Input Parameters**:
- `year` (integer, required): Season year (2018-2025)
- `round_number` (integer, required): Race round (1-24)
- `session_type` (string, required): "FP1", "FP2", or "FP3"

**Response**: Driver positions, team names, lap times

---

#### 15. get_sprint_results
Get sprint race results.

**Input Parameters**:
- `year` (integer, required): Season year (2018-2025)
- `round_number` (integer, required): Race round (1-24)

**Response**: Positions, points awarded, status, grid changes

---

### Advanced Data ⭐ NEW ENDPOINTS

#### 16. get_location
Get GPS coordinates of cars on track.

**Input Parameters**:
- `session_key` (integer, required): OpenF1 session identifier
- `driver_number` (integer, optional): Filter by specific driver

**Response**: X, Y, Z coordinates, DriverNumber, Timestamp

**OpenF1 Source**: `/location` endpoint

**Usage**: Track position visualization, circuit mapping, car positions

---

#### 17. get_team_radio
Get team radio messages with audio links.

**Input Parameters**:
- `session_key` (integer, required): OpenF1 session identifier
- `driver_number` (integer, optional): Filter by specific driver

**Response**: DriverNumber, Timestamp, AudioURL (direct link to radio recording)

**OpenF1 Source**: `/team_radio` endpoint

**Usage**: Access team communications, strategy calls, driver feedback

---

#### 18. get_meetings
Get race weekend (meeting) information.

**Input Parameters**:
- `session_key` (integer, optional): OpenF1 session identifier
- `year` (integer, optional): Filter by year
- `country_name` (string, optional): Filter by country

**Response**: MeetingKey, MeetingName, OfficialName, Location, Country, Circuit, StartDate, Year

**OpenF1 Source**: `/meetings` endpoint

**Usage**: Event information, weekend schedules, circuit details

---

#### 19. get_overtakes ⭐ NEW
Get overtaking maneuvers during a session.

**Input Parameters**:
- `session_key` (integer, required): OpenF1 session identifier
- `driver_number` (integer, optional): Filter by specific driver

**Response**: DriverNumber (overtaken), OvertakingDriverNumber (overtaking), Timestamp, LapNumber

**OpenF1 Source**: `/overtakes` endpoint

**Usage**: Analyze overtaking patterns, identify aggressive drivers, race action highlights


---

## 📊 Usage Examples

### Get Latest Race Results
```python
result = await client.call_tool(
    "get_race_results",
    {"year": 2025, "round_number": 24, "use_realtime": True}
)
```

### Get Real-Time Race Positions (CORRECT METHOD)
```python
# First, get session_key from get_session()
positions = await client.call_tool(
    "get_positions",
    {"session_key": 9559}  # Abu Dhabi 2025 Race
)
# Returns: Position (P1, P2, P3...), NOT calculated from lap times
```

### Get Time Gaps Between Drivers
```python
intervals = await client.call_tool(
    "get_intervals",
    {"session_key": 9559}
)
# Returns: GapToLeader, Interval to car ahead
# Example: Leader: 0.0s, P2: +2.534s, P3: +0.892s (to P2)
```

### Analyze Pit Stop Strategy
```python
pit_stops = await client.call_tool(
    "get_pit_stops",
    {"year": 2025, "round_number": 1}
)
```

### Weather Impact Analysis
```python
weather = await client.call_tool(
    "get_weather",
    {"year": 2025, "round_number": 1}
)
```

### Get Car Telemetry
```python
telemetry = await client.call_tool(
    "get_telemetry",
    {"year": 2025, "round_number": 1, "driver": "VER", "use_realtime": True}
)
# Returns: Speed, RPM, Gear, Throttle, Brake, DRS
```

### Get GPS Positions on Track
```python
locations = await client.call_tool(
    "get_location",
    {"session_key": 9559, "driver_number": 1}
)
# Returns: X, Y, Z coordinates for circuit mapping
```

### Access Team Radio
```python
radio = await client.call_tool(
    "get_team_radio",
    {"session_key": 9559, "driver_number": 1}
)
# Returns: Timestamp, AudioURL (direct link to radio recording)
```

### Get Overtaking Maneuvers
```python
overtakes = await client.call_tool(
    "get_overtakes",
    {"session_key": 9559}
)
# Returns: DriverNumber (overtaken), OvertakingDriverNumber, Timestamp, LapNumber
# Analyze who made the most overtakes and when
```

---

## 🔑 OpenF1 API Endpoints Mapping

| MCP Tool | OpenF1 Endpoint | Coverage |
|----------|----------------|----------|
| `get_driver_info` | `/drivers` | ✅ Full |
| `get_lap_times` | `/laps` | ✅ Full |
| `get_positions` | `/position` | ✅ Full |
| `get_intervals` | `/intervals` | ✅ Full |
| `get_tire_strategy` | `/stints` | ✅ Full |
| `get_pit_stops` | `/pit` | ✅ Full |
| `get_race_control_messages` | `/race_control` | ✅ Full |
| `get_weather` | `/weather` | ✅ Full |
| `get_telemetry` | `/car_data` | ✅ Full |
| `get_location` | `/location` | ✅ Full |
| `get_team_radio` | `/team_radio` | ✅ Full |
| `get_meetings` | `/meetings` | ✅ Full |
| `get_overtakes` | `/overtakes` | ✅ Full |

**All 13 OpenF1 endpoints are fully implemented!** 🎉

---

## ⚠️ Important Notes

### Race Position Calculation

**❌ INCORRECT APPROACH** (Do NOT use):
```python
# Sorting by cumulative lap time - WRONG!
cumulative_time = sum(lap_times)
positions = drivers.sort_values('cumulative_time')
```

**✅ CORRECT APPROACH** (Always use):
```python
# Use OpenF1 positions endpoint
positions = openf1_provider.get_positions(session_key)
# Returns actual race positions at each timestamp
```

**Why it matters**: Race positions are affected by:
- Pit stop strategies (time lost ≠ position lost)
- Safety car periods (gaps compressed)
- Penalties and time adjustments
- Track incidents and retirements

**OpenF1 `/position` endpoint provides the REAL positions**, not calculated estimations.

---

### Data Availability by Year

| Year Range | Data Source | Availability |
|-----------|-------------|--------------|
| 2023-2025 | OpenF1API | ✅ Full real-time + historical |
| 2018-2022 | FastF1 | ✅ Historical only |
| Pre-2018 | Limited | ⚠️ Partial coverage |

---

### Session Key vs Round Number

- **`session_key`**: OpenF1 unique identifier (e.g., 9559)
  - Use with: `get_positions`, `get_intervals`, `get_location`, `get_team_radio`
  - Get from: `get_session()` method in OpenF1provider

- **`round_number`**: Race round in season (1-24)
  - Use with: All other tools
  - Simpler for general queries

---

## 🎯 Best Practices

### For Real-Time Simulation
1. ✅ Use `get_positions()` for race positions
2. ✅ Use `get_intervals()` for time gaps
3. ✅ Use `get_lap_times()` for lap performance
4. ✅ Combine with `get_pit_stops()` for strategy

### For Telemetry Analysis
1. ✅ Use `get_telemetry()` for detailed car data
2. ✅ Use `get_location()` for track position
3. ✅ Combine with `get_weather()` for conditions

### For Strategy Analysis
1. ✅ Use `get_tire_strategy()` for stint info
2. ✅ Use `get_pit_stops()` for timing
3. ✅ Use `get_intervals()` for gap management
4. ✅ Use `get_race_control_messages()` for incidents

---

## 📚 Related Documentation

- [OpenF1 API Documentation](https://openf1.org/)
- [FastF1 Documentation](https://docs.fastf1.dev/)
- [MCP Protocol](https://modelcontextprotocol.io/)
- [Project Architecture](./ARCHITECTURE_DECISIONS.md)
- [Development Guide](./project_development/DEVELOPMENT_GUIDE.md)

---

**Last Updated**: December 23, 2025  
**Version**: 2.0.0  
**Status**: All OpenF1 APIs Implemented ✅
