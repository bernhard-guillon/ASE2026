# Squash Game — Pure-Neural Plan

## Architecture

Two independent MLPs, block-diagonally composed via glue JSON + Rust compiler.
**Zero custom C code for game logic** — all state transitions, physics, and
rendering are learned weights. Only the Rust compiler arm emits boilerplate
data-movement macros.

### Sub-network 1: Game State MLP

Learns squash physics, paddle control, and loss detection.

| Property | Value |
|----------|-------|
| **Input** (one-hot, 107 values) | `ball_x(0..39)` + `ball_y(0..29)` + `ball_vx(0|1)` + `ball_vy(0|1)` + `paddle_y(0..24)` + `game_state(0=live|1=lost)` + `key_up(0|1)` + `key_down(0|1)` |
| **Output** (one-hot, 103 values) | `new_ball_x(40)` + `new_ball_y(30)` + `new_ball_vx(2)` + `new_ball_vy(2)` + `new_paddle_y(25)` + `new_game_state(2)` + `ball_reset(2)` |
| **Layers** | `107 → 128 → 128 → 103` |
| **Learns** | `ball_xy += ball_vxy`; wall bounce (top flip vy↓, bottom flip vy↑); paddle bounce (left + y-overlap → flip vx→); out (`x > 39` → game_state=1); paddle move `±2` on key; auto-reset ball after out |

### Sub-network 2: Renderer MLP

Learns to draw the game state as a 40×30 monochrome frame (each logical pixel
maps to 8×8 real pixels on the 320×240 framebuffer).

| Property | Value |
|----------|-------|
| **Input** (one-hot, 97 values) | `ball_x(40)` + `ball_y(30)` + `paddle_y(25)` + `game_state(2)` |
| **Output** (1200 values, sigmoid) | 40×30 framebuffer pixels, clamped to `[0,1]` × 255 |
| **Layers** | `97 → 128 → 256 → 1200` |
| **Learns** | draw 2×2 ball at `(bx,by)`; draw 3×8 paddle at `(0, py)`; draw top/bottom/right walls; "GAME OVER" when `game_state=1` |

### Merged Block-Diagonal Network

```
                   State one-hot (107)
                  /                   \
     ┌────────────────────┐   ┌──────────────────┐
     │ GameState MLP L0   │   │ Renderer MLP L0   │
     │ 107→128 out_off:0  │   │ 97→128 out_off:128│
     └────────┬───────────┘   └────────┬─────────┘
              │                        │
     ┌────────┴───────────┐   ┌────────┴─────────┐
     │ GameState MLP L1   │   │ Renderer MLP L1   │
     │ 128→128 in_off:0   │   │ 128→256 in_off:128│
     │         out_off:0  │   │          out_off:128│
     └────────┬───────────┘   └────────┬─────────┘
              │                        │
     ┌────────┴───────────┐   ┌────────┴─────────┐
     │ GameState MLP L2   │   │ Renderer MLP L2   │
     │ 128→103 out:1200   │   │ 256→1200 out:0    │
     └────────┬───────────┘   └────────┬─────────┘
              │                        │
              ▼                        ▼
      buf[1200..1302]          buf[0..1199]
      argmax → 7 statics       clamp → fb(40×30)
```

Merged: `107 → 256 → 384 → 1303` (block-diagonal sparse).

---

## Testable Deliverables

Each deliverable has a concrete test that must pass before proceeding.

### D1: Game State Training Data Generator
**File:** `projects/emulator/training/gen_game_state_data.py`
**Tests** (`blackbox_tests/test_squash_game_state_data.py`):
- Output has correct number of samples: all combos of state variables
- Each sample is a valid `(input_one_hot, output_one_hot)` pair
- Physics check: `ball_x=0, ball_y=15, ball_vx=0 → next_ball_x=39, next_ball_y=15` (wrap around left→right? No — should bounce off paddle. Actually: `ball_x=0, ball_vx=0 → new_ball_x=0`, stays at left wall, but `ball_vx` flips if paddle hit)

Wait — actually, let's think about this more carefully. The game physics as MLP function:

```python
def physics(ball_x, ball_y, ball_vx, ball_vy, paddle_y, game_state, key_up, key_down):
    bx, by = ball_x + (1 if ball_vx else -1), ball_y + (1 if ball_vy else -1)
    bvx, bvy = ball_vx, ball_vy
    
    # Top/bottom walls
    if by < 0: by, bvy = 0, 1
    if by > 29: by, bvy = 29, 0
    
    # Paddle bounce (left wall, paddle at x=0, y=paddle_y..paddle_y+7)
    if bx < 0 and paddle_y <= ball_y < paddle_y + 8:
        bx, bvx = 0, 1
    
    # Out (right wall)
    if bx > 39: game_state = 1
    
    # Paddle
    if key_up: paddle_y = max(0, paddle_y - 2)
    if key_down: paddle_y = min(24, paddle_y + 2)
    
    return bx, by, bvx, bvy, paddle_y, game_state
```

Test: For every combination of inputs, the generator produces a valid physics output.

### D2: Game State MLP (trained + exported)
**Files:** `projects/emulator/training/train_game_state.py`, `projects/emulator/build/squash_game_state.json`
**Tests** (`blackbox_tests/test_squash_game_state_model.py`):
- Forward pass via `neural_reference.NeuralNetworkReference` matches expected physics output on ALL training samples
- Deterministic: same input → same output every time
- Edge cases: ball at corners, paddle at edges, key combos

### D3: Renderer Training Data Generator
**File:** `projects/emulator/training/gen_renderer_data.py`
**Tests** (`blackbox_tests/test_squash_renderer_data.py`):
- Each sample: `(ball_x, ball_y, paddle_y, game_state)` → 40×30 pixel array
- Ball always drawn at correct position
- Paddle always drawn at correct position
- Walls always present
- Game over text when game_state=1

### D4: Renderer MLP (trained + exported)
**Files:** `projects/emulator/training/train_renderer.py`, `projects/emulator/build/squash_renderer.json`
**Tests** (`blackbox_tests/test_squash_renderer_model.py`):
- Forward pass matches expected pixel output on ALL training samples
- Deterministic
- Visual sanity: bounding box of active pixels matches expected ball/paddle positions

### D5: Rust Compiler `squash_game` Arm
**File:** modified `projects/emulator/model_to_header/src/main.rs`
**Tests** (via combined ELF build):
- Compiles `model.h` from glue JSON without error
- Emitted `MODEL_MAP_INPUT` correctly one-hot encodes 7 static variables + 2 key flags into 107-wide buffer
- Emitted `MODEL_MAP_OUTPUT` correctly argmax-decodes 103 outputs into 7 statics, and clamps 1200 framebuffer pixels

### D6: Squash Combined ELF
**Files:** `projects/emulator/squash_glue.json`, `projects/emulator/build/squash.elf` (via CMake)
**Tests** (`blackbox_tests/test_squash_combined_smoke.py`):
- ELF starts, runs, produces valid framebuffer output (non-zero pixels)
- Deterministic: same cycle budget → same framebuffer
- State auto-advances: ball_x and ball_y change across frames
- Key input changes paddle position (via `--char-code`)
- Game reaches "lost" state when ball exits right boundary

---

## Implementation Phases

### Phase 1: Training Data Generators (D1 + D3)

Create `projects/emulator/training/` with:
- `gen_game_state_data.py` — enumerate all 107-input → 103-output combos
- `gen_renderer_data.py` — enumerate all 97-input → 1200-output combos
- Tests that generators produce correct physics/pixels

**Pass criteria:** both blackbox tests pass, covering:
- Full combinatorial verification (not just spot checks)
- Edge cases: corners, zero-velocity, all walls

### Phase 2: Train + Export Models (D2 + D4)

Create `train_game_state.py` and `train_renderer.py`:
- Load training data from Phase 1
- Train until 100% accuracy on full training set (memorization is OK — deterministic function)
- Export trained model as JSON (`squash_game_state.json`, `squash_renderer.json`)
- Tests verify forward pass matches expected output for every training sample

**Pass criteria:** `test_squash_game_state_model.py` and `test_squash_renderer_model.py` pass at 100% accuracy.

### Phase 3: Rust Compiler Arm (D5)

Add `"squash_game"` arm to `model_to_header/src/main.rs`:
- Declares static variables: `ball_x, ball_y, ball_vx, ball_vy, paddle_y, game_state, ball_reset`
- `MODEL_READ_A0_EACH_ITER 1` — reads keypress from `a0` each frame
- `MODEL_HAS_DONE_FLAG 1` — one inference per frame
- `MODEL_MAP_INPUT`: one-hot encodes 7 statics + `key_up`/`key_down` from `a0` → 107 inputs
- `MODEL_MAP_OUTPUT`: 7 argmax operations over `buf[1200..1302]`, 1200-pixel clamp for framebuffer
- Initial state from glue JSON's `initial_state`

**Pass criteria:** glue JSON compiles, ELF links.

### Phase 4: CMake + Combined ELF (D6)

Add to `CMakeLists.txt`:
- Custom command to generate `squash_glue.json` → `model.h` via `model_to_header --glue`
- Custom target `squash_elf` linking `runtime.c` with the generated header
- Combined model driven by `inference_loop()` — no new C code

### Phase 5: Combined Blackbox Tests (D6)

Create `test_squash_combined_smoke.py`:
- **determinism**: 2 runs, same cycles → same framebuffer
- **state_progresses**: 2M vs 6M cycles → ball moved
- **keypress_moves_paddle**: `--char-code` w (up) vs s (down) → different paddle position
- **ball_bounces**: ball starts at center, after many frames it's not at initial position
- **out_detection**: after enough frames, game_state becomes 1 (lost) — verify via debug word

**Pass criteria:** all 5 tests pass on CI.

---

## File Checklist

| File | Phase | Purpose |
|------|-------|---------|
| `projects/emulator/training/gen_game_state_data.py` | 1 | Generate training data for squash physics |
| `projects/emulator/training/gen_renderer_data.py` | 1 | Generate training data for squash renderer |
| `blackbox_tests/test_squash_game_state_data.py` | 1 | Verify game state data generator |
| `blackbox_tests/test_squash_renderer_data.py` | 1 | Verify renderer data generator |
| `projects/emulator/training/train_game_state.py` | 2 | Train game state MLP |
| `projects/emulator/training/train_renderer.py` | 2 | Train renderer MLP |
| `blackbox_tests/test_squash_game_state_model.py` | 2 | Verify game state MLP accuracy |
| `blackbox_tests/test_squash_renderer_model.py` | 2 | Verify renderer MLP accuracy |
| `projects/emulator/squash_glue.json` | 3 | Glue description for block-diagonal merge |
| `projects/emulator/model_to_header/src/main.rs` | 3 | Add `squash_game` arm |
| `projects/emulator/CMakeLists.txt` | 4 | Add `squash_elf` CMake target |
| `blackbox_tests/test_squash_combined_smoke.py` | 5 | Combined ELF blackbox tests |
| `.github/workflows/emulator-tests.yml` | 5 | Register squash tests in CI |

---

## Guard: What counts as "no custom C code"

The following is **allowed** (existing infrastructure):
- `runtime.c` inference loop unchanged
- Rust compiler arm emits `MODEL_MAP_INPUT` / `MODEL_MAP_OUTPUT` macros
- Macros do one-hot encode/decode and argmax (boilerplate data movement)

The following is **forbidden** (would be game logic in C):
- Any `if/else` in C that implements game rules (bouncing, scoring, loss)
- Any C function outside the macro skeleton
- Any modification to `runtime.c`
