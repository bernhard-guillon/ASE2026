# Speedup Study: `neural.elf` (naive) vs `neural-ai-opsx77.elf` (first improvement)

## Abstract

We measured character-generation latency in emulator cycles for the baseline scalar neural program (`neural.elf`) and the first optimized variant using custom x77 neural ops (`neural-ai-opsx77.elf`).  
On charset `A-Z0-9` (36 characters), the optimized binary reached stable output in **2,000 cycles** versus **3,000,000 cycles** for the baseline, yielding a consistent **1500x speedup** in this setup.

## Experimental setup

- Emulator: `projects/emulator/build/emulator_runner`
- Baseline ELF: `projects/emulator/build/neural.elf`
- Optimized ELF: `projects/emulator/build/neural-ai-opsx77.elf`
- Test mode: `--render-framebuffer`
- Characters tested: `A-Z` and `0-9` (36 total)
- Stability criterion: first cycle budget whose 20x20 framebuffer exactly matches a high-cycle reference image for the same ELF/character.

### Threshold search

- Baseline reference: `5,000,000` cycles; checked at `[2,000,000, 2,500,000, 3,000,000, 4,000,000]`
- Optimized reference: `20,000` cycles; checked at `[2,000, 5,000, 10,000]`

## Results

Across all 36 tested characters:

- Baseline first exact cycle: min/avg/max = **3,000,000 / 3,000,000 / 3,000,000**
- Optimized first exact cycle: min/avg/max = **2,000 / 2,000 / 2,000**
- Speedup (`baseline / optimized`): min/avg/max = **1500x / 1500x / 1500x**

## HDL/Verilator follow-up results

After implementing CUSTOM0/x77 in the Verilog CPU and re-running the same `A-Z0-9` methodology on `verilator_runner`, we measured:

- Baseline (`neural.elf`) first exact cycle: min/avg/max = **4,000,000 / 4,000,000 / 4,000,000**
- Optimized (`neural-ai-opsx77.elf`) first exact cycle: min/avg/max = **2,000,000 / 2,000,000 / 2,000,000**
- Speedup (`baseline / optimized`): min/avg/max = **2.0x / 2.0x / 2.0x**

### Why Verilator speedup is smaller than emulator_runner speedup

The two backends execute x77 at different abstraction levels:

- `emulator_runner` dispatches each x77 op directly into native C++ neural kernels (`NeuralOps`), so large scalar loops are collapsed into a few host-side calls (very small constant factors).
- `verilator_runner` executes x77 via a microcoded FSM inside `hdl/rtl/cpu.v`; loops still iterate element-by-element with memory transactions and DPI-C FP helper calls.

So while ISA-level instruction count is greatly reduced in both, the Verilog implementation still performs most arithmetic/memory work sequentially at micro-op granularity, yielding a moderate but real gain (~2x), not a three-order-of-magnitude gain.

## Why the speedup happens

## 1) Same math, fewer executed ISA-level instructions

Both binaries compute the same network:

- Layers: `(255->256, ReLU)`, `(256->256, ReLU)`, `(256->400, Sigmoid-PWL)`
- Total MACs per inference: **233,216**
- Activation elements: **912**
- Output pixels: **400**

The naive program performs these via scalar RV32IF loops (many load/compute/store/branch instructions per element).  
The optimized version replaces key phases with custom x77 neural ops:

- `nmatvec.f32`
- `nvrelu.f32`
- `nvsigpwl.f32`
- `nvclampu8.f32`

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
- x77: \(T_{x77} \approx \alpha'\cdot \text{MAC} + \beta'\cdot \text{ACT} + \gamma'\cdot P + c'\), with \(\alpha',\beta',\gamma' \ll \alpha,\beta,\gamma\)

Observed result: ~**1500x** lower cycle threshold to reach stable output.

For the HDL/Verilator backend, asymptotics are likewise unchanged, but constants improve less because loop bodies are still executed in the HDL state machine (not replaced by fully parallel dedicated datapaths), consistent with the observed **~2x**.

## Validity notes

- This study measures cycle budget to stable framebuffer output in this emulator, not wall-clock hardware performance.
- Thresholds depend on tested cycle grids; the true minimum may be lower than the lowest passing point.
- Despite that, the gap is so large (orders of magnitude) that the qualitative conclusion is robust.

## Conclusion

The first x77 integration provides a clear practical win on both backends:

- `emulator_runner`: about **1500x** fewer cycles.
- `verilator_runner` (current HDL microcoded implementation): about **2x** fewer cycles.

Both preserve the same complexity class; gains come from improved constant factors. The remaining HDL gap is a microarchitecture opportunity (e.g., wider/parallel neural datapaths, reduced per-element FSM overhead, and tighter on-chip neural execution units).
