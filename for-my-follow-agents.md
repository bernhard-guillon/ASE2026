# Handoff for Follow-Up Agents: Game-Movement Model Build

## Mission
Build a **modular two-model system** to replace the current hard-to-train single-model gameplay approach.

Goal: make training simpler, improve reliability, and prove model-to-model signaling/feedback in the emulator.

---

## Target Architecture (What to Build)

### Model A: Physics Model (Ball + Walls)
- Grid: `20x20`
- Visual symbols in frame:
  - walls: `#`
  - ball: `o`
- Dynamics:
  - ball moves at constant speed: **1 cell per tick**
  - bounces correctly on walls (reflection behavior)
- Inputs:
  - start position (initial state input)
  - `stop` bit (from Model B)
- Outputs:
  - next state/frame data
  - `hit_wall` pulse bit = `1` when wall collision happens this tick
- Rule:
  - if `stop == 1`, ball must freeze (no movement updates)

### Model B: Counter Model (Hit Counter + Stop Trigger)
- Input:
  - `hit_wall` pulse from Model A
- Behavior:
  - counts wall hits from `0` to `9`
  - renders current count as top-row character (`'0'..'9'`) on the same `20x20` scene
- Outputs:
  - updated counter state/frame contribution
  - `stop` bit = `1` once counter reaches `9`
- Rule:
  - once `stop == 1`, keep it asserted (latched) unless a reset is explicitly defined

### Closed-Loop Integration
- Tick order:
  1. run Model A -> get `hit_wall`
  2. run Model B with `hit_wall` -> get `stop`
  3. feed `stop` into next Model A tick

---

## Strong Recommendation (Must Keep)
**Do not train full text/scene rendering first.**

Train models on **state transitions + control bits** first, and keep rendering deterministic in code initially:
- deterministic renderer draws walls/ball/counter glyphs from compact state
- learned parts focus only on transition logic (`state_t -> state_t+1`, `hit_wall`, `stop`)

Why:
- drastically reduces label noise and output dimensionality
- converges faster and more stably
- isolates failures (physics vs counting vs rendering)
- gives a reliable baseline before optional end-to-end framebuffer learning

---

## Current Repository State (Important Context)
- Worktree is currently dirty with ongoing emulator/game-movement changes.
- Existing game-movement pipeline and `game_movement_elf` target are already present but prior approach did not solve training complexity.
- There is an existing in-progress todo entry: `future-me-handoff`.
- Do **not** revert unrelated user changes.

---

## Execution Deliverables (Concrete)

## D1. Contracts + Oracle Specs
Create explicit contracts for both models:
- state vector schema for Model A
- state vector schema for Model B
- bit semantics for `hit_wall` and `stop`
- reset/initialization semantics

Done when:
- schema and tick semantics are written in code comments/docstrings and used by generator scripts.

## D2. Deterministic Oracles + Dataset Generators
Implement:
- `physics_oracle_step(state_a, stop_bit) -> (next_state_a, hit_wall_bit)`
- `counter_oracle_step(state_b, hit_wall_bit) -> (next_state_b, stop_bit)`
- dataset generation scripts for each model (separate datasets)

Done when:
- reproducible dataset generation succeeds from CLI
- oracle tests pass for edge/bounce/count boundary conditions.

## D3. Two Independent Trainings
Train:
- Model A on physics transitions + hit-wall prediction
- Model B on counting transitions + stop prediction

Done when:
- both models meet deterministic replay thresholds against oracle datasets.

## D4. Chain Integrator (Non-ML Rendering First)
Implement integration loop that composes both models per tick and deterministic renderer that draws:
- walls `#`
- ball `o`
- top-row counter char `0..9`

Done when:
- integrated replay demonstrates counter increments on collisions and ball freeze at `9`.

## D5. Emulator/ELF Integration + Smoke Gates
Add/update build target(s) and blackbox smoke test(s) for chained behavior.

Done when:
- emulator run can show progression from count `0` to `9`, assert stop, and freeze ball.

---

## First Deliverable to Execute Now
Start with **D1 + D2 only** (contracts + deterministic oracles + dataset scripts), because this de-risks all later stages.

Suggested first implementation paths:
- `projects/game-movement/src/dual_model_contract.py`
- `projects/game-movement/src/physics_oracle.py`
- `projects/game-movement/src/counter_oracle.py`
- `projects/game-movement/src/generate_physics_dataset.py`
- `projects/game-movement/src/generate_counter_dataset.py`
- tests:
  - `projects/game-movement/src/test_physics_oracle.py`
  - `projects/game-movement/src/test_counter_oracle.py`

---

## Acceptance Gates for Handoff Completion
Before moving to D3 training, require:
1. Oracle unit tests are green.
2. Datasets are generated deterministically with fixed seed.
3. A pure-oracle integrated simulation (`A -> B -> A`) reaches stop at count `9` and freezes motion.
4. All interfaces are documented and stable.

---

## Notes for Next Agent
- Keep model responsibilities strictly separated; avoid blending counter logic into physics model.
- Prefer explicit bit channels (`hit_wall`, `stop`) over implicit framebuffer inference.
- If training is unstable, reduce task dimensionality further before changing architecture.
