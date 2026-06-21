# ASE2026 — Neural Inference as the Operating System on Minimal RISC-V

> Advanced Systems Engineering (ASE2026), Paris Lodron University of Salzburg
> Author: Bernhard Guillon
> Supervisor: Univ.-Prof. Dipl.-Inform. Dr.-Ing. Christoph Kirsch

[![Emulator Build & Tests](https://github.com/bernhard-guillon/ASE2026/actions/workflows/emulator-tests.yml/badge.svg)](https://github.com/bernhard-guillon/ASE2026/actions/workflows/emulator-tests.yml)
[![Build PDF](https://github.com/bernhard-guillon/ASE2026/actions/workflows/build-pdf.yml/badge.svg)](https://github.com/bernhard-guillon/ASE2026/actions/workflows/build-pdf.yml)

[Latest Paper PDF](https://github.com/bernhard-guillon/ASE2026/releases/download/ase2026-paper-latest/ase2026-latest.pdf)
Fallback: [latest release notes](https://github.com/bernhard-guillon/ASE2026/releases/latest)

## Problem Statement

Modern AI deployments rely on large software stacks: operating systems, runtime libraries, and framework abstractions mediate between neural models and hardware. This project investigates the opposite direction: how far can a compact execution stack be pushed when neural operations are represented as first-class ISA extensions on a minimal RISC-V core?

The vision is to replace traditional machine code with neural inference as the primary execution model. A 162-line `runtime.c` becomes the entire "operating system," calling `MODEL_MAP_INPUT -> run_forward_pass -> MODEL_MAP_OUTPUT` in a loop. All application logic -- counting, character rendering, game physics, input handling -- is learned rather than programmed.

**Research question:** Can a minimal RISC-V system use neural inference as its primary computation model, replacing traditional OS and application code?

## Contributions

1. **Descriptor-based neural ISA**: A 32-byte descriptor struct passed via registers specifies input/output buffers, weights, and dimensions. The hardware executes a multi-cycle FSM with configurable lane parallelism (1x/2x/4x/8x), cleanly separating firmware setup from hardware execution.

2. **Block-diagonal model composition**: Independently trained MLPs are merged into a single weight matrix via a declarative glue JSON format. A Rust compiler reads the glue, assembles block-diagonal weights, and emits C macros for input/output mapping. No retraining is required.

3. **Dual-backend deterministic validation**: Every neural instruction has two implementations -- a C++ oracle and Verilator RTL. Automated CI tests enforce bit-exact byte-level parity between them.

4. **OS-like neural task switching**: A learned router MLP switches between sub-models based on keyboard input, mimicking process scheduling. Background tasks can run with or without updates, analogous to context switching and preemption.

## Benchmark Highlight

From `documentation/collected-data/phase25-neural-lane-cycle-comparison.json`:

| Backend | Variant | Cycles | Speedup vs Baseline |
|---------|---------|--------|---------------------|
| Verilator | Baseline | 4,000,000 | 1.00x |
| Verilator | x7b-8lane | 400,000 | 10.00x |
| Verilator | x7b-8lane-pmac | 200,000 | 20.00x |
| Verilator | x7b-8lane-pmac4 | 150,000 | 26.67x |
| C++ | Baseline | 3,000,000 | 1.00x |
| C++ | x77 (optimized) | 2,000 | 1,500x |
| C++ | x7b-8lane-pmac4 | 1,500 | 2,000x |

## End-to-End Pipeline

1. Train a compact PyTorch character generator model (255 -> 256 -> 256 -> 400)
2. Export weights to an intermediate JSON and compact binary format
3. Compile model-driven programs with custom neural mnemonics
4. Assemble with a Rust-based RISC-V assembler (`rv32as`) and GNU link flow
5. Run on both a C++ emulator and a Verilator RTL backend
6. Validate determinism and parity with automated differential tests

## Repository Map

| Subproject | Path | Purpose |
|------------|------|---------|
| Character generation | `projects/character-generation/` | Train and validate the PyTorch model (255 -> 256 -> 256 -> 400) |
| Game movement | `projects/game-movement/` | Train deterministic 20x20 player-movement transitions (state + action -> next state) |
| Weight export | `projects/weight-export/` | Convert PyTorch checkpoints into JSON + compact binary payloads |
| RV32 assembler | `projects/rv32_assembler/` | Assemble RV32I/RV32F + project neural custom instructions |
| Emulator + RTL flow | `projects/emulator/` | Execute binaries on C++ emulator and Verilator; run full validation |

## Documentation

| Document | Path | Purpose |
|----------|------|---------|
| Paper source | `documentation/ase2026.md` | Full paper (Markdown + LaTeX) |
| Build guide | `BUILD.md` | Consolidated build instructions for all targets |
| Getting started | `GETTING_STARTED.md` | First-time setup and usage guide |
| Project log | `documentation/project-log.md` | Consolidated project log |
| Neural machine reference | `documentation/neural-risc-v-machine.md` | Neural machine reference |
| Benchmark data | `documentation/collected-data/` | Raw benchmark data in JSON |
| Audit | `AUDIT.md` | Project audit with ratings (includes paper quality assessment) |
| Audit guide | `AUDIT_GUIDE.md` | How to audit this project (includes paper audit questions) |
| Model composition | `projects/emulator/COMBINING.md` | Block-diagonal model merging methodology |
| JSON schemas | `schemas/glue.schema.json`, `schemas/model.schema.json` | Validation schemas for glue and model JSON files |

## Paper

The full project paper is at [`documentation/ase2026.pdf`](documentation/ase2026.pdf) and can be compiled from the Markdown source via the instructions in the [Documentation section](#documentation). The latest release PDF is available from the badge at the top of this page.

## Project Audit

A comprehensive audit is available in [AUDIT.md](AUDIT.md), covering research quality, problem definition, implementation, documentation, paper quality, code quality, LLM/AI integrity, and numerical consistency.

## Custom Neural ISA

The project defines custom RISC-V instructions for neural operations:

| Instruction | Description |
|-------------|-------------|
| `NMATVEC` | Matrix-vector multiply |
| `NMATVEC4x` | Matrix-vector multiply (4x lane) |
| `NMATVEC8x` | Matrix-vector multiply (8x lane) |
| `NVRELU` | ReLU activation |
| `NVRELUX` | ReLU activation (extended) |
| `NVSIGPWL` | Sigmoid piecewise-linear |
| `NVCLUAMPU8` | Clamp to uint8 |
| `PMAC` variants | Lane-parallel packed multiply-accumulate |

## Build and Test

```bash
# Build emulator
cmake -S projects/emulator -B projects/emulator/build -DCMAKE_BUILD_TYPE=Release
cmake --build projects/emulator/build -j$(nproc)

# Run tests
ctest --test-dir projects/emulator/build --output-on-failure

# Build Rust assembler
cargo build --release --manifest-path projects/rv32_assembler/Cargo.toml
```

## Subproject READMEs

- [Character Generation](projects/character-generation/README.md)
- [Game Movement](projects/game-movement/README.md)
- [Weight Export](projects/weight-export/README.md)
- [RV32 Assembler](projects/rv32_assembler/README.md)
- [Emulator](projects/emulator/README.md)

## CI Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `emulator-tests.yml` | Push to main/develop | Build and test emulator |
| `build-pdf.yml` | Push to main/develop | Rebuild paper PDF |
| `train-character-generation.yml` | Push to main/develop | Train character generation model |
