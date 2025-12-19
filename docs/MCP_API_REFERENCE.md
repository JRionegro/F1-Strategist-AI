# F1 Data MCP Server API Reference

## Overview

The F1 Data MCP Server provides access to Formula 1 race data
through the Model Context Protocol (MCP). It combines historical
data from FastF1 and real-time data from OpenF1.

**Base Server**: `f1-data-server`

---

## Available Tools

### 1. get_race_results

Get race results for a specific year and round.

**Parameters**:
```json
{
  "year": 2024,
  "round_number": 1,
  "use_realtime": false
}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| year | integer | Yes | Season year (2018-2024) |
| round_number | integer | Yes | Race round (1-24) |
| use_realtime | boolean | No | Use OpenF1 real-time data |

**Response Example**:
```json
[
  {
    "DriverNumber": 1,
    "Driver": "VER",
    "TeamName": "Red Bull Racing",
    "Position": 1,
    "Points": 25.0,
    "Status": "Finished"
  },
  ...
]
```

**Usage**:
```python
from mcp import Client

client = Client("f1-data-server")
result = await client.call_tool(
    "get_race_results",
    {"year": 2024, "round_number": 1}
)
```

---

### 2. get_telemetry

Get detailed telemetry data for a specific driver.

**Parameters**:
```json
{
  "year": 2024,
  "round_number": 1,
  "driver": "VER",
  "use_realtime": false
}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| year | integer | Yes | Season year (2018-2024) |
| round_number | integer | Yes | Race round (1-24) |
| driver | string | Yes | Driver code (3 letters) |
| use_realtime | boolean | No | Use real-time data |

**Response Example**:
```json
[
  {
    "Time": 0.0,
    "Speed": 310.5,
    "nGear": 8,
    "Throttle": 100.0,
    "Brake": 0.0,
    "DRS": 0
  },
  ...
]
```

**Notes**:
- Returns first 100 samples to limit response size
- Full telemetry can be millions of data points

---

### 3. get_qualifying_results

Get qualifying session results.

**Parameters**:
```json
{
  "year": 2024,
  "round_number": 1,
  "use_realtime": false
}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| year | integer | Yes | Season year (2018-2024) |
| round_number | integer | Yes | Race round (1-24) |
| use_realtime | boolean | No | Use real-time data |

**Response Example**:
```json
[
  {
    "DriverNumber": 1,
    "Driver": "VER",
    "TeamName": "Red Bull Racing",
    "Q1": "0 days 00:01:29.708000",
    "Q2": "0 days 00:01:28.997000",
    "Q3": "0 days 00:01:28.319000",
    "GridPosition": 1
  },
  ...
]
```

---

### 4. get_season_schedule

Get complete season calendar.

**Parameters**:
```json
{
  "year": 2024
}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| year | integer | Yes | Season year (2018-2024) |

**Response Example**:
```json
[
  {
    "RoundNumber": 1,
    "Country": "Bahrain",
    "Location": "Sakhir",
    "OfficialEventName": "Bahrain Grand Prix",
    "EventDate": "2024-03-02",
    "EventName": "Bahrain Grand Prix",
    "EventFormat": "conventional"
  },
  ...
]
```

---

## Error Handling

All tools return standard MCP error responses:

```json
{
  "content": [
    {
      "type": "text",
      "text": "Error: Invalid year specified"
    }
  ],
  "isError": true
}
```

**Common Errors**:
- Invalid year (outside 2018-2024)
- Invalid round number
- Driver not found
- No data available
- Network timeout

---

## Rate Limits

- **FastF1** (Historical): No rate limits, uses caching
- **OpenF1** (Real-time): TBD based on API key

---

## Examples

### Get Latest Race Results

```python
result = await client.call_tool(
    "get_race_results",
    {"year": 2024, "round_number": 24}
)
```

### Compare Driver Telemetry

```python
ver_telemetry = await client.call_tool(
    "get_telemetry",
    {"year": 2024, "round_number": 1, "driver": "VER"}
)

ham_telemetry = await client.call_tool(
    "get_telemetry",
    {"year": 2024, "round_number": 1, "driver": "HAM"}
)
```

### Get Full Season Calendar

```python
schedule = await client.call_tool(
    "get_season_schedule",
    {"year": 2024}
)
```

---

## Data Sources

### FastF1 (Historical Data)
- **Coverage**: 2018-present
- **Update Frequency**: Post-race
- **Data Quality**: Official FIA timing
- **Cache**: Enabled by default

### OpenF1 (Real-Time Data)
- **Coverage**: Current season
- **Update Frequency**: Live during races
- **Data Quality**: Real-time feed
- **Requires**: API key (optional)

---

## Server Configuration

```python
server = F1DataMCPServer(
    cache_dir="./cache",
    openf1_api_key="your_api_key"
)

await server.run(host="0.0.0.0", port=8000)
```

---

## Next Steps

1. Install MCP client library
2. Connect to server
3. Start making tool calls
4. Implement strategy analysis

For more examples, see [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md)