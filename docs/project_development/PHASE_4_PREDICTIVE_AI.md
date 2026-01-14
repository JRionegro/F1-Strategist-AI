# Phase 4 - Predictive AI Roadmap (Incremental)

**Last Updated**: January 14, 2026  
**Status**: Started (zero-touch starter implemented)

---

## Goals

Build predictive capabilities that:

- Produce **quantified forecasts** (probabilities/intervals), not just rules.
- Work in **Simulation** first (repeatable), then in **Live** mode.
- Are testable end-to-end (data → features → model → inference → UI).

This plan assumes no predictive phase is complete yet.

---

## Current status (as of January 14, 2026)

### Implemented (zero-touch starter, Option B)

Implemented an isolated predictive package focused on **Option B: suggested pit window**. It is not imported by the Dash app or agents.

- New package: `src/predictive/`
  - `schemas.py`: strict dataset contract + label coherence validation
  - `features.py`: deterministic feature helpers
  - `labels.py`: label builder based on next pit lap (center) + configurable window
  - `dataset_builder.py`: builds a DataFrame with a fixed column set
- New tests: `tests/predictive/`
  - Contract test validates:
    - stable columns
    - determinism (same input -> same output)
    - label ranges are in the future and internally consistent
  - F541 lint test ensures no placeholder-free f-strings in `src/predictive/`

### Test result

- `python -m pytest -q tests/predictive` -> PASS

### Not implemented yet

- No training pipeline, no model artifact, no backtesting.
- No adapters from OpenF1/session objects.
- No UI integration.

---

## Scope: What counts as “Predictive”

A feature is considered predictive if it:

- Uses current + historical context to estimate a **future outcome**.
- Returns probabilities or distributions (e.g., $P(\text{pit in next 5 laps})$).
- Has a measurable target and can be backtested.

---

## Guiding principles

- **Start small**: ship a baseline model quickly, then improve.
- **No leakage**: features at time $t$ must not use future info.
- **Calibration matters**: probabilities must be meaningful.
- **Reproducibility**: deterministic dataset generation and fixed splits.

---

## Phase 4A — Prediction Targets + Data Contracts

### Objective
Define exactly what we predict, what inputs are allowed at inference time, and how the ground truth is built.

### One-time RAG bootstrap (simulation start)
- At the start of each simulation, run a **single RAG lookup** against `strategy.md` to collect the textual rules used for pit/no-pit decisions.
- Cache the result for the whole simulation; **no repeated RAG calls** during the run.
- Expected fields in the bootstrap payload (immutable for the run):
  - `pit_policy_notes`: general pit decision principles and thresholds.
  - `undercut_overcut_rules`: conditions where undercut/overcut is preferred.
  - `tire_compound_rules`: compound usage constraints and stint-length guidance.
  - `degradation_thresholds`: any numeric/qualitative wear cues that trigger a stop.
  - `safety_car_overrides`: SC/VSC-specific pit guidance.
  - `weather_overrides`: rain/temperature rules affecting pit timing.
  - `fuel_energy_notes`: any fuel/ERS considerations tied to pit timing.
- Store in a typed structure (e.g., `PitPolicyContext`) so predictive logic can reference it deterministically.
- If `strategy.md` is missing, log a warning and return an empty-but-well-formed structure.

### Deliverables
- `docs/project_development/PHASE_4_PREDICTIVE_AI.md` (this document) updated with final target definitions.
- A minimal schema for time-indexed “race state” records.

### Candidate prediction targets (MVP first)
1. **Pit stop probability**: $P(\text{pit in next } N \text{ laps})$ per driver.
2. **Pit window recommendation**: expected lap window (interval) per driver.
3. **Undercut success probability**: $P(\Delta\text{position} > 0)$ if pitting now.

Later targets (Phase 4C+)
- SC/VSC probability in next X minutes.
- Finish position distribution / points probability.
- Rain probability in next X minutes (requires reliable weather feed).

### Test plan (Phase 4A)
- **Unit tests**
  - Schema validation: required keys present, types correct.
  - No-leakage checks: ensure feature builder cannot access future laps.
- **Integration tests**
  - Generate dataset for one cached race and confirm row counts > 0.

### Acceptance criteria
- Each target has:
  - A precise definition.
  - An unambiguous ground-truth labeling method.
  - Clear allowed inputs at inference time.
- RAG bootstrap for `strategy.md` executes exactly once per simulation start, produces the typed `PitPolicyContext`, and is available to predictive components without additional RAG queries.

### Phase 4A implementation plan (updated)
1) **Define contracts**
  - Add `PitPolicyContext` schema with the fields above; ensure optional but present keys (empty lists/strings allowed).
  - Add `RaceStateRecord` minimal schema for inference-time inputs (lap, compound, stint age, gaps, SC/VSC flag, weather summary).
2) **Implement bootstrap**
  - Add a `bootstrap_pit_policy_context()` function that queries RAG once (filtering for `strategy.md`), normalizes text into the contract, and caches per simulation.
  - Wire it to the simulation start hook (before first predictive decision).
3) **Tests**
  - Unit: bootstrap returns well-formed defaults when `strategy.md` absent; deterministic output for a fixed fixture.
  - Integration: simulation start triggers exactly one RAG call; subsequent predictive calls use cached context.
4) **Acceptance check**
  - Run a dry simulation and confirm the pit policy context is populated and reused (no repeated RAG queries in logs).

---

## Phase 4B — Dataset Builder (Ground Truth + Features)

### Objective
Create a reproducible pipeline that converts cached races into supervised learning tables.

### Proposed structure
- `src/predictive/` (new package)
  - `dataset_builder.py` (race → rows)
  - `features.py` (feature functions)
  - `labels.py` (target labeling)
  - `schemas.py` (TypedDict / pydantic models)
- `data/processed/predictive/` (outputs)

### Feature set (MVP)
- Driver state: compound, stint age (laps), last pit lap.
- Pace proxies: last-lap time, rolling mean (last 3/5 laps).
- Gap/traffic: gap to car ahead/behind, position. Estimated position after pit.
- Track state: lap number, session time, SC/VSC flag (if available).

### Test plan (Phase 4B)
- **Unit tests**
  - Feature functions: deterministic outputs for fixed inputs.
  - Label functions: known pit events produce correct labels.
  - Ensure all features are numeric or categorical with explicit encoding.
- **Integration tests**
  - Build dataset for 1–2 races from `cache/` and persist to `data/processed/`.
  - Validate:
    - No NaNs in required columns (or controlled NaN policy).
    - Stable column set (contract) across races.

### Acceptance criteria
- Running the pipeline twice on the same input yields identical output (byte-for-byte or row-hash).
- Dataset contains at least one full race worth of samples.

---

## Phase 4C — Baseline Models + Backtesting Harness

### Objective
Train a simple baseline model and backtest it against historical races.

### Model choices (start simple)
- Pit probability: Logistic Regression / XGBoost (if allowed) / LightGBM.
- Pit window: Quantile Regression (or model predicted hazard over laps).

### Backtest harness (must-have)
- A replay loop that, for each time step, runs inference using only info available at that time.
- Metrics aggregated per race and overall.

### Metrics
- Classification: AUC, precision/recall at threshold, Brier score.
- Calibration: reliability plot buckets.
- Business metrics: “decision usefulness” proxies (e.g., top-k pit suggestions correctness).

### Test plan (Phase 4C)
- **Unit tests**
  - Training pipeline produces a model artifact.
  - Inference wrapper loads model and returns valid probability in [0, 1].
- **Integration tests**
  - Train on 1 season subset, evaluate on a held-out race.
  - Backtest runs end-to-end without exceptions.

### Acceptance criteria
- Baseline model beats a naive heuristic baseline (documented) on at least one metric.
- Backtest is reproducible with a fixed random seed.

---

## Phase 4D — Online Inference Integration (Simulation First)

### Objective
Integrate predictive outputs into the Dash UI and agent recommendations.

### Integration points
- Simulation tick loop: compute features from current state and call predictor.
- AI assistant: expose predictions as structured context (not just text).

### UI outputs (MVP)
- “Pit probability next 5 laps” per focused driver.
- “Suggested pit window” with confidence.

### Test plan (Phase 4D)
- **Unit tests**
  - Predictor service returns quickly (< 100ms for one driver on CPU; configurable).
- **Integration tests**
  - Dash callbacks request prediction and render without blocking.
  - “No model available” fallback path is graceful.

### Acceptance criteria
- Predictive panel updates during simulation without UI freezes.
- Clear fallbacks if model artifacts are missing.

---

## Phase 4E — Live Mode + Monitoring + Drift

### Objective
Make predictions stable in live conditions and monitor performance.

### Monitoring
- Log predictions + feature summaries to a local store.
- Track:
  - Input distribution drift.
  - Prediction distribution drift.
  - Latency.

### Test plan (Phase 4E)
- **Integration tests**
  - Live-mode inference works with partial/missing data.
- **Regression tests**
  - Fixed snapshots of live data produce consistent feature vectors.

### Acceptance criteria
- Live inference does not crash on missing fields.
- Monitoring artifacts are written and rotated.

---

## Phase 4F — Explainability + Human Feedback Loop

### Objective
Add “why” explanations and capture user feedback to improve the system.

### Deliverables
- Explainability summaries:
  - Top features contributing to the prediction.
  - Counterfactual hints (e.g., “If pace drops by X, pit probability increases by Y”).
- Feedback capture:
  - User accepted/rejected recommendation.

### Test plan (Phase 4F)
- **Unit tests**
  - Explanation generator returns stable keys/fields.
- **Integration tests**
  - Feedback events persist correctly.

---

## Proposed test tooling

- Use existing `pytest`.
- Add new tests under `tests/predictive/`.
- Add fixture data under `tests/fixtures/predictive/`.
- Keep tests fast; heavy training should be mocked or use tiny subsets.

---

## Implementation order (recommended)

1. 4A: Targets + contracts
2. 4B: Dataset builder
3. 4C: Baseline model + backtest
4. 4D: Simulation integration
5. 4E: Live integration + monitoring
6. 4F: Explainability + feedback

---

## Notes / Risks

- Weather prediction quality depends on availability and reliability of weather inputs.
- SC/VSC prediction requires robust incident/track-status signals.
- Avoid heavy model training inside the app process; keep training offline.
