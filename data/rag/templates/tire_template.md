---
category: tire
template: true
variables: [circuit_name, year]
---

# {circuit_name} - Complete Tire Analysis ({year})

## Circuit Tire Demands

| Metric | Rating | Notes |
|--------|--------|-------|
| **Overall Tire Stress** | {stress_level}/10 | {stress_notes} |
| **Front Tire Stress** | {front_stress}/10 | {front_notes} |
| **Rear Tire Stress** | {rear_stress}/10 | {rear_notes} |
| **Lateral Load** | {lateral_load}/10 | High-speed corners |
| **Traction Demand** | {traction_demand}/10 | Acceleration zones |
| **Braking Severity** | {braking_severity}/10 | Heavy braking zones |

## Limitation Type

- **Primary Limitation**: {limitation_type} (Front/Rear)
- **Degradation Mode**: {deg_mode} (Thermal/Wear/Graining)

---

## 1. Compound Allocation ({year})

### 1.1 Pirelli Selection

| Compound | Pirelli Name | Color | Characteristics |
|----------|--------------|-------|-----------------|
| SOFT | {soft_name} | 🔴 Red | {soft_characteristics} |
| MEDIUM | {medium_name} | 🟡 Yellow | {medium_characteristics} |
| HARD | {hard_name} | ⚪ White | {hard_characteristics} |

### 1.2 Compound Selection Logic

{compound_selection_reasoning}

---

## 2. Compound Performance Analysis

### 2.1 Operating Windows

| Compound | Optimal Track Temp | Warm-up Laps | Peak Performance |
|----------|-------------------|--------------|------------------|
| SOFT | {soft_temp_window}°C | {soft_warmup} | Lap {soft_peak} |
| MEDIUM | {med_temp_window}°C | {med_warmup} | Lap {med_peak} |
| HARD | {hard_temp_window}°C | {hard_warmup} | Lap {hard_peak} |

### 2.2 Degradation Rates

| Compound | Deg/Lap (manage) | Deg/Lap (push) | Cliff Point |
|----------|------------------|----------------|-------------|
| SOFT | {soft_deg_avg}s | {soft_deg_push}s | ~{soft_cliff} laps |
| MEDIUM | {med_deg_avg}s | {med_deg_push}s | ~{med_cliff} laps |
| HARD | {hard_deg_avg}s | {hard_deg_push}s | ~{hard_cliff} laps |

### 2.3 Pace Delta (New Tires)

| Comparison | Delta |
|------------|-------|
| SOFT vs MEDIUM | {soft_med_delta}s |
| MEDIUM vs HARD | {med_hard_delta}s |
| SOFT vs HARD | {soft_hard_delta}s |

---

## 3. Maximum Stint Lengths

### 3.1 Expected Stint Duration

| Compound | Conservative | Normal | Aggressive |
|----------|--------------|--------|------------|
| SOFT | {soft_max_cons} laps | {soft_max_norm} laps | {soft_max_agg} laps |
| MEDIUM | {med_max_cons} laps | {med_max_norm} laps | {med_max_agg} laps |
| HARD | {hard_max_cons} laps | {hard_max_norm} laps | {hard_max_agg} laps |

### 3.2 Stint Length Factors

- **Fuel Load**: Heavy car = +{fuel_deg_impact}% degradation
- **Track Position**: Clean air = better tire life
- **Driving Style**: Aggressive = shorter stints
- **Track Evolution**: More rubber = longer stints possible

---

## 4. Key Corners for Degradation

### 4.1 High Stress Corners

| Corner | Type | Tire Impact | Management Tip |
|--------|------|-------------|----------------|
{high_stress_corners_table}

### 4.2 Traction Zones

{traction_zones_description}

### 4.3 Critical Braking Zones

{braking_zones_description}

---

## 5. Graining vs Thermal Degradation

### 5.1 Graining Risk

- **Risk Level**: {graining_risk}/10
- **Conditions**: {graining_conditions}
- **Most Affected Compound**: {graining_compound}
- **Recovery**: {graining_recovery}
- **Mitigation**: {graining_mitigation}

**Signs of Graining:**

1. Initial lap time loss (0.5-1.5s)
2. Lack of front/rear grip
3. Typically occurs in first 5-10 laps
4. Can "work through" graining with consistent pace

### 5.2 Thermal Degradation

- **Risk Level**: {thermal_risk}/10
- **Conditions**: {thermal_conditions}
- **Most Affected Compound**: {thermal_compound}
- **Prevention**: {thermal_mitigation}

**Signs of Thermal Deg:**

1. Progressive lap time loss
2. Blistering visible on tire surface
3. Occurs throughout stint
4. Cannot recover - must pit

### 5.3 Wear Degradation

- **Risk Level**: {wear_risk}/10
- **Conditions**: High abrasion circuits
- **Characteristics**: Linear time loss per lap

---

## 6. Tire Management Strategies

### 6.1 Lift and Coast Zones

{lift_coast_zones}

### 6.2 Management Techniques

| Technique | Benefit | Time Cost |
|-----------|---------|-----------|
| **Lift and coast** | Save ~{lift_coast_save}% deg | +{lift_coast_time}s/lap |
| **Smooth inputs** | Save ~{smooth_save}% deg | Minimal |
| **Avoid kerbs** | Save ~{kerb_save}% deg | +{kerb_time}s/lap |
| **Trail braking** | Better balance | Skill-dependent |

### 6.3 When to Push vs Manage

**Push (attack mode):**

- Fresh tires (first 3-5 laps)
- After pit stop, before traffic
- Final stint defense/attack
- Undercut/overcut execution

**Manage (preservation mode):**

- Mid-stint cruise
- Clear track position secured
- Waiting for pit window
- Nursing tires to end of stint

---

## 7. Fuel Load Impact

### 7.1 Degradation by Fuel Level

| Fuel Level | Deg Impact | Notes |
|------------|------------|-------|
| Full (Race Start) | +{fuel_full_impact}% | Heavy car, more sliding |
| 75% | +{fuel_75_impact}% | Still significant |
| 50% | Baseline | Reference point |
| 25% | -{fuel_25_impact}% | Lighter, less stress |
| Light (End) | -{fuel_light_impact}% | Optimal tire life |

### 7.2 Fuel Burn Effect

- Fuel consumption: ~{fuel_consumption} kg/lap
- Weight reduction: ~{weight_per_lap} kg/lap  
- Lap time gain: ~{lap_time_per_kg}s per kg lighter

---

## 8. Historical Stint Data

### 8.1 Winning Strategies

| Year | Winner | Strategy | Compounds | Stint Lengths |
|------|--------|----------|-----------|---------------|
{historical_stints_table}

### 8.2 Average Stint Lengths

{avg_stint_analysis}

### 8.3 Notable Tire Strategies

{notable_tire_strategies}

---

## 9. Temperature Sensitivity

### 9.1 Track Temperature Impact

| Track Temp | Soft Life | Medium Life | Hard Life |
|------------|-----------|-------------|-----------|
| 25°C | {soft_25} | {med_25} | {hard_25} |
| 35°C | {soft_35} | {med_35} | {hard_35} |
| 45°C | {soft_45} | {med_45} | {hard_45} |
| 55°C | {soft_55} | {med_55} | {hard_55} |

### 9.2 Temperature Trends During Race

{temp_trend_impact}

---

## 10. Qualifying vs Race Considerations

### 10.1 Qualifying Strategy

{quali_recommendation}

### 10.2 Q2 Tire Decision (Top 10)

| Scenario | Recommendation |
|----------|----------------|
| Hot track (>40°C) | MEDIUM - softs won't last |
| Cool track (<30°C) | SOFT - pace advantage |
| Rain possible | SOFT - maximize dry laps |
| Starting P8-10 | MEDIUM - strategy flexibility |

### 10.3 Race Start Recommendations

{race_start_recommendation}

---

## 11. Think Out of the Box 🧠

### 11.1 Unconventional Tire Strategies

{unconventional_tire_strategies}

### 11.2 Risk vs Reward Analysis

| Strategy | Risk Level | Potential Reward |
|----------|------------|------------------|
| Super long first stint | Medium | Undercut protection |
| SOFT-SOFT-SOFT | High | Track position if SC |
| Starting on HARD | Medium | Ultimate strategy freedom |
| Extreme tire saving | Low | Extend 1-stop range |

### 11.3 Counter-Strategies

When opponents choose standard strategy, consider:

- {counter_strategy_1}
- {counter_strategy_2}
- {counter_strategy_3}

---

## 12. Quick Reference Card

```
🛞 TIRE GUIDE: {circuit_name} ({year})

COMPOUNDS:
├── SOFT ({soft_name}): ~{soft_max_norm} laps, {soft_deg_avg}s/lap deg
├── MEDIUM ({medium_name}): ~{med_max_norm} laps, {med_deg_avg}s/lap deg
└── HARD ({hard_name}): ~{hard_max_norm} laps, {hard_deg_avg}s/lap deg

PACE DELTA (new tires):
├── SOFT vs MED: {soft_med_delta}s
├── MED vs HARD: {med_hard_delta}s
└── SOFT vs HARD: {soft_hard_delta}s

CIRCUIT STRESS:
├── Front: {front_stress}/10
├── Rear: {rear_stress}/10
└── Primary Limit: {limitation_type}

DEG MODE: {deg_mode}
├── Graining Risk: {graining_risk}/10
├── Thermal Risk: {thermal_risk}/10
└── Wear Risk: {wear_risk}/10

MANAGEMENT SAVINGS:
└── Lift & Coast: ~{lift_coast_save}% deg saved
```

---

*Generated from template. Data: OpenF1 API, Pirelli Data, Historical Analysis*
*Last updated: {generation_date}*
