# ASE2026 — Neural-Driven Computing on a Minimal RISC-V Stack

## Overview

This repository implements an end-to-end neural execution toolchain: train a PyTorch model, export weights, compile programs with custom neural ISA extensions, assemble with a Rust-based RV32 assembler, and run on both a C++ emulator and Verilator RTL backend.

## Tech Stack

- **Emulator**: C++17, CMake, GoogleTest
- **RTL**: Verilog (Verilator 5.x)
- **Assembler**: Rust (edition 2021)
- **ML Training**: Python 3.14, PyTorch, NumPy
- **RISC-V Toolchain**: `riscv64-elf-gcc`, `riscv64-elf-as`, `riscv64-elf-ld`
- **CI**: GitHub Actions

## Repository Structure

| Directory | Purpose |
|---|---|
| `projects/emulator/` | C++ emulator, Verilator RTL, blackbox tests, CMake build |
| `projects/character-generation/` | PyTorch model training (255->256->256->400) |
| `projects/game-movement/` | Deterministic 20x20 player-movement transitions |
| `projects/weight-export/` | Export PyTorch checkpoints to JSON + binary |
| `projects/rv32_assembler/` | Rust RV32I/F assembler with custom neural instructions |
| `documentation/` | Paper, presentation, benchmark data |

## Build Commands

```bash
# Full emulator build
cmake -S projects/emulator -B projects/emulator/build
cmake --build projects/emulator/build -j$(nproc)

# Run unit tests
./projects/emulator/build/test_*

# Run all tests (includes long-running blackbox tests)
ctest --test-dir projects/emulator/build --output-on-failure

# Build Rust assembler standalone
cargo build --release --manifest-path projects/rv32_assembler/Cargo.toml
```

## Key Conventions

- Build output goes to `projects/emulator/build/` (gitignored)
- Each Python subproject has its own `requirements.txt` and `.venv` (not committed)
- Generated model files (`*.json`, `*.bin` in weight-export) are tracked in git as reference data
- No comments in code unless explicitly asked for
- Follow existing code patterns in each subproject
- C++ standard: C++17. Rust edition: 2021.

## CI Workflows

- `emulator-tests.yml` — builds and tests the emulator on every push
- `build-pdf.yml` — rebuilds the paper PDF when documentation changes
- `train-character-generation.yml` — trains the character generation model

## Custom Neural ISA

The project defines custom RISC-V instructions for neural operations:
- `NMATVEC` / `NMATVEC4x` / `NMATVEC8x` — matrix-vector multiply
- `NVRELU` / `NVRELUX` — ReLU activation
- `NVSIGPWL` — sigmoid piecewise-linear
- `NVCLUAMPU8` — clamp to uint8
- PMAC variants — lane-parallel packed multiply-accumulate

These are encoded in `projects/emulator/Instruction.{h,cpp}` and `projects/emulator/NeuralOps.{h,cpp}`.
