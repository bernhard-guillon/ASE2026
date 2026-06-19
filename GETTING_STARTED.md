# Getting Started

This guide walks you through setting up, building, and running the project for the first time.

## Prerequisites

Install these tools before proceeding:

| Tool | Version | Install |
|------|---------|---------|
| C++ compiler | C++17 | `g++` or `clang++` |
| CMake | ≥ 3.14 | Package manager |
| Rust | stable | `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \| sh` |
| RISC-V toolchain | riscv64 | `riscv64-elf-gcc`, `riscv64-elf-as`, `riscv64-elf-ld` |
| Python | ≥ 3.10 | Package manager |
| Verilator | 5.x (optional) | Package manager for RTL backend |

## Quick Start

### 1. Build the Emulator

```bash
cmake -S projects/emulator -B projects/emulator/build
cmake --build projects/emulator/build -j$(nproc)
```

This compiles the C++ emulator, Rust assembler, and all model ELFs.

### 2. Run a Program

```bash
# Run character generation on the emulator
./projects/emulator/build/emulator_runner \
  projects/emulator/build/neural-op-enhance8pmac4.elf \
  --char-code 65 --cycles 10000 --render-framebuffer

# Run on the Verilator RTL backend
./projects/emulator/build/verilator_runner \
  projects/emulator/build/neural-op-enhance8pmac4.elf \
  --char-code 65 --render-framebuffer
```

### 3. Run All Tests

```bash
ctest --test-dir projects/emulator/build --output-on-failure
```

This runs 292 unit tests + 91 blackbox tests + Python integration tests.

## Build Targets

Key ELF targets you can build individually:

```bash
cmake --build projects/emulator/build --target neural_elf          # Character generation
cmake --build projects/emulator/build --target movement_elf        # Game movement
cmake --build projects/emulator/build --target counter255_elf      # Counter model
cmake --build projects/emulator/build --target counter_chargen_combined_elf  # Combined models
cmake --build projects/emulator/build --target mega_combined_elf   # Mega combined
```

## Test Categories

Run specific test suites:

```bash
# Unit tests only
ctest --test-dir projects/emulator/build -R "^test_" --output-on-failure

# Blackbox tests only
ctest --test-dir projects/emulator/build -R "^blackbox/" --output-on-failure

# RTL parity tests
ctest --test-dir projects/emulator/build -R "^parity/" --output-on-failure

# Assembler tests
ctest --test-dir projects/emulator/build -R "^asm" --output-on-failure

# Verilator differential tests
ctest --test-dir projects/emulator/build -R "^python/verilator/differential_validation$" --output-on-failure
```

## Project Layout

```
ASE2026/
├── projects/
│   ├── emulator/          # Main build directory
│   │   ├── CMakeLists.txt # Build configuration
│   │   ├── build/         # Build output (generated)
│   │   ├── src/           # C++ source
│   │   ├── tests/         # Unit tests (GoogleTest)
│   │   └── python/        # Integration tests
│   ├── rv32_assembler/    # Rust assembler
│   ├── character-generation/  # PyTorch training
│   ├── weight-export/     # Model export
│   └── game-movement/     # Movement model training
└── documentation/         # Paper and docs
```

## Workflow Overview

The typical development workflow:

1. **Train** a model in Python (`projects/character-generation/`)
2. **Export** weights to JSON/binary (`projects/weight-export/`)
3. **Compile** model into a RISC-V ELF binary (CMake build)
4. **Assemble** neural ISA extensions (Rust assembler, built by CMake)
5. **Run** on emulator or Verilator RTL backend
6. **Validate** output with test suite

## Troubleshooting

**Build fails with missing `riscv64-elf-gcc`:**
Install a RISC-V bare-metal toolchain. On Ubuntu: `apt install gcc-riscv64-unknown-elf` or build from source.

**Build fails with missing Rust/Cargo:**
Install Rust: `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`

**Verilator tests fail:**
Verilator is optional. Skip RTL tests by not running `ctest -R "verilator"`.

**Python tests fail:**
Ensure Python ≥ 3.10 is installed and accessible as `python3`.
