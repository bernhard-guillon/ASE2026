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
└── chatlog.md                # Design discussion history
```

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
