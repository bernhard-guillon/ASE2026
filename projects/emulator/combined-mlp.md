# Block-Diagonal Parallel Counter+Chargen MLP

Merges a 3-layer counter MLP and a 3-layer chargen MLP into a single network
by stacking activations and zeroing cross-connections in the weight matrices.

```
╔══════════════════════════════════════════════════════════════════════╗
║           block-diagonal-parallel: single merged MLP                ║
║  input_mapping: "counter_char_a0_bridge"  (a0 → one-hot 255)       ║
║  output_size: 400  (only chargen output goes to framebuffer)        ║
╚══════════════════════════════════════════════════════════════════════╝

              a0 (0..254)
                  │
                  ▼ one-hot
          ┌───────┴───────┐
          │    255-wide   │
          └───────┬───────┘
                  │
  ┌─────────────────┬──────────────────────────────────┐
  │  COUNTER PATH   │     CHARGEN PATH                  │
  │  (no act.)      │     (relu/sigmoid)                │
  │                 │                                   │
  │  ┌───────────┐  │  ┌───────────┐                    │
  │  │ L0:256    │  │  │ L0:256    │  w=[255×256] each  │
  │  │(no act)   │  │  │(relu)     │  concat horiz →    │
  │  └─────┬─────┘  │  └─────┬─────┘  255×512           │
  │        │        │        │                           │
  │        ├── 256 ─┤   ── 256 ──┤                       │
  │        │        │        │                           │
  │  ┌─────┴─────┐  │  ┌─────┴─────┐                    │
  │  │ L1:256    │  │  │ L1:256    │  w=512×512         │
  │  │(no act)   │  │  │(relu)     │  block-diag         │
  │  └─────┬─────┘  │  └─────┬─────┘  ┌─256──256─┐     │
  │        │        │        │         │ cnt│  0  │     │
  │        ├── 256 ─┤   ── 256 ──┤     │────┼─────│     │
  │        │        │        │         │  0 │cgen │     │
  │  ┌─────┴─────┐  │  ┌─────┴─────┐  └──────┴─────┘    │
  │  │ L2:255    │  │  │ L2:400    │  w=512×655         │
  │  │(no act)   │  │  │(sigmoid)  │  block-diag         │
  │  └─────┬─────┘  │  └─────┬─────┘  ┌───400───┬255┐   │
  │        │        │        │         │   0     │cnt│   │
  │        │        │        │         │─────────┼───│   │
  │        │        │        │         │  cgen   │ 0 │   │
  │        │        │        │         └─────────┴───┘   │
  └────────┼────────┘   ────┼────────                     │
           │                │                             │
           ▼                ▼                             │
     counter_out(255)   chargen_out(400)  →  framebuffer
     (discarded)
```

## Weight layout by layer

| Layer | Input | Output | Counter block | Chargen block | Cross-connections |
|-------|-------|--------|---------------|---------------|-------------------|
| 0     | 255   | 512    | cols 0-255    | cols 256-511  | share same input → concat horizontally |
| 1     | 512   | 512    | rows/cols 0-255 | rows/cols 256-511 | zeros |
| 2     | 512   | 655    | inputs 0-255 → outputs 400-654 | inputs 256-511 → outputs 0-399 | zeros |

Layer 2 output is `[chargen_pixels(400) || counter_state(255)]`; only the first
400 bytes go to the framebuffer, the counter state is discarded.

## Source files

- **Glue description**: `combined_glue.json` — references counter + chargen JSONs and block layout
- **Rust compiler**: `model_to_header/src/main.rs` — `--glue` flag reads glue JSON, merges weights into block-diagonal matrices, emits `model.h` with `combined_counter_chargen` macros
- **Runtime**: `runtime.c` — shared C runtime, drives the merged network via `inference_loop()`
- **CMake target**: `counter_chargen_combined_elf` — uses `riscv64-elf-gcc` + `runtime.c` + generated `model.h`
- **Counter input**: `counter255_three_layer.json` — 3 layers `255→256→256→255`, no activation
- **Chargen input**: `../weight-export/character_generator.json` — 3 layers `255→256→256→400`, relu + sigmoid
- **Output ELF**: `build/counter-chargen-combined.elf`
- **Tests**: `blackbox_tests/test_counter_chargen_combined_smoke.py` — 5 tests verifying counter advance, determinism, framebuffer output, and character change across cycle budgets
