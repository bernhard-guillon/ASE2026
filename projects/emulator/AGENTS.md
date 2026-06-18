# Emulator + RTL Flow

## Overview

C++17 RV32I/F emulator with custom neural ISA extensions, Verilator RTL backend, and comprehensive test suite.

## Build

```bash
cmake -B build -S .
cmake --build build -j$(nproc)
```

Build output goes to `build/` (gitignored).

## Test Strategy

The test pipeline follows a layered approach:

1. **Train model** — Python training scripts produce `.pth` checkpoints (in `character-generation/`, `game-movement/`)
2. **Export weights** — `weight-export/export_generator.py` converts to JSON + binary
3. **Model compiler** — CMake custom commands run `model_compiler_interactive.py` to generate assembly from JSON
4. **Build ELF** — Assemble with `rv32as`, link with `riscv64-elf-ld`
5. **Blackbox tests** — Run on both `emulator_runner` and `verilator_runner` via CTest

For **combined models** (counter+chargen, mega-combined), specialized test targets are created in CMakeLists.txt. Currently only the squash model has dedicated verilator tests; counter+chargen and mega-combined are tested via emulator only.

For **interactive UI tests** (GUI, key input), the newest approach uses **TTY emulation** via `pty.openpty()`. This allows injecting real keystrokes and capturing ASCII framebuffer output. Three TTY test targets exist: `python/squash/gui_tty`, `python/squash/blackbox_tty`, `python/squash/blackbox_tty_verilator`.

All tests are registered in CMake and run in CI via `ctest`.

## Testing Commands

```bash
# Unit tests (fast, ~200 tests)
./build/test_*

# All tests via CTest (includes long-running blackbox tests)
ctest --test-dir build --output-on-failure

# Specific blackbox test categories
ctest --test-dir build -R "asm"
ctest --test-dir build -R "parity"
ctest --test-dir build -R "verilator"
ctest --test-dir build -R "tty"
```

### Test structure

- `utest/` — GoogleTest unit tests (instruction decode, execution, memory, CPU, neural ops, etc.)
- `blackbox_tests/asm/` — assembly test programs run on the emulator
- `blackbox_tests/c/` — C test programs compiled with riscv64-elf-gcc
- `blackbox_tests/*.py` — Python-based integration tests (pytest)
- `blackbox_tty_test.py` — TTY-based interactive UI test (PTY emulation)
- `cmake/BlackboxTests.cmake` — registers assembly and C blackbox tests
- `cmake/PurityTesting.cmake` — Rust vs GNU assembler parity tests

## Running

```bash
# Emulator (software simulation)
./build/emulator_runner <elf> --char-code <N> --cycles <N> --dump-framebuffer

# Verilator (hardware simulation)
./build/verilator_runner <elf> --char-code <N> --cycles <N> --render-framebuffer
```

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

## CMake Integration

- Rust assembler is built automatically via `cargo build --release` during CMake configure
- Blackbox test ELFs are assembled with `rv32as` (Rust) and linked with `riscv64-elf-ld`
- Bootloader ELF files are generated from model JSON via `compile_model_bootloader.py`
- Model JSON is converted to C headers via `model_to_header/` (Rust tool)

## Neural Model Pipeline

1. Python training scripts produce `.pth` checkpoints
2. `weight-export/export_generator.py` converts to JSON + binary
3. CMake's `model_to_header` converts JSON to `model.h` headers
4. Programs include `model.h` and use neural instructions to run inference

## Code Style

- C++17, no exceptions in core emulator (used in tests)
- Verilog follows existing patterns in `hdl/rtl/`
- Python scripts follow existing patterns in the same directory
