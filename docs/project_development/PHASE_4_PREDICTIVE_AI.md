# Phase 4 - Predictive AI Roadmap (Incremental)

**Last Updated**: January 14, 2026  
**Status**: Phase 4A–4C implemented offline (baseline model + backtest)

---

## Goals

Build predictive capabilities that:

- Produce **quantified forecasts** (probabilities/intervals), not just rules.
- Work in **Simulation** first (repeatable), then in **Live** mode.
- Are testable end-to-end (data → features → model → inference → UI).

This plan assumes no predictive phase is complete yet.

---

## Current status (as of January 14, 2026)

### Implemented (Phase 4A–4C groundwork)

- Pit policy bootstrap (Phase 4A): `bootstrap_pit_policy_context()` runs a single RAG lookup for `strategy.md`,
  returns a typed `PitPolicyContext`, and falls back to an empty-but-valid context when RAG is missing. Tested with
  `tests/predictive/test_bootstrap.py`.
- Option B pit-window dataset builder (Phase 4B): from lap/pit frames → deterministic supervised table via
  `build_pit_window_dataset_from_frames()`, including rolling lap-time feature, stint lap, and pit window labels.
  Sorted persistence for reproducibility. Tested with `tests/predictive/test_dataset_builder_from_frames.py` and
  `tests/predictive/test_dataset_contract.py`.
- Contracts and helpers: `schemas.py` (PitPolicyContext, PitWindowRow), `features.py`, `labels.py`,
  `dataset_builder.py`, `bootstrap.py`.
- Lint guard: `tests/predictive/test_flake8_f541.py` prevents placeholder-free f-strings.
- Baseline model + backtest (Phase 4C): logistic regression baseline (`PitStopBaselineModel`) with deterministic
  time-ordered split and metrics (AUC, Brier). Backtest harness `backtest_pit_baseline()` and deterministic split
  `time_order_split()`. Tests: `tests/predictive/test_modeling.py`, `tests/predictive/test_backtesting.py`.

### Test result

- `python -m pytest -q tests/predictive` → PASS (unit + contract + lint)

### Not implemented yet

- No persisted model artifact export/loading; training is in-memory only.
- No adapters from OpenF1/session objects.
- No UI integration; predictive package remains offline-only.

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

### Phase 4A — Prediction Targets + Data Contracts

**Status: Implemented (bootstrap + contracts in code, offline)**

### Objective
Define exactly what we predict, what inputs are allowed at inference time, and how the ground truth is built.

### One-time RAG bootstrap (simulation start)
- At the start of each simulation, run a **single RAG lookup** against `strategy.md` to collect the textual rules used for pit/no-pit decisions.
- Cache the result for the whole simulation; **no repeated RAG calls** during the run. Implemented via
  `bootstrap_pit_policy_context()` which falls back gracefully if the file or context is missing.
- Expected fields in the bootstrap payload (immutable for the run):
  - `pit_policy_notes`: general pit decision principles and thresholds.
  - `undercut_overcut_rules`: conditions where undercut/overcut is preferred.
  - `tire_compound_rules`: compound usage constraints and stint-length guidance.
  - `degradation_thresholds`: any numeric/qualitative wear cues that trigger a stop.
  - `safety_car_overrides`: SC/VSC-specific pit guidance.
  - `weather_overrides`: rain/temperature rules affecting pit timing.
  - `fuel_energy_notes`: any fuel/ERS considerations tied to pit timing.
- Store in a typed structure (`PitPolicyContext`) so predictive logic can reference it deterministically. Currently,
  the bootstrap populates `pit_policy_notes` and `source`; other fields remain empty placeholders until richer
  parsing is added.
- If `strategy.md` is missing, log a warning and return an empty-but-well-formed structure (implemented).

### Deliverables
- `docs/project_development/PHASE_4_PREDICTIVE_AI.md` (this document) updated with final target definitions.
- A minimal schema for time-indexed “race state” records (`RaceStateRecord` in code).

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

### Phase 4A implementation plan (status)
1) **Define contracts** — DONE
  - `PitPolicyContext` schema with the fields above; keys exist even when empty.
  - `RaceStateRecord` minimal schema for inference-time inputs (lap, compound, stint age, gaps, SC/VSC flag, weather summary).
2) **Implement bootstrap** — DONE (offline)
  - `bootstrap_pit_policy_context()` queries RAG once for `strategy.md`, normalizes text into the contract, and returns cached data to callers.
  - Not yet wired into simulation start; to be integrated when predictive loop is added.
3) **Tests** — DONE
  - Unit: bootstrap returns well-formed defaults when `strategy.md` absent; deterministic for a fixed fixture.
  - Integration with simulation pending wiring.
4) **Acceptance check** — PENDING
  - Wire into a dry simulation and confirm the pit policy context is populated and reused (no repeated RAG queries in logs).

---

## Phase 4B — Dataset Builder (Ground Truth + Features)

**Status: Implemented (offline, deterministic tables)**

### Objective
Create a reproducible pipeline that converts cached races into supervised learning tables.

### Implemented structure
- `src/predictive/`
  - `dataset_builder.py` (lap/pit frames → supervised rows; persistence sorted for determinism)
  - `features.py` (rolling mean, stint lap helpers)
  - `labels.py` (pit window label builder)
  - `schemas.py` (pydantic models / contracts)
  - `bootstrap.py` (pit policy bootstrap)
- `data/processed/predictive/` (outputs, created on persist)

### Feature set (MVP, implemented)
- Driver state: compound, stint age (laps via `compute_stint_lap`), last pit lap.
- Pace proxies: last-lap time, rolling mean (configurable window, default 3).
- Gap/traffic: gap to car ahead/behind, position.
- Track state: lap number. (SC/VSC hooks reserved in `RaceStateRecord` but not yet wired.)

### Test plan (Phase 4B)
- **Unit tests** — DONE
  - Feature functions deterministic; labels coherent (see `tests/predictive/test_dataset_contract.py`).
- **Integration-style tests** — DONE (offline frames fixture)
  - `tests/predictive/test_dataset_builder_from_frames.py` builds twice to assert determinism, contract, and persistence.
  - Core identifiers non-null; rolling window configurable.
- **Pending**
  - Full-race integration from cached data.

### Acceptance criteria
- Running the pipeline twice on the same input yields identical output (met in tests with deterministic frames).
- Dataset contains at least one full race worth of samples (pending full-race integration).

---

## Phase 4C — Baseline Models + Backtesting Harness

**Status: Implemented (offline baseline + deterministic backtest)**

### Objective
Train a simple baseline model and backtest it against historical races.

### Implemented baseline/backtest
- Model: logistic regression pipeline (`PitStopBaselineModel`) over the pit-window dataset features (stint lap,
  lap times, gaps, position). Requires both positive/negative labels to fit.
- Backtest: deterministic time-ordered split (`time_order_split`) to avoid leakage; metrics: AUC (if computable),
  Brier score, positive rate, train/test counts. Helper `backtest_pit_baseline()` returns model + metrics object.
- Tests: `tests/predictive/test_modeling.py`, `tests/predictive/test_backtesting.py` cover fitting, probabilities,
  deterministic splits, and metric sanity.

### Metrics
- Classification: AUC (None when labels are single-class in test split).
- Calibration: Brier score (always computed).
- Quick sanity: positive rate in test split for monitoring class balance.

### Test plan (Phase 4C)
- **Unit tests** — DONE
  - Model fits and returns probabilities in [0, 1].
  - Enforces presence of both classes before training.
- **Integration-style tests** — DONE (synthetic fixtures)
  - Deterministic time-ordered split.
  - Backtest runs end-to-end and produces metrics.

### Acceptance criteria
- Backtest reproducible with deterministic split (met).
- Metrics surface even on small fixtures; AUC is optional when only one class in test split.

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
