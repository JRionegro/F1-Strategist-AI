# Race Control Analysis: {{circuit_name}} - {{year}}

## Executive Summary

Circuit: {{circuit_name}} ({{circuit_type}})
Analysis Date: {{generation_date}}
Safety Rating: {{safety_rating}}/10
Historical Incident Rate: {{incident_rate}}%

---

## 1. SAFETY CAR PROBABILITY

### 1.1 Historical Statistics
- **SC Probability**: {{sc_probability}}%
- **VSC Probability**: {{vsc_probability}}%
- **Red Flag Probability**: {{red_flag_probability}}%
- **Average SC Laps**: {{avg_sc_laps}} laps
- **Most Common SC Window**: Laps {{sc_window_start}}-{{sc_window_end}}

### 1.2 SC Trigger Zones
| Zone | Location | Risk Level | Common Cause |
|------|----------|------------|--------------|
| Z1   | {{zone1_location}} | {{zone1_risk}}/10 | {{zone1_cause}} |
| Z2   | {{zone2_location}} | {{zone2_risk}}/10 | {{zone2_cause}} |
| Z3   | {{zone3_location}} | {{zone3_risk}}/10 | {{zone3_cause}} |
| Z4   | {{zone4_location}} | {{zone4_risk}}/10 | {{zone4_cause}} |

### 1.3 Lap 1 Incident Analysis
- **T1 Collision Risk**: {{t1_risk}}/10
- **Historical Lap 1 SCs**: {{lap1_sc_count}} in last 5 years
- **Typical Resolution**: {{lap1_resolution}} laps

---

## 2. FLAG PROTOCOLS

### 2.1 Yellow Flag Sectors
Permanent yellow risk areas:
{{yellow_flag_zones}}

### 2.2 Double Yellow Patterns
- **Average Duration**: {{double_yellow_duration}} laps
- **Recovery Protocol**: {{recovery_protocol}}
- **Typical Cause**: {{double_yellow_cause}}

### 2.3 Blue Flag Zones
Critical lapping zones:
- **Primary**: {{blue_primary}}
- **Secondary**: {{blue_secondary}}
- **Average Backmarker Delay**: {{backmarker_delay}}s

---

## 3. VSC (VIRTUAL SAFETY CAR)

### 3.1 VSC Deployment Criteria
At {{circuit_name}}:
- **Light Debris**: {{light_debris_response}}
- **Car Recovery**: {{car_recovery_response}}
- **Medical Response**: {{medical_response}}

### 3.2 VSC Pit Window Benefit
- **Normal Pit Loss**: {{pit_loss}}s
- **VSC Pit Loss**: {{vsc_pit_loss}}s
- **Net Advantage**: {{vsc_pit_advantage}}s

### 3.3 Historical VSC Timing
| Year | Lap | Duration | Trigger |
|------|-----|----------|---------|
{{vsc_history}}

---

## 4. FULL SAFETY CAR

### 4.1 SC Timing Strategies
- **Early SC (Lap 1-15)**: {{early_sc_strategy}}
- **Mid-Race SC (Lap 15-40)**: {{mid_sc_strategy}}
- **Late SC (Last 15 laps)**: {{late_sc_strategy}}

### 4.2 SC Pit Strategy Impact
| Current Position | Recommended Action |
|------------------|-------------------|
| P1-P3            | {{top3_sc_strategy}} |
| P4-P10           | {{midfield_sc_strategy}} |
| P10+             | {{backfield_sc_strategy}} |

### 4.3 SC Queue Positioning
- **Optimal Gap Behind SC**: {{optimal_sc_gap}}m
- **Restart Preparation Lap**: {{restart_prep_lap}}
- **Tire Warm-up Required**: {{restart_warmup}} corners

---

## 5. RED FLAG SCENARIOS

### 5.1 Red Flag Triggers
At {{circuit_name}}:
1. **Weather**: {{weather_red_flag}}
2. **Major Incident**: {{incident_red_flag}}
3. **Track Damage**: {{track_damage_red_flag}}
4. **Barriers**: {{barrier_red_flag}}

### 5.2 Red Flag Tire Rules
- **Free Tire Change**: {{free_tire_change}}
- **Optimal Compound Post-Red**: {{post_red_compound}}
- **Warm-up Strategy**: {{post_red_warmup}}

### 5.3 Historical Red Flags
{{red_flag_history}}

---

## 6. TRACK LIMITS

### 6.1 Monitored Corners
| Corner | Location | Penalty Type | Tolerance |
|--------|----------|--------------|-----------|
{{track_limits_table}}

### 6.2 Track Limit Enforcement
- **Warning Threshold**: {{warning_threshold}} violations
- **Lap Deletion Threshold**: {{deletion_threshold}} violations
- **Time Penalty**: {{time_penalty_threshold}} violations ({{penalty_time}}s)

### 6.3 Corner-Specific Guidance
{{corner_guidance}}

---

## 7. PENALTIES AND INVESTIGATIONS

### 7.1 Common Penalties at {{circuit_name}}
| Infraction | Typical Penalty | Frequency |
|------------|-----------------|-----------|
| Track Limits | {{track_limits_penalty}} | {{track_limits_freq}} |
| Unsafe Release | {{unsafe_release_penalty}} | {{unsafe_release_freq}} |
| Forcing Off | {{forcing_penalty}} | {{forcing_freq}} |
| Speeding in Pit | {{speeding_penalty}} | {{speeding_freq}} |

### 7.2 Steward Tendencies
- **Investigation Speed**: {{investigation_speed}}
- **Penalty Consistency**: {{penalty_consistency}}/10
- **Racing Incident Tolerance**: {{racing_tolerance}}/10

### 7.3 Strategic Penalty Management
- **5s Penalty Gap Needed**: {{gap_5s}}s at pit stop
- **10s Penalty Option**: {{penalty_10s_strategy}}
- **Drive-Through Alternative**: {{dt_strategy}}

---

## 8. PIT LANE REGULATIONS

### 8.1 Pit Lane Details
- **Speed Limit**: {{pit_speed}} km/h
- **Entry Type**: {{pit_entry_type}}
- **Exit Type**: {{pit_exit_type}}
- **White Line Crossing**: {{white_line_rule}}

### 8.2 Unsafe Release Criteria
- **Contact Threshold**: {{contact_threshold}}
- **Near Miss Definition**: {{near_miss_def}}
- **Historical Penalties**: {{unsafe_release_history}}

### 8.3 Pit Lane Closure
Automatic closure triggers:
{{pit_closure_triggers}}

---

## 9. THINK OUT OF THE BOX - RACE CONTROL

### 9.1 Exploiting VSC
- **Preemptive Pit Call**: {{vsc_preemptive}}
- **Delta Manipulation**: {{vsc_delta}}
- **Double Stack VSC**: {{vsc_double_stack}}

### 9.2 SC Restart Tactics
- **Surprise Restart**: {{surprise_restart}}
- **Slipstream Positioning**: {{slipstream_position}}
- **Defensive Line Choice**: {{defensive_restart}}

### 9.3 Penalty-Free Limit Pushing
- **Rotation Limit Strategy**: {{rotation_strategy}}
- **Quali vs Race Differences**: {{quali_race_diff}}
- **Last Lap Aggression**: {{last_lap_limits}}

### 9.4 Historical Controversial Decisions
Key precedents at this circuit:
{{controversial_decisions}}

---

## 10. REAL-TIME MONITORING CHECKLIST

### Pre-Race
- [ ] Review track limit cameras
- [ ] Note current steward panel
- [ ] Check weather radar for red flag potential

### During Race
- [ ] Monitor incident zones
- [ ] Track track limit warnings
- [ ] Calculate SC probability windows

### Post-Incident
- [ ] Evaluate penalty impact
- [ ] Adjust strategy for investigations
- [ ] Anticipate future enforcement

---

*Document generated: {{generation_date}}*
*Data source: OpenF1 API + FIA Race Director Guidelines*
