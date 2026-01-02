# Performance Analysis: {{circuit_name}} - {{year}}

## Executive Summary

Circuit: {{circuit_name}} ({{circuit_type}})
Analysis Date: {{generation_date}}
Data Sources: OpenF1 API, Historical Telemetry

---

## 1. LAP TIME ANALYSIS

### 1.1 Benchmark Times
- **Theoretical Best**: {{theoretical_best}}s
- **Practical Race Pace**: {{practical_race_pace}}s
- **Typical Qualifying Spread**: {{quali_spread}}s (P1-P10)
- **Midfield Variance**: {{midfield_variance}}s

### 1.2 Session Evolution
| Session     | Expected Delta (vs FP1) |
|-------------|-------------------------|
| FP1         | Baseline               |
| FP2         | {{fp2_improvement}}s   |
| FP3         | {{fp3_improvement}}s   |
| Qualifying  | {{quali_improvement}}s |
| Race        | +{{race_fuel_delta}}s (fuel load) |

### 1.3 Lap Time Degradation Curve
- **Soft Compound**: {{soft_deg}}s/lap degradation
- **Medium Compound**: {{medium_deg}}s/lap degradation
- **Hard Compound**: {{hard_deg}}s/lap degradation
- **Cliff Point** (Soft): Lap {{soft_cliff}}
- **Cliff Point** (Medium): Lap {{medium_cliff}}

---

## 2. SECTOR BREAKDOWN

### 2.1 Sector Characteristics
| Sector | Length  | Type          | Key Corners      | Typical Time |
|--------|---------|---------------|------------------|--------------|
| S1     | {{s1_length}}m | {{s1_type}} | {{s1_corners}} | {{s1_time}}s |
| S2     | {{s2_length}}m | {{s2_type}} | {{s2_corners}} | {{s2_time}}s |
| S3     | {{s3_length}}m | {{s3_type}} | {{s3_corners}} | {{s3_time}}s |

### 2.2 Performance Gain Opportunities
- **S1 Key**: {{s1_key_factor}}
- **S2 Key**: {{s2_key_factor}}
- **S3 Key**: {{s3_key_factor}}

### 2.3 Team Strengths by Sector
Based on historical data:
- **S1 Dominant Teams**: {{s1_dominant_teams}}
- **S2 Dominant Teams**: {{s2_dominant_teams}}
- **S3 Dominant Teams**: {{s3_dominant_teams}}

---

## 3. SPEED TRAP ANALYSIS

### 3.1 Speed Trap Locations
- **Main Speed Trap**: {{main_trap_location}}
- **Intermediate 1**: {{int1_location}}
- **Intermediate 2**: {{int2_location}}

### 3.2 Expected Speeds
- **Maximum Recorded**: {{max_speed}} km/h
- **Average Top Speed**: {{avg_top_speed}} km/h
- **Low Downforce Gain**: +{{low_df_speed}} km/h
- **High Downforce Cost**: -{{high_df_speed}} km/h

### 3.3 Team Power Rankings
Historical speed comparison:
{{team_speed_ranking}}

---

## 4. UNDERPERFORMANCE DETECTION

### 4.1 Warning Thresholds
| Metric                    | Yellow Flag (Watch) | Red Flag (Concern) |
|---------------------------|---------------------|---------------------|
| Lap Time vs Teammate      | >{{yellow_teammate}}s | >{{red_teammate}}s |
| Sector Variance           | >{{yellow_sector}}%   | >{{red_sector}}%   |
| Speed Trap Deficit        | >{{yellow_speed}} km/h | >{{red_speed}} km/h |
| Tire Degradation Rate     | >{{yellow_deg}}% avg  | >{{red_deg}}% avg  |

### 4.2 Common Underperformance Causes
At {{circuit_name}}:
1. **Setup Issues**: {{setup_issues}}
2. **Tire Management**: {{tire_management_issues}}
3. **Traffic Impact**: {{traffic_impact}}
4. **Power Unit Concerns**: {{pu_concerns}}

### 4.3 Recovery Strategies
- **Quick Fix (1-3 laps)**: {{quick_fix}}
- **Medium Term (pit window)**: {{medium_fix}}
- **Strategic Adaptation**: {{strategic_fix}}

---

## 5. COMPARATIVE ANALYSIS

### 5.1 Teammate Delta Interpretation
| Delta Range | Interpretation | Action Required |
|-------------|----------------|-----------------|
| 0-0.2s      | Normal variance | Monitor |
| 0.2-0.5s    | Setup or driving issue | Review data |
| 0.5-1.0s    | Significant problem | Strategic intervention |
| >1.0s       | Critical issue | Consider change |

### 5.2 Grid Position Impact
- **P1-P3 Advantage**: {{top3_advantage}}
- **P4-P10 Density**: {{midfield_density}}
- **P10+ Passing Difficulty**: {{backfield_passing}}

---

## 6. HISTORICAL PERFORMANCE PATTERNS

### 6.1 Circuit Specialists
Drivers with exceptional records:
{{circuit_specialists}}

### 6.2 Year-over-Year Improvements
- **2023 vs 2022**: {{yoy_2023}}s improvement
- **Regulation Impact**: {{reg_impact}}
- **Track Evolution**: {{track_evolution_impact}}

### 6.3 Weather Sensitivity
- **Dry-Wet Delta**: {{dry_wet_delta}}s
- **Temperature Sensitivity**: {{temp_sensitivity}}s per 5°C
- **Wind Impact**: {{wind_impact}}

---

## 7. THINK OUT OF THE BOX - PERFORMANCE

### 7.1 Unconventional Setups
- **Extreme Low Downforce**: {{extreme_low_df}}
- **Asymmetric Setup**: {{asymmetric_setup}}
- **Tire Pressure Gamble**: {{pressure_gamble}}

### 7.2 Psychological Performance Factors
- **Home Race Boost**: {{home_advantage}}
- **Championship Pressure Impact**: {{pressure_impact}}
- **Wet Weather Specialists**: {{wet_specialists}}

### 7.3 Data Mining Insights
Hidden patterns from historical analysis:
{{data_mining_insights}}

---

## 8. REAL-TIME MONITORING CHECKLIST

### Pre-Session
- [ ] Compare practice pace vs expectations
- [ ] Verify speed trap data consistency
- [ ] Check tire degradation early indicators

### During Session
- [ ] Monitor sector-by-sector evolution
- [ ] Track teammate deltas
- [ ] Alert on threshold breaches

### Post-Session
- [ ] Compile performance summary
- [ ] Identify optimization areas
- [ ] Update predictions for next session

---

*Document generated: {{generation_date}}*
*Data source: OpenF1 API + Historical Analysis*
