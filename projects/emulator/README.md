# RV32I RISC-V Emulator

A complete emulator for the RV32I RISC-V instruction set, implemented in C++ with comprehensive unit tests and blackbox integration tests.

## Features

- **Full RV32I Instruction Set Support**
  - All 6 instruction formats (R, I, S, B, U, J)
  - Arithmetic operations (ADD, SUB, AND, OR, XOR, SLT, SLTU)
  - Shift operations (SLL, SRL, SRA with masking)
  - Load/Store operations (LW, LH, LB, LBU, LHU, SW, SH, SB)
  - Branch instructions (BEQ, BNE, BLT, BGE, BLTU, BGEU)
  - Jump instructions (JAL, JALR)
  - Upper immediates (LUI, AUIPC)

- **System Calls Support**
  - `write(fd, buf, count)` syscall 64 - Write to stdout/stderr
  - `exit(status)` syscall 93 - Exit with status code
  - `brk(addr)` syscall 214 - Heap break management
  - `mmap2(addr, len, prot, flags, fd, offset)` syscall 192 - Memory mapping
  - `munmap(addr, len)` syscall 215 - Memory unmapping
  - ECALL instruction for syscall handling

- **C Program Support**
  - Bare-metal C program execution with crt0 runtime
  - Dynamic memory allocation with malloc/free
  - Local variables, arrays, and function calls
  - Stack-based calling conventions
  - Exit code support

- **Comprehensive Testing**
  - 135 unit tests (GoogleTest)
  - 26 blackbox integration tests
  - 4 malloc/dynamic memory tests
  - 140+ total tests with 100% pass rate

## Prerequisites

### Emulator Build
- CMake 3.14+
- C++17 compatible compiler
- GoogleTest (auto-fetched by CMake)

### Running Programs
- RISC-V GNU toolchain (optional, for compiling test programs):
  ```bash
  # On Arch Linux:
  sudo pacman -S riscv64-elf-gcc riscv64-elf-binutils
  
  # Or from AUR:
  yay -S riscv64-unknown-elf-gcc
  ```

## Building

```bash
cd projects/emulator
mkdir -p build && cd build
cmake ..
cmake --build .
```

## Running Tests

### Unit Tests (GoogleTest)
```bash
# Run all tests
ctest --verbose

# Run specific test suite
./test_memory
./test_cpu
./test_instruction
./test_execution
./test_emulator
```

### Blackbox Tests
```bash
# Using CMake target
cmake --build . --target blackbox_tests

# Or directly with Python
../run_blackbox_tests.py
../run_blackbox_tests.py -v                    # Verbose with diffs
../run_blackbox_tests.py -p basic              # Match pattern
../run_blackbox_tests.py -v -p fibonacci       # Verbose + pattern
```

### CTest (includes both unit and blackbox)
```bash
cd build
ctest                    # Run all tests
ctest --verbose          # Show output
ctest -R "blackbox"      # Run only blackbox tests
```

## Running Programs

### Using emulator_runner
```bash
# Manual workflow
riscv64-elf-as -march=rv32i -mabi=ilp32 -o program.o program.s
riscv64-elf-ld -m elf32lriscv -T linker.ld -o program.elf program.o
riscv64-elf-objcopy -O binary program.elf program.bin
./build/emulator_runner program.bin
```

### Running C Programs
```bash
# Compile C program with stdlib
riscv64-elf-gcc -march=rv32i -mabi=ilp32 -nostdlib \
    -o program.elf crt0.s program.c malloc.c syscalls.s -T linker.ld
riscv64-elf-objcopy -O binary program.elf program.bin
./build/emulator_runner program.bin

# With verbose output
./build/emulator_runner program.bin --verbose
```

### Using convenience scripts
```bash
# Compile and run hello.s
./run_hello.sh

# With verbose output
./build/emulator_runner program.bin --verbose
```

## Project Structure

```
emulator/
├── Memory.h/cpp              # Memory subsystem (read8, write8, read32, write32)
├── CPU.h/cpp                 # CPU state (registers, PC, execute)
├── Instruction.h/cpp         # Instruction decoder (all 6 formats)
├── Emulator.h/cpp            # Main emulator (CPU + Memory + Syscalls)
├── emulator_runner.cpp       # Binary loader and execution harness
├── test_*.cpp                # Unit tests (GoogleTest)
├── blackbox_tests/           # Integration test cases
│   ├── basic/
│   │   ├── hello/            # Test: print "Hello, World!"
│   │   ├── arithmetic/       # Test: ALU operations
│   │   ├── memory/           # Test: Load/Store operations
│   │   └── fibonacci/        # Test: Function calls & recursion
│   └── branches/
│       └── conditional/      # Test: All branch types
├── run_blackbox_tests.py     # Blackbox test runner (Python)
├── hello.s                   # Example: Hello World assembly
├── run_hello.sh              # Example: Build & run script
├── linker.ld                 # Linker script for test binaries
├── CMakeLists.txt            # Build configuration
├── chatlog.md                # Design discussion history
│
├── BOOTLOADER SYSTEM (Phases 1-6)
├── ──────────────────────────
├── model_compiler.py         # Phase 1-2: JSON → Binary + Assembly (642 lines)
├── compile_model_bootloader.py # Phase 4: Full pipeline orchestration (420 lines)
├── bootloader.ld             # Phase 3: Memory layout linker script (65 lines)
├── cmake/
│   └── BootloaderBuild.cmake # Phase 5: CMake integration module (210 lines)
├── test_model_compiler.py    # Phase 1 unit tests
├── test_model_compiler_blackbox.py # Phase 1 blackbox tests
├── test_bootloader_phase2.py    # Phase 2 unit tests
├── test_bootloader_phase2_blackbox.py # Phase 2 blackbox tests
├── test_bootloader_phase3.py    # Phase 3 unit tests
├── test_bootloader_phase3_blackbox.py # Phase 3 blackbox tests
├── test_bootloader_phase3_integration.py # Phase 3 integration tests
├── test_bootloader_phase4_integration.py # Phase 4 integration tests
├── test_bootloader_phase5.py # Phase 5 unit tests
├── test_bootloader_phase6_integration.py # Phase 6 comprehensive tests (500+ lines)
│
├── DOCUMENTATION
├── ──────────────
├── docs/
│   ├── guides/                        # Implementation guides and references
│   │   ├── BOOTLOADER_IMPLEMENTATION.md # Complete implementation guide (13KB)
│   │   ├── BOOTLOADER_QUICK_START.md   # Quick reference and getting started (7KB)
│   │   ├── PHASE5_CMAKE_GUIDE.md       # CMake usage guide (3.6KB)
│   │   ├── PHASE6_TESTING_GUIDE.md     # Testing documentation (5.9KB)
│   │   ├── C_PROGRAM_GUIDE.md          # C program execution guide
│   │   └── LINUX_SYSCALLS.md           # Supported syscalls reference
│   ├── planning/                      # Design and planning documents
│   │   ├── BOOTLOADER_PLAN.md          # 7-phase architecture plan
│   │   ├── emulator-plan.md            # Emulator design plan
│   │   └── chatlog.md                  # Design discussion history
│   ├── summaries/                     # Phase reports and verification summaries
│   │   ├── PHASE1_VERIFICATION_COMPLETE.md
│   │   ├── PHASE2_SUMMARY.md
│   │   ├── PHASE3_SUMMARY.md
│   │   ├── PHASE4_SUMMARY.md
│   │   ├── STATIC_CHAR_GEN_REPORT.md
│   │   ├── MODEL_LOADING_REPORT.md
│   │   ├── SESSION_SUMMARY.md
│   │   ├── TEST_ORGANIZATION.md
│   │   └── UNIT_TEST_GAPS.md
│   └── summary.md                     # Overview summary

## Blackbox Testing

The blackbox test runner provides end-to-end validation by:
1. Discovering test programs in `blackbox_tests/`
2. Compiling with GNU RISC-V toolchain
3. Running in emulator_runner
4. Capturing stdout
5. Validating output and exit codes

Each test has three files:
- `test.s` - RV32I assembly source
- `expected.txt` - Expected stdout output
- `config.txt` - Test configuration (exit code, timeouts)

### Test Coverage
- **Basic Operations**: Arithmetic (ADD, SUB, AND, OR, XOR), immediate operations
- **Control Flow**: All 6 branch types, jumps (JAL, JALR), function calls
- **Memory**: Load/store with sign extension, different widths (byte, halfword, word)
- **Syscalls**: write() and exit() integration

## Bootloader System (Phases 1-6)

The bootloader system enables embedding pre-trained neural network models as ROM-like firmware in the RISC-V emulator.

### Quick Start

**Compile a model to bootloader:**
```bash
python3 compile_model_bootloader.py model.json -o bootloader.elf
```

**Or use CMake:**
```cmake
include(cmake/BootloaderBuild.cmake)
bootloader_build_system_init()
add_model_bootloader(my_model "model.json")
```

### Six-Phase Architecture

| Phase | Component | Output | Tests |
|-------|-----------|--------|-------|
| 1-2 | Model Compiler | Binary + Assembly | 23 |
| 3 | Linker Script | Memory layout | 59 |
| 4 | Pipeline | Orchestration | 13 |
| 5 | CMake | Build automation | 13 |
| 6 | Testing | Validation | 13 |

**Total: 243 tests (233 C++ emulator + 74 Python bootloader), 100% passing ✅**

### Bootloader Features

- **JSON Input**: Neural network specifications (layers, weights, biases)
- **Optimized Binary Format**: 28-byte header + layer table + data sections
- **RISC-V Code Generation**: Assembly with embedded data via `.incbin` directives
- **Linker Integration**: Memory regions (0x0-0x10000 code, 0x10000-0xFFFFF data)
- **Automated Pipeline**: Single command orchestrates compile → assemble → link → extract
- **CMake Integration**: `add_model_bootloader()` function for seamless build integration
- **Memory Verification**: Bootloader validates loaded data before execution
- **Comprehensive Testing**: End-to-end validation of ELF format, binary content, model loading

### Memory Layout

```
0x00000 - 0x10000   Bootloader Code (64 KB)
0x10000 - 0xF3C7F   Generator Model
0xF4ABC - 0xFFFFF   Recognizer Model
```

### Documentation

**Guides & References:**
- **[docs/guides/BOOTLOADER_IMPLEMENTATION.md](docs/guides/BOOTLOADER_IMPLEMENTATION.md)** - Complete implementation guide (13 KB)
  - Architecture, components, memory layout, file formats, usage examples
- **[docs/guides/BOOTLOADER_QUICK_START.md](docs/guides/BOOTLOADER_QUICK_START.md)** - Quick reference (7 KB)
  - One-minute overview, common commands, troubleshooting
- **[docs/guides/PHASE5_CMAKE_GUIDE.md](docs/guides/PHASE5_CMAKE_GUIDE.md)** - CMake integration (3.6 KB)
- **[docs/guides/PHASE6_TESTING_GUIDE.md](docs/guides/PHASE6_TESTING_GUIDE.md)** - Testing documentation (5.9 KB)
- **[docs/guides/C_PROGRAM_GUIDE.md](docs/guides/C_PROGRAM_GUIDE.md)** - C program execution guide
- **[docs/guides/LINUX_SYSCALLS.md](docs/guides/LINUX_SYSCALLS.md)** - Supported syscalls reference

**Design & Planning:**
- **[docs/planning/BOOTLOADER_PLAN.md](docs/planning/BOOTLOADER_PLAN.md)** - 7-phase architecture plan
- **[docs/planning/emulator-plan.md](docs/planning/emulator-plan.md)** - Emulator design plan
- **[docs/planning/chatlog.md](docs/planning/chatlog.md)** - Design discussion history

**Summaries & Verification:**
- **[docs/summaries/](docs/summaries/)** - Phase verification and test reports

### Example: Compile and Load Bootloader

```cpp
#include "Emulator.h"

// Compile model to ELF
// $ python3 compile_model_bootloader.py model.json -o bootloader.elf

// Load and run
Emulator emulator;
std::vector<uint32_t> bootloader = load_elf("bootloader.elf");
emulator.loadProgram(bootloader, 0x0);
emulator.run(10000);

std::cout << "Exit code: " << emulator.getExitCode() << std::endl;
```

## Architecture Decisions

- **Little-endian** byte ordering per RISC-V spec
- **x0 register** hardwired to zero (writes ignored, reads always 0)
- **Sign extension** for signed loads (LB, LH) and arithmetic right shift
- **JALR LSB clearing**: `(rs1 + offset) & ~1` as per RISC-V spec
- **Shift masking**: Shift amount masked to lower 5 bits
- **PC auto-increment**: +4 after most instructions; branches/jumps set PC directly

## Future Work

- [ ] M extension (MUL, MULH, DIV, REM) for multiplication/division
- [ ] More syscalls (open, read, close, malloc, brk)
- [ ] ELF file format support (currently raw binary only)
- [ ] Debugging features (single-step, breakpoints, instruction trace)
- [ ] Performance optimizations (instruction cache, JIT compilation)
- [ ] Additional test coverage (edge cases, stress tests)

## Statistics

- **Lines of Code**: ~2000 (core emulator)
- **Test Coverage**: 136 tests (99.3% pass rate initially, now 100%)
- **Instruction Count**: 47 instructions implemented
- **Syscalls**: 2 syscalls (write, exit)
- **Compilation Time**: ~5 seconds
- **Test Runtime**: ~0.4 seconds (all tests)

## References

- RISC-V Specification: https://riscv.org/
- RV32I Base Instruction Set: https://github.com/riscv/riscv-isa-manual
- GNU RISC-V Tools: https://github.com/riscv/riscv-gnu-toolchain

## License

Educational project for Advanced Software Engineering course.
