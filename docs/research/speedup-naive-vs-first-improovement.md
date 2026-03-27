# Speedup Study: `neural.elf` vs `neural-ai-opsx77.elf` vs x7B lane variants

## Abstract

We measured character-generation latency in emulator cycles for:

- baseline scalar neural program (`neural.elf`)
- x77 optimized variant (`neural-ai-opsx77.elf`)
- x7B base (`neural-op-enhance.elf`)
- x7B 4-lane (`neural-op-enhance4.elf`)
- x7B 8-lane (`neural-op-enhance8.elf`)

On charset `A-Z0-9` (36 characters), x7B lane variants preserve deterministic output and improve over x77 on Verilator, but 4-lane and 8-lane currently show identical threshold-cycle results (no linear 2x scaling yet).

Reference artifact: `docs/research/phase14-neural-lane-cycle-comparison.json`.

## Experimental setup

- Runners:
  - `projects/emulator/build/emulator_runner`
  - `projects/emulator/build/verilator_runner`
- ELFs:
  - baseline: `projects/emulator/build/neural.elf`
  - x77: `projects/emulator/build/neural-ai-opsx77.elf`
  - x7B base: `projects/emulator/build/neural-op-enhance.elf`
  - x7B 4-lane: `projects/emulator/build/neural-op-enhance4.elf`
  - x7B 8-lane: `projects/emulator/build/neural-op-enhance8.elf`
- Test mode: `--render-framebuffer`
- Characters tested: `A-Z` and `0-9` (36 total)
- Stability criterion: first cycle budget whose 20x20 framebuffer exactly matches a high-cycle reference image for the same ELF/character.

## Results

Across all 36 tested characters, min/avg/max were identical per backend.

### `emulator_runner` (C++)

- Baseline first exact cycle: **3,000,000 / 3,000,000 / 3,000,000**
- x77 first exact cycle: **2,000 / 2,000 / 2,000**
- x7B base first exact cycle: **1,500 / 1,500 / 1,500**
- x7B 4-lane first exact cycle: **1,500 / 1,500 / 1,500**
- x7B 8-lane first exact cycle: **1,500 / 1,500 / 1,500**
- Speedup baseline/x77: **1500x / 1500x / 1500x**
- Speedup baseline/x7B (base/4-lane/8-lane): **2000x / 2000x / 2000x**
- Speedup x77/x7B (base/4-lane/8-lane): **1.333x / 1.333x / 1.333x**
- Observed 4-lane to 8-lane scaling: **1.0x** (ideal: 2.0x)
- 4->8 efficiency vs ideal 2.0x: **0.5**

### `verilator_runner` (HDL)

- Baseline first exact cycle: **4,000,000 / 4,000,000 / 4,000,000**
- x77 first exact cycle: **1,000,000 / 1,000,000 / 1,000,000**
- x7B base first exact cycle: **750,000 / 750,000 / 750,000**
- x7B 4-lane first exact cycle: **600,000 / 600,000 / 600,000**
- x7B 8-lane first exact cycle: **600,000 / 600,000 / 600,000**
- Speedup baseline/x77: **4.0x / 4.0x / 4.0x**
- Speedup baseline/x7B base: **5.333x / 5.333x / 5.333x**
- Speedup baseline/x7B 4-lane: **6.667x / 6.667x / 6.667x**
- Speedup baseline/x7B 8-lane: **6.667x / 6.667x / 6.667x**
- Speedup x77/x7B 4-lane and 8-lane: **1.667x / 1.667x / 1.667x**
- Observed 4-lane to 8-lane scaling: **1.0x** (ideal: 2.0x)
- 4->8 efficiency vs ideal 2.0x: **0.5**

## Interpretation

## 1) Lane rollout improved HDL vs prior x7B base

Compared to x7B base on Verilator:

- `x7b-base`: 750,000 cycles
- `x7b-4lane`: 600,000 cycles
- `x7b-8lane`: 600,000 cycles

So the lane path provides an additional gain over prior x7B base, but currently plateaus between 4-lane and 8-lane.

## 2) No linear 4->8 scaling yet

The expected ideal doubling from 4-lane to 8-lane would be 2.0x speedup.  
Observed is 1.0x on both backends, i.e., efficiency 0.5 versus ideal.

This indicates a bottleneck outside the nominal lane width parameter in the current execution path.

## 3) Why Verilator gains are still moderate vs C++

- `emulator_runner` dispatches custom ops directly to native C++ kernels, minimizing instruction-stream overhead.
- `verilator_runner` executes custom ops in a microcoded FSM with per-element memory/DPI behavior still present.

That explains why absolute speedups remain far smaller in HDL than C++ despite ISA-level instruction reduction.

## Validity notes

- This study measures cycle budget to stable framebuffer output in this emulator, not wall-clock hardware performance.
- Thresholds depend on tested cycle grids; true minima may be lower than the first passing threshold.
- Results are still robust enough for relative comparisons due large separations between variants.

## Conclusion

Phase 14 confirms:

- Strong gains over baseline and x77 remain intact.
- Lane-enabled x7B variants improve HDL further versus x7B base.
- **4-lane to 8-lane scaling is currently non-linear and flat (1.0x observed)**, so the next optimization wave should target the bottleneck preventing 8-lane from outperforming 4-lane.
