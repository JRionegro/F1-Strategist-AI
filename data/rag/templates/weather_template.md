---
category: weather
template: true
variables: [circuit_name, circuit_location, timezone]
---

# {circuit_name} - Complete Weather & Track Conditions Guide

## Location Information

| Property | Value |
|----------|-------|
| **Location** | {circuit_location} |
| **Timezone** | {timezone} |
| **Typical Race Time** | {race_local_time} local |
| **Climate Type** | {climate_type} |

---

## 1. Typical Race Conditions

### 1.1 Temperature Profiles

| Metric | Average | Range |
|--------|---------|-------|
| **Air Temperature** | {avg_air_temp}°C | {air_temp_range}°C |
| **Track Temperature** | {avg_track_temp}°C | {track_temp_range}°C |
| **Humidity** | {avg_humidity}% | {humidity_range}% |

### 1.2 Wind Conditions

- **Prevailing Direction**: {wind_direction}
- **Average Speed**: {avg_wind_speed} km/h
- **Maximum Gusts**: Up to {max_wind_gust} km/h
- **Wind Impact Level**: {wind_impact_level}/10

---

## 2. Temperature Evolution During Race

### 2.1 Typical Pattern

{temp_evolution_description}

### 2.2 Strategic Impact by Track Temperature

| Track Temp | Tire Behavior | Strategy Impact |
|------------|---------------|-----------------|
| < 25°C | Slow warm-up, graining risk | Longer stints, HARD viable |
| 25-35°C | Optimal operating window | Normal degradation expected |
| 35-45°C | Faster deg, blistering risk | Shorter stints recommended |
| > 45°C | High deg, overheating | Consider 2-stop strategy |

### 2.3 Tire Temperature Windows

| Compound | Optimal Track Temp | Operating Window |
|----------|-------------------|------------------|
| SOFT | {soft_optimal_temp}°C | {soft_temp_range}°C |
| MEDIUM | {medium_optimal_temp}°C | {medium_temp_range}°C |
| HARD | {hard_optimal_temp}°C | {hard_temp_range}°C |
| INTERMEDIATE | {inter_optimal_temp}°C | Any wet condition |
| WET | Any | Heavy standing water |

---

## 3. Rain Probability & Analysis

### 3.1 Historical Data

| Condition | Probability |
|-----------|-------------|
| **Completely Dry Race** | {dry_probability}% |
| **Some Rain During Weekend** | {rain_probability}% |
| **Wet Race (Inters/Wets Used)** | {wet_race_probability}% |
| **Red Flag Due to Weather** | {red_flag_probability}% |

### 3.2 Seasonal Variations

{seasonal_rain_description}

### 3.3 Rain Prediction Indicators

Watch for these signs:

1. {rain_indicator_1}
2. {rain_indicator_2}
3. {rain_indicator_3}

### 3.4 Radar & Weather Tools

- F1 Weather radar refresh: Every 5 minutes
- Local weather station data available
- Team meteorologists typically 10-15 min ahead

---

## 4. Track Evolution

### 4.1 Rubber Build-Up Pattern

| Session | Grip Level | Notes |
|---------|-----------|-------|
| FP1 | Low (Green track) | Initial rubber laying |
| FP2 | Medium | Representative conditions |
| FP3 | Medium-High | Near race grip |
| Qualifying | High | Peak grip levels |
| Race Start | High | Best grip of weekend |
| Race End | Very High | Maximum rubber down |

### 4.2 Track Evolution per Session

- **FP1 to FP2**: ~{fp1_fp2_evolution}s improvement
- **FP2 to FP3**: ~{fp2_fp3_evolution}s improvement
- **FP3 to Quali**: ~{fp3_quali_evolution}s improvement
- **Quali to Race**: ~{quali_race_evolution}s (same conditions)

### 4.3 After Rain Reset

When rain washes away rubber:

- Track grip drops ~{rain_grip_loss}%
- Re-rubbering takes ~{re_rubber_laps} laps
- First dry lap after rain: Extra caution needed
- Crossover point: Track must be {crossover_water_level}% dry

---

## 5. Wind Impact Analysis

### 5.1 Sector Analysis

| Sector | Wind Effect | Corner Impact |
|--------|-------------|---------------|
| Sector 1 | {s1_wind_effect} | {s1_corners} |
| Sector 2 | {s2_wind_effect} | {s2_corners} |
| Sector 3 | {s3_wind_effect} | {s3_corners} |

### 5.2 Crosswind Zones

{crosswind_description}

### 5.3 High-Speed Wind Impact

| Wind Speed | Impact |
|------------|--------|
| < 15 km/h | Minimal, normal setup |
| 15-25 km/h | Slight adjustments, consistent |
| 25-35 km/h | Noticeable effect, balance changes |
| > 35 km/h | Significant, car stability affected |

---

## 6. Rain Strategy Protocols

### 6.1 Dry to Wet Transition

**When Rain Starts:**

1. **Light Drizzle (Track Damp)**
   - Continue on slicks if possible
   - Watch for spray from cars ahead
   - Be ready for instant swap

2. **Moderate Rain (Track Wet)**
   - Intermediates become necessary
   - Pit window opens: ~3-5 laps after rain
   - Track temp drops rapidly

3. **Heavy Rain (Standing Water)**
   - Full wets required
   - Consider SC/VSC probability
   - Visibility concerns

### 6.2 Wet to Dry Transition

**When Rain Stops:**

1. **Track Drying Begins**
   - Racing line dries first (~5-10 laps)
   - Monitor lap time improvements
   - Leaders report track conditions

2. **Crossover Point**
   - Intermediate to slick: When {dry_crossover_time}s faster
   - Full wet to inter: When standing water clears
   - Timing is crucial: First to switch gains ~2-5 seconds

3. **Dry Line Formation**
   - Stay on racing line only
   - Off-line remains slippery for ~10 laps
   - Kerbs extremely slippery when damp

### 6.3 Intermediate vs Wet Tires

| Condition | Intermediate | Full Wet |
|-----------|-------------|----------|
| Standing water | ❌ Aquaplane risk | ✅ Best |
| Heavy spray | ⚠️ Risky | ✅ Best |
| Light rain | ✅ Best | ❌ Too slow |
| Drying track | ✅ Best | ❌ Overheats |
| Mixed conditions | ✅ Versatile | ⚠️ Only wet zones |

---

## 7. Strategic Weather Implications

### 7.1 Dry Conditions Strategy

{dry_strategy}

### 7.2 Changing Conditions Strategy

{changing_conditions_strategy}

### 7.3 Wet Conditions Strategy

{wet_strategy}

### 7.4 Think Out of the Box 🧠

**Weather-Based Creative Strategies:**

- **Early weather call**: Pit before others when rain radar shows incoming
- **Staying out gamble**: If rain is light, slicks may survive
- **Opposite strategy**: When field pits for inters, stay out if rain stops
- **Double-stack timing**: Coordinate if teammate has different tire age

---

## 8. Historical Weather Data

### Recent Race Conditions

| Year | Air Temp | Track Temp | Rain | Key Impact |
|------|----------|------------|------|------------|
{historical_weather_table}

### Notable Weather Events

{notable_weather_events}

---

## 9. Quick Reference Card

```
🌡️ WEATHER OVERVIEW: {circuit_name}
📍 Climate: {climate_type}

TYPICAL CONDITIONS:
├── Air Temp: {avg_air_temp}°C ({air_temp_range}°C range)
├── Track Temp: {avg_track_temp}°C
├── Humidity: {avg_humidity}%
└── Wind: {avg_wind_speed} km/h from {wind_direction}

RAIN PROBABILITY:
├── Dry Race: {dry_probability}%
├── Some Rain: {rain_probability}%
└── Wet Race: {wet_race_probability}%

TIRE WINDOWS (Track Temp):
├── SOFT: Best at {soft_optimal_temp}°C
├── MEDIUM: Best at {medium_optimal_temp}°C
└── HARD: Best at {hard_optimal_temp}°C

CROSSOVER TIMES:
├── Slick → Inter: When {slick_to_inter_delta}s slower
└── Inter → Slick: When {dry_crossover_time}s faster
```

---

*Generated from template. Data: OpenF1 API, Weather Services, Historical Analysis*
*Last updated: {generation_date}*
