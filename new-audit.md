# Project Audit: Neural-Driven Computing on Minimal RISC-V

## The Vision

**Replace traditional machine code with neural inference as the primary execution model.**

Step by step, the project proves that trained neural networks can perform tasks normally done by hand-written RISC-V code: counting, character rendering, game-state transitions, input handling — all through a shared neural inference pipeline. The operating system shrinks to a 141-line `runtime.c` that calls `MODEL_MAP_INPUT → run_forward_pass → MODEL_MAP_OUTPUT` in an infinite loop. Everything else is learned.

---

## What Makes This Project Unique (vs. Related Work)

| Dimension | This project | Typical approach |
|-----------|-------------|-----------------|
| **Neural ISA** | Descriptor-based calling convention (32-byte struct via register) | SIMD/vector extensions (RVV, P-ext) or coprocessor offload (NVDLA) |
| **RTL validation** | Dual-backend: identical C++ oracle + Verilator RTL with automated differential tests | Single implementation or software-only |
| **Model composition** | Block-diagonal weight splicing via glue JSON + Rust compiler | Weight averaging, task vectors, or learned projectors |
| **Deployment** | Bare-metal RISC-V ELF, no OS, no ML framework | Linux + PyTorch/TF runtime or RTOS + driver stack |
| **Custom opcode space** | Two opcodes (0x77, 0x7B) with 10 sub-ops for MLP primitives | Single-purpose accelerator or full vector extension |
| **Interactive neural apps** | Shared-memory protocol (framebuffer + done flag + key register) | Polling or interrupt-driven I/O through kernel |

### Related work

**RISC-V neural ISA extensions:**
- **RV-SCNN** (IEEE TCAD 2025) — SIMD custom ops for CNN/SNN, uses coprocessor-like offload, verifed on CV32E40P
- **MARVEL** (arXiv 2025) — generates model-class-specific RISC-V extensions via ASIP Designer + TVM, targets CNNs
- **FPGA-accelerated RISC-V** (arXiv 2024) — 4 custom ops (VCONV, GEMM, RELU, CUSTOM) on PYNQ-Z2
- **Mixed-precision NN on RISC-V** (arXiv 2024) — 3 MAC instructions for mixed-precision, verified on Ibex core
- **SPEED** (arXiv 2024) — RVV-based multi-precision vector processor

Our project differs in: **descriptor-based abstraction** (not SIMD), **MLP focus** (not CNN), **complete dual-backend oracle+RTL validation**, and **interactive model composition** at the compiler level.

**AI-as-OS / bare-metal AI:**
- **nCPU** (Price, 2025) — fully differentiable CPU where every ALU op is a trained NN. Most radical version of the same vision. Different: everything is neural, runs on GPU, proven on Apple Silicon Metal. Our approach keeps conventional RISC-V for control flow and uses neural ops for data path.
- **embodiOS** (2025) — LLM as OS on x86_64 UEFI, runs GGUF models. Different: runs LLMs, not custom neural instructions, on x86 not RISC-V.
- **OSymbiote** (2026) — AI agent as PID1 on Linux. Different: agent controls Linux, not running neural inference natively.
- **OO (Operating Organism)** (2025) — bare-metal Mamba/LLaMA inference via UEFI. Different: LLMs on x86_64, not our lightweight MLP approach.
- **AEG** (arXiv 2025) — bare-metal framework for AMD AI Engine arrays, 9.2x efficiency vs Linux. Different: targets specialized accelerator arrays, not custom RISC-V ISA.
- **NVDLA + RISC-V bare-metal** (arXiv 2025) — tight NVDLA-RISC-V coupling with bare-metal assembly. Different: uses NVDLA as coprocessor, needs assembly traces per model.

---

## Contribution Candidates

### 1. Descriptor-Based Neural Custom Instructions for RISC-V

Most RISC-V neural extensions use SIMD or vector approaches. Our **descriptor-based calling convention** is novel for MLP inference:

```c
neural_desc_t desc = {
    .input_ptr = INPUT_BUF,
    .weights_ptr = weights_addr,
    .bias_ptr = biases_addr,
    .output_ptr = output_addr,
    .input_len = input_size,
    .output_len = output_size,
    .flags = 0, .reserved = 0
};
neural_matvec(&desc);  // single custom instruction 0x557B
```

The 32-byte descriptor is read from memory by the hardware, which then executes a multi-cycle FSM with configurable lane parallelism (1x/2x/4x/8x). This cleanly separates concern: firmware sets up a struct, hardware executes it.

**Evidence:** `projects/emulator/runtime.c:28-33` (software) + `projects/emulator/hdl/cpu.v` (RTL FSM with `ST_NMATVEC_DESC_READ` through `ST_NMATVEC_STORE_COMMIT`).

**Novelty:** Most academic projects and commercial offerings either (a) use vector/SIMD extensions (RVV, P-ext), (b) offload to a coprocessor (NVDLA, Gemmini), or (c) generate model-specific hardware accelerators. The descriptor-based calling convention is a middle ground: it is a fixed instruction that can execute any MLP layer by changing the descriptor contents.

---

### 2. Dual-Backend Deterministic Validation (Oracle + RTL)

Every neural instruction has two implementations:
- **C++ oracle** (`NeuralOps.cpp`) — portable, bounds-checked, readable reference
- **Verilator RTL** (`hdl/cpu.v`) — hardware FSM with lane-parallel PMAC

The two are validated against each other by:
- Running identical ELF binaries on both backends
- Comparing framebuffer output byte-for-byte
- Automated CI gate: `blackbox_tests/test_counter255_runtime_smoke.py` and others

**Evidence:** CI workflow `.github/workflows/emulator-tests.yml` runs both emulator and Verilator tests, including differential comparison.

**Novelty:** Most RISC-V custom instruction projects validate either in simulation only or against a software model at the functional level. Ours enforces bit-exact byte-level parity between a portable C++ oracle and the Verilator RTL, with automated regression tests in CI.

---

### 3. Block-Diagonal Model Composition via Glue JSON

The `model_to_header` Rust compiler can merge independently trained models into a single block-diagonal weight matrix:

```json
{"merged_layers": [{"blocks": [
    {"model": "counter", "layer": 0, "out_offset": 0},
    {"model": "chargen", "layer": 0, "out_offset": 256}
]}]}
```

This produces an ELF that runs both models in a single inference pipeline. The output is partitioned: `buf[0..399]` = chargen pixels, `buf[400..654]` = counter state. The counter auto-advances each frame unless a keypress overrides it (one-shot `model_key` consumption).

**Evidence:** `projects/emulator/model_to_header/src/main.rs:386-482` (build_merged), `projects/emulator/COMBINING.md`, `projects/emulator/block-diagonal-composition.md`.

**Novelty:** The glue JSON approach is a practical compiler technique for model composition. Existing work (FS-Merge, Merging of Neural Networks, LoRA-LEGO) either requires training or uses different forms of concatenation. Our approach is declarative, training-free, and lossless for independent models.

---

### 4. Neural Inference Replacing Application Logic

The combined counter+chargen model replaces what would normally be:
- A `for` loop with modulo counter (software)
- A character lookup table or bitmap font (data)
- Framebuffer memory copy (software)
- Input event handling (driver/OS)

...all with a single neural inference call. The game-movement model similarly replaces:
- A game state machine (software)
- Collision detection logic (software)
- Action mapping (software)

...with a learned neural transition function.

**Evidence:** `projects/emulator/model_to_header/src/main.rs:240-338` (four input-mapping arms showing different ways inference replaces code), `projects/emulator/emulator_runner.cpp` (GUI loop that just polls framebuffer + done flag).

**Novelty:** While projects like nCPU and OSymbiote propose AI-as-OS conceptually, this project demonstrates the pattern concretely with working neural models that replace specific application functions. The counter+chargen combined model is a concrete demonstration: without inference, you'd need a counter loop + glyph lookup + framebuffer render. With inference, it's just `run_forward_pass()`.

---

### 5. Lane-Parallel PMAC Datapath with 26.67x Speedup

The Verilator RTL implements a multi-cycle matvec FSM that exploits quad-port memory (4 concurrent data reads) to issue up to 4 multiply-accumulates per cycle:

| Variant | Lanes | MACs/cycle | Cycles (benchmark) |
|---------|-------|------------|-------------------|
| Baseline | 1 | 1 | 4,000,000 |
| PMAC4 | 8 | 4 | 150,000 |

**Speedup: 26.67x**

**Evidence:** `documentation/collected-data/phase25-neural-lane-cycle-comparison.json`, `projects/emulator/hdl/cpu.v` (ST_NMATVEC_SCRATCH_STREAM_PMAC state).

**Novelty:** The PMAC datapath is a microarchitecture contribution for resource-constrained RISC-V cores. Unlike GPU-style wide SIMD, it uses a scratchpad bank (8 entries) + incremental lane-width configuration to adapt parallelism at runtime. The 26.67x speedup on a single-cycle RV32IF core shows that simple hardware additions (quad-port memory, scratchpad prefetch) can dramatically accelerate neural inference.

---

## Assessment Summary

| Area | Rating | Why |
|------|--------|-----|
| **Novelty** | 8/10 | Descriptor-based neural ISA + block-diagonal composition + dual-backend validation is a unique combination |
| **Completeness** | 9/10 | Working end-to-end: PyTorch → ELF → C++ emulator → Verilator RTL, with CI tests |
| **Related work** | 7/10 | Could cite more (nCPU, OSymbiote, MARVEL, RV-SCNN); block-diagonal-composition.md now covers this |
| **AI-as-OS vision** | 6/10 | Pattern demonstrated concretely but not yet generalized — needs more model types and OS primitives replaced |
| **Writeup** | 5/10 | Need a paper that positions descriptor-based ISA vs. SIMD/vector/coprocessor approaches |

### What would make this a strong publication

1. **Position paper** arguing that descriptor-based neural custom instructions are the right abstraction for lightweight MLP inference on tiny RISC-V cores — simpler than RVV, more flexible than fixed accelerators.
2. **Comparison benchmark** against a software-only baseline (same RISC-V core, same model, but using standard floating-point instructions instead of custom ops) — measure cycle count with and without neural ISA.
3. **Generalize the composition framework** to support more model types (convolution, attention) and more complex composition patterns (feedback loops, multi-model arbitration).
4. **Formalize the AI-as-OS pattern** with a taxonomy of OS primitives that can be replaced by neural inference (state machines → neural transitions, lookup tables → neural function approximation, event handlers → neural classification).
