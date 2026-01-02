---
category: strategy
template: true
variables: [circuit_name, circuit_type, lap_length, total_laps, pit_loss, drs_zones]
---

# {circuit_name} - Complete Strategy Guide

## Circuit Characteristics

| Property | Value |
|----------|-------|
| **Circuit Type** | {circuit_type} |
| **Lap Length** | {lap_length} km |
| **Race Laps** | {total_laps} |
| **Pit Lane Time Loss** | {pit_loss} seconds |
| **DRS Zones** | {drs_zones} |

## Track Layout

{track_layout_description}

---

## 1. Race Strategy Fundamentals

### Starting Grid Position Value

- **Overtaking Difficulty**: {overtaking_difficulty}/10
- **Track Position Importance**: {track_position_importance}/10
- **First Lap Position Gain Potential**: {first_lap_gain_potential}
- **Clean Air Premium**: ~{clean_air_delta}s per lap

### Strategic Race Phases

| Phase | Laps | Key Considerations |
|-------|------|---------------------|
| **Start** | 1-5 | Position defense/attack, tire preservation |
| **Early Race** | 6-20 | Undercut window opens, fuel burn effect |
| **Mid-Race** | 21-40 | Primary pit window, SC probability peak |
| **Late Race** | 41-{total_laps} | Final stint management, DRS trains |

---

## 2. Pit Stop Strategies

### 2.1 Optimal Strategy Windows

| Strategy | Stops | Lap Range | Compounds | Notes |
|----------|-------|-----------|-----------|-------|
| **One-Stop Optimal** | 1 | Lap {one_stop_window} | {one_stop_compounds} | {one_stop_notes} |
| **Two-Stop Aggressive** | 2 | Laps {two_stop_windows} | {two_stop_compounds} | {two_stop_notes} |
| **Three-Stop Sprint** | 3 | Laps {three_stop_windows} | {three_stop_compounds} | {three_stop_notes} |

### 2.2 Pit Lane Analysis

- **Entry Speed Limit**: {pit_entry_speed} km/h
- **Pit Lane Length**: {pit_lane_length} m
- **Typical Stationary Time**: {typical_pit_time} seconds
- **Total Time Loss per Stop**: {total_pit_loss} seconds
- **Delta vs Track (per stop)**: ~{pit_delta_track}s

### 2.3 Undercut Analysis

The **undercut** involves pitting earlier than your rival to gain track position
through fresh tire pace advantage.

- **Undercut Power at {circuit_name}**: {undercut_power}/10
- **Optimal Window**: {undercut_window} laps before rival
- **Fresh Tire Advantage**: ~{undercut_gain}s per lap
- **Effective For**: {undercut_conditions}
- **Risk**: May compromise tire life later in stint

**When to Undercut:**

1. Rival is struggling with tire degradation
2. Track temperature is stable or rising
3. Clean air available after pit exit
4. Not expecting imminent Safety Car

### 2.4 Overcut Analysis

The **overcut** involves staying out longer to benefit from lighter fuel load
and potentially clear track after rivals pit.

- **Overcut Viability**: {overcut_viability}/10
- **Best Conditions**: {overcut_conditions}
- **Fuel Advantage per Lap**: ~{fuel_advantage}s lighter = faster
- **Risk**: Losing track position if undercut is powerful

**When to Overcut:**

1. Tire warm-up is slow (cold track, hard compound)
2. Traffic in pit lane or pit exit
3. Clear air advantage significant
4. Can maintain race pace without degradation

---

## 3. Overtaking Opportunities

### 3.1 Primary Overtaking Zones

{overtaking_zones}

### 3.2 DRS Zones

| Zone | Detection Point | Activation | Notes |
|------|-----------------|------------|-------|
{drs_zones_table}

### 3.3 Non-DRS Opportunities

{non_drs_overtaking}

### 3.4 Defensive Lines

{defensive_lines}

---

## 4. Safety Car Strategy

### 4.1 Historical Data

- **SC Probability**: {sc_probability}%
- **Average SCs per Race**: {avg_sc_per_race}
- **VSC Probability**: {vsc_probability}%
- **Red Flag Probability**: {red_flag_probability}%

### 4.2 Common SC Zones

{sc_zones_description}

### 4.3 SC/VSC Strategy Protocols

**When Safety Car Deploys:**

1. **Pit Immediately If:**
   - You have >3-second gap to car behind
   - Tire condition is marginal
   - You're outside optimal pit window but close
   - Strategy model shows net position gain

2. **Stay Out If:**
   - You're leading with fresh tires
   - Pit would drop you into traffic
   - Expecting restart battles benefit fresh tires
   - Second SC likely before end

3. **VSC vs Full SC:**
   - VSC: ~10-12s stop (vs 20-25s normal), pit if gap allows
   - Full SC: Field bunches, position matters more than gap

{sc_strategy}

### 4.4 Red Flag Strategy

- Free tire change opportunity
- Consider compound switch for restart
- Track evolution after red flag delay
- Cold tire/brake risks on restart

---

## 5. Think Out of the Box Strategies 🧠

**Unconventional but legal strategies that can change race outcomes:**

### 5.1 Alternative Strategic Options

{alternative_strategies}

### 5.2 Historical Creative Strategies

| Strategy | Example Race | Result |
|----------|--------------|--------|
| **Very early stop** | {early_stop_example} | Undercut entire field |
| **Super-extended stint** | {extended_stint_example} | One-stop vs two-stop |
| **Compound switch** | {compound_switch_example} | Better race pace |
| **Split strategy** | {split_strategy_example} | Cover scenarios |

### 5.3 Scenario Analysis

**"What If" Strategic Pivots:**

1. **SC in Lap 1-5**: Reset race, soft tires viable for longer
2. **Rain Threat at 30%**: Pre-position for intermediate crossover
3. **Top 3 pit together**: Consider overcut or mega-undercut
4. **Stuck in DRS train**: Early stop to find clean air

### 5.4 Reverse Strategy Analysis

What strategies would opponents fear most at {circuit_name}?

- Leader fears: {leader_fear}
- Midfield fears: {midfield_fear}
- Backmarker opportunity: {backmarker_opportunity}

---

## 6. Qualifying Strategy

### 6.1 Q1/Q2/Q3 Approach

- **Q2 Tire Choice for Top 10**: {q2_tire_recommendation}
- **Starting Compound Impact**: {start_compound_impact}
- **Track Evolution**: +{track_evolution_quali}s improvement per session

### 6.2 Grid Position Analysis

| Position | Typical Race Finish | Strategy Freedom |
|----------|---------------------|------------------|
| P1-P3 | P1-P5 | Standard optimal |
| P4-P10 | P3-P10 | Alternative viable |
| P11-P15 | P7-P15 | Free tire choice advantage |
| P16-P20 | P12-P20 | Aggressive strategies |

---

## 7. Historical Winning Strategies

### Recent Winners

| Year | Winner | Strategy | Key Factor |
|------|--------|----------|------------|
{historical_winners_table}

### Common Winning Patterns

{strategy_patterns}

### Circuit-Specific Trends

{circuit_specific_trends}

---

## 8. Key Strategic Considerations

### Do's ✅

1. {consideration_do_1}
2. {consideration_do_2}
3. {consideration_do_3}

### Don'ts ❌

1. {consideration_dont_1}
2. {consideration_dont_2}
3. {consideration_dont_3}

---

## 9. Weather Contingency

- **Rain Probability**: See weather_patterns.md
- **Intermediate Crossover**: Track temp below {crossover_temp}°C
- **Wet Race Impact**: See dedicated weather strategy section

---

## 10. Quick Reference Card

```
🏁 CIRCUIT: {circuit_name}
📍 TYPE: {circuit_type}
🔄 LAPS: {total_laps} @ {lap_length} km
⏱️ PIT LOSS: {pit_loss}s

OPTIMAL STRATEGIES:
├── 1-STOP: Lap {one_stop_window} ({one_stop_compounds})
├── 2-STOP: Laps {two_stop_windows} ({two_stop_compounds})
└── SC REACT: {sc_react_quick}

KEY METRICS:
├── Overtake Difficulty: {overtaking_difficulty}/10
├── Undercut Power: {undercut_power}/10
└── SC Probability: {sc_probability}%
```

---

*Generated from template. Data: OpenF1 API, FIA Regulations, Historical Analysis*
*Last updated: {generation_date}*
