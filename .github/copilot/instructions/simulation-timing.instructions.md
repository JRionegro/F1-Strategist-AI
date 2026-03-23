---
applyTo: "app_dash.py,src/session/**,src/dashboards_dash/race_control_dashboard.py,src/data/**,tests/test_simulation_*"
---

# Simulation Timing Guardrails

Use this instruction set for any change that touches simulation timing, session clocks,
track map interpolation, race control filtering, AI race snapshot, cache offsets, or MCP
time semantics.

## Invariants (do not break)

- The simulation controller clock is the source of truth for elapsed race time.
- Track map may use rebased/interpolated timelines, but race control and AI status
  must not double-apply formation offsets when filtering OpenF1 timestamped events.
- If `simulation_controller.start_time` is already shifted to race start, race control
  filters must use raw controller elapsed seconds.
- Safety car and VSC status must appear in race control and AI context at the same lap/time
  window shown by race playback behavior.
- Any offset introduced in one dashboard path must be reviewed in all time-dependent paths:
  race overview, track map, race control, telemetry, weather, and AI snapshot.

## Required update checklist

1. Locate all consumers of simulation elapsed time in app and dashboard callbacks.
2. Verify whether each consumer requires raw elapsed time or transformed timeline time.
3. Never add `formation_offset_seconds` in race control if controller start time already encodes it.
4. Keep timing logic centralized in helper utilities and avoid duplicated math in callbacks.
5. If lap timing normalization changes, validate effects on race control and AI snapshot.
6. Confirm no fallback path bypasses the agreed timing reference.

## Mandatory regression tests before merge

Run all of these tests when changing timing logic:

```bash
python -m pytest -q tests/test_simulation_controller_qatar_regression.py tests/test_simulation_time_alignment.py
```

If any fail, do not merge.

## High-risk files

- app_dash.py
- src/session/simulation_controller.py
- src/dashboards_dash/race_control_dashboard.py
- src/utils/simulation_time_alignment.py

## Anti-patterns

- Applying a time rebase only for one dashboard and assuming others remain correct.
- Adding formation offset twice (once in controller start time and again in race control/AI filters).
- Spreading offset math across callbacks instead of shared utility helpers.
- Adding new timing behavior without adding or updating regression tests.

## MCP and cache notes

- Treat MCP outputs and cached frames as data sources with potentially different time bases.
- Normalize and align as close as possible to the consumer boundary.
- Log timing offsets explicitly when applied so diagnostics can be traced in runtime logs.
