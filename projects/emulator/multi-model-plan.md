# Mega Combined Model: Tab-Switching Multi-Model Architecture

## Goal

Combine the **squash combined** model (game_state + renderer) and the **counter-chargen combined** model (counter + chargen) into a single mega model with a **router MLP** that learns to switch between them based on the Tab key.

## Architecture Overview

```
Input Buffer (313 neurons):
┌──────────────────────────────────────────────────────────────────────┐
│ chargen/counter (255) │ squash input (56) │ Tab state (2)           │
└──────────────┬────────┴────────┬──────────┴────────┬────────────────┘
               │                 │                   │
               ▼                 ▼                   ▼
╔══════════════════════════════════════════════════════════════════════╗
║                     Merged Layer 0 (720 output)                     ║
║  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ ┌───────────┐   ║
║  │ Router  │ │ Counter  │ │ Chargers │ │GameSt  │ │ Renderer  │   ║
║  │  2 → 16 │ │ 255 → 256│ │ 255 → 256│ │ 56 → 64│ │  48 → 128 │   ║
║  │  (relu) │ │  (relu)  │ │  (relu)  │ │ (relu) │ │  (relu)   │   ║
║  └────┬────┘ └────┬─────┘ └────┬─────┘ └───┬────┘ └─────┬─────┘   ║
║       │16         │256         │256        │64          │128       ║
╠═══════╪═══════════╪════════════╪═══════════╪════════════╪══════════╣
║                     Merged Layer 1 (706 output)                     ║
║  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ ┌───────────┐   ║
║  │ Router  │ │ Counter  │ │ Chargers │ │GameSt  │ │ Renderer  │   ║
║  │ 16 → 2  │ │ 256 → 256│ │ 256 → 256│ │ 64 → 64│ │ 128 → 128 │   ║
║  │ (sigmoid)│ │  (relu)  │ │  (relu)  │ │ (relu) │ │  (relu)   │   ║
║  └────┬────┘ └────┬─────┘ └────┬─────┘ └───┬────┘ └─────┬─────┘   ║
║       │2          │256         │256        │64          │128       ║
╠═══════╪═══════════╪════════════╪═══════════╪════════════╪══════════╣
║                     Merged Layer 2 (1009 output)                    ║
║  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ ┌───────────┐   ║
║  │ Router  │ │ Counter  │ │ Chargers │ │GameSt  │ │ Renderer  │   ║
║  │  2 → 2  │ │ 256 → 255│ │ 256 → 400│ │ 64 → 52│ │ 128 → 300 │   ║
║  │ (none)  │ │  (none)  │ │ (sigmoid)│ │ (none) │ │ (sigmoid) │   ║
║  └────┬────┘ └────┬─────┘ └────┬─────┘ └───┬────┘ └─────┬─────┘   ║
╚═══════╪═══════════╪════════════╪═══════════╪════════════╪══════════╝
        │2          │255         │400        │52          │300
        ▼           ▼            ▼           ▼            ▼
Output Buffer (1009 neurons):
┌────────┬───────────┬────────────┬───────────┬────────────┐
│ Router │ Counter   │ Chargers   │ Squash    │ Squash     │
│ Gates  │ State     │ Framebuf   │ State     │ Framebuf   │
│  (2)   │  (255)    │  (400)     │  (52)     │  (300)     │
│[0..1]  │[754..1008]│ [2..401]   │[402..453] │[454..753]  │
└────┬───┴───────────┴─────┬──────┴───────────┴─────┬──────┘
     │                     │                        │
     ▼                     ▼                        ▼
  gate values        gate_chargen > gate_squash → display chargen FB
  (0=chargen,        gate_squash > gate_chargen → display squash FB
   1=squash)
```

## Layer Dimensions

| Layer | Router | Counter | Chargers | GameSt | Renderer | Total Input | Total Output |
|-------|--------|---------|----------|--------|----------|-------------|--------------|
| 0     | 2→16   | 255→256 | 255→256  | 56→64  | 48→128   | 313         | 720          |
| 1     | 16→2   | 256→256 | 256→256  | 64→64  | 128→128  | 720         | 706          |
| 2     | 2→2    | 256→255 | 256→400  | 64→52  | 128→300  | 706         | 1009         |

## Weight Matrix Sizes (block-diagonal, cross-connections zeroed)

| Layer | Weight Matrix | Float Params | Bytes (float32) |
|-------|---------------|--------------|------------------|
| 0     | 313 × 720     | 225,360      | 901,440          |
| 1     | 720 × 706     | 508,320      | 2,033,280        |
| 2     | 706 × 1,009   | 712,354      | 2,849,416        |
| **Total** |             | **1,446,034** | **5,784,136** (~5.5 MB) |

Plus biases: 720 + 706 + 1,009 = 2,435 floats = 9,740 bytes.

**Grand total model data: ~5.8 MB**

## Memory Layout

```
FRAMEBUFFER_BASE = 0x00020000  (display output)
BUFFER_BASE      = 0x00150000  (neural computation buffers)

INPUT_BUF        = 0x00150000  (313 floats = 1,252 bytes)
ACTIVATION_A     = 0x00151000  (ping-pong buffer A, ≥720 floats = 2,880 bytes)
ACTIVATION_B     = 0x00152000  (ping-pong buffer B, ≥706 floats = 2,824 bytes)
OUTPUT_BUF       = 0x00153000  (1,009 floats = 4,036 bytes)
DONE_FLAG_ADDR   = 0x00154000  (4 bytes)

MODEL_DATA       = 0x00030000  (model binary blob)
                 → ends at 0x00030000 + 5.8 MB ≈ 0x005D0000
```

**Note**: The model data extends to ~0x5D0000, which exceeds the original 0xE0000 limit. The emulator/verilator memory size must be increased to accommodate this. The linker script (`riscv_generator_high.ld`) and memory modules (`memory.v`, `Memory.cpp`) need their size parameters updated.

## Input Buffer Layout

| Offset | Size | Content |
|--------|------|---------|
| 0      | 255  | chargen/counter one-hot input (from `model_key` or `model_counter`) |
| 255    | 20   | ball_x one-hot |
| 275    | 15   | ball_y one-hot |
| 290    | 11   | paddle_y one-hot |
| 301    | 2    | game_state one-hot |
| 303    | 2    | ball_vx one-hot |
| 305    | 2    | ball_vy one-hot |
| 307    | 2    | key_up one-hot |
| 309    | 2    | key_down one-hot |
| 311    | 1    | Tab state: chargen active (1.0 when mega_mode=0) |
| 312    | 1    | Tab state: squash active (1.0 when mega_mode=1) |
| **Total** | **313** | |

## Output Buffer Layout

| Offset | Size | Content |
|--------|------|---------|
| 0      | 2    | Router gate values (gate_chargen, gate_squash) — sigmoid output |
| 2      | 400  | Chargers framebuffer (20×20 pixels, sigmoid [0,1]) |
| 402    | 52   | Squash game state (argmax-decoded: ball_x, ball_y, paddle_y, game_state, ball_vx, ball_vy) |
| 454    | 300  | Squash framebuffer (20×15 pixels, sigmoid [0,1]) |
| 754    | 255  | Counter state (argmax-decoded) |
| **Total** | **1009** | |

## Router MLP

The router is a small 3-layer MLP that learns to switch between the two sub-models based on the Tab key state.

### Architecture
```
Tab state (one-hot 2D)
    │
    ▼
┌─────────┐
│ FC 2→16 │  weights: [2×16], biases: [16]
│  ReLU   │
└────┬────┘
     │
┌─────────┐
│ FC 16→2 │  weights: [16×2], biases: [2]
│ Sigmoid │
└────┬────┘
     │
┌─────────┐
│ FC 2→2  │  weights: [2×2] = identity, biases: [2] = 0
│  None   │  (passthrough to preserve gates in final output)
└────┬────┘
     │
     ▼
gate_chargen, gate_squash
```

### Training

The router is trained with a simple objective:
- **Input**: Tab state one-hot `[tab_chargen, tab_squash]`
- **Target**: Same as input (identity mapping)
- **Loss**: MSE between output and target
- **Optimizer**: Adam, lr=0.01, ~200 iterations
- **Convergence**: Near-perfect (< 1e-6 loss)

The L2 layer is initialized as identity (not trained) to preserve gate values.

### Initialization

```python
# L0: small random weights, relu
# L1: small random weights, sigmoid
# L2: identity matrix, no activation
W2 = [[1, 0], [0, 1]]
b2 = [0, 0]
```

## MODEL_MAP_INPUT Macro

```c
register uint32_t model_key asm("s1");

static uint32_t model_counter = 97;
static uint32_t ball_x = 10, ball_y = 7, ball_vx = 1, ball_vy = 0;
static uint32_t paddle_y = 3, game_state = 0;
static uint32_t mega_mode = 0; // 0=chargen, 1=squash

#define MODEL_MAP_INPUT(buf) do { \
    for (uint32_t i = 0; i < MODEL_INPUT_SIZE; i++) buf[i] = 0.0f; \
    \
    /* Chargen/counter input (offset 0..254) */ \
    uint32_t _idx; \
    if (model_key >= 32 && model_key < 255) { \
        _idx = model_key; \
        model_key = 0; \
    } else { \
        _idx = model_counter; \
    } \
    if (_idx < 255) buf[_idx] = 1.0f; \
    \
    /* Squash input (offset 255..310) */ \
    if (ball_x < 20) buf[255 + ball_x] = 1.0f; \
    if (ball_y < 15) buf[275 + ball_y] = 1.0f; \
    if (paddle_y < 11) buf[290 + paddle_y] = 1.0f; \
    if (game_state < 2) buf[301 + game_state] = 1.0f; \
    if (ball_vx < 2) buf[303 + ball_vx] = 1.0f; \
    if (ball_vy < 2) buf[305 + ball_vy] = 1.0f; \
    uint32_t _key = *((volatile uint32_t *)0x154004); \
    buf[307] = 1.0f; buf[308] = 0.0f; \
    buf[309] = 1.0f; buf[310] = 0.0f; \
    if (_key == 'w' || _key == 'W') { buf[307] = 0.0f; buf[308] = 1.0f; } \
    if (_key == 's' || _key == 'S') { buf[309] = 0.0f; buf[310] = 1.0f; } \
    \
    /* Tab state (offset 311..312) */ \
    if (_key == 0x09) { mega_mode = 1; } \
    else if (_key == 0x1B) { mega_mode = 0; } \
    if (mega_mode == 0) { buf[311] = 1.0f; buf[312] = 0.0f; } \
    else { buf[311] = 0.0f; buf[312] = 1.0f; } \
} while(0)
```

## MODEL_MAP_OUTPUT Macro

```c
#define MODEL_MAP_OUTPUT(buf, fb) do { \
    float _gs = (buf)[0]; /* gate_squash */ \
    float _gc = (buf)[1]; /* gate_chargen */ \
    \
    /* Always update counter state (buf[754..1008]) */ \
    uint32_t _mi = 0; \
    float _mv = (buf)[754]; \
    for (uint32_t _i = 1; _i < 255; _i++) { \
        if ((buf)[754 + _i] > _mv) { _mv = (buf)[754 + _i]; _mi = _i; } \
    } \
    model_counter = _mi; \
    \
    /* Always update squash state (buf[402..453]) */ \
    _mi = 0; _mv = (buf)[402]; \
    for (uint32_t _i = 1; _i < 20; _i++) { if ((buf)[402+_i] > _mv) { _mv = (buf)[402+_i]; _mi = _i; } } \
    ball_x = _mi; \
    _mi = 0; _mv = (buf)[422]; \
    for (uint32_t _i = 1; _i < 15; _i++) { if ((buf)[422+_i] > _mv) { _mv = (buf)[422+_i]; _mi = _i; } } \
    ball_y = _mi; \
    /* ... (paddle_y, game_state, ball_vx, ball_vy decoding) ... */ \
    \
    /* Select framebuffer based on router gates */ \
    if (_gc > _gs) { \
        /* Chargers active: buf[2..401] → fb (20×20, linear) */ \
        for (uint32_t _i = 0; _i < 400; _i++) { \
            float _v = (buf)[2 + _i]; \
            if (_v < 0.0f) _v = 0.0f; \
            if (_v > 1.0f) _v = 1.0f; \
            fb[_i] = (uint8_t)(_v * 255.0f); \
        } \
    } else { \
        /* Squash active: buf[454..753] → fb (20×15, stride 320) */ \
        for (uint32_t _y = 0; _y < 15; _y++) { \
            for (uint32_t _x = 0; _x < 20; _x++) { \
                float _v = (buf)[454 + _y * 20 + _x]; \
                if (_v < 0.0f) _v = 0.0f; \
                if (_v > 1.0f) _v = 1.0f; \
                fb[_y * 320 + _x] = (uint8_t)(_v * 255.0f); \
            } \
        } \
    } \
} while(0)
```

## Files to Create

| File | Purpose |
|------|---------|
| `models/router_tab_switch.json` | Router MLP weights (trained) |
| `mega_combined_glue.json` | Block-diagonal merging description |
| `train_router.py` | Training script for router MLP |
| `blackbox_tests/test_mega_combined.py` | End-to-end tests |

## Files to Modify

| File | Change |
|------|--------|
| `model_to_header/src/main.rs` | Add `mega_combined` input_mapping case |
| `CMakeLists.txt` | Add `mega_combined_elf` build target |
| `riscv_generator_high.ld` | Increase memory size for larger model |
| `hdl/rtl/memory.v` | Increase memory depth if needed |
| `Memory.cpp` | Increase memory size if needed |

## Implementation Steps

| Step | Task | Status |
|------|------|--------|
| 1 | Write `train_router.py`, generate `models/router_tab_switch.json` | Pending |
| 2 | Create `mega_combined_glue.json` with correct block offsets | Pending |
| 3 | Add `mega_combined` case to `model_to_header/src/main.rs` | Pending |
| 4 | Update memory sizes in linker script, Memory.cpp, memory.v | Pending |
| 5 | Add CMake build target for `mega-combined.elf` | Pending |
| 6 | Build and fix compilation errors | Pending |
| 7 | Write `test_mega_combined.py` | Pending |
| 8 | Test end-to-end with `--gui` mode | Pending |

## Runtime Behavior

### Default Mode (Chargen)
1. Router receives Tab state `[1, 0]` → outputs gate `[~1.0, ~0.0]`
2. chargen/counter sub-model runs, produces character glyphs
3. C code selects chargen framebuffer (20×20, 400 pixels)
4. Counter auto-advances each frame

### After Tab Press
1. Router receives Tab state `[0, 1]` → outputs gate `[~0.0, ~1.0]`
2. squash sub-model runs, produces game rendering
3. C code selects squash framebuffer (20×15, 300 pixels, stride 320)
4. Squash physics continue updating

### After Escape Press (switch to chargen + pause)
1. Router receives Tab state `[1, 0]` → outputs gate `[~1.0, ~0.0]`
2. Squash state decode is **skipped** in MODEL_MAP_OUTPUT
3. Static variables (ball_x, ball_y, etc.) retain their last values
4. Next iteration: MODEL_MAP_INPUT re-encodes the same state → game is frozen

### After \ Press (switch to chargen, no pause)
1. Router receives Tab state `[1, 0]` → outputs gate `[~1.0, ~0.0]`
2. Squash state decode **continues** (squash_always_run = 1)
3. Squash game keeps running in background while chargen is displayed

## Key Bindings

| Key | Action |
|-----|--------|
| **Tab** | Switch to squash mode (game runs) |
| **Escape** | Switch to chargen mode (squash **pauses**) |
| **\\** | Switch to chargen mode (squash **keeps running**) |
| **w/s** | Paddle up/down (squash mode) |

### Pause Behavior
- **Default**: Squash game pauses when chargen is shown (Escape behavior)
- **Override**: Press `\` to switch to chargen without pausing (old behavior)
- The `squash_always_run` flag controls this:
  - `0` = pause when chargen shown (default)
  - `1` = always run regardless of mode

## Design Decisions

1. **Router is a real MLP** — not a hard-coded rule. It learns the switching logic via training, making it a genuine neural component.

2. **Both sub-models always run** — block-diagonal parallel execution means both produce outputs every frame. The router only gates which framebuffer is displayed. This keeps architecture simple.

3. **Router L2 is identity passthrough** — 2→2 with identity weights preserves gate values into the final output buffer where C code can read them.

4. **Tab toggles, Escape resets** — Tab switches to squash mode, Escape returns to chargen mode. This provides clear navigation.

5. **Memory increase needed** — ~5.8 MB model data exceeds original limits. Emulator/verilator memory size must be increased.

## Sub-Model Reference

| Sub-Model | Architecture | Input Encoding | Output |
|-----------|-------------|----------------|--------|
| Counter | 255→256→256→255 | one-hot from model_counter | argmax → model_counter |
| Chargers | 255→256→256→400 | one-hot from model_key | sigmoid → framebuffer |
| Game_State | 56→64→64→52 | ball/key state encoding | argmax → squash state |
| Renderer | 48→128→128→300 | game_state output subset | sigmoid → framebuffer |
| Router | 2→16→2→2 | Tab state one-hot | sigmoid → gate values |

---

## Task Breakdown

### Task 1: Router MLP Training & Export
**Depends on**: Nothing (parallelizable)
**Deliverables**:
- `train_router.py` — PyTorch training script
- `models/router_tab_switch.json` — trained router weights

**Verification**:
```bash
python3 train_router.py
python3 -c "
import json
m = json.load(open('models/router_tab_switch.json'))
assert len(m['layers']) == 3
assert m['layers'][0]['input_size'] == 2
assert m['layers'][2]['output_size'] == 2
print('Router JSON valid')
"
```
Router must output `(~1.0, ~0.0)` for input `[1,0]` and `(~0.0, ~1.0)` for input `[0,1]`.

---

### Task 2: Mega Combined Glue JSON
**Depends on**: Task 1 (router JSON must exist)
**Deliverables**:
- `mega_combined_glue.json` — block-diagonal merging description

**Verification**:
```bash
cargo run --manifest-path model_to_header/Cargo.toml \
    -- --glue mega_combined_glue.json -o /tmp/test_model.h
grep "MODEL_INPUT_SIZE" /tmp/test_model.h   # expect 313
grep "MODEL_OUTPUT_SIZE" /tmp/test_model.h  # expect 1009
```
Compiler must produce valid `model.h` with correct dimensions.

---

### Task 3: Rust Compiler `mega_combined` Mapping
**Depends on**: Task 2
**Deliverables**:
- Updated `model_to_header/src/main.rs` with new `mega_combined` case

**Verification**:
```bash
cargo run --manifest-path model_to_header/Cargo.toml \
    -- --glue mega_combined_glue.json -o /tmp/mega_model.h
grep "mega_combined" /tmp/mega_model.h
grep "MODEL_MAP_INPUT" /tmp/mega_model.h
grep "MODEL_MAP_OUTPUT" /tmp/mega_model.h
```
Generated macros must handle both chargen and squash input encoding, and router-gated output selection.

---

### Task 4: Memory Size Adjustments
**Depends on**: Nothing (parallelizable)
**Deliverables**:
- Updated `riscv_generator_high.ld` (increase `.model` region)
- Updated `Memory.cpp` (increase memory size)
- Updated `hdl/rtl/memory.v` (increase memory depth)

**Verification**:
```bash
cd build && cmake .. && make -j4
ctest -R "python/counter_chargen_combined" -V
ctest -R "python/squash" -V
```
Existing `counter-chargen-combined.elf` and `squash.elf` must still build and pass all tests (no regressions).

---

### Task 5: CMake Integration & ELF Build
**Depends on**: Tasks 2, 3, 4
**Deliverables**:
- Updated `CMakeLists.txt` with `mega_combined_elf` target
- `build/mega-combined.elf` — compiled binary

**Verification**:
```bash
cd build && cmake .. && make mega_combined_elf -j4
ls -la mega-combined.elf
file mega-combined.elf
```
ELF must build without linker errors. Model data section must fit within memory bounds.

---

### Task 6: End-to-End GUI Test
**Depends on**: Task 5
**Deliverables**:
- `blackbox_tests/test_mega_combined.py` — automated test suite

**Verification**:
```bash
ctest -R "python/mega_combined" -V

# Manual GUI test
./build/emulator_runner build/mega-combined.elf --gui
# Press 'a' → should show chargen glyph
# Press Tab → should switch to squash game
# Press Escape → should return to chargen
```
Tab switching must work in both cpp emulator and verilator runner. Framebuffer must update correctly for each mode.

---

### Dependency Graph

```
Task 1 (Router)  ──────┐
                        ├──→ Task 5 (CMake/ELF) ──→ Task 6 (E2E Test)
Task 4 (Memory)  ──────┤
                        │
Task 2 (Glue JSON) ────┤
          │             │
          └──→ Task 3 (Rust Compiler) ──┘
```

### Parallelization Opportunities

| Time Slot | Track A | Track B |
|-----------|---------|---------|
| Week 1 | Task 1: Router training | Task 4: Memory adjustments |
| Week 2 | Task 2: Glue JSON | Task 3: Rust compiler |
| Week 3 | Task 5: CMake + build | |
| Week 4 | Task 6: E2E tests | |
