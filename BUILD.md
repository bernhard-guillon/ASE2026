# Build Guide

This document consolidates all build instructions for the emulator, RTL backend, and model pipeline.

## Prerequisites

- C++17 compiler (`g++` or `clang++`)
- CMake ≥ 3.14
- Rust toolchain (`cargo`) — for assembler and model tools
- RISC-V toolchain (`riscv64-elf-gcc`, `riscv64-elf-as`, `riscv64-elf-ld`)
- Python ≥ 3.10 — for training scripts and integration tests
- Verilator 5.x (optional) — for RTL hardware simulation

## Quick Build

```bash
cmake -S projects/emulator -B projects/emulator/build
cmake --build projects/emulator/build -j$(nproc)
```

Output goes to `projects/emulator/build/` (gitignored).

## Build Targets

Build individual ELF binaries:

```bash
cmake --build projects/emulator/build --target neural_elf              # Character generation
cmake --build projects/emulator/build --target movement_elf            # Game movement
cmake --build projects/emulator/build --target counter255_elf          # Counter model
cmake --build projects/emulator/build --target counter_chargen_combined_elf  # Combined models
cmake --build projects/emulator/build --target mega_combined_elf       # Mega combined
cmake --build projects/emulator/build --target squash_elf              # Squash game
```

## Running

```bash
# Emulator (software simulation)
./projects/emulator/build/emulator_runner \
  projects/emulator/build/neural-op-enhance8pmac4.elf \
  --char-code 65 --cycles 10000 --render-framebuffer

# Verilator (hardware simulation)
./projects/emulator/build/verilator_runner \
  projects/emulator/build/neural-op-enhance8pmac4.elf \
  --char-code 65 --render-framebuffer

# GUI mode (requires display)
./projects/emulator/build/emulator_runner \
  projects/emulator/build/squash.elf --gui
```

## Testing

### Run All Tests

```bash
ctest --test-dir projects/emulator/build --output-on-failure
```

### Run Specific Test Categories

```bash
# Unit tests (fast, ~292 tests)
./projects/emulator/build/test_*

# Blackbox tests only
ctest --test-dir projects/emulator/build -R "^blackbox/" --output-on-failure

# RTL parity tests
ctest --test-dir projects/emulator/build -R "^parity/" --output-on-failure

# Assembler tests
ctest --test-dir projects/emulator/build -R "^asm" --output-on-failure

# Verilator differential tests
ctest --test-dir projects/emulator/build -R "^python/verilator/differential_validation$" --output-on-failure

# TTY/interactive tests
ctest --test-dir projects/emulator/build -R "^tty" --output-on-failure
```

### Test Structure

- `utest/` — GoogleTest unit tests (instruction decode, execution, memory, CPU, neural ops)
- `blackbox_tests/asm/` — assembly test programs run on the emulator
- `blackbox_tests/c/` — C test programs compiled with riscv64-elf-gcc
- `blackbox_tests/*.py` — Python-based integration tests (pytest)
- `blackbox_tty_test.py` — TTY-based interactive UI test (PTY emulation)

## Neural Model Pipeline

```
Train (.pth) → Export (JSON) → Compile (assembly) → Assemble (ELF) → Run
```

1. **Train** model in Python (`projects/character-generation/`, `projects/game-movement/`)
2. **Export** weights via `projects/weight-export/export_generator.py`
3. **Compile** model into assembly via CMake custom commands (`model_compiler_interactive.py`)
4. **Assemble** with Rust assembler (`rv32as`) and link with `riscv64-elf-ld`
5. **Run** on emulator or Verilator RTL backend

## CMake Integration

- Rust assembler built automatically via `cargo build --release` during CMake configure
- Blackbox test ELFs assembled with `rv32as` (Rust) and linked with `riscv64-elf-ld`
- Bootloader ELFs generated from model JSON via `compile_model_bootloader.py`
- Model JSON converted to C headers via `model_to_header/` (Rust tool)

## Key Source Files

| File | Purpose |
|---|---|
| `CPU.{h,cpp}` | Register file, program counter |
| `Instruction.{h,cpp}` | Instruction decoding (RV32I/F + custom neural) |
| `Emulator.{h,cpp}` | Main execution loop, ELF loading |
| `Memory.{h,cpp}` | Memory subsystem, syscalls |
| `NeuralOps.{h,cpp}` | Neural instruction implementations |
| `emulator_runner.cpp` | CLI entry point |
| `hdl/rtl/` | Verilog RTL sources |
| `hdl/sim/` | Verilator C++ simulation wrapper |

## Troubleshooting

**Missing `riscv64-elf-gcc`:**
Install a RISC-V bare-metal toolchain. On Ubuntu: `apt install gcc-riscv64-unknown-elf` or build from source.

**Missing Rust/Cargo:**
Install Rust: `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`

**Verilator tests fail:**
Verilator is optional. Skip RTL tests by not running `ctest -R "verilator"`.

**Python tests fail:**
Ensure Python ≥ 3.10 is installed and accessible as `python3`.

**Errors about missing files:**
1. Make sure you're in the project root directory
2. Make sure you've built the targets first
3. Never manually create or delete files in `build/` — let CMake manage it
