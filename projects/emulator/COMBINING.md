# Combining Neural Network Models into a Single Merged MLP

This document captures the methodology used to merge two independent
MLPs (a modulo-255 counter and a character generator) into a single
block-diagonal network that runs on the RISC-V emulator. Future model
combinations should follow the same patterns.

## Requirements / Prerequisites

### Toolchain
- Rust (for `model_to_header` compiler)
- RISC-V GCC (`riscv64-elf-gcc`) with rv32if + ilp32f
- CMake build system
- Python 3 for exporting model JSONs and tests
- The emulator (`emulator_runner`) for running ELF binaries

### Model JSONs
Each sub-network must be exported as a JSON file with:
- `metadata.model_type`, `metadata.precision` (`"float32"` only)
- `layers[]` — array of layer objects with `input_size`, `output_size`,
  `activation` (`"relu"`, `"sigmoid"`, or `"none"`), `weights` (2D array),
  `biases` (1D array)
- `metadata.input_mapping` (string, optional — used if model is run standalone)
- `metadata.initial_state` (map of variable-name → u32, optional)

All weights and biases must be float32. The JSONs live in `build/`
or under `../weight-export/`.

### Layer compatibility
For a block-diagonal merge, all sub-networks should have the **same
number of layers** and each corresponding layer pair must map to the
same merged input span and produce compatible output sizes.

In the counter+chargen example, both models were made 3-layer deep:
- Counter: 255→256→256→255
- Chargen: 255→256→256→400

The counter originally had 1 layer but was re-exported as 3 layers
(`export_counter255_three_layer.py`) to match the chargen depth.
This is critical — the merge cannot splice networks of different depths
without padding or redesign.

## Network Diagrams

### Standalone counter (modulo-255 auto-increment)

```
                     model_counter (0..254)
                           │
                           ▼ one-hot 255
              ┌────────────┴────────────┐
              │  L0: 255 × 256          │
              │  no activation          │
              │  shift: in[i]→out[i+1]  │
              └────────────┬────────────┘
                           │ 256
              ┌────────────┴────────────┐
              │  L1: 256 × 256          │
              │  no activation          │
              │  identity               │
              └────────────┬────────────┘
                           │ 256
              ┌────────────┴────────────┐
              │  L2: 256 × 255          │
              │  no activation          │
              │  truncate (keep 255)     │
              └────────────┬────────────┘
                           │ 255
                           ▼ argmax
                    next = (input+1) % 255
                    → model_counter
                    → debug word at 0x153FE0
```

### Standalone chargen (character-to-pixel rendering)

```
                      model_key (ASCII 32..126)
                           │
                           ▼ one-hot 255
              ┌────────────┴────────────┐
              │  L0: 255 × 256          │
              │  activation: relu       │
              │  learned weights        │
              └────────────┬────────────┘
                           │ 256
              ┌────────────┴────────────┐
              │  L1: 256 × 256          │
              │  activation: relu       │
              │  learned weights        │
              └────────────┬────────────┘
                           │ 256
              ┌────────────┴────────────┐
              │  L2: 256 × 400          │
              │  activation: sigmoid   │
              │  learned weights        │
              └────────────┬────────────┘
                           │ 400
                           ▼ clamp [0,1] × 255
                     framebuffer pixels (400 bytes)
```

### Combined block-diagonal merge

Both sub-networks share the same 255-element one-hot input. The merged
weight matrices are block-diagonal — each path occupies its own
diagonal block with zeros in cross-block positions.

```
                         model_counter (initial_state or s1 override)
                               │
                               ▼ one-hot 255
              ┌────────────────┼────────────────┐
              │   Counter Path │  Chargen Path   │
              │   (out_off:0)  │  (out_off:256)  │
              ▼                ▼                  ▼
     ┌────────────────┐ ┌────────────────────────┐
     │ Merged Layer 0 │ │ Merged Layer 0         │
     │ 255 → 256      │ │ 255 → 256              │
     │ activation:relu│ │ activation:relu        │
     │ in_off:0       │ │ in_off:0               │
     └───────┬────────┘ └──────────┬─────────────┘
             │                     │
     ┌───────┴────────┐ ┌──────────┴─────────────┐
     │ Merged Layer 1 │ │ Merged Layer 1         │
     │ 256 → 256      │ │ 256 → 256              │
     │ activation:relu│ │ activation:relu        │
     │ in_off:0       │ │ in_off:256             │
     │ out_off:0      │ │ out_off:256            │
     └───────┬────────┘ └──────────┬─────────────┘
             │                     │
     ┌───────┴────────┐ ┌──────────┴─────────────┐
     │ Merged Layer 2 │ │ Merged Layer 2         │
     │ 256 → 255      │ │ 256 → 400              │
     │ act:sigmoid    │ │ act:sigmoid            │
     │ in_off:0       │ │ in_off:256             │
     │ out_off:400    │ │ out_off:0              │
     └───────┬────────┘ └──────────┬─────────────┘
             │                     │
             ▼                     ▼
      counter_out(255)       chargen_out(400)
      buf[400..654]          buf[0..399]
             │                     │
             └─────────┬───────────┘
                       ▼
              ┌────────────────────┐
              │    MAP_OUTPUT      │
              │  buf[400..654]     │
              │    → argmax        │
              │    → model_counter │
              │                    │
              │  buf[0..399]       │
              │    → clamp [0,1]   │
              │    → fb[0..399]    │
              └────────────────────┘
```

**Weight matrix layout (block-diagonal)**

Layer 0 (255 × 512):
```
          ← 256 →  ← 256 →
          ┌────────┬────────┐
   256    │ counter│   0    │
          │weights │        │
          ├────────┼────────┤
   256    │   0    │ chargen│
          │        │weights │
          └────────┴────────┘
```

Layer 1 (512 × 512):
```
          ← 256 →  ← 256 →
          ┌────────┬────────┐
   256    │ counter│   0    │
          ├────────┼────────┤
   256    │   0    │ chargen│
          └────────┴────────┘
```

Layer 2 (512 × 655):
```
          ← 400 →  ← 255 →
          ┌────────┬────────┐
   256    │ chargen│   0    │
          ├────────┼────────┤
   256    │   0    │ counter│
          └────────┴────────┘
```

The output vector is `[chargen_pixels(400) || counter_state(255)]`.
`MODEL_MAP_OUTPUT` reads each region differently: chargen pixels are
clamped and scaled to the framebuffer; counter state is argmax'd to
produce the next `model_counter`.

## Glue JSON Format

A "glue" file describes how to merge sub-networks into one:

```json
{
  "input_mapping": "combined_counter_chargen",
  "output_mapping": "combined_counter_chargen",
  "initial_state": { "model_counter": 97 },
  "models": [
    { "name": "counter",  "path": "build/counter255_three_layer.json" },
    { "name": "chargen",  "path": "../weight-export/character_generator.json" }
  ],
  "merged_layers": [
    {
      "name": "layer_0_parallel",
      "activation": "relu",
      "blocks": [
        { "model": "counter", "layer": 0, "out_offset": 0 },
        { "model": "chargen", "layer": 0, "out_offset": 256 }
      ]
    },
    {
      "name": "layer_1_parallel",
      "activation": "relu",
      "blocks": [
        { "model": "counter", "layer": 1, "in_offset": 0,   "out_offset": 0 },
        { "model": "chargen", "layer": 1, "in_offset": 256, "out_offset": 256 }
      ]
    },
    {
      "name": "layer_2_parallel",
      "activation": "sigmoid",
      "blocks": [
        { "model": "counter", "layer": 2, "in_offset": 0,   "out_offset": 400 },
        { "model": "chargen", "layer": 2, "in_offset": 256, "out_offset": 0 }
      ]
    }
  ],
  "output_ranges": [
    { "name": "framebuffer",   "offset": 0,   "size": 400 },
    { "name": "counter_state", "offset": 400, "size": 255 }
  ]
}
```

| Field | Purpose |
|-------|---------|
| `input_mapping` | Selects the `MODEL_MAP_INPUT` / `MODEL_MAP_OUTPUT` macro arm in the Rust compiler |
| `output_mapping` | (Reserved) |
| `initial_state` | Starting values for C static variables emitted in `model.h` |
| `models[]` | References to the sub-network JSON files (paths relative to glue file) |
| `merged_layers[]` | How to assemble each merged layer from sub-network blocks |
| `output_ranges[]` | Documents the layout of the merged output vector |

### Block layout rules

Each `merged_layers` entry specifies how one merged layer is assembled:

- **Layer 0 (input layer)**: Both sub-networks share the same merged
  input (the raw 255-element one-hot). In the glue, both blocks omit
  `in_offset` (defaults to 0) and write to different `out_offset` values
  to place their hidden states side-by-side in the merged output.
- **Hidden layers**: Each block reads from `in_offset` (matching where
  its previous layer wrote) and writes to the same `out_offset` — the
  diagonal blocks stay aligned through the network.
- **Output layer**: Each block writes to a different region of the final
  merged output vector (e.g., chargen → [0..399], counter → [400..654]).

The Rust compiler places block `(in_offset + i, out_offset + j)` values
into the merged weight matrix at `(in_offset + i) * total_output + (out_offset + j)`,
with zeros for unassigned positions (cross-block connections).

## Rust Compiler (`model_to_header`)

### `--glue` flag
When `--glue <path>` is passed, the compiler reads the glue JSON,
loads all referenced model JSONs, and builds merged layers using
the block-diagonal procedure described above.

### Input-mapping arms
Each `input_mapping` value corresponds to a `match` arm that emits:

1. **Register/variable declarations** — e.g., `register uint32_t model_key asm("s1")`
2. **Constants** — `MODEL_READ_A0_EACH_ITER`, `MODEL_HAS_DONE_FLAG`
3. **State variables** with initial values from `initial_state`
4. **`MODEL_MAP_INPUT(buf)`** — how to fill the input buffer from state + registers
5. **`MODEL_MAP_OUTPUT(buf, fb)`** — how to extract framebuffer and state from output buffer

### Key macros understood by `runtime.c`

| Macro | Meaning |
|-------|---------|
| `MODEL_INPUT_SIZE` | Input dimension (set automatically from merged network) |
| `MODEL_OUTPUT_SIZE` | Output dimension |
| `MODEL_MAP_INPUT(buf)` | Called each iteration to prepare `buf[0..INPUT_SIZE-1]` |
| `MODEL_MAP_OUTPUT(buf, fb)` | Called each iteration to consume output and update framebuffer |
| `MODEL_READ_A0_EACH_ITER` | If 1, `inference_loop` re-reads `a0` each iteration (for movement model) |
| `MODEL_HAS_DONE_FLAG` | If 1, writes 1 to `0x154000` after each iteration — GUI breaks after done flag |

## Combining Key Insights

### 1. Block-diagonal vs. fully-connected

For combining sub-networks that share only the input and do not need
cross-talk in hidden layers, a **block-diagonal** weight matrix is
correct. Each sub-network's weights occupy diagonal blocks; zeros
fill the off-diagonal cross-connections. This keeps the sub-networks
independent while running on the same hardware.

### 2. `model_key` (s1) one-shot consumption

The `_start` function saves `a0` to `s1` (`mv s1, a0`). The GUI
loop writes key codes to both `a0` (reg 10) and `s1` (reg 9) on
each keypress.

The combined model declares `register uint32_t model_key asm("s1")`
and checks it in `MODEL_MAP_INPUT`. **The key insight**: `model_key`
must be **consumed** (set to 0) after the first use, so it only
overrides the counter on the first iteration after a keypress:

```c
if (model_key >= 32 && model_key < MODEL_INPUT_SIZE) {
    _idx = model_key;
    model_key = 0;  // one-shot: consumed
} else {
    _idx = model_counter;  // auto-advance
}
```

Without consumption, `model_key` overrides every iteration and the
counter never advances.

### 3. `MODEL_HAS_DONE_FLAG 1` for combined models

Models with internal state progression (counter auto-advance) must
use `MODEL_HAS_DONE_FLAG 1`. This makes the GUI loop break after
exactly 1 inference per frame, so each keypress shows exactly the
pressed character and subsequent frames auto-advance one step at a
time.

### 4. GUI loop must always step

The `process_gui_input` function was changed to run the inference
step on **every** frame iteration, not only when a key is pressed:

```cpp
// Always clear done flag and run inference (auto-advance)
emulator.getMemory().write32(0x154000, 0);
for (...) { emulator.step(); ... }
```

Without this, models with `MODEL_HAS_DONE_FLAG 1` would only advance
on keypress and appear frozen.

### 5. `initial_state` enables configurable start values

The `initial_state` HashMap in JSON metadata provides initial values
for C static variables. Each arm reads what it needs:

```rust
let cnt_init = initial_state.get("model_counter").copied().unwrap_or(97);
// → "static uint32_t model_counter = 97;"
```

The movement model uses `model_state`, the combined model uses
`model_counter`. The key name in the map matches the C variable name.

### 6. Layer depth parity

Both sub-networks must have the **same number of layers** for a clean
block-diagonal merge. If they differ, the shallower network must be
re-exported with identity layers to match depth. See
`export_counter255_three_layer.py` which wraps the 1-layer counter
into 3 layers by adding identity projections.

### 7. Output region partitioning

The merged output vector is partitioned into contiguous regions, one
per sub-network. `MODEL_MAP_OUTPUT` reads each region differently:

```c
// Chargen region: buf[0..399] → clamp [0,1] → scale ×255 → framebuffer
for (uint32_t _i = 0; _i < CB_FB_SIZE; _i++) {
    float _v = (buf)[_i];
    if (_v < 0.0f) _v = 0.0f;
    if (_v > 1.0f) _v = 1.0f;
    fb[_i] = (uint8_t)(_v * 255.0f);
}
// Counter region: buf[400..654] → argmax → model_counter
uint32_t _mi = 0;
float _mv = (buf)[CB_FB_SIZE];
for (uint32_t _i = 1; _i < CB_CNT_SIZE; _i++) {
    if ((buf)[CB_FB_SIZE + _i] > _mv) { _mv = (buf)[CB_FB_SIZE + _i]; _mi = _i; }
}
model_counter = _mi;
```

## Mega Combined Model (Squash + Counter-Chargen + Router)

The mega combined model merges four sub-networks into one: a **router MLP**
that learns to switch between a chargen mode and a squash game mode via
the Tab key.

### Architecture

```
Input Buffer (313 neurons):
┌──────────────────────────────────────────────────────────────────────┐
│ chargen/counter (255) │ squash input (56) │ Tab state (2)           │
└──────────────┬────────┴────────┬──────────┴────────┬────────────────┘
               │                 │                   │
               ▼                 ▼                   ▼
╔══════════════════════════════════════════════════════════════════════╗
║                     Merged Layer 0 (772 output)                     ║
║  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ ┌───────────┐   ║
║  │ Router  │ │ Counter  │ │ Chargers │ │GameSt  │ │ Renderer  │   ║
║  │  2 →  4 │ │ 255 → 256│ │ 255 → 256│ │ 56 → 64│ │  48 → 128 │   ║
║  │  (relu) │ │  (relu)  │ │  (relu)  │ │ (relu) │ │  (relu)   │   ║
║  └────┬────┘ └────┬─────┘ └────┬─────┘ └───┬────┘ └─────┬─────┘   ║
║       │4          │256         │256        │64          │128       ║
╠═══════╪═══════════╪════════════╪═══════════╪════════════╪══════════╣
║                     Merged Layer 1 (1010 output)                    ║
║  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ ┌───────────┐   ║
║  │ Router  │ │ Counter  │ │ Chargers │ │GameSt  │ │ Renderer  │   ║
║  │  4 →  2 │ │ 256 → 256│ │ 256 → 256│ │ 64 → 64│ │ 128 → 256 │   ║
║  │ (sigmoid│ │  (relu)  │ │  (relu)  │ │ (relu) │ │  (relu)   │   ║
║  └────┬────┘ └────┬─────┘ └────┬─────┘ └───┬────┘ └─────┬─────┘   ║
║       │2          │256         │256        │64          │256       ║
╠═══════╪═══════════╪════════════╪═══════════╪════════════╪══════════╣
║                     Merged Layer 2 (1013 output)                    ║
║  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ ┌───────────┐   ║
║  │ Router  │ │ Counter  │ │ Chargers │ │GameSt  │ │ Renderer  │   ║
║  │  2 →  2 │ │ 256 → 255│ │ 256 → 400│ │ 64 → 52│ │ 256 → 300 │   ║
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
│[0..1]  │[768..1008]│ [4..403]   │[404..455] │[456..755]  │
└────┬───┴───────────┴─────┬──────┴───────────┴─────┬──────┘
     │                     │                        │
     ▼                     ▼                        ▼
  gate values        gate_chargen > gate_squash → display chargen FB
  (0=chargen,        gate_squash > gate_chargen → display squash FB
   1=squash)
```

### Router MLP

The router is a small 3-layer MLP that learns to switch between the two
sub-models based on the Tab key state.

**Architecture:** `2 → 4 → 2 → 2` (relu, sigmoid, none)

**Training approach:**
- Input: Tab state one-hot `[tab_chargen, tab_squash]`
- Target: Same as input (identity mapping)
- Loss: MSE between output and target
- Optimizer: Adam, lr=0.01, ~200 iterations
- Convergence: Near-perfect (< 1e-6 loss)

The L2 layer is initialized as identity (not trained) to preserve gate
values into the final output buffer where C code can read them.

### Key Bindings

| Key | Action |
|-----|--------|
| **Tab** | Switch to squash mode (game runs) |
| **Escape** | Switch to chargen mode (squash **pauses**) |
| **\\** | Switch to chargen mode (squash **keeps running**) |
| **w/s** | Paddle up/down (squash mode) |

### Pause Behavior

- **Default**: Squash game pauses when chargen is shown (Escape behavior)
- **Override**: Press `\` to switch to chargen without pausing
- The `squash_always_run` flag controls this:
  - `0` = pause when chargen shown (default)
  - `1` = always run regardless of mode

### Runtime Behavior

1. **Default mode (chargen)**: Router receives Tab state `[1, 0]` →
   outputs gate `[~1.0, ~0.0]`. Chargen sub-model produces character
   glyphs. Counter auto-advances each frame.

2. **After Tab press**: Router receives Tab state `[0, 1]` → outputs
   gate `[~0.0, ~1.0]`. Squash sub-model produces game rendering.
   Squash physics continue updating.

3. **After Escape press**: Router returns to `[1, 0]`. Squash state
   decode is **skipped** in MODEL_MAP_OUTPUT. Static variables retain
   last values → game is frozen.

4. **After \\ press**: Router returns to `[1, 0]`. Squash state decode
   **continues** (`squash_always_run = 1`). Game keeps running in
   background while chargen is displayed.

### Glue JSON

The mega combined glue is at `mega_combined_glue.json`. It references
five sub-networks: router, counter, chargen, game_state, and renderer.
Output ranges:

| Region | Offset | Size | Content |
|--------|--------|------|---------|
| Router gates | 0 | 2 | gate_chargen, gate_squash |
| Chargers FB | 4 | 400 | 20×20 character pixels |
| Squash state | 404 | 52 | ball_x, ball_y, paddle_y, etc. |
| Squash FB | 456 | 300 | 20×15 game pixels |
| Counter state | 768 | 255 | counter argmax output |

## Adding a New Combination

1. **Export sub-network JSONs** with matching layer depths.
   Add `initial_state` and `input_mapping` to metadata.

2. **Write a glue JSON** referencing the sub-network JSONs,
   declaring merged layers with block offsets, and setting
   `input_mapping` to a new unique string.

3. **Add a `match` arm** in `model_to_header/src/main.rs`
   for the new `input_mapping` string that emits:
   - Any needed register declarations
   - `MODEL_READ_A0_EACH_ITER` and `MODEL_HAS_DONE_FLAG`
   - State variables with `initial_state` values
   - `MODEL_MAP_INPUT` and `MODEL_MAP_OUTPUT` macros

4. **Add a CMake target** in `CMakeLists.txt` that calls
   the Rust compiler with `--glue` and links via `runtime.c`.

5. **Write smoke tests** verifying determinism, state
   progression, and framebuffer output.

6. **Update the GUI loop** if the new model needs different
   interaction (e.g., step-on-keypress vs step-always).

## Files reference

| File | Role |
|------|------|
| `model_to_header/src/main.rs` | Rust compiler — `--glue` merge + macro generation |
| `runtime.c` | Shared C runtime — `inference_loop()` drives the network |
| `emulator_runner.cpp` | C++ emulator with GUI and batch modes |
| `combined_glue.json` | Glue description for counter+chargen merge |
| `mega_combined_glue.json` | Glue description for mega combined (squash + counter-chargen + router) |
| `models/router_tab_switch.json` | Trained router MLP weights |
| `export_counter255_three_layer.py` | Exports 3-layer counter to match chargen depth |
| `export_counter255_plain.py` | Exports 1-layer counter (standalone use) |
| `CMakeLists.txt` | Build rules for `counter255_elf`, `counter_chargen_combined_elf`, `mega_combined_elf` |
| `blackbox_tests/test_counter_chargen_combined_smoke.py` | Counter+chargen combined model tests |
| `blackbox_tests/test_counter255_runtime_smoke.py` | Standalone counter tests |
| `blackbox_tests/test_mega_combined.py` | Mega combined model tests |
| `combined-mlp.md` | ASCII-art diagram of the counter+chargen block-diagonal structure |
