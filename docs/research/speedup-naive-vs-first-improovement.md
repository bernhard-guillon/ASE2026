# Speedup Study: `neural.elf` vs `neural-ai-opsx77.elf` vs `neural-op-enhance.elf`

## Abstract

We measured character-generation latency in emulator cycles for:

- baseline scalar neural program (`neural.elf`)
- x77 optimized variant (`neural-ai-opsx77.elf`)
- new x7B enhanced variant (`neural-op-enhance.elf`)

On charset `A-Z0-9` (36 characters), x7B is consistently faster than x77 on both backends while preserving deterministic output matching under the same framebuffer-stability criterion.

## Experimental setup

- Emulator: `projects/emulator/build/emulator_runner`
- Baseline ELF: `projects/emulator/build/neural.elf`
- x77 ELF: `projects/emulator/build/neural-ai-opsx77.elf`
- x7B ELF: `projects/emulator/build/neural-op-enhance.elf`
- Test mode: `--render-framebuffer`
- Characters tested: `A-Z` and `0-9` (36 total)
- Stability criterion: first cycle budget whose 20x20 framebuffer exactly matches a high-cycle reference image for the same ELF/character.

### Threshold search

- Baseline reference: `5,000,000` cycles; checked at backend-specific threshold grids.
- x77 reference: `20,000` (C++) / `5,000,000` (Verilator), with backend-specific threshold grids.
- x7B reference: `20,000` (C++) / `5,000,000` (Verilator), with backend-specific threshold grids.

## Results

Across all 36 tested characters (min/avg/max were identical per backend):

### `emulator_runner` (C++)

- Baseline first exact cycle: **3,000,000 / 3,000,000 / 3,000,000**
- x77 first exact cycle: **2,000 / 2,000 / 2,000**
- x7B first exact cycle: **1,500 / 1,500 / 1,500**
- Speedup baseline/x77: **1500x / 1500x / 1500x**
- Speedup baseline/x7B: **2000x / 2000x / 2000x**
- Speedup x77/x7B: **1.333x / 1.333x / 1.333x**

### `verilator_runner` (HDL)

- Baseline first exact cycle: **4,000,000 / 4,000,000 / 4,000,000**
- x77 first exact cycle: **1,000,000 / 1,000,000 / 1,000,000**
- x7B first exact cycle: **750,000 / 750,000 / 750,000**
- Speedup baseline/x77: **4.0x / 4.0x / 4.0x**
- Speedup baseline/x7B: **5.333x / 5.333x / 5.333x**
- Speedup x77/x7B: **1.333x / 1.333x / 1.333x**

### Why Verilator speedup is smaller than emulator_runner speedup

The two backends execute custom neural ops at different abstraction levels:

- `emulator_runner` dispatches each op directly into native C++ neural kernels (`NeuralOps`), so large scalar loops are collapsed into a few host-side calls (very small constant factors).
- `verilator_runner` executes x77/x7B via a microcoded FSM inside `hdl/rtl/cpu.v`; loops still iterate element-by-element with memory transactions and DPI-C FP helper calls.

So while ISA-level instruction count is greatly reduced in both, the Verilog implementation still performs most arithmetic/memory work sequentially at micro-op granularity, yielding moderate but real gains (4.0x for x77, 5.333x for x7B), not a three-order-of-magnitude gain.

## Why the speedup happens

## 1) Same math, fewer executed ISA-level instructions

Both binaries compute the same network:

- Layers: `(255->256, ReLU)`, `(256->256, ReLU)`, `(256->400, Sigmoid-PWL)`
- Total MACs per inference: **233,216**
- Activation elements: **912**
- Output pixels: **400**

The naive program performs these via scalar RV32IF loops (many load/compute/store/branch instructions per element).  
The optimized versions replace key phases with custom neural ops:

- x77 path: `nmatvec.f32`, `nvrelu.f32`, `nvsigpwl.f32`, `nvclampu8.f32`
- x7B path: `nmatvecx.f32`, `nvrelux.f32`, `nvsigpwlx.f32`, `nvclampu8x.f32`

So the dominant work is dispatched through a small number of custom instructions, collapsing instruction-stream overhead dramatically.

## 2) Branch and address-update overhead reduction

Naive nested loops repeatedly pay per-element branch/indexing overhead in the instruction stream.  
Custom ops encapsulate loop mechanics internally in the emulator backend, reducing front-end decode/dispatch pressure and loop-control cost.

## 3) Better constant factors, unchanged asymptotics

Asymptotic complexity in terms of network shape is unchanged:

- Dense layers: \(O(\sum_i n_i n_{i+1})\)
- Elementwise activations/output mapping: \(O(\sum_i n_{i+1}) + O(P)\), with \(P=400\)

Overall:

\[
T = O\!\left(\sum_i n_i n_{i+1} + \sum_i n_{i+1} + P\right)
\]

For fixed architecture, this is effectively constant-time per character, but with very different constants:

- Naive: \(T_{\text{naive}} \approx \alpha\cdot \text{MAC} + \beta\cdot \text{ACT} + \gamma\cdot P + c\)
- x77/x7B: \(T_{\text{custom}} \approx \alpha'\cdot \text{MAC} + \beta'\cdot \text{ACT} + \gamma'\cdot P + c'\), with \(\alpha',\beta',\gamma' \ll \alpha,\beta,\gamma\)

Observed result:

- C++: **1500x** (x77) and **2000x** (x7B) lower cycle threshold vs baseline.
- Verilator: **4.0x** (x77) and **5.333x** (x7B) lower cycle threshold vs baseline.

For the HDL/Verilator backend, asymptotics are likewise unchanged, but constants improve less because loop bodies are still executed in the HDL state machine (not replaced by fully parallel dedicated datapaths), consistent with the observed **4.0x-5.333x** range.

## Validity notes

- This study measures cycle budget to stable framebuffer output in this emulator, not wall-clock hardware performance.
- Thresholds depend on tested cycle grids; the true minimum may be lower than the lowest passing point.
- Despite that, the gap is so large (orders of magnitude) that the qualitative conclusion is robust.

## Conclusion

The custom-op rollout provides a clear practical win on both backends:

- `emulator_runner`: about **1500x** fewer cycles with x77, **2000x** with x7B.
- `verilator_runner` (current HDL microcoded implementation): about **4.0x** fewer cycles with x77, **5.333x** with x7B.

x7B is consistently ~**1.333x** faster than x77 in this benchmark configuration.

Both preserve the same complexity class; gains come from improved constant factors. The remaining HDL gap is still a microarchitecture opportunity (e.g., wider/parallel neural datapaths, reduced per-element FSM overhead, and tighter on-chip neural execution units).
